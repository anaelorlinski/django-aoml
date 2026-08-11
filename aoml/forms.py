
"""Forms for """
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Contact
from .models import MailingList
from .utils.segmentation import DEFAULT_INACTIVITY_MONTHS
from .utils.segmentation import SCOPE_ANY
from .utils.segmentation import SCOPE_CHOICES


class MailingListSegmentationForm(forms.Form):
    """Criteria for splitting a mailing list between openers and non openers."""

    months = forms.IntegerField(
        label=_('Months'), min_value=1, max_value=240,
        initial=DEFAULT_INACTIVITY_MONTHS,
        help_text=_('Length of the period looked at, ending today.'))

    scope = forms.ChoiceField(
        label=_('Openings counted'), choices=SCOPE_CHOICES, initial=SCOPE_ANY,
        help_text=_('A contact subscribed to several lists is engaged if he '
                    'opens any of them, so "any newsletter" is the safe '
                    'measure for a cleanup. Restrict to this list only to '
                    'measure the interest for this list in particular.'))

    include_unsubscribers = forms.BooleanField(
        label=_('Include unsubscribers'), required=False, initial=False,
        help_text=_('Off, the contacts who unsubscribed from this list are '
                    'left out of both segments.'))

    include_never_mailed = forms.BooleanField(
        label=_('Treat the contacts never mailed as non openers'),
        required=False, initial=False,
        help_text=_('Off, the contacts who received nothing during the period '
                    '(recent subscribers, typically) are left out: they had no '
                    'occasion to open anything.'))

    name_prefix = forms.CharField(
        label=_('Name of the created lists'), required=False, max_length=200,
        help_text=_('Prefix of the two created mailing lists. Empty, the name '
                    'of the current list is used.'))

    def criteria(self):
        """The submitted values, or the defaults when the form has not been
        submitted yet, so the page can show a result on first display."""
        if self.is_bound and self.is_valid():
            return self.cleaned_data
        return dict((name, field.initial) for name, field in self.fields.items())


class MailingListSubscriptionForm(forms.ModelForm):
    """Form for subscribing to a mailing list"""
    # Notes : This form will not check the uniquess of
    # the 'email' field, by defining it explictly and setting
    # it the Meta.exclude list, for allowing registration
    # to a mailing list even if the contact already exists.
    # Then the contact is always added to the subscribers field
    # of the mailing list because it will be cleaned with no
    # double.

    email = forms.EmailField(label=_('Email'), max_length=75)

    def save(self, mailing_list):
        data = self.cleaned_data
        contact, created = Contact.objects.get_or_create(
            email=data['email'])

        mailing_list.subscribers.add(contact)
        mailing_list.unsubscribers.remove(contact)

    class Meta:
        model = Contact
        exclude = ('email',)


#class AllMailingListSubscriptionForm(MailingListSubscriptionForm):
#    """Form for subscribing to all mailing list"""
#
#    mailing_lists = forms.ModelMultipleChoiceField(
#        queryset=MailingList.objects.all(),
#        initial=[obj.id for obj in MailingList.objects.all()],
#        label=_('Mailing lists'),
#        widget=forms.CheckboxSelectMultiple())
#
#    def save(self, mailing_list):
#        data = self.cleaned_data
#        contact, created = Contact.objects.get_or_create(
#            email=data['email'],
#            defaults={'first_name': data.get('first_name', None),
#                      'last_name': data.get('last_name', None)})
#
#        for mailing_list in data['mailing_lists']:
#            mailing_list.subscribers.add(contact)
