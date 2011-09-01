from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment

from actions.models import UserActionProgress
from commitments.models import Commitment, ContributorSurvey
from events.models import Event
from media_widget.models import StickerImage
from invite.models import Invitation
from rah.models import Profile
from dated_static.templatetags.dated_static import timestamp_file

from brabeion import badges as badge_cache
from brabeion.models import BadgeAward

# We need to import the badge module early, so that its badges will be
# registered with the brabeion badge cache before any code tries to
# award a badge out of the cache. Otherwise we get semi-unreproducible
# KeyErrors in brabeion internals when calling `possibly_award_badge`
import badges

def all_badges(user=None):
    import badges
    #Fetch all badges and add in the image links
    badges_dict = badge_cache._registry
    for key,value in badges_dict.items():
        badges_dict[key].awarded_at = None
        badges_dict[key] = add_images(badges_dict[key])

    #Add in the awarded date if the use is authenticated
    if user and user.is_authenticated():
        for award in BadgeAward.objects.filter(user=user).order_by("awarded_at"):
            badges_dict[award.slug].awarded_at = award.awarded_at

    #Sort the values such that awarded badges are in cronological order at the top of the list
    return sorted(badges_dict.values(), key=lambda x: x.awarded_at if x.awarded_at else datetime.max)

def user_badges(user):
    import badges
    all_badges = badge_cache._registry
    user_badges = []
    for award in BadgeAward.objects.filter(user=user):
        all_badges[award.slug].awarded_at = award.awarded_at
        all_badges[award.slug].level = award.level
        all_badges[award.slug] = add_images(all_badges[award.slug])
        user_badges.append(all_badges[award.slug])
    return user_badges

def get_badge(slug, user=None):
    import badges
    badge = badge_cache._registry[slug]
    if user and user.is_authenticated():
        try:
            award = BadgeAward.objects.get(slug=slug, user=user)
            badge.awarded_at = award.awarded_at
        except BadgeAward.DoesNotExist:
            pass
    return add_images(badge)

def add_images(badge):
    if not hasattr(badge, "level"):
        badge.level = 0
    badge.img_small = timestamp_file("images/badges/%s-%s-small.png" % (badge.slug, badge.level))
    badge.img_small_inactive = timestamp_file("images/badges/%s-%s-small-inactive.png" % (badge.slug, badge.level))
    badge.img_large = timestamp_file("images/badges/%s-%s-large.png" % (badge.slug, badge.level))
    badge.img_large_inactive = timestamp_file("images/badges/%s-%s-large-inactive.png" % (badge.slug, badge.level))
    badge.img_mega = timestamp_file("images/badges/%s-%s-mega.png" % (badge.slug, badge.level))
    badge.img_white = timestamp_file("images/badges/%s-%s-white.png" % (badge.slug, badge.level))
    return badge

def possibly_award_action_badge(sender, instance, created, **kwargs):
    if instance.is_completed:
        import badges # this is a hack to make sure all Badge Classes have been loaded into the BadgeCache
        from badges import event_name
        badge_cache.possibly_award_badge(event_name(instance.action), user=instance.user)
models.signals.post_save.connect(possibly_award_action_badge, sender=UserActionProgress)

def possibly_award_trendsetter_badge(sender, instance, created, **kwargs):
    if created and instance.question == 'pledge':
        import badges
        badge_cache.possibly_award_badge('took_the_pledge', user=instance.contributor.user)
models.signals.post_save.connect(possibly_award_trendsetter_badge, sender=Commitment)

def possibly_award_hosting_hero_badge(sender, instance, created, **kwargs):
    if created:
        import badges
        badge_cache.possibly_award_badge('created_an_event', user=instance.creator)
models.signals.post_save.connect(possibly_award_hosting_hero_badge, sender=Event)

def possibly_award_gift_of_gab_badge(sender, instance, created, **kwargs):
    if created:
        import badges
        badge_cache.possibly_award_badge('created_a_comment', user=instance.user)
models.signals.post_save.connect(possibly_award_gift_of_gab_badge, sender=Comment)

def possibly_award_paparazzi_badge(sender, instance, created, **kwargs):
    if instance.approved:
        import badges
        try:
            user = User.objects.get(email=instance.email)
            badge_cache.possibly_award_badge('uploaded_an_image', user=user)
        except User.DoesNotExist:
            pass
models.signals.post_save.connect(possibly_award_paparazzi_badge, sender=StickerImage)

def possibly_award_momentum_builder_badge(sender, instance, created, **kwargs):
    if created:
        import badges
        badge_cache.possibly_award_badge('invited_a_friend', user=instance.user)
models.signals.post_save.connect(possibly_award_momentum_builder_badge, sender=Invitation)

def possibly_award_social_media_maven_badge(sender, instance, created, **kwargs):
    if instance.twitter_access_token or instance.facebook_access_token:
        import badges
        badge_cache.possibly_award_badge('linked_social_account', user=instance.user)
models.signals.post_save.connect(possibly_award_social_media_maven_badge, sender=Profile)

def possibly_award_follow_through_badge(sender, instance, created, **kwargs):
    if instance.entered_by:
        import badges
        badge_cache.possibly_award_badge('entered_commitment_card', user=instance.entered_by)
models.signals.post_save.connect(possibly_award_follow_through_badge, sender=ContributorSurvey)

def possibly_award_shout_out_badge(sender, instance, created, **kwargs):
    if instance.twitter_share or instance.facebook_share:
        import badges
        badge_cache.possibly_award_badge('opted_to_share_activity', user=instance.user)
models.signals.post_save.connect(possibly_award_shout_out_badge, sender=Profile)

def possibly_award_storyteller_badge(sender, instance, created, **kwargs):
    if instance.location and instance.building_type and instance.about and \
            instance.get_profile().first_name and instance.get_profile().last_name:
        import badges
        badge_cache.possibly_award_badge('completed_profile', user=instance.user)
models.signals.post_save.connect(possibly_award_storyteller_badge, sender=Profile)

def possibly_award_dogged_badge(sender, instance, created, **kwargs):
    if instance.is_completed and instance.date_committed:
        import badges
        badge_cache.possibly_award_badge('completed_a_commitment', user=instance.user)
models.signals.post_save.connect(possibly_award_dogged_badge, sender=UserActionProgress)

def possibly_award_unbelievable_badge(sender, instance, created, **kwargs):
    if instance.is_completed:
        import badges
        badge_cache.possibly_award_badge('completed_an_action', user=instance.user)
models.signals.post_save.connect(possibly_award_unbelievable_badge, sender=UserActionProgress)
