import boto
import os
import random
import re
import string
import tempfile
import time

from fabric.api import env, settings, local, run, sudo, put, hide, abort
from fabric.contrib.console import confirm
from fabric.colors import green, red

from deploy import install_requirements

env.disable_known_hosts = True

env.zone = "us-east-1d"
#env.key_name = "lpkey"
env.db_name = "lp"
env.db_user = "lp_db_user"

AMIs = {
    "ubuntu-11-10-64": "ami-00b14b69",
}

env.aws_key = local("echo $LP_AWS_ACCESS_KEY", capture=True)
env.aws_secret = local("echo $LP_AWS_SECRET_KEY", capture=True)
env.owner_id = local("echo $LP_AWS_OWNER_ID", capture=True)
env.key_filename = local("echo $LP_KEY_FILENAME", capture=True)
if not (env.aws_key and env.aws_secret and env.key_filename and env.owner_id):
    abort(red("You must set LP_AWS_ACCESS_KEY, LP_AWS_SECRET_KEY, LP_AWS_OWNER_ID, and LP_KEY_FILENAME in your environment."))
env.ec2_conn = boto.connect_ec2(env.aws_key, env.aws_secret)
env.rds_conn = boto.connect_rds(env.aws_key, env.aws_secret)
env.security_groups = dict([(sg.name, sg) for sg in env.ec2_conn.get_all_security_groups()])

DEFAULT_BOOTSTRAP_SCRIPT = "fabfile/bootstrap.sh"
DEFAULT_USER_DATA_FILE = "fabfile/user_data.sh"

def _generate_password(length=36):
    return ''.join([random.choice(string.ascii_letters + string.digits) for i in range(length)])

def _slugify(value):
    return value.replace(" ", "-")

def _launch_ec2_ami(ami, *args, **kwargs):
    kwargs["placement"] = env.zone
    user_data_file = kwargs.pop("user_data_file", None)
    if user_data_file:
        kwargs["user_data"] = open(user_data_file, "r").read()
    launched_image = env.ec2_conn.get_image(ami).run(key_name=env.key_name, **kwargs)
    time.sleep(4)
    return launched_image

def _wait_for_resources(resources, check_increment=5, up_state="running", test_ssh=True):
    while any([r.update() != up_state for r in resources]):
        time.sleep(check_increment)
        print ", ".join(["%s is %s" % (r, r.state) for r in resources])
    if test_ssh:
        with settings(hide("running", "warnings", "stderr"), warn_only=True):
            while any([local("ssh -o StrictHostKeyChecking=no ubuntu@%s 'echo TEST'" % r.public_dns_name).failed for r in resources]):
                time.sleep(check_increment)
                print ", ".join(["%s is %s" % (r, r.state) for r in resources])

def _bootstrap(shell_vars=None, command="bootstrap_system;", script=DEFAULT_BOOTSTRAP_SCRIPT):
    remote_script = "/home/ubuntu/%s" % os.path.basename(script)
    parent_dir = os.path.dirname(os.path.abspath(script))
    contents = re.sub("::(.*)::", lambda x: open("%s/%s" % (parent_dir, x.group(1))).read().replace("$", "\$"),
        open(script).read()) # the bootstrap script needs to be filled with external file contents
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(contents)
    temp.flush()
    put(temp.name, remote_script)
    temp.close()
    var_exports = " && ".join(['export %s="%s"' % (k,v) for k,v in shell_vars.items()])
    sudo("%s && source %s && %s" % (var_exports, remote_script, command))
    run("rm %s" % remote_script)

def _print_mysqlduplicate_alias(cloud_name, db_password, host):
    appserver_master_ip = get_cloud_instances(cloud_name, "appserver_master")[0].public_dns_name
    print(green("""
        "%s": {
            "SERVER": "%s@%s",
            "DATABASE": "%s",
            "HOST": "%s",
            "USER": "%s",
            "PASSWORD": "%s",
            "CAN_REPLACE": True,
        },""" % (cloud_name, env.user, appserver_master_ip, env.db_name, host, env.db_user, db_password)))
    print(green("Add the above setting to your local_settings module and execute:"))
    print(green("\t./mysqlduplicate.py prod %s [if this is a prod environment your creating, remember to copy ALL tables]" % cloud_name))
    print(green("\tfab -H %s syncdb" % appserver_master_ip))

def launch_server(cloud_name, environment="staging", instance_type="t1.micro", ami=AMIs["ubuntu-11-10-64"]):
    "launch a new server"
    cloud_name = _slugify(cloud_name)
    instance = _launch_ec2_ami(ami, instance_type=instance_type, security_groups=(
        env.security_groups["ssh_access"],
        env.security_groups["load_balancers"],
        env.security_groups["app_servers"])).instances[0]
    _wait_for_resources([instance])
    instance.add_tag(key="cloud_name", value=cloud_name)
    instance.add_tag(key="roles", value="appserver,appserver_master,loadbalancer")
    with settings(host_string=instance.public_dns_name):
        db_password = _generate_password()
        shell_vars = {
            "AWS_ACCESS_KEY": env.aws_key,
            "AWS_SECRET_KEY": env.aws_secret,
            "PUBLIC_DNS_NAME": instance.public_dns_name,
            "APP_SERVER_IPS": instance.private_ip_address,
            "DB_PASSWORD": db_password,
            "ENVIRONMENT": environment,
            "DB_NAME": env.db_name,
            "DB_USER": env.db_user
        }
        _bootstrap(shell_vars=shell_vars,
            command="bootstrap_system; bootstrap_database; bootstrap_appserver; bootstrap_loadbalancer;")
        install_requirements()
    _print_mysqlduplicate_alias(cloud_name, db_password, "127.0.0.1")

def launch_cloud(cloud_name, environment="staging", count=1, lb_type="t1.micro", app_type="t1.micro",
        rds_type="db.m1.small", ami=AMIs["ubuntu-11-10-64"]):
    "launch a new cloud (loadbalancer, appserver(s) and RDS)"
    cloud_name = _slugify(cloud_name)
    db_host, db_password = _launch_rds(cloud_name, rds_type)
    _launch_appservers(cloud_name, db_password, db_host, environment, count, app_type, ami)
    _launch_loadbalancer(cloud_name, ami, lb_type)
    nginx_upsteam_update(cloud_name)
    memcached_pool_update(cloud_name)
    _print_mysqlduplicate_alias(cloud_name, db_password, db_host)

def grow_cloud(cloud_name, count=1):
    appserver_master = get_cloud_instances(cloud_name, "appserver_master")[0]
    _duplicate_appserver(appserver_master.id, cloud_name, appserver_master.instance_type, count)
    nginx_upsteam_update(cloud_name)
    memcached_pool_update(cloud_name)

def get_cloud_instances(cloud_name, role):
    """
    Get a list of attributes from instances in a given cloud.
    attr: some attribute of an instance. e.g.: id, ip_address, public_dns_name, private_ip_address, private_dns_name
    role: specify a role defined in roles. e.g.: "loadbalancer", "appserver", "appserver_master"
    """
    instances = []
    reservations = env.ec2_conn.get_all_instances()

    for res in reservations:
        instance = res.instances[0]
        tags = instance.tags
        if "cloud_name" in tags and tags["cloud_name"] == cloud_name \
            and "roles" in tags and role in tags["roles"].split(","):
            instances.append(instance)

    if not instances:
        abort(red("No instances found in %s." % cloud_name))

    return instances

def nginx_upsteam_update(cloud_name):
    loadbalancers = get_cloud_instances(cloud_name, "loadbalancer")
    app_servers = get_cloud_instances(cloud_name, "appserver")
    app_ips = " ".join(["server %s:3031;" % inst.private_ip_address for inst in app_servers])

    for loadbalancer in loadbalancers:
        with settings(host_string=loadbalancer.public_dns_name):
            sudo("sed -i 's/server .*;/%s/' /etc/nginx/sites-available/rah" % app_ips)
            sudo("/etc/init.d/nginx reload")

def memcached_pool_update(cloud_name):
    app_servers = get_cloud_instances(cloud_name, "appserver")
    memcached_ips = ";".join(["%s:11211" % inst.private_ip_address for inst in app_servers])

    for appserver in app_servers:
        with settings(host_string=appserver.public_dns_name):
            run("sed -i 's/\(CACHE_BACKEND.*\/\/\).*\(\/.*\)/\\1%s\\2/' /home/ubuntu/webapp/settings.py" % memcached_ips)
            run("echo 'flush_all' | nc %s 11211" % appserver.private_ip_address)
            sudo("stop uwsgi")
            sudo("start uwsgi")

def _launch_rds(id, instance_type, size="5"):
    "Start up a new RDS, returns a 3-tuple - (RDS, RDS Endpoint, DB Password)"
    password = _generate_password()
    host = "%s.co6ulcbqxe1u.us-east-1.rds.amazonaws.com" % id
    rds = env.rds_conn.create_dbinstance(id=id, allocated_storage=size, instance_class=instance_type,
        master_username=env.db_user, master_password=password, db_name=env.db_name, security_groups=["default"],
        param_group="rah", availability_zone=env.zone, preferred_maintenance_window="Sun:10:00-Sun:14:00",
        preferred_backup_window="08:00-10:00", backup_retention_period=7)
    return (host, password)

def _launch_appservers(cloud_name, db_password, db_host, environment, count, instance_type, ami):
    "Start up a set of new app servers"
    count = int(count)
    server = _launch_ec2_ami(ami, min_count=1, max_count=1, instance_type=instance_type,
        security_groups=(env.security_groups["ssh_access"], env.security_groups["app_servers"])).instances[0]
    _wait_for_resources([server])
    server.add_tag(key="roles", value="appserver,appserver_master")
    server.add_tag(key="cloud_name", value=cloud_name)
    with settings(host_string=server.public_dns_name):
        shell_vars = {
            "AWS_ACCESS_KEY": env.aws_key,
            "AWS_SECRET_KEY": env.aws_secret,
            "PUBLIC_DNS_NAME": server.public_dns_name,
            "DB_PASSWORD": db_password,
            "ENVIRONMENT": environment,
            "DB_NAME": env.db_name,
            "DB_USER": env.db_user,
            "DB_HOST": db_host
        }
        _bootstrap(shell_vars=shell_vars, command="bootstrap_system; bootstrap_appserver;")

    if count > 1:
        _duplicate_appserver(server.id, cloud_name, instance_type, count-1, no_reboot=False)

def _duplicate_appserver(id, cloud_name, instance_type, count, no_reboot=True):
    image_names = [i.name for i in env.ec2_conn.get_all_images(owners=[env.owner_id])]
    counter = 1
    while True:
        if not any("%s-%s appserver" % (cloud_name, counter) == n for n in image_names):
            break;
        counter += 1
    image_id = env.ec2_conn.create_image(id, "%s-%s appserver" % (cloud_name, counter), no_reboot=no_reboot)
    image = env.ec2_conn.get_image(image_id)
    _wait_for_resources([image], up_state="available", test_ssh=False)
    servers = _launch_ec2_ami(image_id, min_count=count, max_count=count,
        instance_type=instance_type, security_groups=(env.security_groups["ssh_access"],
        env.security_groups["app_servers"])).instances
    _wait_for_resources(servers)
    for s in servers:
        s.add_tag(key="roles", value="appserver")
        s.add_tag(key="cloud_name", value=cloud_name)
    return servers

def _launch_loadbalancer(cloud_name, ami, instance_type):
    "Start up a new load balancer server"
    server = _launch_ec2_ami(ami, instance_type=instance_type, security_groups=(
        env.security_groups["ssh_access"], env.security_groups["load_balancers"])).instances[0]
    _wait_for_resources([server])
    server.add_tag(key="roles", value="loadbalancer")
    server.add_tag(key="cloud_name", value=cloud_name)

    with settings(host_string=server.public_dns_name):
        shell_vars = {
            "AWS_ACCESS_KEY": env.aws_key,
            "AWS_SECRET_KEY": env.aws_secret,
            "PUBLIC_DNS_NAME": server.public_dns_name
        }
        _bootstrap(shell_vars, command="bootstrap_system; bootstrap_loadbalancer;")

