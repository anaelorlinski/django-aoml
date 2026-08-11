"""ModelAdmin for MailingList"""
from datetime import datetime

from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import path
from django.utils.encoding import smart_str
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe

from ..forms import MailingListSegmentationForm
from ..models import Contact
from ..models import MailingList
from ..utils.excel import ExcelResponse
from ..utils.segmentation import segment_mailing_list

class MailingListAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('name', 'effective_list_id', 'creation_date',
                    'subscribers_count', 'unsubscribers_count',
                    'activity_link', 'exportation_links')
    list_filter = ('creation_date', 'modification_date')
    search_fields = ('name', 'description', 'list_id',)
    filter_horizontal = ['subscribers', 'unsubscribers',]
    # list_id sits with the name because the two are connected: the
    # derived default follows the name, so showing them together is what
    # makes it visible that renaming re-identifies the list unless the
    # override is set.
    fieldsets = ((None, {'fields': ('name', 'description', 'list_id',)}),
                 )
    actions = ['merge_mailinglist', 'segment_mailinglist']
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

    @admin.action(
        description=_('Split by newsletter activity (openers / non openers)')
    )
    def segment_mailinglist(self, request, queryset):
        """Open the segmentation page for the selected mailing list"""
        if queryset.count() != 1:
            self.message_user(request, _('Please select exactly one mailing list.'),
                              level=messages.WARNING)
            return None

        return HttpResponseRedirect(
            reverse('admin:newsletter_mailinglist_segment',
                    args=[queryset[0].pk]))

    def segmentation(self, request, mailinglist_id):
        """Split a mailing list between the contacts who opened a newsletter
        during the last N months and those who did not.

        The page recomputes on every submission and only writes anything when
        the "create" button is used, so the numbers can be explored freely
        before committing to two new lists.
        """
        mailinglist = get_object_or_404(MailingList, pk=mailinglist_id)
        opts = self.model._meta

        if not self.has_view_permission(request, mailinglist):
            raise PermissionDenied

        form = MailingListSegmentationForm(request.POST or None)
        criteria = form.criteria()
        segmentation = segment_mailing_list(
            mailinglist,
            months=criteria['months'],
            scope=criteria['scope'],
            include_unsubscribers=criteria['include_unsubscribers'])

        if request.method == 'POST' and form.is_valid():
            if 'export' in request.POST:
                return self.export_segment_csv(
                    request, segmentation, request.POST['export'],
                    criteria['include_never_mailed'])

            if 'create' in request.POST:
                if not self.has_add_permission(request):
                    raise PermissionDenied
                active_list, inactive_list = segmentation.create_mailing_lists(
                    name_prefix=criteria['name_prefix'],
                    include_never_mailed=criteria['include_never_mailed'])
                self.message_user(
                    request,
                    _('"%(active)s" (%(active_count)s contacts) and '
                      '"%(inactive)s" (%(inactive_count)s contacts) '
                      'successfully created.') % {
                        'active': active_list.name,
                        'active_count': active_list.subscribers.count(),
                        'inactive': inactive_list.name,
                        'inactive_count': inactive_list.subscribers.count()})
                return HttpResponseRedirect(
                    reverse('admin:aoml_mailinglist_changelist'))

        counts = segmentation.counts()
        audience = counts['audience']
        segments = [
            {'key': 'active',
             'title': _('Openers'),
             'help': _('Opened or clicked at least one newsletter during the period.'),
             'count': counts['active'],
             'percent': percentage(counts['active'], audience)},
            {'key': 'inactive',
             'title': _('Non openers'),
             'help': _('Received at least one newsletter during the period, opened none.'),
             'count': counts['inactive'],
             'percent': percentage(counts['inactive'], audience)},
            {'key': 'never_mailed',
             'title': _('Never mailed'),
             'help': _('Received nothing during the period: nothing to judge them on.'),
             'count': counts['never_mailed'],
             'percent': percentage(counts['never_mailed'], audience)},
        ]

        context = {'title': _('Activity of %s') % mailinglist.name,
                   'opts': opts,
                   'app_label': opts.app_label,
                   'root_path': reverse('admin:index'),
                   'mailinglist': mailinglist,
                   'form': form,
                   'segmentation': segmentation,
                   'cutoff': segmentation.cutoff,
                   'audience_count': audience,
                   'segments': segments,
                   'media': self.media + form.media}

        return render(request, 'newsletter/mailinglist_segmentation.html', context)

    def export_segment_csv(self, request, segmentation, segment_key,
                           include_never_mailed=False):
        """Export one segment, with the dates it was decided on"""
        querysets = {'active': segmentation.active,
                     'inactive': segmentation.droppable(include_never_mailed),
                     'never_mailed': segmentation.never_mailed}
        if segment_key not in querysets:
            return HttpResponseRedirect(request.get_full_path())

        contacts = segmentation.annotate(querysets[segment_key])
        rows = [{'email': contact.email,
                 'subscription_date': format_date(contact.creation_date),
                 'last_sending_date': format_date(contact.last_sending_date),
                 'last_opening_date': format_date(contact.last_opening_date)}
                for contact in contacts]

        if not rows:
            self.message_user(request, _('This segment is empty, nothing to export.'),
                              level=messages.WARNING)
            return HttpResponseRedirect(request.get_full_path())

        name = '%s_%s_%smonths' % (smart_str(segmentation.mailing_list.name),
                                   segment_key, segmentation.months)
        return ExcelResponse(rows, name)

    @admin.display(
        description=_('Activity')
    )
    def activity_link(self, mailinglist):
        """Display a link to the segmentation page"""
        return mark_safe('<a href="%s">%s</a>' % (
            reverse('admin:newsletter_mailinglist_segment',
                    args=[mailinglist.pk]), _('Openers / non openers')))

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
                               name='newsletter_mailinglist_export_csv'),
                    path('segment/<int:mailinglist_id>/',
                               self.admin_site.admin_view(self.segmentation),
                               name='newsletter_mailinglist_segment')]
        return my_urls + urls


def percentage(value, total):
    """Share of `value` in `total`, in percent"""
    if not total:
        return 0.0
    return round(float(value) / float(total) * 100, 1)


def format_date(date):
    """Local date of a datetime, empty when there is none"""
    if not date:
        return ''
    if not timezone.is_naive(date):
        date = timezone.localtime(date)
    return date.strftime('%Y-%m-%d')
