from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib import pagesizes
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, BaseDocTemplate
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.platypus import Frame, PageTemplate
import tempfile
import random

class FancyFrame(Frame):

    def add(self, flowable, canvas, trySplit=0):
        result = Frame.add(self, flowable, canvas, trySplit=trySplit)
        if result == 0:
            return result
        
        # Slight hack: we're assuming that trySplit==0 iff this flowable
        # is an already-split portion of another flowable. So we don't want
        # to draw a line below it, since it's not the end of an entry.
        # This assumes that this frame's parent doctemplate allowSplitting
        # has not been changed from the default.
        if trySplit == 0:
            return result

        canvas.saveState()
        canvas.setStrokeColor(colors.gray)
        fudge = flowable.getSpaceAfter() / 2.0
        canvas.line(self._x, self._y + fudge,
                    self._x + self.width, self._y + fudge)
        canvas.restoreState()
        return result

class DocTemplate(BaseDocTemplate):
    def beforePage(self):
        if self.pageheader is None:
            return
        canvas = self.canv
        canvas.drawCentredString(canvas._pagesize[0] / 2.0,
                                 canvas._pagesize[1] - 0.5*inch,
                                 self.pageheader)

    def afterPage(self):
        if self.pagefooter is None:
            return
        canvas = self.canv
        canvas.drawCentredString(canvas._pagesize[0] / 2.0, 0.5*inch,
                                 self.pagefooter)

    def __init__(self, *args, **kw):
        BaseDocTemplate.__init__(self, *args, **kw)

        doc = self
        columns = []
        columns.append(FancyFrame(doc.leftMargin, doc.bottomMargin, 
                                  doc.width, doc.height))
        
        doc.addPageTemplates([
                PageTemplate(id='OneColumn', frames=columns),
                ])
        doc.pageheader = None
        doc.pagefooter = None

def _download(request, challenge, supporters):
    styles = getSampleStyleSheet()
    styles['Heading1'].spaceAfter = 12
    styles['Heading1'].fontName = "Helvetica"
    styles['Normal'].fontSize = 16

    # Use a random number in a large range so that hopefully 
    # the sequence counter will be reset, rather than counting
    # up from an old download
    entry_prefix = u"<seq id='%d'/>. " % random.randint(0, 10000)
    data = []

    for sig in supporters:
        contributor = sig.contributor
        para = Paragraph(
            u"%s<b>%s</b><br/>%s" % (
                entry_prefix,
                contributor.name, 
                contributor.geom or ''),
            styles['Heading1'])
        data.append(para)

    fd, filename = tempfile.mkstemp(suffix=".pdf")
    doc = DocTemplate(filename, pagesize=pagesizes.letter)
    #doc.pageheader = header
    #doc.pagefooter = footer
    doc.build(data, canvasmaker=canvas.Canvas)

    with open(filename) as fp:
        content = fp.read()
        resp = HttpResponse(content, content_type="application/pdf")

    import os
    os.unlink(filename)
    del(fd)

    from django.template.defaultfilters import slugify
    resp['Content-Disposition'] = "attachment; filename=%s.pdf" % (
        slugify(challenge.title))
    return resp
