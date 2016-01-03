from django.conf.urls import url
from django.conf.urls import patterns

from emencia.django.newsletter.forms import MailingListSubscriptionForm
from emencia.django.newsletter.forms import AllMailingListSubscriptionForm

urlpatterns = patterns('emencia.django.newsletter.views.newsletter',
                       url(r'^preview/(?P<slug>[-\w]+)/$',
                           'view_newsletter_preview',
                           name='newsletter_newsletter_preview'),
                       url(r'^(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           'view_newsletter_contact',
                           name='newsletter_newsletter_contact'),
                       )


urlpatterns += patterns('emencia.django.newsletter.views.mailing_list',
                       url(r'^unsubscribe/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           'view_mailinglist_unsubscribe',
                           name='newsletter_mailinglist_unsubscribe'),
                       url(r'^subscribe/(?P<mailing_list_id>\d+)/',
                           'view_mailinglist_subscribe',
                           {'form_class': MailingListSubscriptionForm},
                           name='newsletter_mailinglist_subscribe'),
                       url(r'^subscribe/',
                           'view_mailinglist_subscribe',
                           {'form_class': AllMailingListSubscriptionForm},
                           name='newsletter_mailinglist_subscribe_all'),
                       )

urlpatterns += patterns('emencia.django.newsletter.views.statistics',
                       url(r'^(?P<slug>[-\w]+)/$',
                           'view_newsletter_statistics',
                           name='newsletter_newsletter_statistics'),
                       url(r'^report/(?P<slug>[-\w]+)/$',
                           'view_newsletter_report',
                           name='newsletter_newsletter_report'),
                       url(r'^charts/(?P<slug>[-\w]+)/$',
                           'view_newsletter_charts',
                           name='newsletter_newsletter_charts'),
                       url(r'^density/(?P<slug>[-\w]+)/$',
                           'view_newsletter_density',
                           name='newsletter_newsletter_density'),
                       )

urlpatterns += patterns('emencia.django.newsletter.views.tracking',
                       url(r'^newsletter/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)\.(?P<format>png|gif|jpg)$',
                           'view_newsletter_tracking',
                           name='newsletter_newsletter_tracking'),
                       url(r'^link/(?P<slug>[-\w]+)/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/(?P<link_id>\d+)/$',
                           'view_newsletter_tracking_link',
                           name='newsletter_newsletter_tracking_link'),
                       url(r'^historic/(?P<slug>[-\w]+)/$',
                           'view_newsletter_historic',
                           name='newsletter_newsletter_historic'),
                       )
