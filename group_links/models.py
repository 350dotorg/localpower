from django.db import models
from django.utils.translation import ugettext_lazy as _

from groups.models import Group

class ExternalLink(models.Model):
    class Meta:
        verbose_name = _("external link")
        verbose_name_plural = _("external links")

    group = models.ForeignKey(Group, verbose_name=_("group"),
                              related_name="external_link_set")
    url = models.URLField(_("URL"), verify_exists=False)

    def __unicode__(self):
        return self.url

    def is_facebook(self):
        return "facebook.com" in self.url
    
    def is_twitter(self):
        return "twitter.com" in self.url
