"""
SMApply API backend
"""
import copy
import json
import logging

from urllib.parse import urljoin, urlparse
from datetime import timedelta

from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.encoding import smart_text
from requests_oauthlib import OAuth2Session

from klasses.constants import ApplicationSource
from klasses.models import BootcampRun, Bootcamp
from ecommerce.models import Line, Order
from mail.api import MailgunClient
from profiles.models import Profile
from fluidreview.serializers import UserSerializer
from fluidreview.constants import WebhookParseStatus
from fluidreview.utils import utc_now
from smapply.models import OAuthTokenSMA, WebhookRequestSMA

log = logging.getLogger(__name__)

BASE_API_URL = urljoin(settings.SMAPPLY_BASE_URL, '/api/')

DEMOGRAPHICS_TASK_NAME = 'Part 1: Complete Your Application Form'


class SMApplyException(Exception):
    """
    Custom exception for SMApply
    """


class MissingTaskNameException(Exception):
    """
    Custom exception for syncing demographics information
    """


class SMApplyAPI:
    """
    Class for making authorized requests to the SMApply API via OAuth2
    """

    def __init__(self):
        """
        Prepare to make OAuth2 requests to the API
        """
        self.session = self.initialize_session()

    def initialize_session(self):
        """
        Initialize an OAuth2 session with an auto-refreshing token.

        Returns:
            OAuth2Session: an OAuth2 session
        """
        token = self.get_token()
        extra = {
            'client_id': settings.SMAPPLY_CLIENT_ID,
            'client_secret': settings.SMAPPLY_CLIENT_SECRET,
        }
        return OAuth2Session(settings.SMAPPLY_CLIENT_ID,
                             token=token,
                             auto_refresh_kwargs=extra,
                             auto_refresh_url=urljoin(BASE_API_URL, 'o/token/'),
                             token_updater=self.save_token)

    def get_token(self):
        """
        Return an OAuth token for the API. Search for an OAuthToken model first,
        and if not found then seed from the initial settings.

        Returns:
            dict: OAuthToken model instance in JSON format

        """
        token = OAuthTokenSMA.objects.first()
        if not token:
            token = OAuthTokenSMA.objects.create(
                access_token=settings.SMAPPLY_ACCESS_TOKEN,
                refresh_token=settings.SMAPPLY_REFRESH_TOKEN,
                token_type='Bearer',
                expires_on=utc_now()
            )
        return token.json

    def save_token(self, new_token):
        """
        Create or update the SMApply token parameters.
        Should be automatically called when a new token is required.
        With the SMApply API, the refresh token can only be used once and is then invalidated,
        so it must be saved and updated in the database.

        Args:
            new_token(dict): New token sent by the SMApply API

        Returns:
            OAuthTokenSMA: the saved object

        """
        token, _ = OAuthTokenSMA.objects.get_or_create(id=1)
        token.access_token = new_token['access_token']
        token.refresh_token = new_token['refresh_token']
        # Shave 10 seconds off the expiration time just to be cautious.
        token.expires_on = utc_now() + timedelta(seconds=new_token['expires_in']-10)
        token.token_type = new_token['token_type'] or 'Bearer'
        token.save()
        return token

    def get(self, url_suffix, **kwargs):
        """
        Make a GET request to the API

        Args:
            url_suffix(str): The URL fragment to be appended to the base API URL

        Returns:
            requests.Response: The API response
        """
        return self.request('get', url_suffix, **kwargs)

    def post(self, url_suffix, **kwargs):
        """
        Make a POST request to the API

        Args:
            url_suffix(str): The URL fragment to be appended to the base API URL

        Returns:
            requests.Response: The API response
        """
        return self.request('post', url_suffix, **kwargs)

    def put(self, url_suffix, **kwargs):
        """
        Make a PUT request to the API

        Args:
            url_suffix(str): The URL fragment to be appended to the base API URL

        Returns:
            requests.Response: The API response
        """
        return self.request('put', url_suffix, **kwargs)

    def patch(self, url_suffix, **kwargs):
        """
        Make a PATCH request to the API

        Args:
            url_suffix(str): The URL fragment to be appended to the base API URL

        Returns:
            requests.Response: The API response
        """
        return self.request('patch', url_suffix, **kwargs)

    def request(self, method, url_suffix, **kwargs):
        """
        Make a request to the API using the designated method (GET, POST, PUT)

        Args:
            method(str): The method of the request
            url_suffix(str): The URL fragment to be appended to the base API URL

        Returns:
            requests.Response: The API response
        """
        if url_suffix and url_suffix.startswith('/'):
            url_suffix = url_suffix[1:]
        response = getattr(self.session, method)(urljoin(BASE_API_URL, url_suffix), **kwargs)
        if response.status_code == 401:
            # The session is no longer valid, possibly a new token has been retrieved and
            # saved to the database by another instance. Re-initialize session and try again.
            self.session = self.initialize_session()
            response = getattr(self.session, method)(urljoin(BASE_API_URL, url_suffix), **kwargs)
        response.raise_for_status()
        return response

def process_user(sma_user, require_validation=True):
    """
    Create/update User and Profile model objects based on SMApply user info

    Args:
        sma_user (ReturnDict): Data from a smapply.serializers.UserSerializer object
        require_validation (bool): if the user data should be validated or not

    Returns:
        User: user modified or created by the function
    """
    if require_validation:
        serializer = UserSerializer(data=sma_user)
        serializer.is_valid(raise_exception=True)

    user, _ = User.objects.get_or_create(
        email__iexact=sma_user['email'],
        defaults={'email': sma_user['email'], 'username': sma_user['email']}
    )
    profile, _ = Profile.objects.get_or_create(user=user)
    if not profile.smapply_id:
        profile.smapply_id = sma_user['id']
        profile.smapply_user_data = sma_user
        profile.name = '{} {}'.format(sma_user['first_name'], sma_user['last_name'])
        profile.save()
    return user


def parse_webhook(webhook):
    """
    Attempt to load a WebhookRequestSMA body as JSON and assign its values to other attributes.

    Args:
        webhook (WebhookRequestSMA): WebhookRequestSMA instance

    """
    try:
        body_json = json.loads(smart_text(webhook.body))
        field_mapping = {'id': 'submission_id', 'award': 'award_id', 'user_id': 'user_id'}
        required_fields = field_mapping.keys()
        if not set(required_fields).issubset(body_json.keys()):
            raise SMApplyException("Missing required field(s)")
        for att in field_mapping:
            if att in body_json and body_json[att]:
                setattr(webhook, field_mapping[att], int(body_json[att]))
        parse_webhook_user(webhook)
        webhook.status = WebhookParseStatus.SUCCEEDED
    except:  # pylint: disable=bare-except
        webhook.status = WebhookParseStatus.FAILED
        log.exception('Webhook %s body is not valid JSON or has invalid/missing values.', webhook.id)
    finally:
        webhook.save()


def parse_webhook_user(webhook):
    """
    Create/update User and Profile objects if necessary for a SMApply user id
    Args:
        webhook(WebhookRequestSMA): a WebhookRequestSMA object
    """
    if webhook.user_id is None:
        raise SMApplyException('user_id is required in WebhookRequestSMA')
    profile = Profile.objects.filter(smapply_id=webhook.user_id).first()
    if not profile:
        # Get user info from SMApply API (ensures that user id is real).
        user_info = SMApplyAPI().get('/users/{}'.format(webhook.user_id)).json()

        user = process_user(user_info)
    else:
        user = profile.user

    # Sync user demographics data
    try:
        store_demographics_data(user.profile, webhook.submission_id)
    except MissingTaskNameException:
        # Log error instead of stopping execution with an exception
        log.exception('Demographics form name was not found within application tasks')

    from hubspot.task_helpers import sync_hubspot_user
    sync_hubspot_user(user.profile)

    if webhook.award_id is not None:
        application_meta = SMApplyAPI().get('/applications/{}/'.format(
            webhook.submission_id
        )).json()
        personal_price = get_custom_field(application_meta['custom_fields'], settings.SMAPPLY_AMOUNT_TO_PAY_ID)
        application_stage = application_meta['current_stage']
        if not personal_price:
            award_meta = SMApplyAPI().get('/programs/{}/'.format(
                webhook.award_id
            )).json()
            personal_price = get_custom_field(award_meta['custom_fields'], settings.SMAPPLY_AWARD_COST_ID)

        bootcamp_run = BootcampRun.objects.filter(run_key=webhook.award_id, source=ApplicationSource.SMAPPLY).first()
        if not bootcamp_run:
            if not personal_price:
                raise SMApplyException(
                    "BootcampRun has no price and run_key %s does not exist" %
                    webhook.award_id
                )
            bootcamp_run_info = SMApplyAPI().get('/programs/{}'.format(webhook.award_id)).json()
            bootcamp = Bootcamp.objects.create(title=bootcamp_run_info['name'])

            # Sync the newly created bootcamp
            from hubspot.task_helpers import sync_hubspot_product
            sync_hubspot_product(bootcamp)

            bootcamp_run = BootcampRun.objects.create(
                bootcamp=bootcamp,
                source=ApplicationSource.SMAPPLY,
                title=bootcamp_run_info['name'],
                run_key=bootcamp_run_info['id'])
            try:
                MailgunClient().send_individual_email(
                    "BootcampRun and Bootcamp {name} was created".format(
                        name=bootcamp_run_info['name'],
                    ),
                    "BootcampRun and Bootcamp {name} was created, for run_key {run_key} at {base_url}".format(
                        run_key=bootcamp_run_info['id'],
                        name=bootcamp_run_info['name'],
                        base_url=settings.BOOTCAMP_ECOMMERCE_BASE_URL
                    ),
                    settings.EMAIL_SUPPORT,
                    sender_address=settings.MAILGUN_FROM_EMAIL
                )
            except:  # pylint: disable=bare-except
                log.exception(
                    "Error occurred when sending the email to notify "
                    "about BootcampRun and Bootcamp creation for bootcamp run key %s",
                    bootcamp_run_info['id']
                )
        if personal_price:
            personal_price = user.run_prices.update_or_create(
                bootcamp_run=bootcamp_run,
                defaults={'price': personal_price, 'application_stage': application_stage['title']}
            )[0]
            # Sync the personal price
            from hubspot.task_helpers import sync_hubspot_deal
            sync_hubspot_deal(personal_price)
        else:
            user.run_prices.filter(bootcamp_run=bootcamp_run).delete()


def get_tasks(application_id):
    """
    Generator for tasks on a specific application in SMApply

    Yields:
        dict: SMApply task responses as dict
    """
    smapi = SMApplyAPI()
    url = f'applications/{application_id}/tasks'
    while url:
        response = smapi.get(url).json()
        tasks = response['results']
        for task in tasks:
            yield task
        url = response['next']


def store_demographics_data(profile, application_id):
    """
    Stores demographics data for a user in their profile.
    Iterates over all of an application's tasks to find the demographics task and stores the json data in a Profile.

    Args:
        profile(Profile): a profile object to store application data
        application_id(int): the id of the application to retrieve
    """
    for task in get_tasks(application_id):
        if task['name'] == DEMOGRAPHICS_TASK_NAME:
            profile.smapply_demographic_data = task
            profile.save()
            break
    else:
        raise MissingTaskNameException(
            f'Demographics task name was not found within application tasks for application {application_id}'
        )


def list_users():
    """
    Generator for all users in SMApply

    Yields:
        dict: SMApply user as dict

    """
    smapi = SMApplyAPI()
    url = 'users'
    while url:
        response = smapi.get(url).json()
        users = response['results']
        for sma_user in users:
            yield sma_user
        next_page = urlparse(response['next']).query
        url = 'users?{}'.format(next_page) if next_page else None


def post_payment(order):
    """
    Update amount paid by a user for a class when an order is fulfilled.

    Args:
        order(Order): the Order object to send payment info about to SMApply

    """
    if order.status != Order.FULFILLED:
        return
    bootcamp_run = order.get_bootcamp_run()
    user = order.user
    if not bootcamp_run or bootcamp_run.bootcamp.legacy:
        return
    total_paid = Line.total_paid_for_bootcamp_run(order.user, bootcamp_run.run_key).get('total') or Decimal('0.00')
    payment_metadata = {
        'custom_fields': [{
            'id': settings.SMAPPLY_AMOUNTPAID_ID,
            'value': '{:0.2f}'.format(total_paid)
        }]
    }
    webhook = WebhookRequestSMA.objects.filter(user_id=user.profile.smapply_id, award_id=bootcamp_run.run_key).last()
    if webhook.submission_id is None:
        raise SMApplyException("Webhook has no submission id for order %s" % order.id)
    try:
        SMApplyAPI().patch(
            'applications/{}/'.format(webhook.submission_id),
            data=json.dumps(payment_metadata)
        )
    except Exception as exc:
        raise SMApplyException(
            "Error updating amount paid by user %s to class %s" % (user.email, bootcamp_run.run_key)
        ) from exc


def get_custom_field(custom_fields, field_id):
    """
    Get the value of a custom field by id
    """
    return [custom_field for custom_field in custom_fields
            if custom_field['id'] == field_id][0]['value']
