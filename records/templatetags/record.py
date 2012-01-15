from django import template

from ..models import Activity

register = template.Library()

class RecordNode(template.Node):
    @classmethod
    def parse(cls, parser, token):
        tokens = token.contents.split()
        if len(tokens) != 2:
            raise template.TemplateSyntaxError("Only 2 arguments needed for %s, the second should be a record" % tokens[0])
        return parser.compile_filter(tokens[1])

    def __init__(self, record_expr):
        self.record_expr = record_expr

    def render(self, context):
        record = self.record_expr.resolve(context)
        request = context["request"]
        from django.core.urlresolvers import NoReverseMatch
        try:
            return record.render(request)
        except NoReverseMatch:
            record.delete()
            return ''

@register.tag
def render_record(parser, token):
    """
    Render the record within the given context

    Syntax::

        {% render_record [record] %}
    """
    record_expr = RecordNode.parse(parser, token)
    return RecordNode(record_expr)

class ActivityNode(template.Node):
    def __init__(self, activity, var_name):
        self.activity = activity
        self.var_name = var_name

    def render(self, context):
        context[self.var_name] = self.activity
        return ""

@register.tag
def activity_by_slug(parser, token):
    """
    Assign an activity object to a variable based on the slug provided.

    Syntax::
        {% activity_by_slug [slug] as [variable_name] %}

    Example usage::
        {% activity_by_slug group_create as group_create_activity %}
    """
    try:
        tag_name, slug, as_token, var_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%(tag_name)s tag requires 4 arguments {%% %(tag_name)s [slug] as [var_name] %%}" % {"tag_name": token.contents.split()[0]}

    if slug[0] == slug[-1] and slug[0] in ('"', "'"):
        slug = slug[1:-1] #slug came through in quotes, strip them away

    activity = Activity.objects.get(slug=slug)
    return ActivityNode(activity, var_name)
