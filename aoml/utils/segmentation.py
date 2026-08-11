"""Segmentation of a mailing list by newsletter activity.

Splits the audience of a mailing list in three buckets, over a sliding
window of N months:

- ``active``       : opened at least one newsletter during the window,
- ``inactive``     : was mailed during the window but never opened,
- ``never_mailed`` : received nothing during the window, so there is
                     nothing to judge them on.

The third bucket is the whole point of this being three buckets and not
two. "Has not opened anything in 12 months" is true both of a subscriber
who ignored 40 newsletters and of one who subscribed last week and has
not been sent anything yet. Dropping the second kind is a bug, so they
are kept apart and the caller decides explicitly what to do with them.
"""
import calendar

from django.db import transaction
from django.db.models import Max
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..models import ContactMailingStatus as Status
from ..models import MailingList


#: Statuses that prove a human being looked at the newsletter. A click is
#: counted as an opening because image tracking is blocked far more often
#: than links are rewritten: a contact who clicks but whose OPENED never
#: fired is engaged, not dormant.
OPENING_STATUSES = (Status.OPENED, Status.OPENED_ON_SITE, Status.LINK_OPENED)

DEFAULT_INACTIVITY_MONTHS = 12

#: Which newsletters count as activity.
SCOPE_ANY = 'any'
SCOPE_LIST = 'list'
SCOPE_CHOICES = (
    (SCOPE_ANY, _('any newsletter')),
    (SCOPE_LIST, _('only the newsletters of this mailing list')),
)


def months_ago(months, reference_date=None):
    """Return the datetime `months` calendar months before `reference_date`
    (defaults to now). Clamped to the last day of the target month, so
    31/03 minus 1 month is 28/02 (or 29/02) and never overflows."""
    reference_date = reference_date or timezone.now()

    month = reference_date.month - 1 - months
    year = reference_date.year + month // 12
    month = month % 12 + 1
    day = min(reference_date.day, calendar.monthrange(year, month)[1])

    return reference_date.replace(year=year, month=month, day=day)


def annotate_activity(queryset, mailing_list=None, scope=SCOPE_ANY):
    """Annotate a Contact queryset with `last_opening_date` and
    `last_sending_date` (all time, not windowed), so a segment can be
    exported or displayed with the date it was decided on."""
    opening = Q(contactmailingstatus__status__in=OPENING_STATUSES)
    sending = Q(contactmailingstatus__status=Status.SENT)

    if scope == SCOPE_LIST and mailing_list is not None:
        in_list = Q(contactmailingstatus__newsletter__mailing_list=mailing_list)
        opening &= in_list
        sending &= in_list

    return queryset.annotate(
        last_opening_date=Max('contactmailingstatus__creation_date',
                              filter=opening),
        last_sending_date=Max('contactmailingstatus__creation_date',
                              filter=sending))


class MailingListSegmentation(object):
    """The three buckets of a mailing list for a given window.

    Every bucket is a lazy Contact queryset: nothing hits the database
    until it is counted, iterated or exported.
    """

    def __init__(self, mailing_list, months=DEFAULT_INACTIVITY_MONTHS,
                 reference_date=None, scope=SCOPE_ANY,
                 include_unsubscribers=False):
        self.mailing_list = mailing_list
        self.months = months
        self.scope = scope
        self.include_unsubscribers = include_unsubscribers
        self.reference_date = reference_date or timezone.now()
        self.cutoff = months_ago(months, self.reference_date)

        if include_unsubscribers:
            self.audience = mailing_list.subscribers.all()
        else:
            self.audience = mailing_list.expedition_set()

        status = Status.objects.filter(creation_date__gte=self.cutoff,
                                       contact__in=self.audience.values('id'))
        if scope == SCOPE_LIST:
            status = status.filter(newsletter__mailing_list=mailing_list)

        self.opened = status.filter(status__in=OPENING_STATUSES).values('contact')
        self.mailed = status.filter(status=Status.SENT).values('contact')

        self.active = self.audience.filter(id__in=self.opened)
        self.inactive = self.audience.filter(id__in=self.mailed).exclude(id__in=self.opened)
        self.never_mailed = self.audience.exclude(id__in=self.mailed).exclude(id__in=self.opened)

    def droppable(self, include_never_mailed=False):
        """The contacts to consider dropping: the inactive ones, plus the
        never mailed ones only if the caller insists."""
        if include_never_mailed:
            return self.audience.exclude(id__in=self.opened)
        return self.inactive

    def counts(self):
        return {'audience': self.audience.count(),
                'active': self.active.count(),
                'inactive': self.inactive.count(),
                'never_mailed': self.never_mailed.count()}

    def annotate(self, queryset):
        """Add the activity dates to one of the buckets."""
        return annotate_activity(queryset, self.mailing_list, self.scope)

    def describe(self):
        """One-line, human readable description of the criteria used.
        Stored on the created lists so a list found six months later still
        says what it was made of."""
        scope = dict(SCOPE_CHOICES)[self.scope]
        return _('Openings of %(scope)s between %(start)s and %(end)s '
                 '(%(months)s months), computed from "%(list)s"'
                 '%(unsubscribers)s.') % {
            'scope': scope,
            'start': self.cutoff.strftime('%Y-%m-%d'),
            'end': self.reference_date.strftime('%Y-%m-%d'),
            'months': self.months,
            'list': self.mailing_list.name,
            'unsubscribers': self.include_unsubscribers
                             and _(', unsubscribers included') or ''}

    @transaction.atomic
    def create_mailing_lists(self, name_prefix=None, include_never_mailed=False):
        """Create the two fresh lists, and return them as
        ``(active_list, inactive_list)``.

        The new lists deliberately get no ``list_id`` override: they are new
        audiences and must be identified as such, not inherit the identity
        of the list they came from.
        """
        prefix = name_prefix or self.mailing_list.name
        stamp = self.reference_date.strftime('%Y-%m-%d')
        criteria = self.describe()

        active_list = MailingList.objects.create(
            name=_('%(prefix)s - openers %(months)s months (%(stamp)s)') % {
                'prefix': prefix, 'months': self.months, 'stamp': stamp},
            description=_('Contacts who opened at least one newsletter. %s') % criteria)
        active_list.subscribers.add(*self.active.values_list('id', flat=True))

        droppable = self.droppable(include_never_mailed)
        inactive_list = MailingList.objects.create(
            name=_('%(prefix)s - non openers %(months)s months (%(stamp)s)') % {
                'prefix': prefix, 'months': self.months, 'stamp': stamp},
            description=_('Contacts who opened no newsletter%(never)s. %(criteria)s') % {
                'never': include_never_mailed
                         and _(', including those mailed nothing during the period') or '',
                'criteria': criteria})
        inactive_list.subscribers.add(*droppable.values_list('id', flat=True))

        return active_list, inactive_list


def segment_mailing_list(mailing_list, months=DEFAULT_INACTIVITY_MONTHS,
                         reference_date=None, scope=SCOPE_ANY,
                         include_unsubscribers=False):
    """Shortcut for `MailingListSegmentation`."""
    return MailingListSegmentation(mailing_list, months=months,
                                   reference_date=reference_date,
                                   scope=scope,
                                   include_unsubscribers=include_unsubscribers)
