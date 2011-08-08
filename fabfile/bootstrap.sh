#!/bin/bash

set -e -x
export DEBIAN_FRONTEND=noninteractive
export LANG='en_US.UTF-8'
export LC_ALL='en_US.UTF-8'

function system_enable_universe {
    sed -i 's/^#\(.*deb.*\) universe/\1 universe/' /etc/apt/sources.list
    sed -i 's/^#\(.*deb.*\) multiverse/\1 multiverse/' /etc/apt/sources.list
}

function system_update {
    apt-get update
    apt-get -y upgrade
}

function system_update_locale_en_US_UTF_8 {
    dpkg-reconfigure locales
    update-locale LANG=en_US.UTF-8
}

function system_set_timezone {
    # $1 - Timezone
    echo $1 > /etc/timezone
    dpkg-reconfigure -f noninteractive tzdata
}

function get_user_home {
    # $1 - username
    cat /etc/passwd | grep "^$1:" | cut -d: -f6
}

function install_htop {
    apt-get -y install htop
}

function mysql_client_install {
    apt-get -y install mysql-client
}

function mysql_server_install {
    # $1 - the mysql root password
    if [ ! -n "$1" ]; then
        echo "mysql_install() requires the root pass as its first argument"
        return 1;
    fi

    echo "mysql-server-5.1 mysql-server/root_password password $1" | debconf-set-selections
    echo "mysql-server-5.1 mysql-server/root_password_again password $1" | debconf-set-selections
    apt-get -y install mysql-server

    echo "Sleeping while MySQL starts up for the first time..."
    sleep 5
}

function mysql_create_database {
    # $1 - the mysql root password
    # $2 - the db name to create
    if [ ! -n "$1" ]; then
        echo "mysql_create_database() requires the root pass as its first argument"
        return 1;
    fi
    if [ ! -n "$2" ]; then
        echo "mysql_create_database() requires the name of the database as the second argument"
        return 1;
    fi
    echo "CREATE DATABASE $2;" | mysql -u root -p$1
}

function mysql_create_user {
    # $1 - the mysql root password
    # $2 - the user to create
    # $3 - their password
    if [ ! -n "$1" ]; then
        echo "mysql_create_user() requires the root pass as its first argument"
        return 1;
    fi
    if [ ! -n "$2" ]; then
        echo "mysql_create_user() requires username as the second argument"
        return 1;
    fi
    if [ ! -n "$3" ]; then
        echo "mysql_create_user() requires a password as the third argument"
        return 1;
    fi
    echo "CREATE USER '$2'@'localhost' IDENTIFIED BY '$3';" | mysql -u root -p$1
}

function mysql_grant_user {
    # $1 - the mysql root password
    # $2 - the user to bestow privileges
    # $3 - the database
    if [ ! -n "$1" ]; then
        echo "mysql_create_user() requires the root pass as its first argument"
        return 1;
    fi
    if [ ! -n "$2" ]; then
        echo "mysql_create_user() requires username as the second argument"
        return 1;
    fi
    if [ ! -n "$3" ]; then
        echo "mysql_create_user() requires a database as the third argument"
        return 1;
    fi
    echo "GRANT ALL PRIVILEGES ON $3.* TO '$2'@'localhost';" | mysql -u root -p$1
    echo "FLUSH PRIVILEGES;" | mysql -u root -p$1
}

function install_appserver_libs {
    apt-get -y install memcached git-core mercurial
    apt-get -y install libjpeg62-dev libfreetype6-dev # Needed for PIL
    apt-get -y install libxml2-dev # Needed to make uWSGI
    apt-get -y install libmysqlclient-dev # Needed for MySQL-python
    apt-get -y install python python-dev python-setuptools
    easy_install pip virtualenv yolk
    apt-get -y install default-jre # needed for running yui-compressor during deploy process
}

function install_nginx {
    apt-get -y install nginx-full 
}

function install_uwsgi {
    $1 <string> version of uWSGI to be installed
    
    uwsgi_version="$1"
    uwsgi_tarball="uwsgi-$uwsgi_version.tar.gz"
    uwsgi_folder="uwsgi-$uwsgi_version"
    
    # Download and compile uWSGI
    wget "http://projects.unbit.it/downloads/$uwsgi_tarball"
    tar -xf $uwsgi_tarball
    cd $uwsgi_folder
    # TODO need to sed the configure file to remove a Werror (or something) flag.
    make
    mv uwsgi /usr/local/bin
    cd ..
    rm $uwsgi_tarball
    rm -rf $uwsgi_folder
    # Install an Upstart item for uwsgi
    cat > '/etc/init/uwsgi.conf' << EOF
::server_config_files/uwsgi.conf::
EOF
}

function configure_memcached {
    cat > '/etc/memcached.conf' << EOF
::server_config_files/memcached.conf::
EOF
}

function install_send_messages_cron {
    cat > '/etc/cron.d/send_read_messages' << EOF
SHELL=/bin/bash
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin:/usr/local/sbin
MAILTO="jonlesser+350devcron@gmail.com"
HOME=/home/ubuntu

*/15 * * * * ubuntu /home/ubuntu/webapp/manage.py send_ready_messages >> /home/ubuntu/send_ready_messages.log 2>&1
EOF
}

function install_s3cmd {
    apt-get -y install s3cmd
    cat > s3cmd_input << EOF
`echo $AWS_ACCESS_KEY`
`echo $AWS_SECRET_KEY`


Yes
Y
Y
Y
EOF
    s3cmd --configure < s3cmd_input
    rm s3cmd_input
}

function init_project {
    USER_HOME=`get_user_home ubuntu`
    sudo -u "ubuntu" git clone git://github.com/350org/localpower.git "$USER_HOME/webapp/"
    sudo -u "ubuntu" mkdir "$USER_HOME/requirements/"
    
    # Install requirements
    cd "$USER_HOME/requirements/"
    pip install -r ../webapp/requirements.txt
    cd
}

function s3_key_replacement {
    # $1 - key to download
    # $2 - file to replace in
    # $3 - string to replace
    KEY_NAME="$1"
    FILE="$2"
    PATTERN="$3"
    s3cmd get --force "s3://private.localpower.350.org/$KEY_NAME" temp_key
    sed -i 's/[\&]/\\&/g' temp_key # escape any special chars in the key
    sed -i "s/$PATTERN/`cat temp_key`/g" "$FILE"
    rm temp_key
}

function install_local_settings {
    USER_HOME=`get_user_home ubuntu`
    sudo -u "ubuntu" touch "$USER_HOME/webapp/local_settings.py"
    sudo -u "ubuntu" cat > "$USER_HOME/webapp/local_settings.py" << EOF
::server_config_files/local_settings_template.py::
EOF
    sed -i "s/_s3_bucket_name/`echo $ENVIRONMENT`.static.localpower.350.org/g" "$USER_HOME/webapp/local_settings.py"
    sed -i "s|_aws_secret_key|`echo $AWS_SECRET_KEY`|g" "$USER_HOME/webapp/local_settings.py"
    sed -i "s/_aws_access_key/`echo $AWS_ACCESS_KEY`/g" "$USER_HOME/webapp/local_settings.py"
    sed -i "s/_db_password/`echo $DB_PASSWORD`/g" "$USER_HOME/webapp/local_settings.py"
    sed -i "s/_db_host/`echo $DB_HOST`/g" "$USER_HOME/webapp/local_settings.py"
    sed -i "s/_db_port/`echo $DB_PORT`/g" "$USER_HOME/webapp/local_settings.py"

    s3_key_replacement "django/secret_key" "$USER_HOME/webapp/local_settings.py" "_secret_key"
    s3_key_replacement "django/postmark_api_key" "$USER_HOME/webapp/local_settings.py" "_postmark_api_key"
    s3_key_replacement "django/$ENVIRONMENT/twitter_consumer_key" "$USER_HOME/webapp/local_settings.py" "_twitter_consumer_key"
    s3_key_replacement "django/$ENVIRONMENT/twitter_consumer_secret" "$USER_HOME/webapp/local_settings.py" "_twitter_consumer_secret"
    s3_key_replacement "django/$ENVIRONMENT/facebook_appid" "$USER_HOME/webapp/local_settings.py" "_facebook_appid"
    s3_key_replacement "django/$ENVIRONMENT/facebook_secret" "$USER_HOME/webapp/local_settings.py" "_facebook_secret"
    s3_key_replacement "django/$ENVIRONMENT/ak_api_host" "$USER_HOME/webapp/local_settings.py" "_ak_api_host"
    s3_key_replacement "django/$ENVIRONMENT/ak_api_user" "$USER_HOME/webapp/local_settings.py" "_ak_api_user"
    s3_key_replacement "django/$ENVIRONMENT/ak_api_pass" "$USER_HOME/webapp/local_settings.py" "_ak_api_pass"
}

function install_loadbalancer_libs {
    apt-get -y install libssl-dev memcached libpcre3-dev
}

function configure_nginx {
    #mkdir /etc/nginx/sites-available
    #mkdir /etc/nginx/sites-enabled
    
    cat > '/etc/nginx/nginx.conf' << EOF
::server_config_files/nginx/nginx.conf::
EOF
    cat > '/etc/nginx/sites-available/maintenance' << EOF
::server_config_files/nginx/maintenance::
EOF
    cat > '/etc/nginx/sites-available/maintenance_base' << EOF
::server_config_files/nginx/maintenance_base::
EOF
    cat > '/etc/nginx/sites-available/maintenance_ssl' << EOF
::server_config_files/nginx/maintenance_ssl::
EOF
    cat > '/etc/nginx/sites-available/rah' << EOF
::server_config_files/nginx/rah::
EOF
    cat > '/etc/nginx/sites-available/rah_base' << EOF
::server_config_files/nginx/rah_base::
EOF
    cat > '/etc/nginx/sites-available/rah_base_http' << EOF
::server_config_files/nginx/rah_base_http::
EOF
    cat > '/etc/nginx/sites-available/rah_base_https' << EOF
::server_config_files/nginx/rah_base_https::
EOF
    cat > '/etc/nginx/uwsgi_params' << EOF
::server_config_files/nginx/uwsgi_params::
EOF
    
    sed -i "s/_public_dns_name/`echo $PUBLIC_DNS_NAME`/" /etc/nginx/sites-available/*
    sed -i "s/_s3_domain/`echo $ENVIRONMENT`.static.localpower.350.org/g" /etc/nginx/sites-available/*
    ln -s /etc/nginx/sites-available/rah /etc/nginx/sites-enabled/rah
}

function configure_ssl {
    s3cmd get --force s3://private.localpower.350.org/ssl/lp.crt /etc/ssl/certs/lp.crt
    s3cmd get --force s3://private.localpower.350.org/ssl/lp.key /etc/ssl/private/lp.key
}

function configure_htpasswd {
    USER_HOME=`get_user_home ubuntu`
    s3cmd get s3://private.localpower.350.org/htpasswd "$USER_HOME/htpasswd"
    chown ubuntu:ubuntu "$USER_HOME/htpasswd"
}

function bootstrap_system {
    system_enable_universe
    system_update
    system_update_locale_en_US_UTF_8
    system_set_timezone 'America/New_York'
    install_htop
    apt-get -y install make build-essential python-dev libxml2-dev
}

function bootstrap_database {
    mysql_client_install
    mysql_server_install "$DB_PASSWORD"
    mysql_create_database "$DB_PASSWORD" "$DB_NAME"
    mysql_create_user "$DB_PASSWORD" "$DB_USER" "$DB_PASSWORD"
    mysql_grant_user "$DB_PASSWORD" "$DB_USER" "$DB_NAME"
}

function bootstrap_appserver {
    install_appserver_libs
    configure_memcached
    install_uwsgi "0.9.6.8"
    mysql_client_install
    install_send_messages_cron
    install_s3cmd
    init_project
    install_local_settings
    start uwsgi
}

function bootstrap_loadbalancer {
    install_loadbalancer_libs
    configure_memcached
    install_nginx "1.0.5"
    configure_nginx
    install_s3cmd
    configure_ssl
    configure_htpasswd
    /etc/init.d/nginx restart
}
