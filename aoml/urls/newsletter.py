"""Urls for the . Newsletter"""
from django.urls import re_path
from ..views.newsletter import *

urlpatterns = [
                       re_path(r'^preview/(?P<slug>[-\w]+)/$',
                           view_newsletter_preview,
                           name='newsletter_newsletter_preview'),
                       re_path(r'^(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           view_newsletter_contact,
                           name='newsletter_newsletter_contact'),
]
