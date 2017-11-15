"""Command for sending the newsletter"""
from django.conf import settings
from django.utils.translation import activate
from django.core.management.base import NoArgsCommand, BaseCommand
from optparse import make_option

from emencia.django.newsletter.mailer import Mailer
from emencia.django.newsletter.models import Newsletter


class Command(NoArgsCommand):

    """Send the newsletter in queue"""
    help = 'Send the newsletter in queue'

    option_list = BaseCommand.option_list + (
        make_option('--test',
                    action='store_true',
                    dest='test',
                    default=False,
                    help='test only',
                    ),
    )

    def handle_noargs(self, **options):
        verbose = int(options['verbosity'])

        if verbose:
            print('Starting sending newsletters...')

        activate(settings.LANGUAGE_CODE)

        is_test = options.get('test', False)

        for newsletter in Newsletter.objects.exclude(
                status=Newsletter.DRAFT).exclude(status=Newsletter.SENT):
            mailer = Mailer(newsletter, test=is_test, verbose=verbose)
            if mailer.can_send:
                if verbose:
                    print('Start emailing %s' % str(
                        newsletter.title).encode('utf-8'))
                mailer.run()

        if verbose:
            print('End session sending')
