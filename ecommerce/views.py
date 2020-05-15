"""Views for ecommerce"""
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status as statuses
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from backends.edxorg import EdxOrgOAuth2
from ecommerce.api import (
    complete_successful_order,
    create_unfulfilled_order,
    generate_cybersource_sa_payload,
    get_new_order_by_reference_number,
    handle_rejected_order,
    serialize_user_bootcamp_run,
    serialize_user_bootcamp_runs,
)
from ecommerce.constants import (
    CYBERSOURCE_DECISION_ACCEPT,
    CYBERSOURCE_DECISION_CANCEL,
)
from ecommerce.exceptions import EcommerceException
from ecommerce.models import (
    Line,
    Order,
    Receipt,
)
from ecommerce.permissions import IsSignedByCyberSource
from ecommerce.serializers import PaymentSerializer
from hubspot.task_helpers import sync_hubspot_deal_from_order
from klasses.models import BootcampRun
from klasses.permissions import CanReadIfSelf
from main.serializers import serialize_maybe_user


log = logging.getLogger(__name__)
User = get_user_model()


class PaymentView(CreateAPIView):
    """
    View for payment API. This creates an Order in our system and provides a dictionary to send to Cybersource.
    """
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentSerializer

    def post(self, request, *args, **kwargs):
        """
        Create an unfulfilled order and return a response for it.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment_amount = Decimal(serializer.data['payment_amount'])
        run_key = serializer.data['run_key']

        order = create_unfulfilled_order(self.request.user, run_key, payment_amount)

        # Sync order data with hubspot
        sync_hubspot_deal_from_order(order)

        redirect_url = self.request.build_absolute_uri(reverse('pay'))

        return Response({
            'payload': generate_cybersource_sa_payload(order, redirect_url),
            'url': settings.CYBERSOURCE_SECURE_ACCEPTANCE_URL,
        })


class OrderFulfillmentView(APIView):
    """
    View for order fulfillment API. This API is special in that only CyberSource should talk to it.
    Instead of authenticating with OAuth or via session this looks at the signature of the message
    to verify authenticity.
    """

    authentication_classes = ()
    permission_classes = (IsSignedByCyberSource, )

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Confirmation from CyberSource which fulfills an existing Order.
        """
        # First, save this information in a receipt
        receipt = Receipt.objects.create(data=request.data)

        # Link the order with the receipt if we can parse it
        reference_number = request.data['req_reference_number']
        order = get_new_order_by_reference_number(reference_number)
        receipt.order = order
        receipt.save()

        decision = request.data['decision']
        if order.status == Order.FAILED and decision == CYBERSOURCE_DECISION_CANCEL:
            # This is a duplicate message, ignore since it's already handled
            return Response(status=statuses.HTTP_200_OK)
        elif order.status != Order.CREATED:
            raise EcommerceException("Order {} is expected to have status 'created'".format(order.id))

        if decision != CYBERSOURCE_DECISION_ACCEPT:
            handle_rejected_order(order=order, decision=decision)
        else:
            complete_successful_order(order)

        # Sync order data with hubspot
        sync_hubspot_deal_from_order(order)

        # The response does not matter to CyberSource
        return Response(status=statuses.HTTP_200_OK)


class UserBootcampRunDetail(GenericAPIView):
    """
    Class based view for user bootcamp run view.
    """
    authentication_classes = (
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        CanReadIfSelf,
    )
    lookup_field = "run_key"
    lookup_url_kwarg = "run_key"
    queryset = BootcampRun.objects.all()

    def get(self, request, username, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a serialized bootcamp run and payment for a user
        """
        user = get_object_or_404(
            User,
            social_auth__uid=username,
            social_auth__provider=EdxOrgOAuth2.name
        )
        bootcamp_run = self.get_object()
        return Response(serialize_user_bootcamp_run(user=user, bootcamp_run=bootcamp_run))


class UserBootcampRunStatement(RetrieveAPIView):
    """
    View class for a user's bootcamp run payment statement
    """
    authentication_classes = (
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
    )
    lookup_field = "run_key"
    lookup_url_kwarg = "run_key"
    queryset = BootcampRun.objects.all()
    renderer_classes = (TemplateHTMLRenderer,)

    def get(self, request, *args, **kwargs):
        """
        Fetches a user's bootcamp run payment information and renders their statement
        (or raises a 404 if they have no payments for the specified bootcamp run)
        """
        bootcamp_run = self.get_object()
        if Line.for_user_bootcamp_run(request.user, bootcamp_run.run_key).count() == 0:
            raise Http404
        return Response(
            {
                "user": serialize_maybe_user(request.user),
                "bootcamp_run": serialize_user_bootcamp_run(user=request.user, bootcamp_run=bootcamp_run)
            },
            template_name='bootcamp/statement.html'
        )


class UserBootcampRunList(APIView):
    """
    Class based view for user bootcamp run list view.
    """
    authentication_classes = (
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        CanReadIfSelf,
    )

    def get(self, request, username, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns serialized bootcamp runs and payments for all runs that a user can pay for.
        """
        user = get_object_or_404(
            User,
            social_auth__uid=username,
            social_auth__provider=EdxOrgOAuth2.name
        )

        return Response(serialize_user_bootcamp_runs(user=user))
