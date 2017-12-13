"""
Models classes needed for bootcamp
"""
from django.conf import settings
from django.db.models import Model
from django.db.models.fields import TextField, IntegerField
from django.db.models.fields.related import OneToOneField


class Profile(Model):
    """Used to store information about the User"""
    user = OneToOneField(settings.AUTH_USER_MODEL)
    name = TextField(blank=True)
    fluidreview_id = IntegerField(null=True, blank=True)

    def __str__(self):
        return "Profile for user {}".format(self.user)
