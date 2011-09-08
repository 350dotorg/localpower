from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.exceptions import ImproperlyConfigured

from core import PMMail

class EmailBackend(BaseEmailBackend):
    
    def __init__(self, api_key=None, default_sender=None, **kwargs):
        """
        Initialize the backend.
        """
        super(EmailBackend, self).__init__(**kwargs)
        self.api_key = getattr(settings, 'POSTMARK_API_KEY', api_key)
        if not self.api_key:
            raise ImproperlyConfigured('POSTMARK API key must be set in Django settings file or passed to backend constructor.')            
        self.default_sender = getattr(settings, 'POSTMARK_SENDER', default_sender)
                                    
    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        if not email_messages:
            return         
        num_sent = 0
        for message in email_messages:
            sent = self._send(message)
            if sent:
                num_sent += 1
        return num_sent
        
        
    def _send(self, message):
        """A helper method that does the actual sending."""
        if not message.recipients():
            return False            
        try:
            recipients = ','.join(message.to)
            
            html_body = None
            no_text = False
            if message.__class__.__name__ == 'EmailMultiAlternatives':
                for alt in message.alternatives:
                    if alt[1] == "text/html":
                        html_body=alt[0]
                        break
            elif message.content_subtype == "html":
                html_body = message.body
                no_text = True
            
            reply_to = None
            custom_headers = {}           
            if message.extra_headers and isinstance(message.extra_headers, dict):
                if message.extra_headers.has_key('Reply-To'):
                    reply_to = message.extra_headers.pop('Reply-To')
                if len(message.extra_headers):
                    custom_headers = message.extra_headers
            
            postmark_message = PMMail(api_key=self.api_key, 
                                  subject=message.subject,
                                  sender=message.from_email,
                                  to=recipients,
                                  text_body=None if no_text else message.body,
                                  html_body=html_body,
                                  reply_to=reply_to,
                                  custom_headers=custom_headers)

            postmark_message.send()
        except:
            if self.fail_silently:
                # Since we try to email admins if fail_silently=False
                # we need to just throw away the error if fail_silently=True
                # or else we could end up with infinite loops of failed
                # mail-sending if the problem is with the mail configuration
                # or postmark service.
                return False

            import sys, traceback
            traceback = '\n'.join(traceback.format_exception(*(sys.exc_info())))
            from pprint import pformat
            mail_data = pformat(postmark_message.__dict__)
            message = u"%s\n\n%s" % (traceback, mail_data)
            from django.core.mail import mail_admins
            mail_admins('Error sending mail', message, fail_silently=True)
            #raise
        return True

