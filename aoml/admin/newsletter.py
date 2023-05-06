"""ModelAdmin for Newsletter"""

from django import forms
from django.db.models import Q
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from ..models import Contact
from ..models import Newsletter
from ..models import Attachment
from ..models import MailingList
from ..mailer import Mailer
from ..settings import USE_TINYMCE
from ..settings import USE_WORKGROUPS
import urllib.request
import urllib.parse
from premailer import Premailer
from premailer.premailer import PremailerError, ExternalNotFoundError


class AttachmentAdminInline(admin.TabularInline):
    model = Attachment
    extra = 1
    fieldsets = ((None, {'fields': (('title', 'file_attachment'))}),)


class BaseNewsletterAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('title', 'mailing_list', 'status',
                    'sending_date',
                    'historic_link', 'statistics_link')
    list_filter = ('status', 'sending_date', 'creation_date', 'modification_date')
    search_fields = ('title', 'content', 'header_sender', 'header_reply')
    filter_horizontal = ['test_contacts']
    fieldsets = ((None, {'fields': ('title', 'import_url', 'content',)}),
                 (_('Receivers'), {'fields': ('mailing_list', 'test_contacts',)}),
                 (_('Sending'), {'fields': ('sending_date', 'status',)}),
                 (_('Miscellaneous'), {'fields': ('server', 'header_sender',
                                                  'header_reply', 'slug'),
                                       'classes': ('collapse',)}),
                 )
    prepopulated_fields = {'slug': ('title',)}
    inlines = (AttachmentAdminInline,)
    actions = ['send_mail_test', 'make_ready_to_send', 'make_cancel_sending']
    actions_on_top = False
    actions_on_bottom = True



    def get_actions(self, request):
        actions = super(BaseNewsletterAdmin, self).get_actions(request)
        if not request.user.has_perm('newsletter.can_change_status'):
            del actions['make_ready_to_send']
            del actions['make_cancel_sending']
        return actions

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'status' and \
               not request.user.has_perm('newsletter.can_change_status'):
            kwargs['choices'] = ((Newsletter.DRAFT, _('Default')),)
            return db_field.formfield(**kwargs)
        return super(BaseNewsletterAdmin, self).formfield_for_choice_field(
            db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'test_contacts':
            queryset = Contact.objects.filter(tester=True)
            kwargs['queryset'] = queryset
        return super(BaseNewsletterAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs)

    def save_model(self, request, newsletter, form, change):
        if len(newsletter.import_url):
            try:
                with urllib.request.urlopen(newsletter.import_url) as response:
                    charset=response.info().get_content_charset()
                    data=response.read().decode(charset)
                    split_url = urllib.parse.urlsplit(newsletter.import_url)
                    
                    premailer = Premailer(data, base_url=split_url.scheme+"://"+split_url.netloc+"/")
                    newsletter.content = premailer.transform()
                    newsletter.import_url = ""
            except ExternalNotFoundError as e:
                    self.message_user(request, _('Missing external file %s') % e)
            except PremailerError:
                    self.message_user(request, _('Unable to download HTML, due to errors within.'))
        if not request.user.has_perm('newsletter.can_change_status'):
            newsletter.status = form.initial.get('status', Newsletter.DRAFT)

        newsletter.save()

    def historic_link(self, newsletter):
        """Display link for historic"""
        if newsletter.contactmailingstatus_set.count():
            return mark_safe('<a href="%s">%s</a>' % (newsletter.get_historic_url(), _('View historic')))
        return _('Not available')
    historic_link.allow_tags = True
    historic_link.short_description = _('Historic')

    def statistics_link(self, newsletter):
        """Display link for statistics"""
        if newsletter.status == Newsletter.SENDING or \
           newsletter.status == Newsletter.SENT:
            return mark_safe('<a href="%s">%s</a>' % (newsletter.get_statistics_url(), _('View statistics')))
        return _('Not available')
    statistics_link.allow_tags = True
    statistics_link.short_description = _('Statistics')

    def send_mail_test(self, request, queryset):
        """Send newsletter in test"""
        for newsletter in queryset:
            if newsletter.test_contacts.count():
                mailer = Mailer(newsletter, test=True)
                try:
                    mailer.run()
                except Exception as e:
                    self.message_user(request, _('Error : %s') % e)
                    continue
                self.message_user(request, _('%s succesfully sent.') % newsletter)
            else:
                self.message_user(request, _('No test contacts assigned for %s.') % newsletter)
    send_mail_test.short_description = _('Send test email')

    def make_ready_to_send(self, request, queryset):
        """Make newsletter ready to send"""
        queryset = queryset.filter(status=Newsletter.DRAFT)
        for newsletter in queryset:
            newsletter.status = Newsletter.WAITING
            newsletter.save()
        self.message_user(request, _('%s newletters are ready to send') % queryset.count())
    make_ready_to_send.short_description = _('Make ready to send')

    def make_cancel_sending(self, request, queryset):
        """Cancel the sending of newsletters"""
        queryset = queryset.filter(Q(status=Newsletter.WAITING) |
                                   Q(status=Newsletter.SENDING))
        for newsletter in queryset:
            newsletter.status = Newsletter.CANCELED
            newsletter.save()
        self.message_user(request, _('%s newletters are cancelled') % queryset.count())
    make_cancel_sending.short_description = _('Cancel the sending')


if USE_TINYMCE:
    from tinymce.widgets import TinyMCE

    class NewsletterTinyMCEForm(forms.ModelForm):
        content = forms.CharField(
            widget=TinyMCE(attrs={'cols': 150, 'rows': 80}))

        class Meta:
            fields = '__all__'
            model = Newsletter

    class NewsletterAdmin(BaseNewsletterAdmin):
        form = NewsletterTinyMCEForm
else:
    class NewsletterAdmin(BaseNewsletterAdmin):
        pass
