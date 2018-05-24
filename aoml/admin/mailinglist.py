"""ModelAdmin for MailingList"""
from datetime import datetime

from django.contrib import admin
from django.conf.urls import url
from django.utils.encoding import smart_str
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect

from ..models import Contact
from ..models import MailingList
from ..utils.excel import ExcelResponse

class MailingListAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('creation_date', 'name', 'description',
                    'subscribers_count',
                    'exportation_links')
    list_editable = ('name', 'description')
    list_filter = ('creation_date', 'modification_date')
    search_fields = ('name', 'description',)
    filter_horizontal = ['subscribers',]
    fieldsets = ((None, {'fields': ('name', 'description',)}),
                 (None, {'fields': ('subscribers',)}),
                 )
    actions = ['merge_mailinglist']
    actions_on_top = False
    actions_on_bottom = True

    # filter the contacts excluding the ones with unsubscribed flag
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "subscribers":
            kwargs["queryset"] = Contact.objects.filter(unsubscribed=False)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def merge_mailinglist(self, request, queryset):
        """Merge multiple mailing list"""
        if queryset.count() == 1:
            self.message_user(request, _('Please select a least 2 mailing list.'))
            return None

        subscribers = {}
        for ml in queryset:
            for contact in ml.subscribers.all():
                subscribers[contact] = ''

        when = str(datetime.now()).split('.')[0]
        new_mailing = MailingList(name=_('Merging list at %s') % when,
                                  description=_('Mailing list created by merging at %s') % when)
        new_mailing.save()
        new_mailing.subscribers = list(subscribers.keys())
        
        self.message_user(request, _('%s succesfully created by merging.') % new_mailing)
        return HttpResponseRedirect(reverse('admin:aoml_mailinglist_change',
                                            args=[new_mailing.pk]))
    merge_mailinglist.short_description = _('Merge selected mailinglists')

    def exportation_links(self, mailinglist):
        """Display links for exportation"""
        return '<a href="%s">%s</a>' % (
            reverse('admin:newsletter_mailinglist_export_csv',
                    args=[mailinglist.pk]), _('CSV'))
    exportation_links.allow_tags = True
    exportation_links.short_description = _('Export')

    def export_csv(self, request, mailinglist_id):
        """Export subscribers in the mailing in CSV"""
        mailinglist = get_object_or_404(MailingList, pk=mailinglist_id)
        name = 'contacts_%s' % smart_str(mailinglist.name)
        return ExcelResponse(mailinglist.subscribers.all(), name)

    def get_urls(self):
        urls = super(MailingListAdmin, self).get_urls()
        my_urls = [ url(r'^export/csv/(?P<mailinglist_id>\d+)/$',
                               self.admin_site.admin_view(self.export_csv),
                               name='newsletter_mailinglist_export_csv')]
        return my_urls + urls
