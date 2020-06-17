"""
URLs for bootcamp
"""
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.urls import re_path, include, path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.images.views.serve import ServeView

from main import features
from main.views import react, BackgroundImagesCSSView, index

root_urlpatterns = [url("", include(wagtail_urls))]
if not features.is_enabled(features.CMS_HOME_PAGE):
    root_urlpatterns = [path("", index, name="deprecated-home")] + root_urlpatterns

urlpatterns = (
    [
        url(r"^pay/$", react, name="pay"),
        url(
            r"^terms_of_service/$",
            TemplateView.as_view(template_name="bootcamp/tos.html"),
            name="bootcamp-tos",
        ),
        url(
            r"^terms_and_conditions/$",
            TemplateView.as_view(template_name="bootcamp/tac.html"),
            name="bootcamp-tac",
        ),
        url(r"^status/", include("server_status.urls")),
        url(r"^admin/", admin.site.urls),
        url(r"^hijack/", include("hijack.urls", namespace="hijack")),
        url("", include("applications.urls")),
        url("", include("ecommerce.urls")),
        url("", include("social_django.urls", namespace="social")),
        path("", include("authentication.urls")),
        path("", include("profiles.urls")),
        path("", include("klasses.urls")),
        url("", include("jobma.urls")),
        url(r"^logout/$", auth_views.LogoutView.as_view(), name="logout"),
        url(
            r"^background-images\.css$",
            BackgroundImagesCSSView.as_view(),
            name="background-images-css",
        ),
        # named routes mapped to the react app
        path("signin/", react, name="login"),
        path("signin/password/", react, name="login-password"),
        re_path(r"^signin/forgot-password/$", react, name="password-reset"),
        re_path(
            r"^signin/forgot-password/confirm/(?P<uid>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
            react,
            name="password-reset-confirm",
        ),
        re_path(
            r"^images/([^/]*)/(\d*)/([^/]*)/[^/]*$",
            ServeView.as_view(),
            name="wagtailimages_serve",
        ),
        path("create-account/", react, name="signup"),
        path("create-account/details/", react, name="signup-details"),
        path("create-account/extra/", react, name="signup-extra"),
        path("create-account/denied/", react, name="signup-denied"),
        path("create-account/error/", react, name="signup-error"),
        path("create-account/confirm/", react, name="register-confirm"),
        path("account/inactive/", react, name="account-inactive"),
        path("account/confirm-email/", react, name="account-confirm-email-change"),
        path("account-settings/", react, name="account-settings"),
        path("applications/", react, name="applications"),
        path(
            "applications/<int:application_id>/payment-history/",
            react,
            name="application-history",
        ),
        re_path(r"^review/", react, name="review"),
        # Wagtail
        re_path(
            r"^images/([^/]*)/(\d*)/([^/]*)/[^/]*$",
            ServeView.as_view(),
            name="wagtailimages_serve",
        ),
        re_path(r"^cms/", include(wagtailadmin_urls)),
        re_path(r"^documents/", include(wagtaildocs_urls)),
    ]
    + root_urlpatterns
    + (
        static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    )
)

handler404 = "main.views.page_404"
handler500 = "main.views.page_500"
