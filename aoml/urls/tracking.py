"""Urls for the . Tracking"""
from django.urls import re_path
from ..views.tracking import *

urlpatterns = [
                       re_path(r'^newsletter/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)\.(?P<format>png|gif|jpg)$',
                           view_newsletter_tracking,
                           name='newsletter_newsletter_tracking'),
                       re_path(r'^link/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/(?P<link_id>\d+)/$',
                           view_newsletter_tracking_link,
                           name='newsletter_newsletter_tracking_link'),
                       re_path(r'^historic/(?P<slug>[-\w]+)/$',
                           view_newsletter_historic,
                           name='newsletter_newsletter_historic'),
]
