"""
URLs for bootcamp
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from bootcamp.views import index


urlpatterns = [
    url(r'^$', index, name='bootcamp-index'),
    url(r'^status/', include('server_status.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url('', include('social_django.urls', namespace='social')),
    url(r'^logout/$', auth_views.logout, {'next_page': '/'}),
]
