"""
Tests for the bootcamp_admission_client module
"""
from urllib.parse import urljoin, urlencode

import pytest
from django.conf import settings
from rest_framework import status

from klasses.bootcamp_admissions_client import BootcampAdmissionClient

# pylint: disable=missing-docstring,redefined-outer-name,unused-argument

pytestmark = pytest.mark.django_db

JSON_RESP_OBJ = {
    "user": "foo@example.com",
    "bootcamps": [
        {
            "bootcamp_id": 1,
            "bootcamp_title": "Entrepreneurship",
            "klasses": [
                {
                    "klass_id": 13,
                    "klass_name": "Class 2 (Student)",
                    "status": "no_show",
                    "is_user_eligible_to_pay": False
                },
                {
                    "klass_id": 12,
                    "klass_name": "Class 1",
                    "status": "coming",
                    "is_user_eligible_to_pay": False
                }
            ]
        },
        {
            "bootcamp_id": 6,
            "bootcamp_title": "Master of Law",
            "klasses": [
                {
                    "klass_id": 16,
                    "klass_name": "Class 1",
                    "status": "scholarship_not_awarded",
                    "is_user_eligible_to_pay": True
                }
            ]
        }
    ]
}


@pytest.fixture()
def test_data():
    """
    Sets up the data for all the tests in this module
    """

    user_email = JSON_RESP_OBJ['user']
    url = "{base_url}?{params}".format(
        base_url=urljoin(settings.BOOTCAMP_ADMISSION_BASE_URL, '/api/v1/user/'),
        params=urlencode({
            'email': user_email,
            'key': settings.BOOTCAMP_ADMISSION_KEY,
        })
    )
    return user_email, url


@pytest.fixture()
def mocked_get_200(mocked_requests_get):
    """
    Mocked get with 200 response
    """
    mocked_requests_get.response.status_code = status.HTTP_200_OK
    mocked_requests_get.response.json.return_value = JSON_RESP_OBJ
    return mocked_requests_get


@pytest.fixture()
def mocked_get_400(mocked_requests_get):
    """
    Mocked get with 400 response
    """
    mocked_requests_get.response.status_code = status.HTTP_400_BAD_REQUEST
    mocked_requests_get.response.json.return_value = JSON_RESP_OBJ
    return mocked_requests_get


@pytest.fixture()
def mocked_update_cache(mocker):
    """
    Mocked async_cache_admissions task
    """
    return mocker.patch('klasses.tasks.async_cache_admissions.delay', autospec=True)


def test_happy_path(test_data, mocked_get_200, mocked_update_cache):
    """
    Test BootcampAdmissionClient with a normal response
    """
    user_email, url = test_data
    boot_client = BootcampAdmissionClient(user_email)
    mocked_get_200.request.assert_called_once_with(url)
    assert boot_client.admissions == JSON_RESP_OBJ
    expected_payable_klasses = {
        16: {
            "klass_id": 16,
            "klass_name": "Class 1",
            "status": "scholarship_not_awarded",
            "is_user_eligible_to_pay": True
        }
    }
    assert boot_client.payable_klasses == expected_payable_klasses
    assert boot_client.payable_klasses_keys == [16]
    mocked_update_cache.assert_called_once_with(user_email, expected_payable_klasses)


def test_get_raises(test_data, mocked_get_200, mocked_update_cache):
    """
    Test BootcampAdmissionClient in case the GET request to the service fails raising anything
    """
    user_email, url = test_data
    mocked_get_200.request.side_effect = ZeroDivisionError

    boot_client = BootcampAdmissionClient(user_email)
    mocked_get_200.request.assert_called_once_with(url)
    assert boot_client.admissions == {}
    assert boot_client.payable_klasses == {}
    assert boot_client.payable_klasses_keys == []
    assert mocked_update_cache.call_count == 0


def test_status_code_not_200(test_data, mocked_get_400, mocked_update_cache):
    """
    Test BootcampAdmissionClient in case the GET returns a status code different from 200
    """
    user_email, url = test_data

    boot_client = BootcampAdmissionClient(user_email)
    mocked_get_400.request.assert_called_once_with(url)
    assert boot_client.admissions == {}
    assert boot_client.payable_klasses == {}
    assert boot_client.payable_klasses_keys == []
    assert mocked_update_cache.call_count == 0


def test_json_raises(test_data, mocked_get_200, mocked_update_cache):
    """
    Test BootcampAdmissionClient in case the GET request to the service fails raising anything
    """
    user_email, url = test_data

    mocked_get_200.response.json.side_effect = ZeroDivisionError

    boot_client = BootcampAdmissionClient(user_email)
    mocked_get_200.request.assert_called_once_with(url)
    assert boot_client.admissions == {}
    assert boot_client.payable_klasses == {}
    assert boot_client.payable_klasses_keys == []
    assert mocked_update_cache.call_count == 0


def test_can_pay_klass(test_data, mocked_get_200):
    """
    Test BootcampAdmissionClient.can_pay_klass
    """
    user_email, _ = test_data

    boot_client = BootcampAdmissionClient(user_email)
    assert boot_client.can_pay_klass(16) is True
    assert boot_client.can_pay_klass(12) is False
    assert boot_client.can_pay_klass('foo') is False