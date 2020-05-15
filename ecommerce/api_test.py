"""
Test for ecommerce functions
"""
from base64 import b64encode
from datetime import datetime
from decimal import Decimal
import hashlib
import hmac
from unittest.mock import patch

import pytest
import pytz
import factory
from rest_framework.exceptions import ValidationError

from applications.constants import AppStates
from applications.factories import BootcampApplicationFactory
from backends.pipeline_api import EdxOrgOAuth2
from ecommerce.api import (
    create_unfulfilled_order,
    generate_cybersource_sa_payload,
    generate_cybersource_sa_signature,
    get_new_order_by_reference_number,
    get_total_paid,
    is_paid_in_full,
    ISO_8601_FORMAT,
    make_reference_id,
    serialize_user_bootcamp_run,
    serialize_user_bootcamp_runs,
)
from ecommerce.exceptions import (
    EcommerceException,
    ParseException,
)
from ecommerce.factories import LineFactory, OrderFactory
from ecommerce.models import (
    Line,
    Order,
    OrderAudit,
)
from ecommerce.serializers import LineSerializer
from klasses.factories import BootcampRunFactory, InstallmentFactory
from klasses.models import Installment, PersonalPrice
from klasses.serializers import InstallmentSerializer
from profiles.factories import UserFactory, ProfileFactory


pytestmark = pytest.mark.django_db


# pylint: disable=redefined-outer-name, unused-argument
def create_purchasable_bootcamp_run():
    """Create a purchasable bootcamp run, and a user to be associated with it"""
    profile = ProfileFactory.create()
    user = profile.user
    user.social_auth.create(
        provider=EdxOrgOAuth2.name,
        uid="{}_edx".format(user.username),
    )
    installment_1 = InstallmentFactory.create(amount=200)
    InstallmentFactory.create(bootcamp_run=installment_1.bootcamp_run)
    return installment_1.bootcamp_run, user


@pytest.fixture
def bootcamp_run_and_user():
    """A pair of (bootcamp run, user)"""
    yield create_purchasable_bootcamp_run()


@pytest.fixture
def user(bootcamp_run_and_user):
    """A user with social auth"""
    _, user = bootcamp_run_and_user
    yield user


@pytest.fixture
def bootcamp_run(bootcamp_run_and_user):
    """
    Creates a purchasable bootcamp run. Bootcamp run price is at least $200, in two installments
    """
    bootcamp_run, _ = bootcamp_run_and_user
    yield bootcamp_run


def create_test_order(user, run_key, payment_amount):
    """
    Pass through arguments to create_unfulfilled_order and mock payable_bootcamp_run_keys
    """
    with patch(
        'ecommerce.api.payable_bootcamp_run_keys',
        return_value=[run_key],
    ):
        return create_unfulfilled_order(user, run_key, payment_amount)


@pytest.mark.parametrize("payment_amount", [0, -1.23])
def test_less_or_equal_to_zero(user, bootcamp_run, payment_amount):
    """
    An order may not have a negative or zero price
    """
    with pytest.raises(ValidationError) as ex:
        create_test_order(user, bootcamp_run.run_key, payment_amount)

    assert ex.value.args[0] == 'Payment is less than or equal to zero'


def test_create_order(user, bootcamp_run):
    """
    Create Order from a purchasable bootcamp run
    """
    payment = 123
    order = create_test_order(user, bootcamp_run.run_key, payment)

    assert Order.objects.count() == 1
    assert order.status == Order.CREATED
    assert order.total_price_paid == payment
    assert order.user == user

    assert order.line_set.count() == 1
    line = order.line_set.first()
    assert line.run_key == bootcamp_run.run_key
    assert line.description == 'Installment for {}'.format(bootcamp_run.title)
    assert line.price == payment

    assert OrderAudit.objects.count() == 1
    order_audit = OrderAudit.objects.first()
    assert order_audit.order == order
    assert order_audit.data_after == order.to_dict()

    # data_before only has modified_at different, since we only call save_and_log
    # after Order is already created
    data_before = order_audit.data_before
    dict_before = order.to_dict()
    del data_before['updated_on']
    del dict_before['updated_on']
    assert data_before == dict_before


def test_not_eligible_to_pay(user, bootcamp_run):
    """
    A validation error should be thrown if the user is not eligible to pay
    """
    with patch(
        'ecommerce.api.payable_bootcamp_run_keys',
        return_value=[],
    ), pytest.raises(ValidationError) as ex:
        create_unfulfilled_order(user, bootcamp_run.run_key, 123)
    assert ex.value.args[0] == "User is unable to pay for bootcamp run {}".format(bootcamp_run.run_key)


PAYMENT = 123


@pytest.fixture
def fulfilled_order(bootcamp_run, user):
    """Make a fulfilled order"""
    order = create_test_order(user, bootcamp_run.run_key, PAYMENT)
    order.status = Order.FULFILLED
    order.save()
    yield order


def test_get_total_paid(fulfilled_order, user, bootcamp_run):
    """
    get_total_paid should look through all fulfilled orders for the payment for a particular user
    """
    # Multiple payments should be added together
    next_payment = 50
    order = create_test_order(user, bootcamp_run.run_key, next_payment)
    order.status = Order.FULFILLED
    order.save()
    assert get_total_paid(user, bootcamp_run.run_key) == PAYMENT + next_payment


def test_get_total_paid_other_user(fulfilled_order, user, bootcamp_run):
    """other_user's payments shouldn't affect user"""
    other_user = UserFactory.create()
    assert get_total_paid(other_user, bootcamp_run.run_key) == 0


def test_get_total_paid_unfulfilled(fulfilled_order, user, bootcamp_run):
    """Unfulfilled orders should be ignored"""
    create_test_order(user, bootcamp_run.run_key, 45)
    assert get_total_paid(user, bootcamp_run.run_key) == PAYMENT


def test_get_total_paid_other_run(fulfilled_order, user, bootcamp_run):
    """Orders for other bootcamp runs should be ignored"""
    other_bootcamp_run, other_user = create_purchasable_bootcamp_run()
    other_order = create_test_order(other_user, other_bootcamp_run.run_key, 50)
    other_order.status = Order.FULFILLED
    other_order.save()

    assert get_total_paid(user, bootcamp_run.run_key) == PAYMENT


def test_get_total_paid_no_payments(fulfilled_order, user, bootcamp_run):
    """If there are no payments get_total_paid should return 0"""
    Order.objects.all().update(status=Order.REFUNDED)
    assert get_total_paid(user, bootcamp_run.run_key) == 0


def test_get_total_paid_app_limit(user, bootcamp_run):
    """get_total_paid should limit the Lines it counts toward the total paid if an application id is specified"""
    lines = LineFactory.create_batch(
        2,
        order__status=Order.FULFILLED,
        order__user=user,
        run_key=bootcamp_run.run_key,
        price=factory.Iterator([10, 20]),
    )
    application_ids = [line.order.application_id for line in lines]
    assert all(application_ids)
    assert get_total_paid(user, bootcamp_run.run_key, application_id=application_ids[0]) == 10
    assert get_total_paid(user, bootcamp_run.run_key, application_id=application_ids[1]) == 20


CYBERSOURCE_ACCESS_KEY = 'access'
CYBERSOURCE_PROFILE_ID = 'profile'
CYBERSOURCE_SECURITY_KEY = 'security'
CYBERSOURCE_REFERENCE_PREFIX = 'prefix'


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
    payload = {
        'x': 'y',
        'abc': 'def',
        'key': 'value',
        'signed_field_names': 'abc,x',
    }
    signature = generate_cybersource_sa_signature(payload)

    message = ','.join('{}={}'.format(key, payload[key]) for key in ['abc', 'x'])

    digest = hmac.new(
        CYBERSOURCE_SECURITY_KEY.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256,
    ).digest()

    assert b64encode(digest).decode('utf-8') == signature


def test_signed_payload(mocker, bootcamp_run, user):
    """
    A valid payload should be signed appropriately
    """
    payment = 123.45
    order = create_test_order(user, bootcamp_run.run_key, payment)
    username = 'username'
    transaction_uuid = 'hex'

    now = datetime.now(tz=pytz.UTC)
    now_mock = mocker.MagicMock(return_value=now)

    mocker.patch('ecommerce.api.get_social_username', autospec=True, return_value=username)
    mocker.patch('ecommerce.api.datetime', autospec=True, now=now_mock)
    mocker.patch('ecommerce.api.uuid.uuid4', autospec=True, return_value=mocker.MagicMock(hex=transaction_uuid))
    payload = generate_cybersource_sa_payload(order, 'dashboard_url')
    signature = payload.pop('signature')
    assert generate_cybersource_sa_signature(payload) == signature
    signed_field_names = payload['signed_field_names'].split(',')
    assert signed_field_names == sorted(payload.keys())

    assert payload == {
        'access_key': CYBERSOURCE_ACCESS_KEY,
        'amount': str(order.total_price_paid),
        'consumer_id': username,
        'currency': 'USD',
        'item_0_code': 'klass',
        'item_0_name': '{}'.format(bootcamp_run.title),
        'item_0_quantity': 1,
        'item_0_sku': '{}'.format(bootcamp_run.run_key),
        'item_0_tax_amount': '0',
        'item_0_unit_price': str(order.total_price_paid),
        'line_item_count': 1,
        'locale': 'en-us',
        'override_custom_cancel_page': 'dashboard_url?status=cancel',
        'override_custom_receipt_page': 'dashboard_url?status=receipt&order={}&award={}'.format(
            order.id, bootcamp_run.run_key
        ),
        'reference_number': make_reference_id(order),
        'profile_id': CYBERSOURCE_PROFILE_ID,
        'signed_date_time': now.strftime(ISO_8601_FORMAT),
        'signed_field_names': ','.join(signed_field_names),
        'transaction_type': 'sale',
        'transaction_uuid': transaction_uuid,
        'unsigned_field_names': '',
        'merchant_defined_data1': 'bootcamp',
        'merchant_defined_data2': '{}'.format(bootcamp_run.bootcamp.title),
        'merchant_defined_data3': 'klass',
        'merchant_defined_data4': '{}'.format(bootcamp_run.title),
        'merchant_defined_data5': '{}'.format(bootcamp_run.run_key),
        'merchant_defined_data6': 'learner',
        'merchant_defined_data7': '{}'.format(order.user.profile.name),
        'merchant_defined_data8': '{}'.format(order.user.email),
    }
    now_mock.assert_called_with(tz=pytz.UTC)


@pytest.mark.parametrize("invalid_title", ["", "<h1></h1>"])
def test_with_empty_or_html_run_title(bootcamp_run, user, invalid_title):
    """ Verify that Validation error raises if title of bootcamp run has only HTML or empty."""
    bootcamp_run.title = invalid_title
    bootcamp_run.save()
    order = create_test_order(user, bootcamp_run.run_key, '123.45')
    with pytest.raises(ValidationError) as ex:
        generate_cybersource_sa_payload(order, 'dashboard_url')

    assert ex.value.args[0] == 'Bootcamp run {run_key} title is either empty or contains only HTML.'.format(
        run_key=bootcamp_run.run_key
    )


@pytest.mark.parametrize("invalid_title", ["", "<h1></h1>"])
def test_with_empty_or_html_bootcamp_title(bootcamp_run, user, invalid_title):
    """ Verify that Validation error raises if title of bootcamp has only HTML or empty."""
    bootcamp_run.bootcamp.title = invalid_title
    bootcamp_run.bootcamp.save()
    order = create_test_order(user, bootcamp_run.run_key, '123.45')
    with pytest.raises(ValidationError) as ex:
        generate_cybersource_sa_payload(order, 'dashboard_url')

    assert ex.value.args[0] == 'Bootcamp {bootcamp_id} title is either empty or contains only HTML.'.format(
        bootcamp_id=bootcamp_run.bootcamp.id
    )


def test_make_reference_id(bootcamp_run, user):
    """
    make_reference_id should concatenate the reference prefix and the order id
    """
    order = create_test_order(user, bootcamp_run.run_key, 123)
    assert "BOOTCAMP-{}-{}".format(CYBERSOURCE_REFERENCE_PREFIX, order.id) == make_reference_id(order)


def test_get_new_order_by_reference_number(bootcamp_run, user):
    """
    get_new_order_by_reference_number returns an Order with status created
    """
    order = create_test_order(user, bootcamp_run.run_key, 123)
    same_order = get_new_order_by_reference_number(make_reference_id(order))
    assert same_order.id == order.id


@pytest.mark.parametrize("reference_number, exception_message", [
    ("XYZ-1-3", "Reference number must start with BOOTCAMP-"),
    ("BOOTCAMP-no_dashes_here", "Unable to find order number in reference number"),
    ("BOOTCAMP-something-NaN", "Unable to parse order number"),
    ("BOOTCAMP-not_matching-3", "CyberSource prefix doesn't match"),
])
def test_parse(reference_number, exception_message):
    """
    Test parse errors are handled well
    """
    with pytest.raises(ParseException) as ex:
        get_new_order_by_reference_number(reference_number)
    assert ex.value.args[0] == exception_message


def test_status(bootcamp_run, user):
    """
    get_order_by_reference_number should only get orders with status=CREATED
    """
    order = create_test_order(user, bootcamp_run.run_key, 123)
    order.status = Order.FAILED
    order.save()

    with pytest.raises(EcommerceException) as ex:
        # change order number to something not likely to already exist in database
        order.id = 98765432
        assert not Order.objects.filter(id=order.id).exists()
        get_new_order_by_reference_number(make_reference_id(order))
    assert ex.value.args[0] == "Unable to find order {}".format(order.id)


@pytest.mark.parametrize("run_price,personal_price,total_paid,expected", [
    [10, None, 5, False],
    [10, None, 10, True],
    [10, 5, 3, False],
    [10, 5, 5, True],
])  # pylint: disable=too-many-arguments
def test_is_paid_in_full(mocker, bootcamp_run, user, run_price, personal_price, total_paid, expected):
    """
    is_paid_in_full should return true if the payments match or exceed the price of the run
    """
    Installment.objects.all().delete()
    for _ in range(2):
        InstallmentFactory.create(amount=run_price/2, bootcamp_run=bootcamp_run)

    if personal_price is not None:
        PersonalPrice.objects.create(bootcamp_run=bootcamp_run, user=user, price=personal_price)

    get_total_paid_mock = mocker.patch('ecommerce.api.get_total_paid', return_value=total_paid)
    assert is_paid_in_full(bootcamp_run=bootcamp_run, user=user) is expected
    get_total_paid_mock.assert_called_once_with(run_key=bootcamp_run.run_key, user=user)


@pytest.fixture()
def test_data(mocker):
    """
    Sets up the data for all the tests in this module
    """
    profile = ProfileFactory.create()
    run_paid = BootcampRunFactory.create()
    BootcampApplicationFactory.create(bootcamp_run=run_paid, user=profile.user, state=AppStates.AWAITING_PAYMENT.value)
    run_not_paid = BootcampRunFactory.create()
    BootcampApplicationFactory.create(bootcamp_run=run_not_paid, user=profile.user, state=AppStates.AWAITING_PAYMENT.value)

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
        "is_user_eligible_to_pay": True,
        "total_paid": Decimal('627.34'),
        "payments": LineSerializer(Line.for_user_bootcamp_run(user, run_paid.run_key), many=True).data,
        "installments": InstallmentSerializer(
            run_paid.installment_set.order_by('deadline'), many=True).data,
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
        "is_user_eligible_to_pay": True,
        "total_paid": Decimal('0.00'),
        "payments": [],
        "installments": InstallmentSerializer(
            run_not_paid.installment_set.order_by('deadline'), many=True).data,
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
            "is_user_eligible_to_pay": True,
            "total_paid": Decimal('627.34'),
            "payments": LineSerializer(Line.for_user_bootcamp_run(user, run_paid.run_key), many=True).data,
            "installments": InstallmentSerializer(
                run_paid.installment_set.order_by('deadline'), many=True).data,
        },
        {
            "run_key": run_not_paid.run_key,
            "bootcamp_run_name": run_not_paid.title,
            "display_title": run_not_paid.display_title,
            "start_date": run_not_paid.start_date,
            "end_date": run_not_paid.end_date,
            "price": run_not_paid.price,
            "is_user_eligible_to_pay": True,
            "total_paid": Decimal('0.00'),
            "payments": [],
            "installments": InstallmentSerializer(
                run_not_paid.installment_set.order_by('deadline'), many=True).data,
        }
    ]
    assert sorted(expected_ret, key=lambda x: x['run_key']) == serialize_user_bootcamp_runs(user)


def test_serialize_user_bootcamp_runs_paid_not_payable(test_data, mocker):
    """
    Test for serialize_user_bootcamp_runs in case the user is not eligible to pay but she has already paid for the
    bootcamp run
    """
    user, run_paid, run_not_paid = test_data
    mocker.patch(
        'ecommerce.api.payable_bootcamp_run_keys',
        return_value=[run_not_paid.run_key],
    )
    res = serialize_user_bootcamp_runs(user)
    assert run_paid.run_key in [bootcamp_run['run_key'] for bootcamp_run in res]
    for bootcamp_run in res:
        if bootcamp_run['run_key'] == run_paid.run_key:
            break
    assert bootcamp_run['is_user_eligible_to_pay'] is False  # pylint: disable=undefined-loop-variable
