"""Urls for the . statistics"""
from django.urls import re_path
from ..views.statistics import *

urlpatterns = [
                       re_path(r'^(?P<slug>[-\w]+)/$',
                           view_newsletter_statistics,
                           name='newsletter_newsletter_statistics'),
                       re_path(r'^report/(?P<slug>[-\w]+)/$',
                           view_newsletter_report,
                           name='newsletter_newsletter_report'),
]
