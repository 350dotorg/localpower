from django.contrib.sitemaps import Sitemap
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from datetime import datetime

class GenericUrl(object):
    def __init__(self, loc):
        self.location = loc

class RahSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5
    lastmod = datetime.now()

    def items(self):
        """Add urls here and they will be added to sitemap.xml"""
        urls = [
            "/projects/",
            "/groups/",
            "/",
            "/user/list/",
        ]
        # Add all the users
        users = User.objects.filter(profile__is_profile_private=False).only('id')
        for user in users:
            urls.append(reverse("profile", args=[user.id]))
        return [GenericUrl(url) for url in urls]

    def location(self, obj):
        return obj.location
