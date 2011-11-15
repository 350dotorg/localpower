from django.db import models
from django.utils.translation import ugettext_lazy as _

class ChallengeManager(models.Manager):
    def all_challenges(self, user=None):
        challenges = self.all()
        if user and user.is_authenticated():
            challenges = challenges.extra(select={'status':
                """
                SELECT CASE WHEN s.contributor_id IS NOT NULL THEN "completed" ELSE "" END
                FROM commitments_contributor c
                LEFT JOIN challenges_support s ON c.id = s.contributor_id
                WHERE c.user_id = %s AND s.challenge_id = challenges_challenge.id
                """}, select_params = (user.id,))
        return challenges

class Challenge(models.Model):

    class Meta:
        verbose_name = _('challenge')
        verbose_name_plural = _('challenges')

    title = models.CharField(_('title'), max_length=70)
    description = models.TextField(_('description'), blank=False, help_text=_(
            "Tell people what this challenge is about, "
            "why you're involved, and what you want to accomplish."))
    goal = models.PositiveIntegerField(_('goal'))
    creator = models.ForeignKey('auth.user', verbose_name=_('creator'))
    supporters = models.ManyToManyField('commitments.contributor', 
                                        through='Support',
                                        verbose_name=_('supporters'))
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)
    objects = ChallengeManager()

    groups = models.ManyToManyField("groups.Group", blank=True,
                                    verbose_name=_("communities"))

    def has_manager_privileges(self, user):
        if not user.is_authenticated():
            return False
        if user.is_staff:
            return True
        if self.creator == user:
            return True
        from groups.models import GroupUsers
        if GroupUsers.objects.filter(
            user=user,
            group__in=self.groups.all(),
            is_manager=True).exists():
            return True
        return False

    def number_of_supporters(self):
        return self.supporters.all().count()

    def percent_complete(self):
        percent_complete = (self.number_of_supporters() / float(self.goal)) * 100
        if percent_complete > 100:
            percent_complete = 100
        elif 0 < percent_complete < 3:
            percent_complete = 3
        return percent_complete

    @models.permalink
    def get_absolute_url(self):
        return ('challenges_detail', [str(self.id)])

    def __unicode__(self):
        return self.title

class Support(models.Model):
    challenge = models.ForeignKey(Challenge, verbose_name=_('challenge'))
    contributor = models.ForeignKey('commitments.contributor', verbose_name=_('contributor'))
    send_updates = models.BooleanField(_('send updates'), default=False)
    pledged_at = models.DateTimeField(_('pledged at'), auto_now_add=True)

    class Meta:
        unique_together = ('challenge', 'contributor',)
        verbose_name = _('support')
        verbose_name_plural = _('supports')
