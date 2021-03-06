"""Views for . Tracking"""
import base64
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse
# For Python < 2.6
try:
    from urllib.parse import parse_qs
except ImportError:
    from cgi import parse_qs

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from ..models import Link
from ..models import Newsletter
from ..utils.tokens import untokenize
from ..models import ContactMailingStatus
from ..settings import USE_UTM_TAGS
from ..settings import TRACKING_IMAGE


def view_newsletter_tracking(request, slug, uidb36, token, format):
    """Track the opening of the newsletter by requesting a blank img"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)
    ContactMailingStatus.objects.create(newsletter=newsletter,
                                        contact=contact,
                                        status=ContactMailingStatus.OPENED)
    return HttpResponse(base64.b64decode(TRACKING_IMAGE),
                        content_type='image/%s' % format)


def view_newsletter_tracking_link(request, slug, uidb36, token, link_id):
    """Track the opening of a link on the website"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)
    link = get_object_or_404(Link, pk=link_id)
    ContactMailingStatus.objects.create(newsletter=newsletter,
                                        contact=contact,
                                        status=ContactMailingStatus.LINK_OPENED,
                                        link=link)
    if not USE_UTM_TAGS:
        return HttpResponseRedirect(link.url)

    url_parts = urlparse(link.url)
    query_dict = parse_qs(url_parts.query)
    query_dict.update({'utm_source': 'newsletter_%s' % newsletter.pk,
                       'utm_medium': 'mail',
                       'utm_campaign': smart_str(newsletter.title)})
    url = urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path,
                      url_parts.params, urlencode(query_dict), url_parts.fragment))
    return HttpResponseRedirect(url)


@login_required
def view_newsletter_historic(request, slug):
    """Display the historic of a newsletter"""
    opts = Newsletter._meta
    newsletter = get_object_or_404(Newsletter, slug=slug)

    context = {'title': _('Historic of %s') % newsletter.__str__(),
               'original': newsletter,
               'opts': opts,
               'object_id': newsletter.pk,
               'app_label': opts.app_label}
    return render(request, 'newsletter/newsletter_historic.html', context)
