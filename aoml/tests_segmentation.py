"""Tests for the segmentation of a mailing list by newsletter activity.

In a separate module from tests.py, which still targets the pre-fork
emencia package and does not import.

    python manage.py test aoml.tests_segmentation
"""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from .models import Contact
from .models import ContactMailingStatus as Status
from .models import MailingList
from .models import Newsletter
from .models import SMTPServer
from .utils.segmentation import SCOPE_ANY
from .utils.segmentation import SCOPE_LIST
from .utils.segmentation import months_ago
from .utils.segmentation import segment_mailing_list


class MonthsAgoTestCase(TestCase):

    def setUp(self):
        # Built from now() so it follows the USE_TZ of the project
        self.reference = timezone.now().replace(year=2026, month=3, day=31,
                                                hour=10, minute=0)

    def test_same_day_of_month(self):
        self.assertEqual(months_ago(12, self.reference).date().isoformat(),
                         '2025-03-31')
        self.assertEqual(months_ago(3, self.reference).date().isoformat(),
                         '2025-12-31')

    def test_clamped_to_the_end_of_a_shorter_month(self):
        # 31/03 minus one month has no 31st to land on
        self.assertEqual(months_ago(1, self.reference).date().isoformat(),
                         '2026-02-28')

    def test_more_than_a_year(self):
        self.assertEqual(months_ago(14, self.reference).date().isoformat(),
                         '2025-01-31')


class SegmentationFixtureMixin(object):

    """A mailing list holding one contact of every kind, over a 12 months
    window: an opener, a clicker, a contact mailed but silent, one whose
    only opening is older than the window, one mailed nothing during the
    window, one who unsubscribed, and one who only opens another list."""

    def setUp(self):
        self.now = timezone.now()
        self.recent = self.now - timedelta(days=30)
        self.old = self.now - timedelta(days=500)

        self.server = SMTPServer.objects.create(name='server', host='host',
                                                tls=False)
        self.mailinglist = MailingList.objects.create(name='Main list')
        self.other_list = MailingList.objects.create(name='Other list')

        self.opener = Contact.objects.create(email='opener@example.com')
        self.clicker = Contact.objects.create(email='clicker@example.com')
        self.dormant = Contact.objects.create(email='dormant@example.com')
        self.old_opener = Contact.objects.create(email='old-opener@example.com')
        self.newbie = Contact.objects.create(email='newbie@example.com')
        self.gone = Contact.objects.create(email='gone@example.com')
        self.cross = Contact.objects.create(email='cross@example.com')

        self.mailinglist.subscribers.add(
            self.opener, self.clicker, self.dormant, self.old_opener,
            self.newbie, self.gone, self.cross)
        self.mailinglist.unsubscribers.add(self.gone)
        self.other_list.subscribers.add(self.cross)

        self.newsletter = Newsletter.objects.create(
            title='Newsletter', slug='newsletter', content='content',
            mailing_list=self.mailinglist, server=self.server,
            sending_date=self.recent)
        self.other_newsletter = Newsletter.objects.create(
            title='Other newsletter', slug='other-newsletter', content='content',
            mailing_list=self.other_list, server=self.server,
            sending_date=self.recent)

        for contact in (self.opener, self.clicker, self.dormant,
                        self.old_opener, self.gone, self.cross):
            self.stamp(contact, Status.SENT, self.recent)
        # Mailed, but before the window: nothing to hold against them
        self.stamp(self.newbie, Status.SENT, self.old)

        self.stamp(self.opener, Status.OPENED, self.recent)
        self.stamp(self.clicker, Status.LINK_OPENED, self.recent)
        self.stamp(self.old_opener, Status.OPENED, self.old)
        self.stamp(self.gone, Status.OPENED, self.recent)
        self.stamp(self.cross, Status.OPENED, self.recent,
                   newsletter=self.other_newsletter)

    def stamp(self, contact, status, when, newsletter=None):
        """Create a status at a chosen date, which auto_now_add forbids
        at creation time."""
        record = Status.objects.create(
            contact=contact, status=status,
            newsletter=newsletter or self.newsletter)
        Status.objects.filter(pk=record.pk).update(creation_date=when)
        return record

    def emails(self, queryset):
        return sorted(queryset.values_list('email', flat=True))


class SegmentationTestCase(SegmentationFixtureMixin, TestCase):

    def test_buckets(self):
        segmentation = segment_mailing_list(self.mailinglist)

        self.assertEqual(self.emails(segmentation.active),
                         ['clicker@example.com', 'cross@example.com',
                          'opener@example.com'])
        self.assertEqual(self.emails(segmentation.inactive),
                         ['dormant@example.com', 'old-opener@example.com'])
        self.assertEqual(self.emails(segmentation.never_mailed),
                         ['newbie@example.com'])

    def test_unsubscribers_are_left_out_by_default(self):
        segmentation = segment_mailing_list(self.mailinglist)
        self.assertEqual(segmentation.counts()['audience'], 6)
        self.assertNotIn('gone@example.com', self.emails(segmentation.active))

        segmentation = segment_mailing_list(self.mailinglist,
                                            include_unsubscribers=True)
        self.assertEqual(segmentation.counts()['audience'], 7)
        self.assertIn('gone@example.com', self.emails(segmentation.active))

    def test_a_click_counts_as_an_opening(self):
        segmentation = segment_mailing_list(self.mailinglist)
        self.assertIn('clicker@example.com', self.emails(segmentation.active))

    def test_scope_any_credits_the_openings_of_the_other_lists(self):
        segmentation = segment_mailing_list(self.mailinglist, scope=SCOPE_ANY)
        self.assertIn('cross@example.com', self.emails(segmentation.active))

    def test_scope_list_ignores_the_openings_of_the_other_lists(self):
        segmentation = segment_mailing_list(self.mailinglist, scope=SCOPE_LIST)
        self.assertEqual(self.emails(segmentation.active),
                         ['clicker@example.com', 'opener@example.com'])
        self.assertIn('cross@example.com', self.emails(segmentation.inactive))

    def test_an_opening_older_than_the_window_does_not_count(self):
        segmentation = segment_mailing_list(self.mailinglist)
        self.assertIn('old-opener@example.com', self.emails(segmentation.inactive))

        segmentation = segment_mailing_list(self.mailinglist, months=24)
        self.assertIn('old-opener@example.com', self.emails(segmentation.active))

    def test_droppable(self):
        segmentation = segment_mailing_list(self.mailinglist)
        self.assertEqual(self.emails(segmentation.droppable()),
                         ['dormant@example.com', 'old-opener@example.com'])
        self.assertEqual(self.emails(segmentation.droppable(include_never_mailed=True)),
                         ['dormant@example.com', 'newbie@example.com',
                          'old-opener@example.com'])

    def test_counts(self):
        self.assertEqual(segment_mailing_list(self.mailinglist).counts(),
                         {'audience': 6, 'active': 3, 'inactive': 2,
                          'never_mailed': 1})

    def test_empty_mailing_list(self):
        empty = MailingList.objects.create(name='Empty')
        self.assertEqual(segment_mailing_list(empty).counts(),
                         {'audience': 0, 'active': 0, 'inactive': 0,
                          'never_mailed': 0})

    def test_annotated_dates(self):
        segmentation = segment_mailing_list(self.mailinglist)
        contacts = dict((contact.email, contact) for contact
                        in segmentation.annotate(segmentation.inactive))

        self.assertIsNone(contacts['dormant@example.com'].last_opening_date)
        self.assertIsNotNone(contacts['dormant@example.com'].last_sending_date)
        # Outside of the window, but still the date it was decided on
        self.assertIsNotNone(contacts['old-opener@example.com'].last_opening_date)

    def test_create_mailing_lists(self):
        segmentation = segment_mailing_list(self.mailinglist)
        active_list, inactive_list = segmentation.create_mailing_lists()

        self.assertEqual(self.emails(active_list.subscribers.all()),
                         ['clicker@example.com', 'cross@example.com',
                          'opener@example.com'])
        self.assertEqual(self.emails(inactive_list.subscribers.all()),
                         ['dormant@example.com', 'old-opener@example.com'])
        self.assertIn('12 months', active_list.name)
        self.assertIn('Main list', active_list.description)

    def test_created_lists_do_not_inherit_the_list_id(self):
        self.mailinglist.list_id = 'main.example.com'
        self.mailinglist.save()

        active_list, inactive_list = segment_mailing_list(
            self.mailinglist).create_mailing_lists()

        for created in (active_list, inactive_list):
            self.assertEqual(created.list_id, '')
            self.assertNotEqual(created.effective_list_id,
                                self.mailinglist.effective_list_id)

    def test_create_mailing_lists_with_the_never_mailed(self):
        segmentation = segment_mailing_list(self.mailinglist)
        active_list, inactive_list = segmentation.create_mailing_lists(
            name_prefix='Cleanup', include_never_mailed=True)

        self.assertTrue(active_list.name.startswith('Cleanup'))
        self.assertEqual(self.emails(inactive_list.subscribers.all()),
                         ['dormant@example.com', 'newbie@example.com',
                          'old-opener@example.com'])

    def test_the_source_list_is_left_untouched(self):
        segmentation = segment_mailing_list(self.mailinglist)
        segmentation.create_mailing_lists()

        self.assertEqual(self.mailinglist.subscribers.count(), 7)
        self.assertEqual(self.mailinglist.unsubscribers.count(), 1)


class SegmentationCommandTestCase(SegmentationFixtureMixin, TestCase):

    def call(self, *arguments):
        output = StringIO()
        call_command('segment_mailinglist', *arguments, stdout=output)
        return output.getvalue()

    def test_report_only(self):
        output = self.call(str(self.mailinglist.pk))

        self.assertIn('Openers:      3', output)
        self.assertIn('Non openers:  2', output)
        self.assertIn('Never mailed: 1', output)
        self.assertEqual(MailingList.objects.count(), 2)

    def test_lookup_by_name(self):
        self.assertIn('Main list', self.call('Main list'))

    def test_unknown_mailing_list(self):
        self.assertRaises(CommandError, self.call, 'Nope')
        self.assertRaises(CommandError, self.call, '99999')

    def test_create_lists(self):
        self.call(str(self.mailinglist.pk), '--create-lists',
                  '--name-prefix', 'CLI')

        active_list = MailingList.objects.get(name__startswith='CLI - openers')
        inactive_list = MailingList.objects.get(name__startswith='CLI - non openers')
        self.assertEqual(active_list.subscribers.count(), 3)
        self.assertEqual(inactive_list.subscribers.count(), 2)

    def test_months_and_scope(self):
        self.call(str(self.mailinglist.pk), '--months', '24',
                  '--scope', SCOPE_LIST, '--create-lists')

        active_list = MailingList.objects.get(name__contains='- openers 24 months')
        self.assertEqual(self.emails(active_list.subscribers.all()),
                         ['clicker@example.com', 'old-opener@example.com',
                          'opener@example.com'])
