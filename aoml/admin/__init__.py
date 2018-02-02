"""Admin for """
from django.contrib import admin
from django.conf import settings

from ..models import Link
from ..models import Contact
from ..models import SMTPServer
from ..models import Newsletter
from ..models import MailingList
from ..models import ContactMailingStatus

from ..settings import USE_WORKGROUPS
from .contact import ContactAdmin
from .newsletter import NewsletterAdmin
from .smtpserver import SMTPServerAdmin
from .mailinglist import MailingListAdmin


admin.site.register(Contact, ContactAdmin)
admin.site.register(SMTPServer, SMTPServerAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(MailingList, MailingListAdmin)


class LinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'creation_date')

if settings.DEBUG:
    admin.site.register(Link, LinkAdmin)
    admin.site.register(ContactMailingStatus)
