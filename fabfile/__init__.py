from fabric.api import env, settings, local, run, abort
from fabric.contrib.console import confirm

from utils import query_revision

env.user = "ubuntu"
env.disable_known_hosts = True

# Roles take a list of one or more servers
env.roledefs = {
    "application": [""],
    "loadbalancer": [""],
    "staging": ["ec2-107-20-218-152.compute-1.amazonaws.com"],
}

env.deploy_to = "/home/%(user)s/webapp" % env
env.parent = "origin"
env.revision = "HEAD"
env.sha = query_revision(env.revision)
env.repository = "git://github.com/350org/localpower.git"

def staging():
    env.roles = ["staging"]
    env.environment = "staging"
    env.loadbalancers = env.roledefs["staging"]

def prod():
    env.roles = ["application"]
    env.environment = "production"
    env.loadbalancers = env.roledefs["loadbalancer"]

def environment(environment):
    env.environment = environment

def test():
    "Run all tests"
    with settings(warn_only=True):
        result = local("./hooks/pre-commit", capture=False)
    if result.failed and not confirm("Tests failed. Continue anyway?"):
        abort("Aborting at user request.")

def clean():
    "Remove all the .pyc files from the deploy directory"
    if env.hosts:
        run("cd %(deploy_to)s && find . -name '*.pyc' -depth -exec rm {} \;" % env)
    else:
        local("find . -name '*.pyc' -depth -exec rm {} \;", capture=True)

from codebase import *
from deploy import *
from server import *
