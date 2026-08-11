"""Command for splitting a mailing list between openers and non openers"""
import csv
import sys

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from ...models import MailingList
from ...utils.segmentation import DEFAULT_INACTIVITY_MONTHS
from ...utils.segmentation import SCOPE_ANY
from ...utils.segmentation import SCOPE_LIST
from ...utils.segmentation import segment_mailing_list


class Command(BaseCommand):

    """Report, and optionally split, the activity of a mailing list"""
    help = ('Split a mailing list between the contacts who opened a newsletter '
            'during the last months and those who did not. Reports only, '
            'unless --create-lists or --export is given.')

    def add_arguments(self, parser):
        parser.add_argument(
            'mailinglist',
            help='Id or exact name of the mailing list')
        parser.add_argument(
            '--months', type=int, default=DEFAULT_INACTIVITY_MONTHS,
            help='Length in months of the period looked at '
                 '(default: %s)' % DEFAULT_INACTIVITY_MONTHS)
        parser.add_argument(
            '--scope', choices=[SCOPE_ANY, SCOPE_LIST], default=SCOPE_ANY,
            help='Count the openings of any newsletter ("any", the default) '
                 'or only of the newsletters of this list ("list")')
        parser.add_argument(
            '--include-unsubscribers', action='store_true',
            help='Keep the contacts who unsubscribed from the list')
        parser.add_argument(
            '--include-never-mailed', action='store_true',
            help='Count the contacts mailed nothing during the period as non '
                 'openers, instead of leaving them out')
        parser.add_argument(
            '--create-lists', action='store_true',
            help='Create the two mailing lists')
        parser.add_argument(
            '--name-prefix', default='',
            help='Prefix of the created lists (default: the name of the list)')
        parser.add_argument(
            '--export', choices=['active', 'inactive', 'never_mailed'],
            help='Write the emails of a segment as CSV on stdout')

    def handle(self, *args, **options):
        verbose = int(options['verbosity'])
        mailinglist = self.get_mailinglist(options['mailinglist'])

        segmentation = segment_mailing_list(
            mailinglist,
            months=options['months'],
            scope=options['scope'],
            include_unsubscribers=options['include_unsubscribers'])

        if options['export']:
            # Reporting goes to stderr so that stdout stays a clean CSV.
            self.export(segmentation, options['export'],
                        options['include_never_mailed'])
            return

        counts = segmentation.counts()
        if verbose:
            self.stdout.write('Mailing list: %s' % mailinglist.name)
            self.stdout.write('Period: since %s (%s months), openings of %s' % (
                segmentation.cutoff.strftime('%Y-%m-%d'), options['months'],
                options['scope'] == SCOPE_LIST and 'this list' or 'any newsletter'))
            self.stdout.write('Audience:     %s' % counts['audience'])
            self.stdout.write('Openers:      %s' % counts['active'])
            self.stdout.write('Non openers:  %s' % counts['inactive'])
            self.stdout.write('Never mailed: %s' % counts['never_mailed'])

        if options['create_lists']:
            active_list, inactive_list = segmentation.create_mailing_lists(
                name_prefix=options['name_prefix'],
                include_never_mailed=options['include_never_mailed'])
            if verbose:
                self.stdout.write('Created "%s" with %s contacts' % (
                    active_list.name, active_list.subscribers.count()))
                self.stdout.write('Created "%s" with %s contacts' % (
                    inactive_list.name, inactive_list.subscribers.count()))

    def get_mailinglist(self, identifier):
        if identifier.isdigit():
            try:
                return MailingList.objects.get(pk=int(identifier))
            except MailingList.DoesNotExist:
                raise CommandError('No mailing list with id %s' % identifier)
        try:
            return MailingList.objects.get(name=identifier)
        except MailingList.DoesNotExist:
            raise CommandError('No mailing list named "%s"' % identifier)
        except MailingList.MultipleObjectsReturned:
            raise CommandError('Several mailing lists are named "%s", '
                               'use their id instead' % identifier)

    def export(self, segmentation, segment_key, include_never_mailed):
        querysets = {'active': segmentation.active,
                     'inactive': segmentation.droppable(include_never_mailed),
                     'never_mailed': segmentation.never_mailed}
        contacts = segmentation.annotate(querysets[segment_key])

        writer = csv.writer(sys.stdout)
        writer.writerow(['email', 'last_sending_date', 'last_opening_date'])
        for contact in contacts.iterator():
            writer.writerow([
                contact.email,
                contact.last_sending_date and contact.last_sending_date.strftime('%Y-%m-%d') or '',
                contact.last_opening_date and contact.last_opening_date.strftime('%Y-%m-%d') or ''])
