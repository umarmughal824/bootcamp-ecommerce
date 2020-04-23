"""Custom strategy"""
from urllib.parse import urlencode

from django.db import transaction
from rest_framework.request import Request
from social_django.strategy import DjangoStrategy

from main import features
from profiles.models import LegalAddress, Profile


class BootcampDjangoStrategy(DjangoStrategy):
    """Abstract strategy for botcamp app"""

    def redirect_with_partial(self, url, partial_token):
        """Redirect to the specified url with a partial token"""
        qs = urlencode({"partial_token": partial_token.token})
        return self.redirect(self.build_absolute_uri(f"{url}?{qs}"))

    def is_api_enabled(self):
        """Returns True if the social auth api is enabled"""
        return features.is_enabled(features.SOCIAL_AUTH_API)

    def is_api_request(self):
        """Returns True if the request is being executed in an API context"""
        raise NotImplementedError("is_api_request must be implemented")


class DefaultStrategy(BootcampDjangoStrategy):
    """Default strategy for standard social auth requests"""

    def is_api_request(self):
        """Returns True if the request is being executed in an API context"""
        return False

    def create_user(self, *args, **kwargs):
        with transaction.atomic():
            user = super().create_user(*args, **kwargs)
            LegalAddress.objects.create(user=user)
            Profile.objects.create(user=user)
        return user


class DjangoRestFrameworkStrategy(BootcampDjangoStrategy):
    """Strategy specific to handling DRF requests"""

    def __init__(self, storage, drf_request=None, tpl=None):
        self.drf_request = drf_request
        # pass the original django request to DjangoStrategy
        request = drf_request._request  # pylint: disable=protected-access
        super().__init__(storage, request=request, tpl=tpl)

    def is_api_request(self):
        """Returns True if the request is being executed in an API context"""
        return True

    def clean_authenticate_args(self, *args, **kwargs):
        """Cleanup request argument if present, which is passed to authenticate as for Django 1.11"""
        # this is similar to what DjangoStrategy does, but is specific to DRF's Request type
        if len(args) > 0 and isinstance(args[0], Request):
            kwargs["request"], args = args[0], args[1:]

        return super().clean_authenticate_args(*args, **kwargs)

    def request_data(self, merge=True):
        """Returns the request data"""
        if not self.drf_request:
            return {}

        # DRF stores json payload data here, not in request.POST or request.GET like PSA expects
        return self.drf_request.data
