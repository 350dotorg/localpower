import time

from django.core.management.base import BaseCommand

from groups.models import Group
from geo.fields import GoogleGeoField

class Command(BaseCommand):
    help = "Generate lat, lon coordinates for all the non geo groups"

    def handle(self, *args, **options):
        field = GoogleGeoField()
        for group in Group.objects.select_related().all():
            time.sleep(.5)
            data = field.clean(str(group.geom))
            print "UPDATE `groups_group` SET `lat`='%s', `lon`='%s' WHERE `id`='%s';" % (data['latitude'], data['longitude'], group.id)
