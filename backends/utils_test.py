"""
Tests for the utils
"""
from datetime import datetime, timedelta
from unittest.mock import (
    MagicMock,
    Mock,
    patch,
)

import pytz
from django.test import TestCase
from requests.exceptions import HTTPError

from backends import utils
from backends.utils import get_social_username
from backends.edxorg import EdxOrgOAuth2
from profiles.factories import UserFactory
# pylint: disable=protected-access


social_extra_data = {
    "access_token": "fooooootoken",
    "refresh_token": "baaaarrefresh",
}


class RefreshTest(TestCase):
    """Class to test refresh token"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # create an user
        cls.user = UserFactory.create()
        # create a social auth for the user
        cls.user.social_auth.create(
            provider=EdxOrgOAuth2.name,
            uid="{}_edx".format(cls.user.username),
            extra_data=social_extra_data
        )

    def setUp(self):
        super(RefreshTest, self).setUp()
        self.now = datetime.now(pytz.utc)

    def update_social_extra_data(self, data):
        """Helper function to update the python social auth extra data"""
        social_user = self.user.social_auth.get(provider=EdxOrgOAuth2.name)
        social_user.extra_data.update(data)
        social_user.save()
        return social_user

    @patch('backends.edxorg.EdxOrgOAuth2.refresh_token', return_value=social_extra_data, autospec=True)
    def test_refresh(self, mock_refresh):
        """The refresh needs to be called"""
        extra_data = {
            "updated_at": (self.now - timedelta(weeks=1)).timestamp(),
            "expires_in": 100  # seconds
        }
        social_user = self.update_social_extra_data(extra_data)
        utils.refresh_user_token(social_user)
        assert mock_refresh.called

    @patch('backends.edxorg.EdxOrgOAuth2.refresh_token', return_value=social_extra_data, autospec=True)
    def test_refresh_no_extradata(self, mock_refresh):
        """The refresh needs to be called because there is not valid timestamps"""
        social_user = self.user.social_auth.get(provider=EdxOrgOAuth2.name)
        social_user.extra_data = {"access_token": "fooooootoken", "refresh_token": "baaaarrefresh"}
        social_user.save()
        utils.refresh_user_token(social_user)
        assert mock_refresh.called

    @patch('backends.edxorg.EdxOrgOAuth2.refresh_token', return_value=social_extra_data, autospec=True)
    def test_no_refresh(self, mock_refresh):
        """The refresh does not need to be called"""
        extra_data = {
            "updated_at": (self.now - timedelta(minutes=1)).timestamp(),
            "expires_in": 31535999  # 1 year - 1 second
        }
        social_user = self.update_social_extra_data(extra_data)
        utils.refresh_user_token(social_user)
        assert not mock_refresh.called

    @patch('backends.edxorg.EdxOrgOAuth2.refresh_token', return_value=social_extra_data, autospec=True)
    def test_refresh_400_error_server(self, mock_refresh):
        """Test to check what happens when the OAUTH server returns 400 code"""
        def raise_http_error(*args, **kwargs):  # pylint: disable=unused-argument
            """Mock function to raise an exception"""
            error = HTTPError()
            error.response = MagicMock()
            error.response.status_code = 400
            raise error

        mock_refresh.side_effect = raise_http_error
        social_user = self.user.social_auth.get(provider=EdxOrgOAuth2.name)
        with self.assertRaises(utils.InvalidCredentialStored):
            utils._send_refresh_request(social_user)

    @patch('backends.edxorg.EdxOrgOAuth2.refresh_token', return_value=social_extra_data, autospec=True)
    def test_refresh_401_error_server(self, mock_refresh):
        """Test to check what happens when the OAUTH server returns 401 code"""
        def raise_http_error(*args, **kwargs):  # pylint: disable=unused-argument
            """Mock function to raise an exception"""
            error = HTTPError()
            error.response = MagicMock()
            error.response.status_code = 401
            raise error

        mock_refresh.side_effect = raise_http_error
        social_user = self.user.social_auth.get(provider=EdxOrgOAuth2.name)
        with self.assertRaises(utils.InvalidCredentialStored):
            utils._send_refresh_request(social_user)

    @patch('backends.edxorg.EdxOrgOAuth2.refresh_token', return_value=social_extra_data, autospec=True)
    def test_refresh_500_error_server(self, mock_refresh):
        """Test to check what happens when the OAUTH server returns 500 code"""
        def raise_http_error(*args, **kwargs):  # pylint: disable=unused-argument
            """Mock function to raise an exception"""
            error = HTTPError()
            error.response = MagicMock()
            error.response.status_code = 500
            raise error

        mock_refresh.side_effect = raise_http_error
        social_user = self.user.social_auth.get(provider=EdxOrgOAuth2.name)
        with self.assertRaises(HTTPError):
            utils._send_refresh_request(social_user)


class SocialTests(TestCase):
    """
    Tests for profile functions
    """

    def setUp(self):
        """
        Create a user with a default social auth
        """
        super().setUp()

        self.user = UserFactory.create()
        self.user.social_auth.create(
            provider='not_edx',
        )
        self.social_username = "{}_edx".format(self.user.username)
        self.user.social_auth.create(
            provider=EdxOrgOAuth2.name,
            uid=self.social_username,
        )

    def test_anonymous_user(self):
        """
        get_social_username should return None for anonymous users
        """
        is_anonymous = Mock(return_value=True)
        user = Mock(is_anonymous=is_anonymous)
        assert get_social_username(user) is None
        assert is_anonymous.called

    def test_zero_social(self):
        """
        get_social_username should return None if there is no edX account associated yet
        """
        self.user.social_auth.all().delete()
        assert get_social_username(self.user) is None

    def test_one_social(self):
        """
        get_social_username should return the social username, not the Django username
        """
        assert get_social_username(self.user) == self.social_username
