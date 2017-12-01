"""Views for fluidreview"""
from rest_framework.response import Response
from rest_framework.views import APIView

from fluidreview.permissions import WebhookPermission
from fluidreview.models import WebhookRequest


class WebhookView(APIView):
    """
    Handle webhooks coming from FluidReview
    """
    permission_classes = (WebhookPermission,)
    authentication_classes = ()

    def post(self, request):
        """Store webhook request for later processing"""
        WebhookRequest.objects.create(body=request.body)
        return Response()