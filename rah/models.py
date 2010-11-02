import datetime
import facebook
import hashlib
import json
import re

from django.db import models
from django.contrib.auth.models import User
from django.contrib.localflavor.us.models import USStateField
from django.core.cache import cache

from geo.models import Location
from records.models import Record
from twitter_app import utils as twitter_app
from actions.models import Action, UserActionProgress
from facebook_app.models import facebook_profile

def yestarday():
    return datetime.datetime.today() - datetime.timedelta(days=1)

class Feedback(models.Model):
    user = models.ForeignKey(User, null=True)
    url = models.CharField(max_length=255, default='')
    comment = models.TextField(default='')
    beta_group = models.BooleanField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s...' % (self.comment[:15])
        
class ProfileManager(models.Manager):
    def user_engagement(self, users=None, date_start=None, date_end=None):
        from django.db import connection, transaction
        
        if not date_start:
            date_start = datetime.date.min
        if not date_end:
            date_end = datetime.date.max

        actions = Action.objects.all()
        action_cases = [
            """
            CASE
                WHEN `%s_uap`.is_completed = 1 AND `%s_uap`.date_committed IS NOT NULL THEN "completed"
                WHEN `%s_uap`.is_completed = 1 THEN "already done"
                WHEN `%s_uap`.date_committed IS NOT NULL THEN "committed"
            END AS '%s'
            """ % (a.slug, a.slug, a.slug, a.slug, a.name.lower()) for a in actions]
        action_joins = [
            """
            LEFT JOIN actions_useractionprogress `%s_uap` ON `%s_uap`.action_id = %s AND `%s_uap`.user_id = u.id
                AND DATE(`%s_uap`.updated) >= '%s' and DATE(`%s_uap`.updated) <= '%s'
            """ % (a.slug, a.slug, a.id, a.slug, a.slug, date_start, a.slug, date_end) for a in actions]
        users_filter = "WHERE u.id IN (%s)" % ",".join([str(u.pk) for u in users]) if users else ""
            
        query_dict = {
            "action_cases": ", ".join(action_cases),
            "action_joins": " ".join(action_joins),
            "users_filter": users_filter,
            "date_start": date_start,
            "date_end": date_end
        }    
        query = """
            SELECT u.id, u.first_name AS "first name", u.last_name AS "last name", u.email,
                NULL AS phone, l.name AS city, l.st AS state, l.zipcode AS "zip code",
                %(action_cases)s,
                NULL AS 'organize',
                NULL AS 'volunteer',
                CASE
                    WHEN EXISTS(SELECT * FROM groups_groupusers gu WHERE u.id = gu.user_id AND gu.is_manager = 1
                        AND DATE(gu.updated) >= '%(date_start)s' AND DATE(gu.updated) <= '%(date_end)s') = 1 THEN "yes"
                END AS "team manager",
                CASE
                    WHEN EXISTS(SELECT * FROM groups_groupusers gu JOIN groups_group g ON gu.group_id = g.id
                        WHERE u.id = gu.user_id AND g.is_geo_group = 0
                        AND DATE(gu.updated) >= '%(date_start)s' AND DATE(gu.updated) <= '%(date_end)s') = 1 THEN "yes"
                END AS "team member",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        JOIN commitments_contributor c ON g.contributor_id = c.id
                        WHERE u.id = c.user_id AND g.is_host = 1
                        AND DATE(e.when) >= '%(date_start)s' AND DATE(e.when) <= '%(date_end)s') = 1 THEN "completed"
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        JOIN commitments_contributor c ON g.contributor_id = c.id
                        WHERE u.id = c.user_id AND g.is_host = 1
                        AND DATE(e.created) >= '%(date_start)s' AND DATE(e.created) <= '%(date_end)s') = 1 THEN "yes"
                END AS "event host",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id
                        JOIN commitments_contributor cn ON g.contributor_id = cn.id
                        JOIN commitments_commitment cm ON cn.id = cm.contributor_id 
                        WHERE u.id = cn.user_id AND e.event_type_id IN (1,4,5)
                        AND DATE(cm.updated) >= '%(date_start)s' AND DATE(cm.updated) <= '%(date_end)s') = 1 THEN "completed"
                END AS "energy event guest",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id 
                        JOIN commitments_contributor cn ON g.contributor_id = cn.id
                        JOIN commitments_commitment cm ON cn.id = cm.contributor_id 
                        WHERE u.id = cn.user_id AND e.event_type_id IN (2)
                        AND DATE(cm.updated) >= '%(date_start)s' AND DATE(cm.updated) <= '%(date_end)s') = 1 THEN "completed"
                END AS "kickoff event guest",
                CASE
                    WHEN EXISTS(SELECT * FROM events_guest g JOIN events_event e ON g.event_id = e.id 
                        JOIN commitments_contributor cn ON g.contributor_id = cn.id
                        JOIN commitments_commitment cm ON cn.id = cm.contributor_id 
                        WHERE u.id = cn.user_id AND e.event_type_id IN (3)
                        AND DATE(cm.updated) >= '%(date_start)s' AND DATE(cm.updated) <= '%(date_end)s') = 1 THEN "completed"
                END AS "field training guest"
            FROM auth_user u
            JOIN rah_profile p ON u.id = p.user_id
            LEFT JOIN geo_location l ON p.location_id = l.id
            %(action_joins)s
            %(users_filter)s
            ORDER BY u.id
            """ % query_dict
        cursor = connection.cursor()
        cursor.execute(query)
        header_row = tuple([d[0] for d in cursor.description])
        queryset = [header_row] + list(cursor.fetchall())
        cursor.close()
        return queryset

class Profile(models.Model):
    """Profile"""
    # OPTIMIZE these choices can be tied to an IntegerField if the value is an integer: (1, 'Apartment'),
    BUILDING_CHOICES = (
        ('S', 'House'),
        ('A', 'Apartment'),
        ('C', 'Condo'),
        ('O', 'Other'),
    )

    user = models.ForeignKey(User, unique=True)
    location = models.ForeignKey(Location, null=True, blank=True)
    building_type = models.CharField(null=True, max_length=1, choices=BUILDING_CHOICES, blank=True)
    about = models.CharField(null=True, blank=True, max_length=255)
    is_profile_private = models.BooleanField(default=0)
    twitter_access_token = models.CharField(null=True, max_length=255, blank=True)
    twitter_share = models.BooleanField(default=False)
    facebook_access_token = models.CharField(null=True, max_length=255, blank=True)
    facebook_connect_only = models.BooleanField(default=False)
    facebook_share = models.BooleanField(default=False)
    ask_to_share = models.BooleanField(default=True)
    total_points = models.IntegerField(default=0)
    objects = ProfileManager()
    
    def __unicode__(self):
        return u'%s' % (self.user.email)

    def profile_picture(self, default_icon='identicon'):
        key = "profile_picture_%s" % self.user.id
        cache_hit = cache.get(key)
        if cache_hit:
            return cache_hit
        else:
            facebook_picture = facebook_profile(self.user, "square")
            if facebook_picture:
                profile_picture = facebook_picture
            else:
                profile_picture = 'http://www.gravatar.com/avatar/%s?r=g&d=%s&s=52' % (self._email_hash(), default_icon)
            
            # Cache the profile picture url for 6 hours
            cache.set(key, profile_picture, 60 * 60 * 6)
            return profile_picture
    
    def profile_picture_large(self, default_icon='identicon'):
        facebook_picture = facebook_profile(self.user, "large")
        if facebook_picture:
            return facebook_picture
        return 'http://www.gravatar.com/avatar/%s?r=g&d=%s&s=189' % (self._email_hash(), default_icon)

    def _email_hash(self):
        return (hashlib.md5(self.user.email.lower()).hexdigest())
        
    def potential_points(self):
        return UserActionProgress.objects.pending_commitments(user=self.user).aggregate(
            models.Sum("action__points"))["action__points__sum"]
            
    def number_of_committed_actions(self):
        return UserActionProgress.objects.pending_commitments(user=self.user).count()
            
    def commitments_made_yestarday(self):
        start = datetime.datetime.combine(yestarday(), datetime.time.min)
        end = datetime.datetime.combine(yestarday(), datetime.time.max)
        return UserActionProgress.objects.pending_commitments(user=self.user).filter(
            updated__gte=start, updated__lte=end).order_by("-date_committed")
        
    def commitments_made_before_yestarday(self):
        start = datetime.datetime.combine(yestarday(), datetime.time.min)
        return UserActionProgress.objects.pending_commitments(user=self.user).filter(
            updated__lt=start).order_by("-date_committed")
            
    def commitments_made_last_24_hours(self):
        return UserActionProgress.objects.pending_commitments(user=self.user).filter(
            updated__gte=yestarday()).order_by("-date_committed")
            
    def commitments_made_more_than_24_hours(self):
        return UserActionProgress.objects.pending_commitments(user=self.user).filter(
            updated__lt=yestarday()).order_by("-date_committed")
        
    def commitments_due_in_a_week(self):
        return self._commitment_due_on(datetime.date.today() + datetime.timedelta(days=7))
        
    def commitments_due_today(self):
        return self._commitment_due_on(datetime.date.today())
            
    def _commitment_due_on(self, due_date):
        return UserActionProgress.objects.pending_commitments(user=self.user).filter(
            date_committed=due_date).order_by("-date_committed")
            
class StickerRecipient(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    state = USStateField()
    zipcode = models.CharField(max_length=10)
    user = models.ForeignKey("auth.user", blank=True, null=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


"""
SIGNALS!
"""
def user_post_save(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
models.signals.post_save.connect(user_post_save, sender=User)

def sticker_recipient_link_user(sender, instance, **kwargs):
    try:
        instance.user = User.objects.get(email=instance.email)
    except:
        pass
models.signals.pre_save.connect(sticker_recipient_link_user, sender=StickerRecipient)