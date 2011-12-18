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

    struct = dict(
        email=user.email,
        first_name=user.first_name or '',
        last_name=user.last_name or '')

    struct['custom_fields'] = {
        '350local_username': user.id
        }
    if location.postal:
        struct['postal'] = location.postal
    if location.state:
        struct['state_name'] = location.state
    if location.city:
        struct['city'] = location.city
    if location.country:
        struct['country'] = location.country

    try:
        ak_user = actionkit.User.save_or_create(struct)
    except:
        return

    try:
        page_name = settings.ACTIONKIT_PAGE_NAME
    except AttributeError:
        return ak_user

    try:
        managers_page_name = settings.ACTIONKIT_MANAGERS_PAGE_NAME
    except AttributeError:
        managers_page_name = None

    ever_been_subscribed = actionkit.Action.search({'user': ak_user['id'], 'page__name': page_name})
    if not ever_been_subscribed:
        try:
            result = actionkit.act(dict(
                    page=page_name,
                    email=user.email))
        except:
            return ak_user

    if managers_page_name is not None:
        groups_managed = GroupUsers.objects.filter(user=user, is_manager=True).values_list(
            "group__slug", flat=True)
        if len(groups_managed):
            ever_been_subscribed_as_manager = actionkit.Action.search({'user': ak_user['id'], 'page__name': managers_page_name})
            if not ever_been_subscribed_as_manager:
                try:
                    result = actionkit.act(dict(
                            page=managers_page_name,
                            email=user.email,
                            action_350localgroups=','.join(groups_managed),
                            ))
                except:
                    return ak_user
            else:
                page_type = actionkit.Page.get({'name': managers_page_name})['type']
                result = getattr(actionkit, '%sAction'%page_type).set_custom_fields({'id': ever_been_subscribed_as_manager[0]['id'],
                                                                                     '350localgroups': ','.join(groups_managed)})

    return ak_user
