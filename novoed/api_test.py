# pylint: disable=redefined-outer-name
"""Test for NovoEd API functionality"""
import pytest

from rest_framework import status
from requests.exceptions import HTTPError

from main.test_utils import MockResponse
from profiles.factories import UserFactory
from novoed.api import enroll_in_novoed_course, unenroll_from_novoed_course
from novoed.constants import REGISTER_USER_URL_STUB, UNENROLL_USER_URL_STUB


FAKE_API_KEY = "apikey"
FAKE_API_SECRET = "apisecret"
FAKE_BASE_URL = "http://localhost"
FAKE_COURSE_STUB = "my-course"


@pytest.fixture(autouse=True)
def novoed_settings(settings):
    """NovoEd-related settings values"""
    settings.NOVOED_API_KEY = FAKE_API_KEY
    settings.NOVOED_API_SECRET = FAKE_API_SECRET
    settings.NOVOED_API_BASE_URL = FAKE_BASE_URL


@pytest.fixture
def novoed_user():
    """User to use in NovoEd test cases"""
    return UserFactory.create(
        legal_address__first_name="Jane", legal_address__last_name="Doe"
    )


@pytest.fixture
def patched_post(mocker):
    """Patches the post function from the requests library"""
    return mocker.patch("novoed.api.requests.post")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "response_status,exp_created,exp_existing",
    [[status.HTTP_200_OK, True, False], [status.HTTP_207_MULTI_STATUS, False, True]],
)
def test_enroll_in_novoed_course(
    patched_post, novoed_user, response_status, exp_created, exp_existing
):
    """
    enroll_in_novoed_course should make a request to enroll a user in NovoEd and return flags indicating the results
    """
    patched_post.return_value = MockResponse(content=None, status_code=response_status)
    result = enroll_in_novoed_course(novoed_user, FAKE_COURSE_STUB)
    patched_post.assert_called_once_with(
        f"{FAKE_BASE_URL}/{FAKE_COURSE_STUB}/{REGISTER_USER_URL_STUB}",
        json={
            "api_key": FAKE_API_KEY,
            "api_secret": FAKE_API_SECRET,
            "catalog_id": FAKE_COURSE_STUB,
            "first_name": novoed_user.legal_address.first_name,
            "last_name": novoed_user.legal_address.last_name,
            "email": novoed_user.email,
        },
    )
    assert result == (exp_created, exp_existing)


@pytest.mark.django_db
def test_enroll_in_novoed_course_exc(patched_post, novoed_user):
    """
    enroll_in_novoed_course should raise if the response indicates an error
    """
    patched_post.return_value = MockResponse(
        content=None, status_code=status.HTTP_400_BAD_REQUEST
    )
    with pytest.raises(HTTPError):
        enroll_in_novoed_course(novoed_user, FAKE_COURSE_STUB)


@pytest.mark.django_db
def test_unenroll_from_novoed_course(patched_post, novoed_user):
    """unenroll_from_novoed_course should make a request to unenroll a user from a NovoEd course"""
    patched_post.return_value = MockResponse(
        content=None, status_code=status.HTTP_200_OK
    )
    unenroll_from_novoed_course(novoed_user, FAKE_COURSE_STUB)
    patched_post.assert_called_once_with(
        f"{FAKE_BASE_URL}/{FAKE_COURSE_STUB}/{UNENROLL_USER_URL_STUB}",
        json={
            "api_key": FAKE_API_KEY,
            "api_secret": FAKE_API_SECRET,
            "email": novoed_user.email,
        },
    )


@pytest.mark.django_db
def test_unenroll_from_novoed_course_exc(patched_post, novoed_user):
    """unenroll_from_novoed_course should raise if the response indicates an error"""
    patched_post.return_value = MockResponse(
        content=None, status_code=status.HTTP_400_BAD_REQUEST
    )
    with pytest.raises(HTTPError):
        unenroll_from_novoed_course(novoed_user, FAKE_COURSE_STUB)
