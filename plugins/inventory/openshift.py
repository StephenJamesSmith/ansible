#!/bin/python

# (c) 2013, Michael Scherer <misc@zarb.org>
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
inventory: openshift
short_description: Openshift gears external inventory script
description:
  - Generates inventory of Openshift gears using the REST interface
  - this permit to reuse playbook to setup a Openshift gear
version_added: None
author: Michael Scherer
'''

import urllib2
try:
    import json
except ImportError:
    import simplejson as json
import os
import os.path
import sys
import ConfigParser
import StringIO

configparser = None


def get_from_rhc_config(variable):
    global configparser
    CONF_FILE = os.path.expanduser('~/.openshift/express.conf')
    if os.path.exists(CONF_FILE):
        if not configparser:
            ini_str = '[root]\n' + open(CONF_FILE, 'r').read()
            configparser = ConfigParser.SafeConfigParser()
            configparser.readfp(StringIO.StringIO(ini_str))
        try:
            return configparser.get('root', variable)
        except ConfigParser.NoOptionError:
            return None


def get_config(env_var, config_var):
    result = os.getenv(env_var)
    if not result:
        result = get_from_rhc_config(config_var)
    if not result:
        print "failed=True msg='missing %s'" % env_var
        sys.exit(1)
    return result


def get_json_from_api(url):
    req = urllib2.Request(url, None, {'Accept': 'application/json; version=1.5'})
    response = urllib2.urlopen(req)
    return json.loads(response.read())['data']


def passwd_setup(top_level_url, username, password):
    # create a password manager
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, top_level_url, username, password)

    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)

    urllib2.install_opener(opener)


username = get_config('ANSIBLE_OPENSHIFT_USERNAME', 'default_rhlogin')
password = get_config('ANSIBLE_OPENSHIFT_PASSWORD', 'password')
broker_url = 'https://%s/broker/rest/' % get_config('ANSIBLE_OPENSHIFT_BROKER', 'libra_server')


passwd_setup(broker_url, username, password)

response = get_json_from_api(broker_url + '/domains')

response = get_json_from_api("%s/domains/%s/applications" %
                             (broker_url, response[0]['id']))

result = {}
for app in response:

    # ssh://520311404832ce3e570000ff@blog-johndoe.example.org
    (user, host) = app['ssh_url'][6:].split('@')
    app_name = host.split('-')[0]

    result[app_name] = {}
    result[app_name]['hosts'] = []
    result[app_name]['hosts'].append(host)
    result[app_name]['vars'] = {}
    result[app_name]['vars']['ansible_ssh_user'] = user

if len(sys.argv) == 2 and sys.argv[1] == '--list':
    print json.dumps(result)
elif len(sys.argv) == 3 and sys.argv[1] == '--host':
    print json.dumps({})
else:
    print "Need a argument, either --list or --host <host>"
