import re

from django import template
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from utils import strip_quotes

register = template.Library()

class ActionFormNode(template.Node):
    def __init__(self, complete_title=None, commit_title=None, undo_title=None):
        self.complete_title = complete_title or _("I did this!")
        self.commit_title = commit_title or _("Make a commitment")
        self.undo_title = undo_title or _("Wait - I'm still working on this action.")

    def render(self, context):
        values = {"complete_title": self.complete_title,
                  "commit_title": self.commit_title,
                  "undo_title": self.undo_title}
        context.push()
        value = render_to_string("actions/_action_form.html", values, context)
        context.pop()
        return value

@register.tag
def action_form(parser, token):
    arguments = token.split_contents()
    if len(arguments) > 4:
        raise template.TemplateSyntaxError, "%(tag_name)s tag takes 3 arguments at most {%% %(tag_name)s \
            [complete_title] [commit_title] [undo_title] %%}" % {"tag_name": token.contents.split()[0]}
    params = []
    if len(arguments) > 1:
        params.append(strip_quotes(arguments[1]))
    if len(arguments) > 2:
        params.append(strip_quotes(arguments[2]))
    if len(arguments) > 3:
        params.append(strip_quotes(arguments[3]))
    return ActionFormNode(*params)

class TemplateSnippetNode(template.Node):
    def __init__(self, filter_expr):
        self.filter_expr = filter_expr
    def render(self, context):
        template = Template(self.filter_expr.resolve(context))
        return template.render(context)

@register.tag
def render_template_snippet(parser, token):
    try:
        tag_name, snippet = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%(tag_name)s tag requires 1 arguments {%% %(tag_name)s \
            [template_snippet] %%}" % {"tag_name": token.contents.split()[0]}
    return TemplateSnippetNode(parser.compile_filter(snippet))
