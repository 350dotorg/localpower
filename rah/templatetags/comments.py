from django import template
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

register = template.Library()

FB_COMMENT_TEMPLATE = """
<script>(function(d){
  var js, id = 'facebook-jssdk'; if (d.getElementById(id)) {return;}
  js = d.createElement('script'); js.id = id; js.async = true;
  js.src = "//connect.facebook.net/en_US/all.js#xfbml=1";
  d.getElementsByTagName('head')[0].appendChild(js);
}(document));</script>
<div class="fb-comments" 
     data-href="%(url)s" 
     data-num-posts="2"
     data-width="500"></div>
"""

class CommentNode(template.Node):
    @classmethod
    def parse(cls, parser, token):
        tokens = token.contents.split()
        if len(tokens) != 3:
            raise template.TemplateSyntaxError("Only 2 arguments needed for %s, "
                                               "the second should be an object" % tokens[0])
        if tokens[1] != "for":
            raise template.TemplateSyntaxError("Only 2 arguments needed for %s, "
                                               "the first should be 'for'" % tokens[0])

        return parser.compile_filter(tokens[2])

    def __init__(self, comment_expr, noop=False):
        self.comment_expr = comment_expr
        self.noop = noop

    def render(self, context):
        if self.noop:
            return ''
        obj = self.comment_expr.resolve(context)
        url = "%s%s" % (settings.SITE_DOMAIN, obj.get_absolute_url())
        return FB_COMMENT_TEMPLATE % locals()
        

@register.tag
def render_comment_list(parser, token):
    comment_expr = CommentNode.parse(parser, token)
    return CommentNode(comment_expr)

@register.tag
def render_comment_form(parser, token):
    comment_expr = CommentNode.parse(parser, token)
    return CommentNode(comment_expr, noop=True)

