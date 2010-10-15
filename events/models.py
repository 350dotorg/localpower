import datetime

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.db import models
from django.dispatch import Signal
from django.template import Context, loader
from django.utils.dateformat import DateFormat

from geo.models import Location
from invite.models import Invitation
from messaging.models import Stream
from commitments.models import Contributor, Commitment, Survey

def yestarday():
    return datetime.datetime.today() - datetime.timedelta(days=1)
    
class EventTypeManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class EventType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    teaser = models.CharField(max_length=150)
    description = models.TextField()
    survey = models.ForeignKey("commitments.survey")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    objects = EventTypeManager()

    def __unicode__(self):
        return self.name
        
    def natural_key(self):
        return [self.name]

class Event(models.Model):
    creator = models.ForeignKey("auth.User")
    event_type = models.ForeignKey(EventType, default="")
    default_survey = models.ForeignKey("commitments.survey")
    place_name = models.CharField(max_length=100, blank=True,
        help_text="Label for where the event is being held (e.g. Jon's House)")
    where = models.CharField(max_length=100)
    location = models.ForeignKey("geo.Location", null=True)
    location.state_filter = True
    when = models.DateField()
    start = models.TimeField()
    duration = models.PositiveIntegerField(blank=True, null=True)
    details = models.TextField(help_text="For example, where should people park,\
        what's the nearest subway, do people need to be buzzed in, etc.", blank=True)
    is_private = models.BooleanField(default=False)
    limit = models.PositiveIntegerField(blank=True, null=True, help_text="Adding a limit sets a \
        cap on the number of guests that can RSVP. If the limit is reached, potential guests \
        will need to contact you first.")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        permissions = (
            ("host_any_event_type", "Can host any event type"),
            ("view_any_event", "Can view host details for any event"),
        )
    
    def __unicode__(self):
        return u"%s %s" % (self.location, self.event_type)
        
    @models.permalink
    def get_absolute_url(self):
        return ("event-detail", [str(self.id)])
        
    def place(self):
        return "%s %s" % (self.where, self.location)
        
    def odd_guests(self):
        return [g for i,g in enumerate(self.guest_set.rsvped_with_order()) if i % 2 != 0]
        
    def even_guests(self):
        return [g for i,g in enumerate(self.guest_set.rsvped_with_order()) if i % 2 == 0]
    
    def start_datetime(self):
        return datetime.datetime.combine(self.when, self.start)
        
    def has_manager_privileges(self, user):
        if not user.is_authenticated():
            return False
        return user.has_perm("events.view_any_event") or \
            Guest.objects.filter(event=self, contributor__user=user, is_host=True).exists()
            
    def is_guest(self, request):
        user = request.user
        if not user.is_authenticated():
            return self._guest_key() in request.session
        return Guest.objects.filter(event=self, contributor__user=user).exists()
        
    def hosts(self):
        return Guest.objects.filter(event=self, is_host=True)
        
    def confirmed_guests(self):
        return Guest.objects.filter(event=self, rsvp_status="A")
        
    def maybe_attending(self):
        return Guest.objects.filter(event=self, rsvp_status="M")
        
    def not_attending(self):
        return Guest.objects.filter(event=self, rsvp_status="N")
        
    def attendees(self):
        return Guest.objects.filter(event=self, rsvp_status__in=["A", "M"])
        
    def invited(self):
         return Guest.objects.filter(event=self, invited__isnull=False).count()
        
    def outstanding_invitations(self):
        return self.guests_that_have_not_responded().count()
        
    def guests_that_have_not_responded(self):
        return Guest.objects.filter(event=self, invited__isnull=False, rsvp_status="")
        
    def guests_no_response_id_list(self):
        return ",".join([g.id for g in self.guests_that_have_not_responded()])
        
    def is_token_valid(self, token):
        try:
            invite = Invitation.objects.get(token=token)
            return invite.content_object == self
        except Invitation.DoesNotExist:
            return False
            
    def next_guest(self, guest):
        guests = list(self.guest_set.all())
        next_index = guests.index(guest) + 1
        return guests[0] if next_index == len(guests) else guests[next_index]
        
    def challenges_committed(self):
        return Commitment.objects.filter(answer="C", guest__event=self)
        
    def challenges_done(self):
        return Commitment.objects.filter(answer="D", guest__event=self)
        
    def has_comments(self):
        return Guest.objects.filter(event=self).exclude(comments="").exists()
            
    def guests_with_commitments(self):
        query = Guest.objects.filter(event=self)
        for question in self.default_survey.questions():
            query = query.extra(select_params=(question,),
                select={question: """
                    SELECT answer FROM commitments_commitment cc
                    WHERE events_guest.contributor_id = cc.contributor_id AND cc.question = %s
                    """
                }
            )
        return query
        
    def _guest_key(self):
        return "event_%d_guest" % self.id
            
    def current_guest(self, request, token=None):
        if request.user.is_authenticated():
            user = request.user
            try:
                return Guest.objects.get(event=self, contributor__user=user)
            except Guest.DoesNotExist:
                try:
                    contributor = Contributor.objects.get(user=user)
                except Contributor.DoesNotExist:
                    contributor = Contributor(first_name=user.first_name, last_name=user.last_name,
                        email=user.email, location=user.get_profile().location, user=user)
                return Guest(event=self, contributor=contributor)
        if self._guest_key() in request.session:
            return request.session[self._guest_key()]
        if token:
            try:
                invite = Invitation.objects.get(token=token)
                guest = Guest.objects.get(event=self, contributor__email=invite.email)
                if not guest.rsvp_status:
                    return guest
            except Invitation.DoesNotExist:
                pass
            except Guest.DoesNotExist:
                pass
        return Guest(event=self)
        
    def save_guest_in_session(self, request, guest):
        request.session[self._guest_key()] = guest
        
    def delete_guest_in_session(self, request):
        del request.session[self._guest_key()]
        
class GuestManager(models.Manager):
    def rsvped_with_order(self):
        return self.exclude(rsvp_status=" ").order_by("rsvp_status", "created")
    
    def guest_engagment(self, date_start=None, date_end=None):
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
                NULL AS "team manager",
                NULL AS "team member",
                CASE 
                    WHEN g.is_host = 1 AND 
                    DATE(e.when) >= '%(date_start)s' AND DATE(e.when) <= '%(date_end)s' 
                        THEN "completed"
                    WHEN g.is_host = 1 AND 
                    DATE(e.created) >= '%(date_start)s' AND DATE(e.created) <= '%(date_end)s' 
                        THEN "yes"
                END AS "event host",
                CASE
                    WHEN e.event_type_id IN (1,4,5) AND cm.id IS NOT NULL AND
                    DATE(g.updated) >= '%(date_start)s' AND DATE(g.updated) <= '%(date_end)s'
                        THEN "completed"
                END AS "energy event guest",
                CASE
                    WHEN e.event_type_id IN (2) AND cm.id IS NOT NULL AND
                    DATE(g.updated) >= '%(date_start)s' AND DATE(g.updated) <= '%(date_end)s'
                        THEN "completed"
                END AS "kickoff event guest",
                CASE
                    WHEN e.event_type_id IN (3) AND cm.id IS NOT NULL AND 
                    DATE(g.updated) >= '%(date_start)s' AND DATE(g.updated) <= '%(date_end)s'
                        THEN "completed"
                END AS "field training guest"
            FROM events_guest g
            JOIN events_event e ON g.event_id = e.id
            JOIN commitments_contributor cn ON cn.id = g.contributor_id
            LEFT JOIN commitments_commitment cm ON cn.id = cm.contributor_id
            LEFT JOIN geo_location l ON cn.location_id = l.id
            LEFT JOIN commitments_commitment `organize_commit` ON `organize_commit`.question = 'organize' 
                AND `organize_commit`.contributor_id = cn.id
                AND DATE(`organize_commit`.updated) >= '%(date_start)s'
                AND DATE(`organize_commit`.updated) <= '%(date_end)s'
            %(action_joins)s
            WHERE cn.user_id IS NULL
            ORDER BY g.id
            """ % query_dict
        cursor = connection.cursor()
        cursor.execute(query)
        header_row = tuple([d[0] for d in cursor.description])
        queryset = [header_row] + list(cursor.fetchall())
        cursor.close()
        return queryset
        
class Guest(models.Model):
    RSVP_STATUSES = (
        ("A", "Attending",),
        ("M", "Maybe Attending",),
        ("N", "Not Attending",),
    )
    event = models.ForeignKey(Event)
    contributor = models.ForeignKey("commitments.contributor")
    invited = models.DateField(null=True, blank=True)
    added = models.DateField(null=True, blank=True)
    rsvp_status = models.CharField(blank=True, max_length=1, choices=RSVP_STATUSES)
    comments = models.TextField(blank=True)
    notify_on_rsvp = models.BooleanField(default=False)
    is_host = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    objects = GuestManager()
    
    class Meta:
        unique_together = (("event", "contributor",),)
        
    def save(self, *args, **kwargs):
        self.contributor.save()
        return super(Guest, self).save(*args, **kwargs)
    
    def status(self):
        if self.rsvp_status:
            return self.get_rsvp_status_display()
        if self.invited:
            return "Invited %s" % DateFormat(self.invited).format("M j")
        if self.added:
            return "Added %s" % DateFormat(self.added).format("M j")
        raise AttributeError
            
    def __unicode__(self):
        return unicode(self.contributor)

# 
# Signals!!!
#

def set_default_survey(sender, instance, **kwargs):
    instance.default_survey = instance.event_type.survey
models.signals.pre_save.connect(set_default_survey, sender=Event)

def make_creator_a_guest(sender, instance, **kwargs):
    creator = instance.creator
    contributor, created = Contributor.objects.get_or_create(user=creator, defaults={
        "first_name":creator.first_name, "last_name":creator.last_name, "email":creator.email,
        "location": creator.get_profile().location})
    Guest.objects.get_or_create(event=instance, contributor=contributor, defaults={
        "added":datetime.date.today(), "rsvp_status": "A", "is_host":True})
models.signals.post_save.connect(make_creator_a_guest, sender=Event)

def update_event_create_stream(sender, instance, created, **kwargs):
    stream = Stream.objects.get(slug="event-create")
    if created:
        stream.enqueue(content_object=instance, start=instance.created, end=instance.start_datetime())
    else:
        stream.upqueue(content_object=instance, start=instance.created, end=instance.start_datetime())
models.signals.post_save.connect(update_event_create_stream, sender=Event)

def remove_event_create_stream(sender, instance, **kwargs):
    Stream.objects.get(slug="event-create").dequeue(content_object=instance)
models.signals.post_delete.connect(remove_event_create_stream, sender=Event)

rsvp_recieved = Signal(providing_args=["guest"])
def notification_on_rsvp(sender, guest, **kwargs):
    if guest.rsvp_status and guest.notify_on_rsvp:
        Stream.objects.get(slug="event-rsvp-notification").enqueue(content_object=guest, start=guest.updated)
rsvp_recieved.connect(notification_on_rsvp)