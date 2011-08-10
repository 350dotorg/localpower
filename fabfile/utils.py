import functools
import re

from fabric.api import local, env

def query_revision(treeish="HEAD"):
    if re.match("^[0-9a-f]{40}$", treeish): return treeish
    return local("git show %s | sed q | cut -d ' ' -f 2" % treeish, capture=True)

def query_branch(treeish="HEAD"):
    return local("git name-rev --name-only %s" % treeish, capture=True)

def runs_last(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if not env.all_hosts or env.host_string == env.all_hosts[-1]:
            return func(*args, **kwargs)
        return None
    return decorated
