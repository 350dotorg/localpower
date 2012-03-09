from django.db import models
from django.contrib.flatpages.models import FlatPage
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from actions.models import Action
from messaging.models import Message

class TranslatedFlatPage(models.Model):
    flatpage = models.ForeignKey(FlatPage)
    language = models.CharField(max_length=10, choices=settings.LANGUAGES)

    title = models.CharField(_('title'), max_length=200)
    content = models.TextField(_('content'), blank=True)

    class Meta:
        verbose_name = _('translated flat page')
        verbose_name_plural = _('translated flat pages')

class TranslatedAction(models.Model):
    action = models.ForeignKey(Action, verbose_name=_('action'))
    language = models.CharField(max_length=10, choices=settings.LANGUAGES)

    name = models.CharField(_('name'), max_length=255)
    teaser = models.TextField(_('teaser'))
    content = models.TextField(_('content'))

    class Meta:
        verbose_name = _('translated project')
        verbose_name_plural = _('translated projects')

    def __unicode__(self):
        return self.name

class TranslatedMessage(models.Model):
    message = models.ForeignKey(Message, verbose_name=_('message'))
    language = models.CharField(max_length=10, choices=settings.LANGUAGES)

    subject = models.CharField(max_length=100)
    body = models.TextField()
