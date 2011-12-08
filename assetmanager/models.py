from django.db import models

def generate_filename(instance, filename):
    return instance.path.strip('/')

class SiteAsset(models.Model):
    path = models.CharField(max_length=255, unique=True)
    file = models.FileField(upload_to=generate_filename)

    def __unicode__(self):
        return self.path

