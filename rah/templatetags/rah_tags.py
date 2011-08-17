from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

register = template.Library()

class UserNode(template.Node):
    @classmethod
    def parse(cls, parser, token):
        tokens = token.contents.split()
        varname = None
        if len(tokens) == 4 and tokens[2] == 'as':
            varname = tokens[3]
        elif len(tokens) != 2:
            raise template.TemplateSyntaxError("Only 2 arguments needed for %s, "
                                               "the second should be a user" % tokens[0])
        return parser.compile_filter(tokens[1]), varname

    def __init__(self, user_expr, varname=None):
        self.user_expr = user_expr
        self.varname = varname

    def render(self, context):
        user = self.user_expr.resolve(context)
        current_user = context["request"].user
        if user.id != current_user.id and user.get_profile().is_profile_private:
            result = str(user.get_full_name())
        else:
            name = _("You") if user.id == current_user.id else user.get_full_name()
            result = "<a href='%s'>%s</a>" % (reverse("profile", args=[user.id]), name)
        if self.varname is not None:
            context[self.varname] = mark_safe(result)
            return ''
        return result

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

    You can also stash the result in a context variable instead of rendering it
    immediately, with this alternate syntax::

        {% safe_user_link [user] as [varname] %}

    """
    user_expr, varname = UserNode.parse(parser, token)
    return UserNode(user_expr, varname)

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

class ContentObjectNode(template.Node):
    @classmethod
    def parse(cls, parser, token):
        tokens = token.contents.split()
        token_len = len(tokens)
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])
        object_expr = parser.compile_filter(tokens[2])
        if token_len == 3:
            return object_expr
        elif token_len == 5:
            if tokens[3] != 'as':
                raise template.TemplateSyntaxError("Third argument in %r must be 'as'" % token[0])
            return object_expr, tokens[4]
        else:
            raise template.TemplateSyntaxError('Unknown format: %s' % token.contents)
    
    def __init__(self, object_expr, varname=None):
        self.object_expr = object_expr
        self.varname = varname

    def get_target(self, context):
        return self.object_expr.resolve(context)

    def render(self, context):
        content_object = self.get_target(context)
        context[self.varname] = ContentType.objects.get_for_model(content_object).id
        return ''

@register.tag
def get_content_type_id(parser, token):
    object_expr, varname = ContentObjectNode.parse(parser, token)
    return ContentObjectNode(object_expr, varname=varname)


class LinkifyNode(template.Node):
    @classmethod
    def parse(cls, parser, token):
        tokens = token.contents.split()
        varname = None
        if len(tokens) == 4 and tokens[2] == 'as':
            varname = tokens[3]
        elif len(tokens) != 2:
            raise template.TemplateSyntaxError("Only 2 arguments needed for %s" % tokens[0])
        return parser.compile_filter(tokens[1]), varname

    def __init__(self, expr, varname=None):
        self.expr = expr
        self.varname = varname

    def render(self, context):
        content_object = self.expr.resolve(context)
        result = u"<a href='%s'>%s</a>" % (content_object.get_absolute_url(), content_object)
        if self.varname is not None:
            context[self.varname] = mark_safe(result)
            return ''
        return result

@register.tag
def linkify(parser, token):
    """
    Wraps the given object in a hyperlink.

    Assumes the object has a get_absolute_url method wired up properly,
    and a __unicode__ method which will be used to generate the text of the link.

    Syntax::

        {% linkify [content_object] as [varname] %}

    """
    expr, varname = LinkifyNode.parse(parser, token)
    return LinkifyNode(expr, varname)
