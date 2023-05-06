from django.core.urlresolvers import reverse
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from emencia.django.newsletter.models import MailingList


class SubscribeWidget(models.Model):
    title = models.CharField(_('title'), max_length=50, blank=True)
    mailing_list = models.ForeignKey(MailingList, on_delete=models.CASCADE, verbose_name=_('mailing list'))

    class Meta:
        abstract = True
        verbose_name = _('Subscribe Widget')

    @property
    def subscribe_url(self):
        return reverse('newsletter_mailinglist_subscribe', kwargs={'mailing_list_id': self.mailing_list.id})

    def render(self, **kwargs):
        return render_to_string('newsletter/feincms/subscribe_widget.html',
                                {'content': self},
                                context_instance=kwargs.get('context'))
