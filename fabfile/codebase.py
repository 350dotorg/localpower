# TODO: Make this work with GitHub instead of CodeBase
import base64
import re
import urllib2

from fabric.api import env, local, require

from utils import query_branch, runs_last

def _send_codebase(path, data=None):
    "POST the given data message to the codebase API, if no data is provided GET"
    match = re.search("git\@(codebasehq.*):(.*)\/(.*)\/.*\.git", env.repository)
    account = match.group(2)
    domain = "api3.%s" % match.group(1)
    project = match.group(3)
    username = local("git config codebase.username", capture=True).strip()
    api_key = local("git config codebase.apikey", capture=True).strip()
    url = "https://%s/%s%s" % (domain, project, path)
    headers = {"Content-type": "application/xml", "Accept": "application/xml", 
        "Authorization": "Basic %s" % base64.b64encode("%s/%s:%s" % (account, username, api_key))}
    request = urllib2.Request(url, data, headers)
    return urllib2.urlopen(request).read()

@runs_last
def codebase_deployment():
    "Notify codebase that a new revision has been deployed"
    require("sha", "environment")
    repository = re.search("git\@codebasehq.*:.*\/.*\/(.*)\.git", env.repository).group(1)

    xml = []
    xml.append("<deployment>")
    xml.append("<servers>%s</servers>" % ",".join(env.all_hosts))
    xml.append("<revision>%(sha)s</revision>" % env)
    xml.append("<environment>%(environment)s</environment>" % env)
    xml.append("<branch>%s</branch>" % query_branch(env.sha))
    xml.append("</deployment>")

    _send_codebase("/%s/deployments" % repository, "".join(xml))
