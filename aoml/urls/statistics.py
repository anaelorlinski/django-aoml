"""Urls for the . statistics"""
from django.conf.urls import url
from ..views.statistics import *

urlpatterns = [
                       url(r'^(?P<slug>[-\w]+)/$',
                           view_newsletter_statistics,
                           name='newsletter_newsletter_statistics'),
                       url(r'^report/(?P<slug>[-\w]+)/$',
                           view_newsletter_report,
                           name='newsletter_newsletter_report'),
]
