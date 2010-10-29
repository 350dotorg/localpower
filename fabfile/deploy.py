import fabric

from fabric.api import env, settings, require, run, sudo, abort, runs_once
from fabric.contrib.console import confirm
from fabric.colors import green, red

from utils import query_revision
from codebase import codebase_deployment

def _truth_value(value):
    return bool(value) and str(value).upper() != "FALSE"

@runs_once
def enable_maintenance_page():
    "Turns on the maintenance page"
    if env.environment == "production":
        for host in env.roledefs["loadbalancer"]:
            with settings(host_string=host):
                sudo("rm /etc/nginx/sites-enabled/rah")
                sudo("ln -s /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/maintenance")
                sudo("/etc/init.d/nginx reload")
    
def _fetch():
    "Updates the application with new code"
    require("hosts", "deploy_to")
    run("cd %(deploy_to)s && git fetch --all" % env)
    
def _reset():
    "Set the workspace to the desired revision"
    require("hosts", "deploy_to")
    run("cd %(deploy_to)s && git reset --hard" % env)
    
def _checkout():
    "Checkout the revision you would like to deploy"
    require("hosts", "deploy_to")
    with settings(warn_only=True):
        result = run("cd %(deploy_to)s && git checkout -b \
            `date +'%%Y-%%m-%%d_%%H-%%M-%%S'`_`whoami` %(sha)s" % env)
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
def minify():
    "Minify the js and css files"
    require("hosts", "deploy_to")
    run("cd %(deploy_to)s/static/minify && ./minify.sh" % env)
    
@runs_once
def s3sync():
    "Sync static data with our s3 bucket"
    require("hosts", "deploy_to")
    run("cd %(deploy_to)s && python manage.py sync_media_s3 --gzip --force --expires" % env)
    
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
    
def restart_apache():
    "Reboot Apache2 server."
    require("hosts")
    sudo("/etc/init.d/apache2 restart")

@runs_once
def disable_maintenance_page():
    "Turns off the maintenance page"
    if env.environment == "production":
        for host in env.roledefs["loadbalancer"]:
            with settings(host_string=host):
                sudo("rm /etc/nginx/sites-enabled/maintenance")
                sudo("ln -s /etc/nginx/sites-available/rah /etc/nginx/sites-enabled/rah")
                sudo("/etc/init.d/nginx reload")
                
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
        minify()
        if _truth_value(sync_media):
            s3sync()
        syncdb()
        migratedb()
    restart_apache()
    disable_maintenance_page()
    codebase_deployment()
    print(green("%(revision)s has been deployed to %(hosts)s" % env))