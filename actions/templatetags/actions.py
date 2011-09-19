import re

from django import template
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from utils import strip_quotes

register = template.Library()

class ActionFormNode(template.Node):
    def __init__(self, complete_title=None, commit_title=None, undo_title=None):
        self.complete_title = complete_title
        self.commit_title = commit_title
        self.undo_title = undo_title

    def render(self, context):
        action = context.get("action")
        if action and action.is_group_project:
            complete_title =  _("My group already did this!")
            commit_title = _("My group will do this")
            undo_title =  _("Wait - my group is still working on this action.")
        else:
            complete_title =  _("I did this!")
            commit_title = _("Make a commitment")
            undo_title =  _("Wait - I'm still working on this action.")
        complete_title = self.complete_title or complete_title
        commit_title = self.commit_title or commit_title
        undo_title = self.undo_title or undo_title
        values = {"complete_title": complete_title,
                  "commit_title": commit_title,
                  "undo_title": undo_title}
        context.push()
        if action and action.is_group_project:
            value = render_to_string("actions/_group_action_form.html", values, context)
        else:
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

@register.filter
def find_action_progress(action, group):
    return action.find_progress_for_group(group)

