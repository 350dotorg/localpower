from django.db.models import get_models, signals
from actions import models as actions_app

def create_default_actions(app, created_models, verbosity, **kwargs):
    from actions.models import Action, ActionForm
    from django.core.management import call_command
    if Action in created_models and kwargs.get('interactive', True):
        msg = "\nYou just installed the actions table, would you like to install the " \
                "default set of actions? (yes/no): "
        confirm = raw_input(msg)
        while 1:
            if confirm not in ('yes', 'no'):
                confirm = raw_input('Please enter either "yes" or "no": ')
                continue
            if confirm == 'yes':
                call_command("loaddata", "actions/fixtures/actions.json", verbosity=0, interactive=True)
            break
    if ActionForm in created_models and kwargs.get('interactive', True):
        msg = "\nYou just installed the action forms table, would you like to install the " \
                "default set of action forms? (yes/no): "
        confirm = raw_input(msg)
        while 1:
            if confirm not in ('yes', 'no'):
                confirm = raw_input('Please enter either "yes" or "no": ')
                continue
            if confirm == 'yes':
                call_command("loaddata", "actions/fixtures/actionforms.json", verbosity=0, interactive=True)
            break

#signals.post_syncdb.connect(create_default_actions, sender=actions_app,
#        dispatch_uid="rah.management.create_default_actions")
