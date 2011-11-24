import fabric

from fabric.api import env, settings, local, require, run, sudo, abort, runs_once
from fabric.contrib.console import confirm
from fabric.colors import green, red

from utils import query_revision, runs_last

env.key_filename = local("echo $LP_KEY_FILENAME", capture=True)

def _truth_value(value):
    return bool(value) and str(value).upper() != "FALSE"

@runs_once
def enable_maintenance_page():
    "Turns on the maintenance page"
    if hasattr(env, "loadbalancers"):
        for host in env.loadbalancers:
            with settings(host_string=host, warn_only=True):
                result = sudo("rm /etc/nginx/sites-enabled/rah")
                if not result.failed:
                    sudo("ln -s /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/maintenance")
                    sudo("/etc/init.d/nginx reload")

def _fetch():
    "Updates the application with new code"
    require("hosts", "deploy_to")
    sudo("cd %(deploy_to)s && git fetch --all" % env, user="wsgi")

def _reset():
    "Set the workspace to the desired revision"
    require("hosts", "deploy_to")
    sudo("cd %(deploy_to)s && git reset --hard" % env, user="wsgi")

def _checkout():
    "Checkout the revision you would like to deploy"
    require("hosts", "deploy_to")
    with settings(warn_only=True):
        result = sudo("cd %(deploy_to)s && git checkout -b \
            `date +'%%Y-%%m-%%d_%%H-%%M-%%S'`_`whoami` %(sha)s" % env,
                      user="wsgi")
        if result.failed:
            abort(red("Have you pushed your latest changes to the repository?"))

def code_deploy():
    "Wrapper for performing a code deploy of fetch, reset and checkout"
    require("hosts", "deploy_to")
    _fetch()
    _reset()
    _checkout()

def install_requirements():
    "Using pip install all of the requirements defined"
    require("hosts", "deploy_to")
    sudo("cd %(deploy_to)s/../requirements && pip install -r %(deploy_to)s/requirements.txt" % env)

@runs_once
def optimize_static():
    "Using requirejs and google closure optimize the resources in the static folder"
    require("hosts", "deploy_to")
    run("cd %(deploy_to)s && rm -rf static_build" % env)
    run("cd %(deploy_to)s && tools/requirejs/build/build.sh tools/app.build.js" % env)
    run("cd %(deploy_to)s/static_build && find . -name '*.psd' -exec rm {} \;" % env)

@runs_once
def s3sync():
    "Sync static data with our s3 bucket"
    require("hosts", "deploy_to")
    run("cd %(deploy_to)s && python manage.py sync_media_s3 --gzip --force --expires --dir %(deploy_to)s/static_build" % env)

@runs_once
def syncdb():
    "Sync the database with any new models"
    require("hosts", "deploy_to")
    if fabric.version.VERSION[0] > 0 or \
        confirm("This script cannot handle interactive shells, are you sure you want to run syncdb?"):
        run("cd %(deploy_to)s && python manage.py syncdb" % env)

@runs_once
def migratedb():
    "Migrate the database"
    require("hosts", "deploy_to")
    if confirm("Would you like to migrate the database?"):
        run("cd %(deploy_to)s && python manage.py migrate" % env)

def restart_app_server():
    "Restart uWSGI processes"
    require("hosts")
    sudo("stop uwsgi")
    sudo("start uwsgi")

@runs_last
def disable_maintenance_page():
    "Turns off the maintenance page"
    if hasattr(env, "loadbalancers"):
        for host in env.loadbalancers:
            with settings(host_string=host):
                sudo("rm /etc/nginx/sites-enabled/maintenance")
                sudo("ln -s /etc/nginx/sites-available/rah /etc/nginx/sites-enabled/rah")
                sudo("/etc/init.d/nginx reload")

def _touch_wsgi():
    require("deploy_to", "hosts", "wsgi_file")
    sudo("touch %(wsgi_file)s" % env, user="wsgi")

@runs_once
def _syncdb():
    "Sync the database with any new models"
    require("hosts", "deploy_to")
    if fabric.version.VERSION[0] > 0 or \
            confirm("This script cannot handle interactive shells, are you sure you want to run syncdb?"):
        sudo("cd %(deploy_to)s && %(virtualenv)s/bin/python manage.py syncdb" % env, user="wsgi")

def push():
    require("deploy_to", "hosts", "environment")
    _fetch()
    _reset()
    _checkout()
    _touch_wsgi()
    _syncdb()

def deploy(revision=None, code_only=False, sync_media=True):
    "Deploy a revision to server"
    if revision:
        env.revision = revision
        env.sha = query_revision(revision)
    require("deploy_to", "hosts", "environment")
    enable_maintenance_page()
    code_deploy()
    if not _truth_value(code_only):
        install_requirements()
        if _truth_value(sync_media):
            optimize_static()
            s3sync()
    syncdb()
    migratedb()
    restart_app_server()
    disable_maintenance_page()
    print(green("%(revision)s has been deployed to %(environment)s" % env))
