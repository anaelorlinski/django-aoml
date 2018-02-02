from django.conf.urls import url, include

urlpatterns = [
        url(r'^mailing/', include('aoml.urls.mailing_list')),
        url(r'^tracking/', include('aoml.urls.tracking')),
        url(r'^statistics/', include('aoml.urls.statistics')),
        url(r'^', include('aoml.urls.newsletter')),
]