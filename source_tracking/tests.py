from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from models import UserSource

class SourceTrackingTests(TestCase):
    fixtures = ["actions.json"]

    def setUp(self):
        self.client = Client()

    def test_register_no_codes(self):
        response = self.client.post(reverse("register"), {"first_name": "test",
            "email": "test@test.com", "password1": "testing", "password2": "testing",}, follow=True)
        self.failUnlessEqual(response.template[0].name, "rah/profile.html")
        sources = UserSource.objects.all()
        self.failUnlessEqual(sources.count(), 1)
        test_source = sources[0]
        self.failUnlessEqual(test_source.user.email, "test@test.com")
        self.failUnlessEqual(test_source.source, "direct")
        self.failUnlessEqual(test_source.subsource, "")
        self.failUnlessEqual(test_source.referrer, "")

    def test_facebook_code(self):
        self.client.get(reverse("index"), {"source": "facebook"}, HTTP_REFERER="http://www.facebook.com/")
        response = self.client.post(reverse("register"), {"first_name": "test",
            "email": "test@test.com", "password1": "testing", "password2": "testing",}, follow=True)
        self.failUnlessEqual(response.template[0].name, "rah/profile.html")
        sources = UserSource.objects.all()
        self.failUnlessEqual(sources.count(), 1)
        test_source = sources[0]
        self.failUnlessEqual(test_source.user.email, "test@test.com")
        self.failUnlessEqual(test_source.source, "facebook")
        self.failUnlessEqual(test_source.subsource, "")
        self.failUnlessEqual(test_source.referrer, "http://www.facebook.com/")

    def test_google_add_code(self):
        self.client.get(reverse("index"), {"source": "google_ad", "subsource": "md_campaign"},
            HTTP_REFERER="http://www.google.com/")
        response = self.client.post(reverse("register"), {"first_name": "test",
            "email": "test@test.com", "password1": "testing", "password2": "testing",}, follow=True)
        self.failUnlessEqual(response.template[0].name, "rah/profile.html")
        sources = UserSource.objects.all()
        self.failUnlessEqual(sources.count(), 1)
        test_source = sources[0]
        self.failUnlessEqual(test_source.user.email, "test@test.com")
        self.failUnlessEqual(test_source.source, "google_ad")
        self.failUnlessEqual(test_source.subsource, "md_campaign")
        self.failUnlessEqual(test_source.referrer, "http://www.google.com/")

    def test_browse_site_before_register(self):
        self.client.get(reverse("index"), {"source": "google_ad", "subsource": "md_campaign"},
            HTTP_REFERER="http://www.google.com/")
        self.client.get(reverse("action_show"))
        self.client.get(reverse("blog_index"))
        self.client.get(reverse("register"))
        response = self.client.post(reverse("register"), {"first_name": "test",
            "email": "test@test.com", "password1": "testing", "password2": "testing",}, follow=True)
        self.failUnlessEqual(response.template[0].name, "rah/profile.html")
        sources = UserSource.objects.all()
        self.failUnlessEqual(sources.count(), 1)
        test_source = sources[0]
        self.failUnlessEqual(test_source.user.email, "test@test.com")
        self.failUnlessEqual(test_source.source, "google_ad")
        self.failUnlessEqual(test_source.subsource, "md_campaign")
        self.failUnlessEqual(test_source.referrer, "http://www.google.com/")

    def test_return_with_different_tracking(self):
        self.client.get(reverse("index"), {"source": "google_ad", "subsource": "md_campaign"},
            HTTP_REFERER="http://www.google.com/")
        self.client.get(reverse("action_show"))
        self.client.get(reverse("register"), {"source": "facebook"}, HTTP_REFERER="http://www.facebook.com/")
        response = self.client.post(reverse("register"), {"first_name": "test",
            "email": "test@test.com", "password1": "testing", "password2": "testing",}, follow=True)
        self.failUnlessEqual(response.template[0].name, "rah/profile.html")
        sources = UserSource.objects.all()
        self.failUnlessEqual(sources.count(), 1)
        test_source = sources[0]
        self.failUnlessEqual(test_source.user.email, "test@test.com")
        self.failUnlessEqual(test_source.source, "facebook")
        self.failUnlessEqual(test_source.subsource, "")
        self.failUnlessEqual(test_source.referrer, "http://www.facebook.com/")

    def test_tracking_after_redirected_with_tracking(self):
        self.client.get(reverse("index"), {"source": "google_ad", "subsource": "md_campaign"},
            HTTP_REFERER="http://www.google.com/")
        self.client.get(reverse("action_show"), {"source": "invite", "subsource": "/actions/"},
            HTTP_REFERER="http://%s/" % Site.objects.get_current().domain)
        response = self.client.post(reverse("register"), {"first_name": "test",
            "email": "test@test.com", "password1": "testing", "password2": "testing",}, follow=True)
        self.failUnlessEqual(response.template[0].name, "rah/profile.html")
        sources = UserSource.objects.all()
        self.failUnlessEqual(sources.count(), 1)
        test_source = sources[0]
        self.failUnlessEqual(test_source.user.email, "test@test.com")
        self.failUnlessEqual(test_source.source, "invite")
        self.failUnlessEqual(test_source.subsource, "/actions/")
        self.failUnlessEqual(test_source.referrer, "http://www.google.com/")

