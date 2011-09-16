from django import forms
from django.contrib.sites.models import Site

from facebook_app.models import publish_message as publish_facebook_message
from twitter_app.utils import update_status as update_twitter_status
from twitter_app.oauth import OAuthToken

from models import Record

class AskToShareForm(forms.Form):
    SOCIAL_NETWORKS = (
        ("t", "Twitter",),
        ("f", "Facebook",),
    )
    has_twitter_access = forms.BooleanField(widget=forms.HiddenInput, required=False)
    has_facebook_access = forms.BooleanField(widget=forms.HiddenInput, required=False)

    def __init__(self, request, *args, **kwargs):
        super(AskToShareForm, self).__init__(*args, **kwargs)
        profile = request.user.get_profile()
        self.fields["has_twitter_access"].initial = bool(profile.twitter_access_token)
        self.fields["has_facebook_access"].initial = bool(profile.facebook_access_token)
        self.social_networks = None

    def clean(self):
        choices = self.data.getlist("social_network")
        for choice in choices:
            if choice not in dict(self.SOCIAL_NETWORKS).keys():
                raise forms.ValidationError("Invalid social network choice %s" % choice)
        self.social_networks = choices
        
    def save(self, request, *args, **kwargs):
        profile = request.user.get_profile()

        last_record = Record.objects.user_records(user=request.user,
                                                  quantity=1)[0]
        message = last_record.render_for_social(request)
        message = message.encode("utf-8")
        link = "http://%s%s" % (Site.objects.get_current().domain,
                                last_record.get_absolute_url())

        for network in self.social_networks:
            self.try_to_enable(network, profile, link, last_record, request, message)
        return True

    def try_to_enable(self, network, profile, link, last_record, request, message):
        if network == "f":
            profile.facebook_share = True
            profile.save()

            if not profile.facebook_access_token:
                return False

            # now post their last record
            fb_link = "%s?source=sm-fb-post&subsource=%s" % (link, 
                                                             last_record.get_absolute_url())
            publish_facebook_message(request.user, message, fb_link)
            return True

        if network == "t":
            profile.twitter_share = True
            profile.save()

            if not profile.twitter_access_token:
                return False

            twitter_msg = "%s (%s)" % (message, link)
            update_twitter_status(OAuthToken.from_string(profile.twitter_access_token), 
                                  twitter_msg)
            return True

        return True

