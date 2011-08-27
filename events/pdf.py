import cStringIO as StringIO
import ho.pisa as pisa
from django.template.loader import get_template
from django.template import Context
from django.utils.translation import ugettext as _
from django.http import HttpResponse
from cgi import escape

def render_to_pdf(template_src, filename, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    result = StringIO.StringIO()

    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), mimetype='application/pdf')
        response["Content-Disposition"] = "attachment; filename=%s" % filename
        return response
    return HttpResponse('We had some errors<pre>%s</pre>' % escape(html))
