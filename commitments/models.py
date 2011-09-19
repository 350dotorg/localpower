import datetime

from django.db import models
from django.contrib.auth.models import User
from django.contrib.gis.db.models import GeoManager

from geo.models import Location

def yesterday():
    return datetime.datetime.today() - datetime.timedelta(days=1)

class ContributorManager(GeoManager):
    def get_or_create_from_user(self, user):
        try:
            return self.get(user=user), True
        except Contributor.DoesNotExist:
            try:
                contributor = self.get(email=user.email)
                contributor.user = user
                contributor.save()
                return contributor, True
            except Contributor.DoesNotExist:
                return (self.create(first_name=user.first_name, last_name=user.last_name,
                                   email=user.email, geom=user.get_profile().geom, user=user), 
                        False)

    def contirbutor_engagment(self, date_start=None, date_end=None):
        from django.db import connection, transaction
        from actions.models import Action

        if not date_start:
            date_start = datetime.date.min
        if not date_end:
            date_end = datetime.date.max

        actions = Action.objects.all()
        action_cases = [
            """
            CASE
                WHEN `%s_commit`.answer = "C" THEN "committed"
                WHEN `%s_commit`.answer = "D" THEN "already done"
            END AS '%s'
            """ % (a.slug, a.slug, a.name.lower()) for a in actions]
        action_joins = [
            """
            LEFT JOIN commitments_commitment `%s_commit` ON `%s_commit`.action_id = %s AND `%s_commit`.contributor_id = cn.id
                AND DATE(`%s_commit`.updated) >= '%s' AND DATE(`%s_commit`.updated) <= '%s'
            """ % (a.slug, a.slug, a.id, a.slug, a.slug, date_start, a.slug, date_end) for a in actions]

        query_dict = {
            "action_cases": ", ".join(action_cases),
            "action_joins": " ".join(action_joins),
            "date_start": date_start,
            "date_end": date_end,
        }
        query = """
            SELECT DISTINCT -1, cn.first_name AS "first name", cn.last_name AS "last name", cn.email,
                cn.phone, l.name AS city, l.st AS state, l.zipcode AS "zip code",
                %(action_cases)s,
                CASE
                    WHEN `organize_commit`.answer = "True" THEN "yes"
                    WHEN `organize_commit`.answer = "False" THEN "no"
                END AS 'organize',
                CASE
                    WHEN `volunteer_commit`.answer = "True" THEN "yes"
                    WHEN `volunteer_commit`.answer = "False" THEN "no"
                END AS 'volunteer',
                NULL AS "community manager",
                NULL AS "community member",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        WHERE cn.id = g.contributor_id and g.is_host = 1
                        AND DATE(e.when) >= '%(date_start)s' AND DATE(e.when) <= '%(date_end)s') = 1
                            THEN "completed"
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        WHERE cn.id = g.contributor_id and g.is_host = 1
                        AND DATE(e.created) >= '%(date_start)s' AND DATE(e.created) <= '%(date_end)s') = 1
                            THEN "yes"
                END AS "event host",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        WHERE cn.id = g.contributor_id and e.event_type_id IN (1,4,5)
                        AND DATE(g.updated) >= '%(date_start)s' AND DATE(g.updated) <= '%(date_end)s') = 1
                            THEN "completed"
                END AS "energy event guest",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        WHERE cn.id = g.contributor_id and e.event_type_id IN (2)
                        AND DATE(g.updated) >= '%(date_start)s' AND DATE(g.updated) <= '%(date_end)s') = 1
                            THEN "completed"
                END AS "kickoff event guest",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        WHERE cn.id = g.contributor_id and e.event_type_id IN (3)
                        AND DATE(g.updated) >= '%(date_start)s' AND DATE(g.updated) <= '%(date_end)s') = 1
                            THEN "completed"
                END AS "field training guest"
            FROM commitments_contributor cn
            LEFT JOIN commitments_commitment cm ON cn.id = cm.contributor_id
            LEFT JOIN geo_location l ON cn.location_id = l.id
            LEFT JOIN commitments_commitment `organize_commit` ON `organize_commit`.question = 'organize'
                AND `organize_commit`.contributor_id = cn.id
                AND DATE(`organize_commit`.updated) >= '%(date_start)s'
                AND DATE(`organize_commit`.updated) <= '%(date_end)s'
            LEFT JOIN commitments_commitment `volunteer_commit` ON `volunteer_commit`.question = 'volunteer'
                AND `volunteer_commit`.contributor_id = cn.id
                AND DATE(`volunteer_commit`.updated) >= '%(date_start)s'
                AND DATE(`volunteer_commit`.updated) <= '%(date_end)s'
            %(action_joins)s
            WHERE cn.user_id IS NULL
            ORDER BY cn.id
            """ % query_dict
        cursor = connection.cursor()
        cursor.execute(query)
        header_row = tuple([d[0] for d in cursor.description])
        queryset = [header_row] + list(cursor.fetchall())
        cursor.close()
        return queryset

class Contributor(models.Model):
    first_name = models.CharField(blank=True, max_length=50)
    last_name = models.CharField(blank=True, max_length=50)
    email = models.EmailField(blank=True, null=True, db_index=True)
    phone = models.CharField(blank=True, max_length=12)

    location = models.ForeignKey("geo.Location", blank=True, null=True)
    geom = models.ForeignKey('geo.Point', blank=True, null=True,
                             verbose_name='location')

    user = models.ForeignKey("auth.User", blank=True, null=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    objects = ContributorManager()

    class Meta:
        unique_together = (("user",),("email",),)
        ordering = ['first_name', 'last_name']
        permissions = (("edit_any_contributor", "Can edit any contributor"),)

    def __init__(self, *args, **kwargs):
        super(Contributor, self).__init__(*args, **kwargs)
        self.contributor_profile = ContributorProfile(self)

    def _set_name(self, value):
        first, space, last = value.partition(" ")
        self.first_name = first
        self.last_name = last
    def _get_name(self):
        if self.user:
            return self.user.get_full_name()
        return ("%s %s" % (self.first_name, self.last_name)).strip()
    name = property(_get_name, _set_name)

    def _set_zipcode(self, value):
        try:
            self.location = Location.objects.get(zipcode=value)
        except Location.DoesNotExist:
            self.location = None
    def _get_zipcode(self):
        return self.location.zipcode if self.location else ""
    zipcode = property(_get_zipcode, _set_zipcode)

    def needs_more_info(self):
        return not (self.user or (self.first_name and self.email))

    def has_made_commitments(self):
        return Commitment.objects.filter(contributor=self).exists()

    def get_profile(self):
        # Note: this is somewhat of a hack to get Commitment objects to behave like UserActionProgress objects
        return self.contributor_profile
    get_profile = property(get_profile)

    def get_full_name(self):
        if self.user:
            return self.user.get_full_name()
        elif self.name:
            return self.name
        else:
            return self.email

    def __unicode__(self):
        return self.get_full_name()

class ContributorProfile(object):
    def __init__(self, contributor):
        self.contributor = contributor

    def potential_points(self):
        return Commitment.objects.pending_commitments(contributor=self.contributor).aggregate(
            models.Sum("action__points"))["action__points__sum"]

    def number_of_committed_actions(self):
        return Commitment.objects.pending_commitments(contributor=self.contributor).count()

    def commitments_made_yesterday(self):
        start = datetime.datetime.combine(yesterday(), datetime.time.min)
        end = datetime.datetime.combine(yesterday(), datetime.time.max)
        return Commitment.objects.pending_commitments(contributor=self.contributor).filter(
            updated__gte=start, updated__lte=end)

    def commitments_made_before_yesterday(self):
        start = datetime.datetime.combine(yesterday(), datetime.time.min)
        return Commitment.objects.pending_commitments(contributor=self.contributor).filter(
            updated__lt=start)

    def commitments_made_last_24_hours(self):
        return Commitment.objects.pending_commitments(contributor=self.contributor).filter(
            updated__gte=yesterday())

    def commitments_made_more_than_24_hours(self):
        return Commitment.objects.pending_commitments(contributor=self.contributor).filter(
            updated__lt=yesterday())

    def commitments_due_in_a_week(self):
        return self._commitment_due_on(datetime.date.today() + datetime.timedelta(days=7))

    def commitments_due_today(self):
        return self._commitment_due_on(datetime.date.today())

    def _commitment_due_on(self, due_date):
        commitments = Commitment.objects.pending_commitments(contributor=self.contributor)
        return [c for c in commitments if c.date_committed == due_date]

class SurveyManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Survey(models.Model):
    name = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=50)
    form_name = models.CharField(max_length=75)
    template_name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    contributors = models.ManyToManyField(Contributor, through="ContributorSurvey")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    objects = SurveyManager()

    class Meta:
        ordering = ['name', 'updated']

    def __unicode__(self):
        return "%s Survey" % self.name

    def natural_key(self):
        return [self.name]

    def questions(self):
        import survey_forms
        form = getattr(survey_forms, self.form_name)(None, None)
        return form.fields.keys()

class ContributorSurvey(models.Model):
    contributor = models.ForeignKey(Contributor)
    survey = models.ForeignKey(Survey)
    entered_by = models.ForeignKey("auth.user", null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("contributor", "survey", "entered_by",),)

class CommitmentManager(models.Manager):
    def pending_commitments(self, contributor=None):
        queryset = self.filter(answer="C", action__isnull=False)
        return queryset if not contributor else queryset.filter(contributor=contributor)

class Commitment(models.Model):
    contributor = models.ForeignKey(Contributor, db_index=True)
    question = models.CharField(max_length=50)
    answer = models.CharField(max_length=100)
    action = models.ForeignKey("actions.Action", null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    objects = CommitmentManager()

    class Meta:
        unique_together = (("contributor", "question",),)

    def _get_user(self):
        # Note: this is somewhat of a hack to get Commitment objects to behave like UserActionProgress objects
        return self.contributor
    user = property(_get_user)

    def _get_date_committed(self):
        # Note: this is somewhat of a hack to get Commitment objects to behave like UserActionProgress objects
        if self.action and self.answer == "C":
            return (self.updated + datetime.timedelta(weeks=3)).date()
        return None
    date_committed = property(_get_date_committed)

def link_contributor_to_user(sender, instance, **kwargs):
    if instance.email:
        try:
            user = User.objects.get(email=instance.email)
            instance.user = user
        except User.DoesNotExist:
            instance.user = None
models.signals.pre_save.connect(link_contributor_to_user, sender=Contributor)

def link_new_user_to_contributor(sender, instance, created, **kwargs):
    """
    When a user registers, see if they exists as a contributor record and if so, link them up.
    """
    if created and instance.email:
        try:
            contributor = Contributor.objects.get(email=instance.email)
            contributor.user = instance
            contributor.save()
        except Contributor.DoesNotExist:
            pass
models.signals.post_save.connect(link_new_user_to_contributor, sender=User)
