from django.conf import settings
from django.http import HttpResponse
from django.template.defaultfilters import slugify, date
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
import ho.pisa as pisa
import pyPdf
import markdown
import os

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
            u"%s<b>%s</b><br/>%s &mdash; %s" % (
                entry_prefix,
                contributor.name, 
                contributor.geom or '',
                date(sig.pledged_at)),
            styles['Heading1'])
        data.append(para)

    fd, filename = tempfile.mkstemp(suffix=".pdf")
    doc = DocTemplate(filename, pagesize=pagesizes.letter)

    doc.pageheader = challenge.title
    doc.pagefooter = "%s%s - 350.org" % (
        settings.SITE_DOMAIN, challenge.get_absolute_url())

    doc.build(data, canvasmaker=canvas.Canvas)

    cover_letter = u"""
# %s

%s

&mdash;%s""" % (challenge.title, challenge.description, challenge.creator.get_full_name())
    groups = list(challenge.groups.all())
    if groups:
        group_string = u""
        last_group = groups[-1]
        for group in groups[:-1]:
            group_string = u"%s, %s" % (group_string, unicode(group))
        group_string += u" and %s" % unicode(last_group)
        cover_letter += group_string
    _default_css = open(settings.PDF_PISA_CSS)
    DEFAULT_CSS = _default_css.read()
    _default_css.close()
    del(_default_css)
    cover_letter = markdown.markdown(cover_letter)
    cover_letter = ("""<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" />"""
                    """</head><body>%s</body></html>""" % (cover_letter.encode("utf8")))
    fd, cover_letter_filename = tempfile.mkstemp(suffix=".pdf")
    cover_letter_file = open(cover_letter_filename, 'wb')
    pisa.CreatePDF(cover_letter, cover_letter_file, default_css=DEFAULT_CSS)
    cover_letter_file.close()

    cover_letter_file = open(cover_letter_filename)
    cover_letter = pyPdf.PdfFileReader(cover_letter_file)
    content_file = open(filename)
    content = pyPdf.PdfFileReader(content_file)
    result = pyPdf.PdfFileWriter()
    for page in cover_letter.pages:
        result.addPage(page)
    for page in content.pages:
        result.addPage(page)

    # Write the combined PDF to a new tempfile
    fd, result_filename = tempfile.mkstemp(suffix=".pdf")
    fp = open(result_filename, 'wb')
    result.write(fp)

    # Clean up after ourselves
    cover_letter_file.close()
    content_file.close()
    fp.close()
    os.unlink(cover_letter_filename)
    os.unlink(filename)
    filename = result_filename

    with open(filename) as fp:
        content = fp.read()
        resp = HttpResponse(content, content_type="application/pdf")
    os.unlink(filename)
    del(fd)

    resp['Content-Disposition'] = "attachment; filename=%s.pdf" % (
        slugify(challenge.title))
    return resp
