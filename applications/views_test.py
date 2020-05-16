"""Tests for bootcamp application views"""
import pytest

from django.urls import reverse
from rest_framework import status

from applications.factories import BootcampApplicationFactory
from applications.serializers import BootcampApplicationDetailSerializer, BootcampApplicationSerializer
from applications.views import BootcampApplicationViewset
from klasses.factories import BootcampRunFactory
from profiles.factories import UserFactory


@pytest.mark.parametrize(
    "action,expected_serializer", [
        ["retrieve", BootcampApplicationDetailSerializer],
        ["list", BootcampApplicationSerializer],
    ]
)
def test_view_serializer(mocker, action, expected_serializer):
    """The bootcamp application view should use the expected serializer depending on the action"""
    serializer_cls = BootcampApplicationViewset.get_serializer_class(mocker.Mock(action=action))
    assert serializer_cls == expected_serializer


@pytest.mark.django_db
def test_app_detail_view(client):
    """The bootcamp application detail view should return a successful response"""
    application = BootcampApplicationFactory.create()
    client.force_login(application.user)
    url = reverse("applications_api-detail", kwargs={"pk": application.id})
    resp = client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == application.id


@pytest.mark.django_db
def test_app_list_view(client):
    """The bootcamp application list view should return a successful response"""
    application = BootcampApplicationFactory.create()
    client.force_login(application.user)
    url = reverse("applications_api-list")
    resp = client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()[0]["id"] == application.id


@pytest.mark.django_db
def test_app_create_view(client):
    """The bootcamp application create view should return a successful response"""
    bootcamp_run = BootcampRunFactory.create()
    user = UserFactory.create()
    client.force_login(user)
    url = reverse("applications_api-list")
    resp = client.post(
        url,
        data={"bootcamp_run_id": bootcamp_run.id}
    )
    assert resp.status_code == status.HTTP_201_CREATED
    application_id = resp.json()["id"]
    # Making a request for an existing application should return a 200 instead of a 201
    resp = client.post(
        url,
        data={"bootcamp_run_id": bootcamp_run.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == application_id


@pytest.mark.django_db
def test_app_detail_view_permissions(client):
    """
    The bootcamp application detail view should return an error if the user is not logged in or
    is requesting an application that isn't their own
    """
    application = BootcampApplicationFactory.create()
    url = reverse("applications_api-detail", kwargs={"pk": application.id})
    resp = client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    other_user_application = BootcampApplicationFactory.create()
    client.force_login(application.user)
    url = reverse("applications_api-detail", kwargs={"pk": other_user_application.id})
    resp = client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
