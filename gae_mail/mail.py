from django.core.mail.backends.base import BaseEmailBackend
from restclient import POST
import base64

class AppEngineEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return

        for msg in email_messages:
            data = dict(
                from_email=msg.from_email,
                recipients=','.join(msg.recipients()),
                reply_to=msg.extra_headers.get('Reply-To', ''),
                subject=msg.subject,
                text=base64.encodestring("Text message"),
                html=base64.encodestring(msg.body.encode("utf8"))
                )
            resp = POST("http://localpower-dev.appspot.com/_send_mail/", params=data, 
                        async=False, resp=True)
            print resp
        return len(email_messages)
