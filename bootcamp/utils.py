"""
General bootcamp utility functions
"""
import json
import logging

from django.conf import settings
from django.core.serializers import serialize


log = logging.getLogger(__name__)


def webpack_dev_server_host(request):
    """
    Get the correct webpack dev server host
    """
    return settings.WEBPACK_DEV_SERVER_HOST or request.get_host().split(":")[0]


def webpack_dev_server_url(request):
    """
    Get the full URL where the webpack dev server should be running
    """
    return 'http://{}:{}'.format(webpack_dev_server_host(request), settings.WEBPACK_DEV_SERVER_PORT)


def serialize_model_object(obj):
    """
    Serialize model into a dict representable as JSON

    Args:
        obj (django.db.models.Model): An instantiated Django model
    Returns:
        dict:
            A representation of the model
    """
    # serialize works on iterables so we need to wrap object in a list, then unwrap it
    data = json.loads(serialize('json', [obj]))[0]
    serialized = data['fields']
    serialized['id'] = data['pk']
    return serialized


def get_field_names(model):
    """
    Get field names which aren't autogenerated

    Args:
        model (class extending django.db.models.Model): A Django model class
    Returns:
        list of str:
            A list of field names
    """
    return [
        field.name for field in model._meta.get_fields() if not field.auto_created  # pylint: disable=protected-access
    ]
