"""ModelAdmin for Contact"""
import io

from django.conf import settings
from datetime import datetime

from django.contrib import admin
from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.contrib.admin.views.main import ChangeList
from django.db import DatabaseError
from django.forms import Form, ModelChoiceField

from ..models import MailingList
from ..utils.importation import text_contacts_import
from ..utils.excel import ExcelResponse

class MailingListForm(Form):
    mailinglist = ModelChoiceField(queryset=MailingList.objects.all().order_by('name'))

class ContactAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('email', 'tester',
                    'total_subscriptions', 'creation_date', 'related_object_admin')
    list_filter = ('tester', 'creation_date', 'modification_date')
    search_fields = ('email', )
    fieldsets = ((None, {'fields': ('email', )}),
                 (_('Status'), {'fields': ('tester',)}),
                 (_('Advanced'), {'fields': ('object_id', 'content_type'),
                                  'classes': ('collapse',)}),
                 )
    actions = ['create_mailinglist', 'export_excel']
    actions_on_top = False
    actions_on_bottom = True

    def related_object_admin(self, contact):
        """Display link to related object's admin"""
        if contact.content_type and contact.object_id:
            admin_url = reverse('admin:%s_%s_change' % (contact.content_type.app_label,
                                                        contact.content_type.model),
                                args=(contact.object_id,))
            return '%s: <a href="%s">%s</a>' % (contact.content_type.model.capitalize(),
                                                admin_url,
                                                contact.content_object.__str__())
        return _('No relative object')
    related_object_admin.allow_tags = True
    related_object_admin.short_description = _('Related object')

    def total_subscriptions(self, contact):
        """Display user subscriptions to unsubscriptions"""
        subscriptions = contact.subscriptions().count()
        return '%s' % (subscriptions)
    total_subscriptions.short_description = _('Total subscriptions')

    def export_excel(self, request, queryset, export_name=''):
        """Export selected contact in Excel"""
        if not export_name:
            export_name = 'contacts_edn_%s' % datetime.now().strftime('%d-%m-%Y')
        return ExcelResponse(queryset, export_name)
    export_excel.short_description = _('Export contacts in Excel')

    def importation(self, request):
        """Import contacts from a VCard"""
        opts = self.model._meta

        form = MailingListForm()
        if request.POST:
            form = MailingListForm(request.POST)
            if form.is_valid():
                # try reading as an uploaded file
                source = request.FILES.get('source')
                if source:
                    source.seek(0)
                    source = io.StringIO(source.read().decode('utf-8'))
                else:
                    source = io.StringIO(request.POST.get('source', ''))
                inserted = text_contacts_import(source, form.cleaned_data['mailinglist'])
                self.message_user(request, _('%s contacts succesfully imported.') % inserted)

        context = {'title': _('Contact importation'),
                   'opts': opts,
                   #'root_path': self.admin_site.root_path,
                   'root_path': reverse('admin:index'),
                   'app_label': opts.app_label,
                   'form':form}

        return render(request, 'newsletter/contact_import.html', context)

    def filtered_request_queryset(self, request):
        """Return queryset filtered by the admin list view"""
        cl = ChangeList(request, self.model, self.list_display,
                        self.list_display_links, self.list_filter,
                        self.date_hierarchy, self.search_fields,
                        self.list_select_related, self.list_per_page,
                        self.list_max_show_all, self.list_editable, self)
        return cl.get_queryset(request)

    def creation_mailinglist(self, request):
        """Create a mailing list form the filtered contacts"""
        return self.create_mailinglist(request, self.filtered_request_queryset(request))

    def exportation_excel(self, request):
        """Export filtered contacts in Excel"""
        return self.export_excel(request, self.filtered_request_queryset(request),
                                 'contacts_edn_%s' % datetime.now().strftime('%d-%m-%Y'))

    def get_urls(self):
        urls = super(ContactAdmin, self).get_urls()
        my_urls = [
                           url(r'^import/$',
                               self.admin_site.admin_view(self.importation),
                               name='newsletter_contact_import'),
                           url(r'^create_mailinglist/$',
                               self.admin_site.admin_view(self.creation_mailinglist),
                               name='newsletter_contact_create_mailinglist'),
                           url(r'^export/excel/$',
                               self.admin_site.admin_view(self.exportation_excel),
                               name='newsletter_contact_export_excel'),]
        return my_urls + urls
