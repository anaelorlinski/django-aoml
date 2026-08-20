"""ModelAdmin for Newsletter"""

from django import forms
from django.db import router
from django.db.models import Q
from django.contrib.admin.utils import NestedObjects
from django.contrib.admin.utils import quote
from django.urls import NoReverseMatch
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import capfirst
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

from ..models import Contact
from ..models import Newsletter
from ..models import ContactMailingStatus
from ..models import Attachment
from ..models import MailingList
from ..mailer import Mailer
from ..settings import USE_TINYMCE
from ..settings import USE_WORKGROUPS
import urllib.request
import urllib.parse
from premailer import Premailer
from premailer.premailer import PremailerError, ExternalNotFoundError


class NestedObjectsWithoutStatuses(NestedObjects):
    """NestedObjects collector that ignores ContactMailingStatus rows, so
    they are never instantiated when building the delete confirmation."""

    def related_objects(self, related_model, related_fields, objs):
        if related_model is ContactMailingStatus:
            # Return an empty, never-evaluated queryset: Collector.collect()
            # evaluates the related queryset (``if sub_objs:``) before
            # cascading, which would load every status in memory.
            return ContactMailingStatus.objects.none()
        return super(NestedObjectsWithoutStatuses, self).related_objects(
            related_model, related_fields, objs)


def get_deleted_objects_without_statuses(objs, request, admin_site):
    """Same as django.contrib.admin.utils.get_deleted_objects but using
    NestedObjectsWithoutStatuses."""
    try:
        obj = objs[0]
    except IndexError:
        return [], {}, set(), []
    else:
        using = router.db_for_write(obj._meta.model)
    collector = NestedObjectsWithoutStatuses(using=using, origin=objs)
    collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        model = obj.__class__
        opts = obj._meta
        no_edit_link = '%s: %s' % (capfirst(opts.verbose_name), obj)
        if admin_site.is_registered(model):
            if not admin_site._registry[model].has_delete_permission(
                    request, obj):
                perms_needed.add(opts.verbose_name)
            try:
                admin_url = reverse(
                    '%s:%s_%s_change' % (admin_site.name, opts.app_label,
                                         opts.model_name),
                    None, (quote(obj.pk),))
            except NoReverseMatch:
                return no_edit_link
            return format_html('{}: <a href="{}">{}</a>',
                               capfirst(opts.verbose_name), admin_url, obj)
        return no_edit_link

    to_delete = collector.nested(format_callback)
    protected = [format_callback(obj) for obj in collector.protected]
    model_count = {
        model._meta.verbose_name_plural: len(objs)
        for model, objs in collector.model_objs.items()
    }
    return to_delete, model_count, perms_needed, protected


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

    def get_deleted_objects(self, objs, request):
        """Keep the (potentially huge) set of ContactMailingStatus out of the
        delete confirmation page: Django's NestedObjects collector loads every
        related row in memory and renders its __str__ (2 queries each).
        Show a single summary line with the count instead. The actual
        deletion is unaffected: the ORM fast-deletes statuses with a single
        DELETE query since nothing references them and they have no signals."""
        deleted_objects, model_count, perms_needed, protected = \
            get_deleted_objects_without_statuses(objs, request, self.admin_site)
        status_count = ContactMailingStatus.objects.filter(
            newsletter__in=objs).count()
        if status_count:
            opts = ContactMailingStatus._meta
            deleted_objects.append(
                _('%(count)d %(name)s (not listed)') % {
                    'count': status_count,
                    'name': opts.verbose_name_plural})
            model_count[opts.verbose_name_plural] = status_count
        return deleted_objects, model_count, perms_needed, protected

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

    @admin.display(
        description=_('Historic')
    )
    def historic_link(self, newsletter):
        """Display link for historic"""
        if newsletter.contactmailingstatus_set.count():
            return mark_safe('<a href="%s">%s</a>' % (newsletter.get_historic_url(), _('View historic')))
        return _('Not available')

    @admin.display(
        description=_('Statistics')
    )
    def statistics_link(self, newsletter):
        """Display link for statistics"""
        if newsletter.status == Newsletter.SENDING or \
           newsletter.status == Newsletter.SENT:
            return mark_safe('<a href="%s">%s</a>' % (newsletter.get_statistics_url(), _('View statistics')))
        return _('Not available')

    @admin.action(
        description=_('Send test email')
    )
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

    @admin.action(
        description=_('Make ready to send')
    )
    def make_ready_to_send(self, request, queryset):
        """Make newsletter ready to send"""
        queryset = queryset.filter(status=Newsletter.DRAFT)
        for newsletter in queryset:
            newsletter.status = Newsletter.WAITING
            newsletter.save()
        self.message_user(request, _('%s newletters are ready to send') % queryset.count())

    @admin.action(
        description=_('Cancel the sending')
    )
    def make_cancel_sending(self, request, queryset):
        """Cancel the sending of newsletters"""
        queryset = queryset.filter(Q(status=Newsletter.WAITING) |
                                   Q(status=Newsletter.SENDING))
        for newsletter in queryset:
            newsletter.status = Newsletter.CANCELED
            newsletter.save()
        self.message_user(request, _('%s newletters are cancelled') % queryset.count())


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
