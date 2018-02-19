"""Views for . Newsletter"""
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.shortcuts import render
#from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


from ..models import Newsletter
from ..models import ContactMailingStatus
from ..utils import render_string
from ..utils.newsletter import track_links
from ..utils.tokens import untokenize
from ..settings import TRACKING_LINKS
from ..settings import DOMAIN
from ..settings import INCLUDE_UNSUBSCRIPTION

def render_newsletter(request, slug, context):
    """Return a newsletter in HTML format"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    
    context.update({'newsletter': newsletter,
                    'domain': DOMAIN})

    unsubscription = render_to_string('newsletter/newsletter_link_unsubscribe.html', context)
    context.update({'unsubscribe':unsubscription,})

    content = render_string(newsletter.content, context)
    title = render_string(newsletter.title, context)
    if TRACKING_LINKS:
        content = track_links(content, context)
    
    return render(request, 'newsletter/newsletter_detail.html',
                              {'content': content,
                               'title': title,
                               'object': newsletter})


@login_required
def view_newsletter_preview(request, slug):
    """View of the newsletter preview"""
    context = {'contact': request.user}
    return render_newsletter(request, slug, context)


def view_newsletter_contact(request, slug, uidb36, token):
    """Visualization of a newsletter by an user"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)
    ContactMailingStatus.objects.create(newsletter=newsletter,
                                        contact=contact,
                                        status=ContactMailingStatus.OPENED_ON_SITE)
    
    context = {'contact': contact,
               'uidb36': uidb36, 'token': token}

    return render_newsletter(request, slug, context)
