"""Utils for newsletter"""
from bs4 import BeautifulSoup
from django.core.urlresolvers import reverse

from ..models import Link
from ..settings import USE_PRETTIFY
from ..settings import BS_PARSER

def track_links(content, context):
    """Convert all links in the template for the user
    to track his navigation"""
    if not context.get('uidb36'):
        return content

    soup = BeautifulSoup(content, BS_PARSER)
    for link_markup in soup('a'):
        if link_markup.get('href') and \
               'no-track' not in link_markup.get('rel', ''):
            link_href = link_markup['href']
            link_title = link_markup.get('title', link_href)
            link, created = Link.objects.get_or_create(url=link_href,
                                                       defaults={'title': link_title})
            link_markup['href'] = 'http://%s%s' % (context['domain'], reverse('newsletter_newsletter_tracking_link',
                                                                              args=[context['newsletter'].slug,
                                                                                    context['uidb36'], context['token'],
                                                                                    link.pk]))
    if USE_PRETTIFY:
        return soup.prettify()
    else:
        return soup.encode_contents()
