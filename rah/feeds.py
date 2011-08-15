from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext as _

from records.models import Record

class UserActivityFeed(Feed):
    feed_type = Atom1Feed

    def get_object(self, request, user_id):
        self.request = request
        return get_object_or_404(User, id=user_id)

    def title(self, user):
        return _("%(user)s Activity Stream") % {'user': user.get_full_name()}

    def link(self, user):
        return user.get_absolute_url()

    def feed_guid(self, user):
        return self.link(user)

    def subtitle(self, user):
        return _("%(user)s's recent activity") % {'user': user.get_full_name()}

    def items(self, user):
        records = Record.objects.filter(user=user)
        records = records.exclude(user__profile__is_profile_private=True)
        records = records.select_related().order_by("-created")
        return records[:30]

    def item_description(self, record):
        return record.render(self.request)

    def item_link(self, record):
        return record.get_absolute_url()

    def item_pudate(self, record):
        return record.created

class CommentsFeed(Feed):
    feed_type = Atom1Feed

    def get_object(self, request, content_type_id, object_pk):
        comment_type = get_object_or_404(ContentType, id=content_type_id)
        return get_object_or_404(comment_type.model_class(), pk=object_pk)

    def title(self, content_object):
        return _("%(content_object)s Comment Stream") % {'content_object': content_object}

    def link(self, content_object):
        return content_object.get_absolute_url()

    def feed_guid(self, content_object):
        return self.link(content_object)

    def items(self, content_object):
        comments = Comment.objects.for_model(content_object)
        return comments.order_by("-submit_date")[:30]

    def item_title(self, comment):
        return _("%(content_object)s comment") % {'content_object': comment.content_object}

    def item_description(self, comment):
        return comment.comment

    def item_link(self, comment):
        return self.link(comment.content_object)

    def item_author_name(self, comment):
        return comment.user.get_full_name()

    def item_author_link(self, comment):
        if comment.user.get_profile().is_profile_private:
            return ''
        return comment.user.get_absolute_url()

    def item_pubdate(self, comment):
        return comment.submit_date
