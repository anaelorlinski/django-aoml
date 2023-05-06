"""Views for . statistics"""
import csv
from datetime import timedelta

from django.db.models import Q
from django.http import HttpResponse
from django.template import RequestContext
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template.defaultfilters import date

from ..models import Newsletter
from ..models import ContactMailingStatus
from ..utils.statistics import get_newsletter_top_links
from ..utils.statistics import get_newsletter_statistics
from ..utils.statistics import get_newsletter_opening_statistics
from ..utils.statistics import get_newsletter_clicked_link_statistics

def get_statistics_period(newsletter):
    status = ContactMailingStatus.objects.filter(Q(status=ContactMailingStatus.OPENED) |
                                                 Q(status=ContactMailingStatus.OPENED_ON_SITE) |
                                                 Q(status=ContactMailingStatus.LINK_OPENED),
                                                 newsletter=newsletter)
    if not status:
        return []
    start_date = newsletter.sending_date.date()
    end_date = status.latest('creation_date').creation_date.date()

    period = []
    for i in range((end_date - start_date).days + 1):
        period.append(start_date + timedelta(days=i))
    return period

def get_daily_stats(newsletter):
    # days to display / hardcoded
    start = 0
    end = 10

    recipients = newsletter.mailing_list.expedition_set().count()

    sending_date = newsletter.sending_date.date()
    days = []

    for i in range(start, end + 1):
        day = sending_date + timedelta(days=i)
        day_status = ContactMailingStatus.objects.filter(newsletter=newsletter,
                                                         creation_date__day=day.day,
                                                         creation_date__month=day.month,
                                                         creation_date__year=day.year)

        opening_stats = get_newsletter_opening_statistics(day_status, recipients)
        click_stats = get_newsletter_clicked_link_statistics(day_status, recipients, 0)
        nday={}
        nday['label']=date(day, 'D d M y').capitalize()
        nday['openings']=opening_stats['total_openings']
        nday['clicks']=click_stats['total_clicked_links']
        
        days.append(nday)
    return days

@login_required
def view_newsletter_statistics(request, slug):
    """Display the statistics of a newsletters"""
    opts = Newsletter._meta
    newsletter = get_object_or_404(Newsletter, slug=slug)

    context = {'title': _('Statistics of %s') % newsletter.__str__(),
               'object': newsletter,
               'opts': opts,
               'object_id': newsletter.pk,
               'app_label': opts.app_label,
               'daily_stats': get_daily_stats(newsletter),
               'stats': get_newsletter_statistics(newsletter),
               'period': get_statistics_period(newsletter)}

    return render(request,'newsletter/newsletter_statistics.html', context)


@login_required
def view_newsletter_report(request, slug):
    newsletter = get_object_or_404(Newsletter, slug=slug)
    status = ContactMailingStatus.objects.filter(newsletter=newsletter,
                                                 creation_date__gte=newsletter.sending_date)
    links = set([s.link for s in status.exclude(link=None)])

    def header_line(links):
        link_cols = [smart_str(link.title) for link in links]
        return [smart_str(_('email')), smart_str(_('openings'))] + link_cols

    def contact_line(contact, links):
        contact_status = status.filter(contact=contact)

        link_cols = [contact_status.filter(status=ContactMailingStatus.LINK_OPENED,
                                           link=link).count() for link in links]
        openings = contact_status.filter(Q(status=ContactMailingStatus.OPENED) |
                                         Q(status=ContactMailingStatus.OPENED_ON_SITE)).count()
        return [smart_str(contact.email), openings] + link_cols

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=report-%s.csv' % newsletter.slug

    writer = csv.writer(response)
    writer.writerow(header_line(links))
    for contact in newsletter.mailing_list.expedition_set():
        writer.writerow(contact_line(contact, links))

    return response
