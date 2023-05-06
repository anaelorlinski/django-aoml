"""Urls for the demo of emencia.django.newsletter"""
from django.contrib import admin
from django.conf.urls import url
from django.urls import include, path
from django.conf.urls import patterns
from django.conf.urls import handler404
from django.conf.urls import handler500

admin.autodiscover()

urlpatterns = patterns('',
                       (r'^$', 'django.views.generic.simple.redirect_to',
                        {'url': '/admin/'}),
                       path('newsletters/', include('emencia.django.newsletter.urls')),
                       path('i18n/', include('django.conf.urls.i18n')),
                       path('admin/', include(admin.site.urls)),
                       )
