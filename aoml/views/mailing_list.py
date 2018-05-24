"""Views for . Mailing List"""
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.shortcuts import render

from ..utils.tokens import untokenize
from ..models import Newsletter
from ..models import MailingList
from ..models import ContactMailingStatus


def view_mailinglist_unsubscribe(request, slug, uidb36, token):
    """Unsubscribe a contact to a mailing list"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)

    # flag the contact as unsubscribed
    if not contact.unsubscribed:
        contact.unsubscribed = True
        contact.save()

    already_unsubscribed = contact not in newsletter.mailing_list.subscribers.all()

    if request.POST.get('email') and not already_unsubscribed:
        newsletter.mailing_list.subscribers.remove(contact)
        newsletter.mailing_list.save()
        already_unsubscribed = True
        ContactMailingStatus.objects.create(newsletter=newsletter, contact=contact,
                                            status=ContactMailingStatus.UNSUBSCRIPTION)

    return render(request,'newsletter/mailing_list_unsubscribe.html',
                              {'email': contact.email,
                               'already_unsubscribed': already_unsubscribed})


def view_mailinglist_subscribe(request, form_class, mailing_list_id=None):
    """
    A simple view that shows a form for subscription
    for a mailing list(s).
    """
    subscribed = False
    mailing_list = None
    if mailing_list_id:
        mailing_list = get_object_or_404(MailingList, id=mailing_list_id)

    if request.POST and not subscribed:
        form = form_class(request.POST)
        if form.is_valid():
            form.save(mailing_list)
            subscribed = True
    else:
        form = form_class()

    return render(request, 'newsletter/mailing_list_subscribe.html',
                              {'subscribed': subscribed,
                               'mailing_list': mailing_list,
                               'form': form})
