import os
import re
import StringIO
import tempfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from django.utils.importlib import import_module

from PIL import Image

from models import Thumbnail
from processors import Resize

def load_processor(path):
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]
    return getattr(import_module(module), attr)

class ImageAndThumbsFile(ImageFieldFile):
    PROCESSORS = getattr(settings, "THUMBMNAIL_PROCESSORS", None)
    PROCESSORS = [load_processor(proc) for proc in PROCESSORS]
    if not PROCESSORS:
        PROCESSORS = [Resize]

    def __init__(self, *args, **kwargs):
        super(ImageAndThumbsFile, self).__init__(*args, **kwargs)

    def __getattribute__(self, name):
        try:
            return super(ImageAndThumbsFile, self).__getattribute__(name)
        except AttributeError:
            if name.startswith("thumbnail"):
                thumbnail_name = self._generate_thumbnail_name(name)
                if not Thumbnail.objects.filter(raw=self.name, thumbnail=thumbnail_name).exists():
                    if not self.storage.exists(thumbnail_name):
                        options = [opt for opt in name.split("_")[1:] if opt]
                        try:
                            thumbnail = self._process_options(options, thumbnail_name)
                        except:
                            return ''
                        thumbnail_name = self.storage.save(thumbnail_name, thumbnail)
                    Thumbnail.objects.create(raw=self.name, thumbnail=thumbnail_name)
                return thumbnail_name
            raise

    def _open_file(self, name):
        return ImageFieldFile(self.storage.open(name, ImageAndThumbsField(), name))

    def _generate_thumbnail_name(self, attribute_name):
        directory = os.path.dirname(self.name)
        basename = os.path.basename(self.name)
        filename, extension = os.path.splitext(basename)
        extension = getattr(settings, "THUMBNAIL_EXTENSION", extension)
        return "%s/%s__%s%s" % (directory, filename, attribute_name, extension)

    def _process_options(self, options, thumbnail_name):
        copy = ContentFile(self.storage.open(self.name).read())
        thumbnail = Image.open(copy)
        for option in options:
            for proc in ImageAndThumbsFile.PROCESSORS:
                matcher = proc.key_expression().match(option)
                if matcher:
                    thumbnail = proc.process(thumbnail, matcher)
                    break
        codec = os.path.splitext(thumbnail_name)[1][1:].lower()
        if codec == "png":
            imgstr = StringIO.StringIO()
            thumbnail.save(imgstr, "png")
            return ContentFile(imgstr.getvalue())
        return ContentFile(thumbnail.tostring(codec, thumbnail.mode))

    def save(self, *args, **kwargs):
        images = Thumbnail.objects.filter(raw=self.name)
        if images:
            for image in images:
                if image.raw != self.field.default:
                    self.storage.delete(image.thumbnail)
            images.delete()
        return super(ImageAndThumbsFile, self).save(*args, **kwargs)

class ImageAndThumbsField(models.ImageField):
    """
    The ImagesAndThumbsField should be used as a drop in replacement for the standard django
    ImagesField.  With this field you get all the niceties the aforementioned provides in addition
    to the ability to generate thumbnails on the fly.  Thumbnail generation works be accessing
    pseudo ``thumbnail`` attributes.

    For example if you've created an ``image`` field for your Community model, you can access a
    thumbmnail using the following: ``community.image.thumbnail_128x128``. If the thumbnail does not
    exist, then it is automatically generated and stored using your default file storage system.

    As you've probably already noticed, the size of the thumbnail is specified in the name of the
    attribute.  This Field has been built to parse multiple options out of the attribute name and
    apply their associated processors in the order they're found. So for example, if you wanted to
    create another *processor* for say cropping the image.  You can create a new ``Processor`` class
    (see the ``processors.py`` module), that defines the ``key_expression()`` method for say
    finding the word *crop* (e.g. ``re.compile("crop")``) and another method ``process(image, matcher)``
    for actually performing the desired operation on the image.
    """
    attr_class = ImageAndThumbsFile
