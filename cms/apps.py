"""Apps for cms"""
from django.apps import AppConfig


class CMSConfig(AppConfig):
    """AppConfig for cms"""

    name = "cms"

    def ready(self):
        """Application is ready"""
        import cms.signals  # pylint:disable=unused-import, unused-variable
