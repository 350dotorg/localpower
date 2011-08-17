from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext_lazy as _

from models import Group

from records.models import Record

class GroupActivityFeed(Feed):
    feed_type = Atom1Feed

    def get_object(self, request, group_slug):
        self.request = request
        return get_object_or_404(Group, slug=group_slug)

    def title(self, group):
        return _("%(group)s Activity Stream") % {'group': group.name}

    def link(self, group):
        return group.get_absolute_url()

    def feed_guid(self, group):
        return self.link(group)

    def subtitle(self, group):
        return _("All of the activity going on for %(group)s") % {'group': group.name}

    def items(self, group):
        return group.group_records(30)

    def item_description(self, record):
        return record.render(self.request)

    def item_link(self, record):
        return record.get_absolute_url()

    def item_pudate(self, record):
        return record.created
