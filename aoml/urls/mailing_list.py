"""Urls for the . Mailing List"""
from django.urls import re_path

from ..forms import MailingListSubscriptionForm
#from ..forms import AllMailingListSubscriptionForm
from ..views.mailing_list import *

urlpatterns = [
                       re_path(r'^unsubscribe/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           view_mailinglist_unsubscribe,
                           name='newsletter_mailinglist_unsubscribe'),
                       re_path(r'^ocu/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           view_mailinglist_oneclick_unsubscribe,
                           name='newsletter_mailinglist_oneclick_unsubscribe'),
                       re_path(r'^subscribe/(?P<mailing_list_id>\d+)/',
                           view_mailinglist_subscribe,
                           {'form_class': MailingListSubscriptionForm},
                           name='newsletter_mailinglist_subscribe'),
                       re_path(r'^contact/subscribe/',
                           view_contact_subscribe,
                           name='newsletter_contact_subscribe'),
#                       url(r'^subscribe/',
#                           view_mailinglist_subscribe,
#                           {'form_class': AllMailingListSubscriptionForm},
#                           name='newsletter_mailinglist_subscribe_all'),
]
