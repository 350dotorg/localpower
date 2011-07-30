form = dict(
    "subject": "Re: Fpp",
    "body": "Fleem",
    "parent_id": "1",
    "parent_id_sig": "???",
    "csrfmiddlewaretoken": "???"
    )

import base64
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from groups.disc_utils import create_discussion
from utils import hash_val
import zlib

@csrf_exempt
def process(req):
    values = dict(
        subject=req.POST['subject'],
        body=base64.decodestring(req.POST['body']))

    group, parent_values = req.POST['recipient'].split("+")
    parent_values = json.loads(base64.b64decode(
            parent_values))
    parent_values['parent_id_sig'] = hash_val(parent_values['parent_id'])
    values.extend(parent_values)

    email = parent_values['user']
    user = User.objects.get(email=email)
    group = Group.objects.get(slug=group)
    
    create_discussion(user, group, values)
