"""Views for . Mailing List"""
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json

from ..utils.tokens import untokenize
from ..models import Newsletter
from ..models import MailingList, Contact
from ..models import ContactMailingStatus


def view_mailinglist_unsubscribe(request, slug, uidb36, token):
    """Unsubscribe a contact to a mailing list"""
    newsletter = get_object_or_404(Newsletter, slug=slug)
    contact = untokenize(uidb36, token)

    # flag the contact as unsubscribed
    if not contact.unsubscribed:
        contact.unsubscribed = True
        contact.save()

    already_unsubscribed = contact in newsletter.mailing_list.unsubscribers.all()

    if request.POST.get('email') and not already_unsubscribed:
        newsletter.mailing_list.unsubscribers.add(contact)
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

@csrf_exempt
def view_contact_subscribe(request):
    """
    Register a contact and add it to the mailinglist
    expect json PUT with 2 fields : mailing_list_id and email
    """
    if request.method == 'PUT':
        err = ""
        try:
            err = "decoding json"
            j = json.loads(request.body)
            err = "missing/wrong mailing_list_id"
            mailing_list = get_object_or_404(MailingList, id=j['mailing_list_id'])
            err = "missing/wrong email"
            contact, created = Contact.objects.get_or_create(email=j['email'])
            if not created and contact.unsubscribed:
                contact.unsubscribed = False
                contact.save()

            mailing_list.subscribers.add(contact)
        except:
            return HttpResponse(json.dumps({"status":"KO", "error":err}), content_type='application/json')
        
        return HttpResponse(json.dumps({"status":"OK"}), content_type='application/json')
    else:
        raise Http404
