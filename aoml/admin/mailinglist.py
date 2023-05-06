"""ModelAdmin for MailingList"""
from datetime import datetime

from django.contrib import admin
from django.urls import path
from django.utils.encoding import smart_str
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe

from ..models import Contact
from ..models import MailingList
from ..utils.excel import ExcelResponse

class MailingListAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('name', 'creation_date',
                    'subscribers_count', 'unsubscribers_count',
                    'exportation_links')
    list_filter = ('creation_date', 'modification_date')
    search_fields = ('name', 'description',)
    filter_horizontal = ['subscribers', 'unsubscribers',]
    fieldsets = ((None, {'fields': ('name', 'description',)}),
                 )
    actions = ['merge_mailinglist']
    actions_on_top = False
    actions_on_bottom = True

    @admin.action(
        description=_('Merge selected mailinglists')
    )
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

    @admin.display(
        description=_('Export')
    )
    def exportation_links(self, mailinglist):
        """Display links for exportation"""
        return mark_safe('<a href="%s">%s</a>' % (
            reverse('admin:newsletter_mailinglist_export_csv',
                    args=[mailinglist.pk]), _('CSV')))

    def export_csv(self, request, mailinglist_id):
        """Export subscribers in the mailing in CSV"""
        mailinglist = get_object_or_404(MailingList, pk=mailinglist_id)
        name = 'contacts_%s' % smart_str(mailinglist.name)
        return ExcelResponse(mailinglist.subscribers.all(), name)

    def get_urls(self):
        urls = super(MailingListAdmin, self).get_urls()
        my_urls = [ path('export/csv/<int:mailinglist_id>/',
                               self.admin_site.admin_view(self.export_csv),
                               name='newsletter_mailinglist_export_csv')]
        return my_urls + urls
