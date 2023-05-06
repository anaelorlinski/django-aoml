from django.urls import include, path

urlpatterns = [
        path('m/', include('aoml.urls.mailing_list')),
        path('t/', include('aoml.urls.tracking')),
        path('s/', include('aoml.urls.statistics')),
        path('', include('aoml.urls.newsletter')),
]