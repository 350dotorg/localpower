from celery.decorators import task

from django.conf import settings
from django.contrib.auth.models import User
from actionkit_usersync.utils import get_client
from geo.fields import GoogleGeoField
from groups.models import GroupUsers

class null_location(object):
    def __getattr__(self, *args, **kw):
        return ''

@task()
def actionkit_push(user, profile):
    geom = profile.geom
    if geom:
        location = geom
    else:
        location = null_location()

    # EGJ TODO: what if profile.geom is None?
    # i think the localpower system allows that
    # currently just setting empty strings (per line above)
   
    try:
        actionkit = get_client()
    except:
        return

    try:
        ak_user = actionkit.User.save_or_create(dict(
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                postal=location.postal,
                state_name=location.state,
                city=location.city,
                country=location.country
                ))
    except:
        return

    try:
        page_name = settings.ACTIONKIT_PAGE_NAME
    except AttributeError:
        return ak_user

    groups_managed = GroupUsers.objects.filter(user=user, is_manager=True).values_list(
        "group__slug", flat=True)

    try:
        history = actionkit.User.subscription_history({'id': ak_user['id']})
    except:
        return ak_user

    ever_been_subscribed = False
    for entry in history:
        if entry.get("page_name") == page_name:
            ever_been_subscribed = True
            break
    if not ever_been_subscribed:
        try:
            result = actionkit.act(dict(
                    page=page_name,
                    email=user.email))
        except:
            return ak_user

    return ak_user
