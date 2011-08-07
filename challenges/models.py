from django.db import models

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
    title = models.CharField(max_length=70)
    description = models.TextField(blank=False, help_text="Tell people what this challenge is about, why you're involved, and what you want to accomplish.")
    goal = models.PositiveIntegerField()
    creator = models.ForeignKey('auth.user')
    supporters = models.ManyToManyField('commitments.contributor', through='Support')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    objects = ChallengeManager()

    groups = models.ManyToManyField("groups.Group", blank=True,
        limit_choices_to = {'is_geo_group': False}, verbose_name="Communities")

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
    challenge = models.ForeignKey(Challenge)
    contributor = models.ForeignKey('commitments.contributor')
    send_updates = models.BooleanField(default=False)
    pledged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('challenge', 'contributor',)
