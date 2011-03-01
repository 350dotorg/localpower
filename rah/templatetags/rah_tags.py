from django import template
from django.core.urlresolvers import reverse

register = template.Library()

class UserNode(template.Node):
    @classmethod
    def parse(cls, parser, token):
        tokens = token.contents.split()        
        if len(tokens) != 2:
            raise template.TemplateSyntaxError("Only 2 arguments needed for %s, the second should be a user" % tokens[0])
        return parser.compile_filter(tokens[1])

    def __init__(self, user_expr):
        self.user_expr = user_expr

    def render(self, context):
        user = self.user_expr.resolve(context)
        current_user = context["request"].user
        if user.id != current_user.id and user.get_profile().is_profile_private:
            return str(user.get_full_name())
        else:
            name = "You" if user.id == current_user.id else user.get_full_name()
            return "<a href='%s'>%s</a>" % (reverse("profile", args=[user.id]), name)

@register.tag
def safe_user_link(parser, token):
    """
    Return a safe user link that is only wrap the user's name in a hyperlink
    to their profile if either their profile is not private or the user
    making the request is trying to view their own link.

    Syntax::

        {% safe_user_link [user] %}

    Example usage::

        {% safe_user_link request.user %}
    """
    user_expr = UserNode.parse(parser, token)
    return UserNode(user_expr)

@register.filter
@template.defaultfilters.stringfilter
def deslug(value):
    return value.title().replace('_', ' ').replace('-', ' ')

@register.filter
@template.defaultfilters.stringfilter
def jsonify(value):
    return value.replace("\n", " ").replace('"', '\\"')

@register.filter
def truncate(value, length, killwords=False, end='...'):
    value = unicode(value)
    if len(value) <= length:
        return value
    elif killwords:
        return value[:length] + end
    words = value.split(' ')
    result = []
    m = 0
    for word in words:
        m += len(word) + 1
        if m > length:
            break
        result.append(word)
    result.append(end)
    return u' '.join(result)

