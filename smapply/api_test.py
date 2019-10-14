"""
SMApply Backend Tests
"""
import datetime
import json

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from django.conf import settings
from requests import HTTPError

from ecommerce.factories import OrderFactory, LineFactory
from ecommerce.models import Order
from fluidreview.constants import WebhookParseStatus
from fluidreview.utils import utc_now
from klasses.factories import KlassFactory, InstallmentFactory
from klasses.models import Bootcamp, Klass, PersonalPrice
from profiles.factories import UserFactory, ProfileFactory
from profiles.models import Profile
from smapply.factories import OAuthTokenSMAFactory, WebhookRequestSMAFactory
from smapply.api import SMApplyAPI, BASE_API_URL, process_user, parse_webhook, list_users, post_payment, \
    SMApplyException, DEMOGRAPHICS_TASK_NAME
from smapply.models import OAuthTokenSMA, WebhookRequestSMA

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name

sma_user = {
    'id': 21231,
    'email': 'sma_user@sma.xyz',
    'first_name': 'Fluid',
    'last_name': 'User'
}


@pytest.fixture()
def mock_user_sync(mocker):
    """ Yield a mock hubspot update task for contacts """
    yield mocker.patch("hubspot.task_helpers.sync_hubspot_user")


@pytest.fixture()
def mock_product_sync(mocker):
    """ Yield a mock hubspot update task for products """
    yield mocker.patch("hubspot.task_helpers.sync_hubspot_product")


@pytest.fixture()
def mock_deal_sync(mocker):
    """ Yield a mock hubspot update task for deals """
    yield mocker.patch("hubspot.task_helpers.sync_hubspot_deal")


class MockGet:
    """
    Helper class to mock multiple SMApply api get requests.
    """
    def __init__(self, key_pairs):
        self.key_pairs = key_pairs

    def mocked_api_get(self, *args):
        """Mock function to replace .get()"""

        class MockResponse:
            """Mocked response with json function"""
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code

            def json(self):
                """return json"""
                return self.json_data

        for key, value in self.key_pairs.items():
            if args[0] == key:
                return MockResponse(value, 200)
        return MockResponse(None, 500)


@pytest.fixture()
def test_payment_data():
    """
    Sets up the data for payment tests in this module
    """
    klass = KlassFactory()
    profile = ProfileFactory(smapply_id=1)
    InstallmentFactory(klass=klass)
    order = OrderFactory(user=profile.user, status=Order.FULFILLED)
    LineFactory.create(order=order, klass_key=klass.klass_key, price=11.38)
    webhook = WebhookRequestSMAFactory(
        award_id=klass.klass_key, status=WebhookParseStatus.SUCCEEDED, user_id=profile.smapply_id, submission_id=1
    )

    return klass, order, webhook


def test_get_token_from_settings(settings):
    """ Test that the SMApplyAPI instance token is initially based off settings"""
    settings.SMAPPLY_ACCESS_TOKEN = 'fakeaccesstoken'
    settings.SMAPPLY_REFRESH_TOKEN = 'fakerefreshtoken'
    smapi = SMApplyAPI()
    token = smapi.get_token()
    assert token['access_token'] == settings.SMAPPLY_ACCESS_TOKEN
    assert token['refresh_token'] == settings.SMAPPLY_REFRESH_TOKEN


def test_get_token_from_database():
    """ Test that a SMApplyAPI instance token is retrieved from the database if it exists"""
    dbtoken = OAuthTokenSMAFactory(expires_on=utc_now())
    smapi = SMApplyAPI()
    token = smapi.get_token()
    assert token['access_token'] == dbtoken.access_token
    assert token['refresh_token'] == dbtoken.refresh_token


def test_save_token_new():
    """Test that the save_token method correctly creates a new OAuthTokenSMA in the database"""
    assert OAuthTokenSMA.objects.first() is None
    response_token = {
        'access_token': 'fakeaccesstoken',
        'refresh_token': 'fakerefreshtoken',
        'expires_in': 1000,
        'token_type': 'faketype'
    }
    smapi = SMApplyAPI()
    now = utc_now()
    new_token = smapi.save_token(response_token)
    for attr in ['access_token', 'refresh_token', 'token_type']:
        assert response_token[attr] == getattr(new_token, attr)
        assert response_token[attr] == new_token.json[attr]
    # Ensure expires_on, expires_in values are close to expected value
    assert now + datetime.timedelta(seconds=985) <= new_token.expires_on <= now + datetime.timedelta(seconds=1000)
    assert 985 <= new_token.json['expires_in'] < 1000


def test_save_token_update():
    """Test that the save_token method correctly updates an existing OAuthTokenSMA in the database"""
    initial_token = OAuthTokenSMAFactory(
        expires_on=utc_now() - datetime.timedelta(seconds=7200),
        access_token='oldaccess',
        refresh_token='oldrefresh'
    )
    response_token = {
        'access_token': 'fakeaccesstoken',
        'refresh_token': 'fakerefreshtoken',
        'expires_in': 7200,
        'token_type': 'faketype'
    }
    base_attrs = ['access_token', 'refresh_token', 'token_type']
    smapi = SMApplyAPI()
    for attr in base_attrs:
        assert getattr(initial_token, attr) == smapi.session.token[attr]
    smapi.save_token(response_token)
    smapi.session = smapi.initialize_session()
    for attr in base_attrs:
        assert response_token[attr] == smapi.session.token[attr]
    # Ensure expires_in is close to expected value
    assert 7185 <= smapi.session.token['expires_in'] <= 7200


@override_settings(SMAPPLY_BASE_URL="http://test.bootcamp.zzz")
@pytest.mark.parametrize(['method', 'url', 'full_url', 'kwargs'], [
    ['get', 'users', '{}users', {}],
    ['get', '/users', '{}users', {}],
    ['get', '/users?testing=true', '{}users?testing=true', {}],
    ['put', 'installments/2', '{}installments/2', {'data': {'transaction': 1}}],
    ['post', 'transactions', '{}transactions', {'data': {'application': 3}}]
])
def test_oauth_requests(mocker, method, url, full_url, kwargs):
    """Test that OAuth2Session calls the correct request method with correct arguments"""
    mock_oauth = mocker.patch('smapply.api.OAuth2Session.{}'.format(method))
    SMApplyAPI().request(method, url, **kwargs)
    mock_oauth.assert_called_once_with(full_url.format(BASE_API_URL), **kwargs)


@pytest.mark.parametrize(['method', 'url', 'kwargs'], [
    ['get', 'users', {}],
    ['put', 'installments/2', {'data': {'transaction': 1}}],
    ['post', 'transactions', {'data': {'application': 3}}]
])
def test_api_requests(mocker, method, url, kwargs):
    """Test that SMApplyAPI.request method gets called with the correct arguments"""
    mock_request = mocker.patch('smapply.api.SMApplyAPI.request')
    smapi = SMApplyAPI()
    getattr(smapi, method)(url, **kwargs)
    mock_request.assert_called_once_with(method, url, **kwargs)


def test_api_request_invalid_token(mocker):
    """Test that a request will be tried 2x and the session reinitialized if the tokens are no longer valid"""
    mock_session = mocker.patch('smapply.api.OAuth2Session')
    mock_init = mocker.patch('smapply.api.SMApplyAPI.initialize_session', return_value=mock_session)
    mock_session.get.return_value.status_code = 401
    smapi = SMApplyAPI()
    smapi.get('users')
    assert mock_session.get.call_count == 2
    assert mock_init.call_count == 2


def test_process_new_user():
    """Test that a new user and profile are successfully created"""
    assert User.objects.filter(email=sma_user['email']).first() is None
    assert Profile.objects.filter(smapply_id=sma_user['id']).first() is None
    process_user(sma_user)
    assert User.objects.filter(email=sma_user['email']).count() == 1
    new_profile = Profile.objects.get(smapply_id=sma_user["id"])
    assert new_profile.name == '{} {}'.format(sma_user['first_name'], sma_user['last_name'])
    assert new_profile.user.email == sma_user['email']


def test_process_new_profile():
    """Test that a new profile is successfully created for an existing user"""
    UserFactory(email=sma_user['email'], username='sma_user')
    assert User.objects.filter(email=sma_user['email']).first().username == 'sma_user'
    assert Profile.objects.filter(smapply_id=sma_user['id']).first() is None
    process_user(sma_user)
    assert User.objects.filter(email=sma_user['email']).count() == 1
    assert Profile.objects.filter(smapply_id=sma_user['id']).count() == 1


def test_process_both_exist_no_smapply_id(mocker):
    """Test that no changes are made to an existing user but existing profile is saved with smapply id"""
    ProfileFactory(
        user=UserFactory(email=sma_user['email'].upper(), username=sma_user['email']),
        smapply_id=None,
        fluidreview_id=78690,
    )
    mock_create_user = mocker.patch('smapply.api.User.objects.create')
    process_user(sma_user)
    mock_create_user.assert_not_called()
    assert Profile.objects.filter(smapply_id=sma_user['id']).count() == 1


def test_process_user_both_exist_with_smapply_id(mocker):
    """Test that no changes are made to an existing user and profile with smapply id"""
    ProfileFactory(
        user=UserFactory(email=sma_user['email'].upper(), username=sma_user['email']),
        smapply_id=1
    )
    mock_create_user = mocker.patch('smapply.api.User.objects.create')
    mock_save_profile = mocker.patch('smapply.api.Profile.save')
    process_user(sma_user)
    mock_create_user.assert_not_called()
    mock_save_profile.assert_not_called()


@pytest.mark.parametrize(['price', 'sends_email'], [
    ['25.99', True],
    ['', False]
])
# pylint: disable=too-many-arguments
def test_parse_webhook_user(mocker, price, sends_email, mock_user_sync, mock_deal_sync, mock_product_sync):
    """Test creation of new Bootcamp if no matching award_id"""
    user_id = 94379385
    award_id = 78456
    submission_id = 4533767
    award_name = "Best monkey prize"
    ProfileFactory(smapply_id=user_id)
    send_email = mocker.patch('smapply.api.MailgunClient.send_individual_email')
    data = {
        'user_id': user_id,
        'id': submission_id,
        'award': award_id,
        'award_title': 'TEST CAMP'
    }
    body = json.dumps(data)
    hook = WebhookRequestSMA(body=body)

    mock_get = MockGet({
        f'/applications/{submission_id}/': {
            'id': submission_id,
            'current_stage': {'id': 1234, 'title': 'Admitted'},
            'custom_fields': [{
                'id': settings.SMAPPLY_AMOUNT_TO_PAY_ID,
                'value': price
            }]
        },
        f'applications/{submission_id}/tasks': {
            'results': {},
            'next': None,
        },
        f'/programs/{award_id}': {
            'id': award_id,
            'name': award_name,
        }
    })
    mocker.patch('smapply.api.SMApplyAPI.get', side_effect=mock_get.mocked_api_get)
    parse_webhook(hook)
    if sends_email:
        assert hook.status == WebhookParseStatus.SUCCEEDED
        assert Klass.objects.filter(title=award_name).exists()
        assert Bootcamp.objects.filter(title=award_name).exists()
        assert PersonalPrice.objects.filter(
            klass__klass_key=award_id,
            user__profile__smapply_id=user_id,
            application_stage='Admitted'
        ).exists()
        assert send_email.call_count == 1
        assert send_email.call_args[0] == (
            "Klass and Bootcamp {award_name} was created".format(award_name=award_name),
            "Klass and Bootcamp {award_name} was created, for klass_key {klass_key} at {url}".format(
                award_name=award_name,
                klass_key=award_id,
                url=settings.BOOTCAMP_ECOMMERCE_BASE_URL
            ),
            'support@example.com',
        )
        mock_user_sync.assert_called_once()
        mock_deal_sync.assert_called_once()
        mock_product_sync.assert_called_once()
    else:
        assert hook.status == WebhookParseStatus.FAILED
        assert send_email.call_count == 0
        mock_user_sync.assert_called_once()
        mock_deal_sync.assert_not_called()
        mock_product_sync.assert_not_called()


@pytest.mark.parametrize('body', [
    '',
    'hello world',
    '{"user_id": "", "award": 1, "id": 1}',
    '{"user_id": null, "award": 1, "id": 1}',
    '{"user_id": 94379385, "award": "a", "id": 1}',
])
def test_parse_failure(mocker, body, mock_user_sync, mock_deal_sync, mock_product_sync):
    """Test that a webhookrequest's status is set to FAILED if it cannot be parsed"""
    mock_api = mocker.patch('smapply.api.SMApplyAPI')
    ProfileFactory(smapply_id=94379385)
    mock_api().get.return_value.json.return_value = {
        'id': 1,
        'name': 'Award name',
        'tag_line': 'The very best!',
        'description': 'Description',
        'price': 50.9,
    }
    request = WebhookRequestSMA(body=body)
    parse_webhook(request)
    assert request.status == WebhookParseStatus.FAILED
    mock_user_sync.assert_not_called()
    mock_deal_sync.assert_not_called()
    mock_product_sync.assert_not_called()


def test_sync_demographics(mocker, mock_user_sync, mock_deal_sync, mock_product_sync):
    """Test that a profile's demographics is set when on webhook receive"""
    user_id = 94379385
    submission_id = 4533767
    award_id = 12345
    profile = ProfileFactory(smapply_id=user_id)
    data = {
        'user_id': user_id,
        'id': submission_id,
        'award': award_id,
    }
    body = json.dumps(data)
    hook = WebhookRequestSMA(body=body)

    not_demographics_task = {'name': 'abcdefg', 'data': {'bad': 'data'}}
    demographics_task = {'name': DEMOGRAPHICS_TASK_NAME, 'data': {'test': 'test'}}

    mock_get = MockGet({
        f'applications/{submission_id}/tasks': {
            'results': [not_demographics_task, demographics_task],
            'next': None,
        },
        f'/programs/{award_id}': {
            'id': award_id,
            'name': 'fake award',
        },
        f'/applications/{submission_id}/': {
            'id': submission_id,
            'current_stage': {'id': 1234, 'title': 'Admitted'},
            'custom_fields': [{
                'id': settings.SMAPPLY_AMOUNT_TO_PAY_ID,
                'value': '12.34'
            }]
        },
    })
    mocker.patch('smapply.api.SMApplyAPI.get', side_effect=mock_get.mocked_api_get)
    logger = mocker.patch('logging.Logger.exception')
    parse_webhook(hook)
    profile.refresh_from_db()
    assert profile.smapply_demographic_data == demographics_task
    logger.assert_called_once()  # Once from mailgun but never from the rest of the code
    mock_user_sync.assert_called_once()
    mock_deal_sync.assert_called_once()
    mock_product_sync.assert_called_once()


def test_sync_demographics_error(mocker, mock_user_sync, mock_deal_sync, mock_product_sync):
    """Test that an error is logged when an application is missing the demographics task"""
    user_id = 94379385
    submission_id = 4533767
    award_id = 12345
    profile = ProfileFactory(smapply_id=user_id)

    data = {
        'user_id': user_id,
        'id': submission_id,
        'award': award_id,
    }
    body = json.dumps(data)
    hook = WebhookRequestSMA(body=body)

    not_demographics_task = {'name': 'abcdefg', 'data': {'bad': 'data'}}

    mock_get = MockGet({
        f'applications/{submission_id}/tasks': {
            'results': [not_demographics_task, not_demographics_task],
            'next': None,
        },
        f'/programs/{award_id}': {
            'id': award_id,
            'name': 'fake award',
        },
        f'/applications/{submission_id}/': {
            'id': submission_id,
            'current_stage': {'id': 1234, 'title': 'Admitted'},
            'custom_fields': [{
                'id': settings.SMAPPLY_AMOUNT_TO_PAY_ID,
                'value': '12.34'
            }]
        },
    })
    mocker.patch('smapply.api.SMApplyAPI.get', side_effect=mock_get.mocked_api_get)
    logger = mocker.patch('logging.Logger.exception')
    parse_webhook(hook)
    profile.refresh_from_db()
    assert profile.smapply_demographic_data is None
    assert logger.call_count == 2  # Once for mailgun error, once for missing demographics data
    mock_user_sync.assert_called_once()
    mock_deal_sync.assert_called_once()
    mock_product_sync.assert_called_once()


def test_list_users(mocker):
    """
    Test that the list_users method yields expected results
    """
    mock_api_results = [
        {
            'count': 3,
            'next': 'https://bootcampmit.fluidreview.com/api/v2/users/?page=2',
            'previous': None,
            'results': [
                {
                    'email': 'fake1@edu.mit',
                    'id': 94379401
                },
                {
                    'email': 'fake2@edu.mit',
                    'id': 94379359,
                }
            ]
        },
        {
            'count': 3,
            'next': None,
            'previous': 'https://bootcampmit.fluidreview.com/api/v2/users',
            'results': [
                {
                    'email': 'fake3@edu.mit',
                    'id': 94379422
                }
            ]
        },
    ]
    mock_api = mocker.patch('smapply.api.SMApplyAPI')
    mock_api().get.return_value.json.side_effect = mock_api_results
    expected_users = [user for results in mock_api_results for user in results['results']]
    assert expected_users == [user for user in list_users()]


@pytest.mark.parametrize('is_legacy', [True, False])
@pytest.mark.parametrize('is_fulfilled', [True, False])
def test_post_payment(mocker, is_legacy, is_fulfilled, test_payment_data, settings):
    """Test that posting a payment is called for non-legacy klasses, with correct data"""
    settings.SMAPPLY_AMOUNTPAID_ID = 100
    mock_api = mocker.patch('smapply.api.SMApplyAPI')
    mock_api().patch.return_value.status_code = 200
    klass, order, hook = test_payment_data
    if not is_fulfilled:
        order.status = Order.FAILED
    Bootcamp.objects.filter(id=klass.bootcamp.id).update(legacy=is_legacy)
    post_payment(order)
    expected_data = {
        'custom_fields': [{
            'id': settings.SMAPPLY_AMOUNTPAID_ID,
            'value': '11.38'
        }]
    }
    assert mock_api().patch.call_count == (0 if is_legacy or not is_fulfilled else 1)
    if is_fulfilled and not is_legacy:
        mock_api().patch.assert_called_with(
            'applications/{}/'.format(hook.submission_id), data=json.dumps(expected_data)
        )


def test_post_payment_bad_response(mocker, test_payment_data):
    """Test that bad responses from SMApply raise expected exceptions"""
    mock_api = mocker.patch('smapply.api.SMApplyAPI')
    mock_api().patch.side_effect = HTTPError
    klass, order, _ = test_payment_data
    Bootcamp.objects.filter(id=klass.bootcamp.id).update(legacy=False)
    with pytest.raises(SMApplyException) as exc:
        post_payment(order)
    assert 'Error updating amount paid by user' in str(exc.value)


def test_post_payment_bad_webhook(mocker, test_payment_data):
    """Test that a webhook without submission id raises expected exception"""
    mocker.patch('smapply.api.SMApplyAPI')
    klass, order, hook = test_payment_data
    hook.submission_id = None
    hook.save()
    Bootcamp.objects.filter(id=klass.bootcamp.id).update(legacy=False)
    with pytest.raises(SMApplyException) as exc:
        post_payment(order)
    assert 'Webhook has no submission id for order' in str(exc.value)
