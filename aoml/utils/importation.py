"""Utils for importation of contacts"""
import csv
import codecs
from datetime import datetime

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from ..models import Contact
from ..models import MailingList


COLUMNS = ['email', 'first_name', 'last_name', 'tags']
csv.register_dialect('edn', delimiter=';')


def create_contact(contact_dict):
    """Create a contact and validate the mail"""
    if not 'email' in contact_dict:
        return None, False
    contact_dict['email'] = contact_dict['email'].strip()
    try:
        validate_email(contact_dict['email'])
        contact, created = Contact.objects.get_or_create(
            email=contact_dict['email'],
            defaults=contact_dict)
        return contact, created
    except ValidationError:
        pass
    return None, False


def create_contacts(contact_dicts, dest_mailing_list):
    """Create all the contacts to import and
    associated them in a mailing list"""
    inserted = 0
    when = str(datetime.now()).split('.')[0]
    
    for contact_dict in contact_dicts:
        contact, created = create_contact(contact_dict)
        if contact:
            dest_mailing_list.subscribers.add(contact)
            inserted += int(created)

    return inserted



def text_contacts_import(stream, dest_mailing_list):
    """Import contact from a plaintext file, like CSV"""
    contacts = []
    contact_reader = csv.reader(stream, dialect='edn')

    for contact_row in contact_reader:
        contact = {}
        for i in range(len(contact_row)):
            contact[COLUMNS[i]] = contact_row[i]
        contacts.append(contact)

    return create_contacts(contacts, dest_mailing_list)
