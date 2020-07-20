"""
Test for ecommerce functions
"""
from base64 import b64encode
from datetime import datetime
from decimal import Decimal
import hashlib
import hmac

from django.core.mail import EmailMessage
import pytest
import pytz
from rest_framework.exceptions import ValidationError

from applications.constants import AppStates
from applications.factories import BootcampApplicationFactory
from applications.models import BootcampApplication
from ecommerce.api import (
    generate_cybersource_sa_payload,
    generate_cybersource_sa_signature,
    get_new_order_by_reference_number,
    ISO_8601_FORMAT,
    make_reference_id,
    serialize_user_bootcamp_run,
    serialize_user_bootcamp_runs,
    send_receipt_email,
    create_refund_order,
    complete_successful_order,
    process_refund,
)
from ecommerce.exceptions import EcommerceException, ParseException
from ecommerce.factories import LineFactory, OrderFactory
from ecommerce.models import Line, Order
from ecommerce.serializers import LineSerializer
from ecommerce.test_utils import create_test_application, create_test_order
from klasses.constants import ENROLL_CHANGE_STATUS_REFUNDED
from klasses.factories import (
    BootcampRunFactory,
    InstallmentFactory,
    BootcampRunEnrollmentFactory,
)
from klasses.models import BootcampRunEnrollment
from klasses.serializers import InstallmentSerializer
from main.test_utils import any_instance_of
from profiles.factories import ProfileFactory


pytestmark = pytest.mark.django_db


# pylint: disable=redefined-outer-name, unused-argument
@pytest.fixture
def application():
    """An application for testing"""
    yield create_test_application()


@pytest.fixture
def user(application):
    """A user with social auth"""
    yield application.user


@pytest.fixture
def bootcamp_run(application):
    """
    Creates a purchasable bootcamp run. Bootcamp run price is at least $200, in two installments
    """
    yield application.bootcamp_run


@pytest.mark.parametrize("payment_amount", [0, -1.23])
def test_less_or_equal_to_zero(application, payment_amount):
    """
    An order may not have a negative or zero price
    """
    with pytest.raises(ValidationError) as ex:
        create_test_order(application, payment_amount, fulfilled=False)

    assert ex.value.args[0] == "Payment is less than or equal to zero"


CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
CYBERSOURCE_REFERENCE_PREFIX = "prefix"


@pytest.fixture(autouse=True)
def cybersource_settings(settings):
    """
    Set some Cybersource settings
    """
    settings.CYBERSOURCE_ACCESS_KEY = CYBERSOURCE_ACCESS_KEY
    settings.CYBERSOURCE_PROFILE_ID = CYBERSOURCE_PROFILE_ID
    settings.CYBERSOURCE_SECURITY_KEY = CYBERSOURCE_SECURITY_KEY
    settings.CYBERSOURCE_REFERENCE_PREFIX = CYBERSOURCE_REFERENCE_PREFIX


def test_valid_signature():
    """
    Signature is made up of a ordered key value list signed using HMAC 256 with a security key
    """
    payload = {"x": "y", "abc": "def", "key": "value", "signed_field_names": "abc,x"}
    signature = generate_cybersource_sa_signature(payload)

    message = ",".join("{}={}".format(key, payload[key]) for key in ["abc", "x"])

    digest = hmac.new(
        CYBERSOURCE_SECURITY_KEY.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    assert b64encode(digest).decode("utf-8") == signature


def test_signed_payload(mocker, application, bootcamp_run):
    """
    A valid payload should be signed appropriately
    """
    payment = 123.45
    order = create_test_order(application, payment, fulfilled=False)
    transaction_uuid = "hex"

    now = datetime.now(tz=pytz.UTC)
    now_mock = mocker.MagicMock(return_value=now)

    mocker.patch("ecommerce.api.datetime", autospec=True, now=now_mock)
    mocker.patch(
        "ecommerce.api.uuid.uuid4",
        autospec=True,
        return_value=mocker.MagicMock(hex=transaction_uuid),
    )
    payload = generate_cybersource_sa_payload(order, "dashboard_url")
    signature = payload.pop("signature")
    assert generate_cybersource_sa_signature(payload) == signature
    signed_field_names = payload["signed_field_names"].split(",")
    assert signed_field_names == sorted(payload.keys())

    assert payload == {
        "access_key": CYBERSOURCE_ACCESS_KEY,
        "amount": str(order.total_price_paid),
        "currency": "USD",
        "item_0_code": "klass",
        "item_0_name": "{}".format(bootcamp_run.title),
        "item_0_quantity": 1,
        "item_0_sku": "{}".format(bootcamp_run.run_key),
        "item_0_tax_amount": "0",
        "item_0_unit_price": str(order.total_price_paid),
        "line_item_count": 1,
        "locale": "en-us",
        "override_custom_cancel_page": "dashboard_url?status=cancel",
        "override_custom_receipt_page": "dashboard_url?status=receipt&order={}&award={}".format(
            order.id, bootcamp_run.run_key
        ),
        "reference_number": make_reference_id(order),
        "profile_id": CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now.strftime(ISO_8601_FORMAT),
        "signed_field_names": ",".join(signed_field_names),
        "transaction_type": "sale",
        "transaction_uuid": transaction_uuid,
        "unsigned_field_names": "",
        "merchant_defined_data1": "bootcamp",
        "merchant_defined_data2": "{}".format(bootcamp_run.bootcamp.title),
        "merchant_defined_data3": "klass",
        "merchant_defined_data4": "{}".format(bootcamp_run.title),
        "merchant_defined_data5": "{}".format(bootcamp_run.run_key),
        "merchant_defined_data6": "learner",
        "merchant_defined_data7": "{}".format(order.user.profile.name),
        "merchant_defined_data8": "{}".format(order.user.email),
    }
    now_mock.assert_called_with(tz=pytz.UTC)


@pytest.mark.parametrize("invalid_title", ["", "<h1></h1>"])
def test_with_empty_or_html_run_title(application, bootcamp_run, invalid_title):
    """ Verify that Validation error raises if title of bootcamp run has only HTML or empty."""
    bootcamp_run.title = invalid_title
    bootcamp_run.save()
    order = create_test_order(application, "123.45", fulfilled=False)
    with pytest.raises(ValidationError) as ex:
        generate_cybersource_sa_payload(order, "dashboard_url")

    assert ex.value.args[
        0
    ] == "Bootcamp run {run_key} title is either empty or contains only HTML.".format(
        run_key=bootcamp_run.run_key
    )


@pytest.mark.parametrize("invalid_title", ["", "<h1></h1>"])
def test_with_empty_or_html_bootcamp_title(application, bootcamp_run, invalid_title):
    """ Verify that Validation error raises if title of bootcamp has only HTML or empty."""
    bootcamp_run.bootcamp.title = invalid_title
    bootcamp_run.bootcamp.save()
    order = create_test_order(application, "123.45", fulfilled=False)
    with pytest.raises(ValidationError) as ex:
        generate_cybersource_sa_payload(order, "dashboard_url")

    assert ex.value.args[
        0
    ] == "Bootcamp {bootcamp_id} title is either empty or contains only HTML.".format(
        bootcamp_id=bootcamp_run.bootcamp.id
    )


def test_make_reference_id(application):
    """
    make_reference_id should concatenate the reference prefix and the order id
    """
    order = create_test_order(application, 123, fulfilled=False)
    assert "BOOTCAMP-{}-{}".format(
        CYBERSOURCE_REFERENCE_PREFIX, order.id
    ) == make_reference_id(order)


def test_get_new_order_by_reference_number(application):
    """
    get_new_order_by_reference_number returns an Order with status created
    """
    order = create_test_order(application, 123, fulfilled=False)
    same_order = get_new_order_by_reference_number(make_reference_id(order))
    assert same_order.id == order.id


@pytest.mark.parametrize(
    "reference_number, exception_message",
    [
        ("XYZ-1-3", "Reference number must start with BOOTCAMP-"),
        ("BOOTCAMP-no_dashes_here", "Unable to find order number in reference number"),
        ("BOOTCAMP-something-NaN", "Unable to parse order number"),
        ("BOOTCAMP-not_matching-3", "CyberSource prefix doesn't match"),
    ],
)
def test_parse(reference_number, exception_message):
    """
    Test parse errors are handled well
    """
    with pytest.raises(ParseException) as ex:
        get_new_order_by_reference_number(reference_number)
    assert ex.value.args[0] == exception_message


def test_status(application):
    """
    get_order_by_reference_number should only get orders with status=CREATED
    """
    order = create_test_order(application, 123, fulfilled=False)
    order.status = Order.FAILED
    order.save()

    with pytest.raises(EcommerceException) as ex:
        # change order number to something not likely to already exist in database
        order.id = 98_765_432
        assert not Order.objects.filter(id=order.id).exists()
        get_new_order_by_reference_number(make_reference_id(order))
    assert ex.value.args[0] == "Unable to find order {}".format(order.id)


@pytest.fixture()
def test_data():
    """
    Sets up the data for all the tests in this module
    """
    profile = ProfileFactory.create()
    run_paid = BootcampRunFactory.create()
    BootcampApplicationFactory.create(
        bootcamp_run=run_paid, user=profile.user, state=AppStates.AWAITING_PAYMENT.value
    )
    run_not_paid = BootcampRunFactory.create()
    BootcampApplicationFactory.create(
        bootcamp_run=run_not_paid,
        user=profile.user,
        state=AppStates.AWAITING_PAYMENT.value,
    )

    InstallmentFactory.create(bootcamp_run=run_paid)
    InstallmentFactory.create(bootcamp_run=run_not_paid)

    order = OrderFactory.create(user=profile.user, status=Order.FULFILLED)
    LineFactory.create(order=order, run_key=run_paid.run_key, price=627.34)

    return profile.user, run_paid, run_not_paid


def test_serialize_user_run_paid(test_data):
    """
    Test for serialize_user_bootcamp_run for a paid bootcamp run
    """
    user, run_paid, _ = test_data

    expected_ret = {
        "run_key": run_paid.run_key,
        "bootcamp_run_name": run_paid.title,
        "display_title": run_paid.display_title,
        "start_date": run_paid.start_date,
        "end_date": run_paid.end_date,
        "price": run_paid.personal_price(user),
        "total_paid": Decimal("627.34"),
        "payments": LineSerializer(
            Line.for_user_bootcamp_run(user, run_paid.run_key), many=True
        ).data,
        "installments": InstallmentSerializer(
            run_paid.installment_set.order_by("deadline"), many=True
        ).data,
    }
    assert expected_ret == serialize_user_bootcamp_run(user, run_paid)


def test_serialize_user_run_not_paid(test_data):
    """
    Test for serialize_user_bootcamp_run for a not paid bootcamp run
    """
    user, _, run_not_paid = test_data

    expected_ret = {
        "run_key": run_not_paid.run_key,
        "bootcamp_run_name": run_not_paid.title,
        "display_title": run_not_paid.display_title,
        "start_date": run_not_paid.start_date,
        "end_date": run_not_paid.end_date,
        "price": run_not_paid.personal_price(user),
        "total_paid": Decimal("0.00"),
        "payments": [],
        "installments": InstallmentSerializer(
            run_not_paid.installment_set.order_by("deadline"), many=True
        ).data,
    }
    assert expected_ret == serialize_user_bootcamp_run(user, run_not_paid)


def test_serialize_user_bootcamp_runs(test_data):
    """
    Test for serialize_user_bootcamp_runs in normal case
    """
    user, run_paid, run_not_paid = test_data
    expected_ret = [
        {
            "run_key": run_paid.run_key,
            "bootcamp_run_name": run_paid.title,
            "display_title": run_paid.display_title,
            "start_date": run_paid.start_date,
            "end_date": run_paid.end_date,
            "price": run_paid.price,
            "total_paid": Decimal("627.34"),
            "payments": LineSerializer(
                Line.for_user_bootcamp_run(user, run_paid.run_key), many=True
            ).data,
            "installments": InstallmentSerializer(
                run_paid.installment_set.order_by("deadline"), many=True
            ).data,
        },
        {
            "run_key": run_not_paid.run_key,
            "bootcamp_run_name": run_not_paid.title,
            "display_title": run_not_paid.display_title,
            "start_date": run_not_paid.start_date,
            "end_date": run_not_paid.end_date,
            "price": run_not_paid.price,
            "total_paid": Decimal("0.00"),
            "payments": [],
            "installments": InstallmentSerializer(
                run_not_paid.installment_set.order_by("deadline"), many=True
            ).data,
        },
    ]
    assert sorted(
        expected_ret, key=lambda x: x["run_key"]
    ) == serialize_user_bootcamp_runs(user)


def test_send_verify_email_change_email(mocker, user):
    """Test send_receipt_email sends a receipt email"""
    application = BootcampApplicationFactory.create()
    OrderFactory.create(
        application=application, user=application.user, status=Order.FULFILLED
    )

    send_messages_mock = mocker.patch("mail.v2.api.send_messages")

    send_receipt_email(application.id)

    send_messages_mock.assert_called_once_with([any_instance_of(EmailMessage)])

    email = send_messages_mock.call_args[0][0][0]
    assert application.bootcamp_run.title in email.body


@pytest.mark.parametrize("has_enrollment", [True, False])
@pytest.mark.parametrize("has_application", [True, False])
def test_refund_enrollment(has_enrollment, has_application, user):
    """
    Test that deactivate_run_enrollment creates a refund order and
    updates enrollment and application objects
    """
    bootcamp_run = BootcampRunFactory.create()
    if has_enrollment:
        BootcampRunEnrollmentFactory.create(bootcamp_run=bootcamp_run, user=user)
    application = (
        BootcampApplicationFactory.create(
            user=user, bootcamp_run=bootcamp_run, state=AppStates.COMPLETE
        )
        if has_application
        else None
    )
    refund_amount = 1.50
    LineFactory.create(
        price=3,
        run_key=bootcamp_run.run_key,
        order=OrderFactory(
            user=user,
            application=application,
            status=Order.FULFILLED,
            total_price_paid=3,
        ),
    )
    process_refund(user=user, bootcamp_run=bootcamp_run, amount=refund_amount)
    if has_enrollment:
        updated_enrollment = BootcampRunEnrollment.objects.get(
            user=user, bootcamp_run=bootcamp_run
        )
        assert updated_enrollment.active is False
        assert updated_enrollment.change_status == ENROLL_CHANGE_STATUS_REFUNDED
    else:
        assert (
            BootcampRunEnrollment.objects.filter(
                user=user, bootcamp_run=bootcamp_run
            ).first()
            is None
        )
    order = Order.objects.get(
        total_price_paid=-refund_amount, application=application, user=user
    )
    assert order.status == Order.FULFILLED
    assert Line.objects.filter(
        order=order,
        run_key=bootcamp_run.run_key,
        price=-refund_amount,
        description="Refund for {}".format(bootcamp_run.title),
    ).exists()
    if has_application:
        assert (
            BootcampApplication.objects.get(id=application.id).state
            == AppStates.REFUNDED.value
        )


@pytest.mark.parametrize("has_application", [True, False])
def test_refund_exceeds_payment(has_application, user):
    """
    Test that refunded amount cannot exceed total paid
    """
    bootcamp_run = BootcampRunFactory.create()
    application = (
        BootcampApplicationFactory.create(
            user=user, bootcamp_run=bootcamp_run, state=AppStates.COMPLETE
        )
        if has_application
        else None
    )
    # Create 3 orders totalling $30 in payments
    orders = OrderFactory.create_batch(
        3,
        user=user,
        application=application,
        status=Order.FULFILLED,
        total_price_paid=10,
    )
    for order in orders:
        LineFactory.create(price=10, run_key=bootcamp_run.run_key, order=order)

    with pytest.raises(EcommerceException) as exc:
        process_refund(user=user, bootcamp_run=bootcamp_run, amount=45.50)
    assert exc.value.args[0] == "Refund exceeds total payment of $30.00"
    process_refund(user=user, bootcamp_run=bootcamp_run, amount=11)
    process_refund(user=user, bootcamp_run=bootcamp_run, amount=11)
    with pytest.raises(EcommerceException) as exc:
        process_refund(user=user, bootcamp_run=bootcamp_run, amount=11)
    assert exc.value.args[0] == "Refund exceeds total payment of $8.00"


@pytest.mark.parametrize("amount", [-5, 0])
def test_bad_refund_amount(amount):
    """ Test that an invalid refund amount raises an exception"""
    enrollment = BootcampRunEnrollmentFactory.create()
    with pytest.raises(EcommerceException) as exc:
        create_refund_order(
            user=enrollment.user, bootcamp_run=enrollment.bootcamp_run, amount=amount
        )
    assert exc.value.args[0] == "Amount to refund must be greater than zero"


@pytest.mark.parametrize("enrollment_exists", [True, False])
def test_complete_successful_order(enrollment_exists):
    """Test that enrollment, application values updated correctly on successful order"""
    installment = InstallmentFactory.create()
    application = BootcampApplicationFactory.create(
        bootcamp_run=installment.bootcamp_run, state=AppStates.AWAITING_PAYMENT
    )
    order = OrderFactory.create(
        status=Order.CREATED,
        total_price_paid=installment.amount,
        application=application,
        user=application.user,
    )
    LineFactory.create(
        order=order, price=installment.amount, run_key=application.bootcamp_run.run_key
    )
    if enrollment_exists:
        BootcampRunEnrollmentFactory.create(
            user=order.user,
            bootcamp_run=application.bootcamp_run,
            active=False,
            change_status=ENROLL_CHANGE_STATUS_REFUNDED,
        )
    complete_successful_order(order)
    assert (
        BootcampApplication.objects.get(id=application.id).state
        == AppStates.COMPLETE.value
    )
    enrollment = BootcampRunEnrollment.objects.get(
        user=application.user, bootcamp_run=application.bootcamp_run
    )
    assert enrollment.active is True
    assert enrollment.change_status is None
