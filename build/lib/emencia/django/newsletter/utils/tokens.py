"""Tokens system for emencia.django.newsletter"""
from django.http import Http404
from django.utils import six
from django.utils.http import int_to_base36, base36_to_int
from emencia.django.newsletter.models import Contact
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import salted_hmac


class ContactTokenGenerator(PasswordResetTokenGenerator):

    """ContactTokengenerator for the newsletter
    based on the PasswordResetTokenGenerator bundled
    in django.contrib.auth"""

    def _make_token_with_timestamp(self, user, timestamp):
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)

        # By hashing on the internal state of the user and using state
        # that is sure to change (the password salt will change as soon as
        # the password is set, at least for current Django auth, and
        # last_login will also change), we produce a hash that will be
        # invalid as soon as it is used.
        # We limit the hash to 20 chars to keep URL short
        key_salt = "django.contrib.auth.tokens.PasswordResetTokenGenerator"

        value = (six.text_type(user.pk) +
                 user.email + six.text_type(timestamp))
        hash = salted_hmac(key_salt, value).hexdigest()[::2]
        return "%s-%s" % (ts_b36, hash)


def tokenize(contact):
    """Return the uid in base 36 of a contact, and a token"""
    token_generator = ContactTokenGenerator()
    return int_to_base36(contact.id), token_generator.make_token(contact)


def untokenize(uidb36, token):
    """Retrieve a contact by uidb36 and token"""
    try:
        contact_id = base36_to_int(uidb36)
        contact = Contact.objects.get(pk=contact_id)
    except:
        raise Http404

    token_generator = ContactTokenGenerator()
    if token_generator.check_token(contact, token):
        return contact
    raise Http404
