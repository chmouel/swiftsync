# -*- coding: utf-8 -*-
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Chmouel Boudjnah <chmouel@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Simple script to see a global swift cluster usage querying keystone server.
"""

# Nicer filesize reporting make it optional
try:
    import hurry.filesize
    prettysize = hurry.filesize.size
except ImportError:
    prettysize = None

import keystoneclient.v2_0.client
import swiftclient

import swsync.utils


def get_swift_auth(auth_url, tenant, user, password):
    """Get swift connexion from args."""
    return swiftclient.client.Connection(
        auth_url,
        '%s:%s' % (tenant, user),
        password,
        auth_version=2).get_auth()


def get_ks_auth_orig():
    """Get keystone cnx from config."""
    orig_auth_url = swsync.utils.get_config('auth', 'keystone_origin')
    cfg = swsync.utils.get_config('auth', 'keystone_origin_admin_credentials')
    (tenant_name, username, password) = cfg.split(':')

    return keystoneclient.v2_0.client.Client(auth_url=orig_auth_url,
                                             username=username,
                                             password=password,
                                             tenant_name=tenant_name)


def main():
    keystone_cnx = get_ks_auth_orig()
    auth_url = swsync.utils.get_config('auth', 'keystone_origin')
    korigcredential = swsync.utils.get_config(
        'auth', 'keystone_origin_admin_credentials')
    tenant, admin_user, admin_password = (korigcredential.split(':'))

    storage_url, token = get_swift_auth(
        auth_url, tenant,
        admin_user, admin_password)

    bare_storage_url = storage_url[:storage_url.find('AUTH_')] + "AUTH_"

    total_size = 0
    total_containers = 0
    total_objects = 0
    for tenant in keystone_cnx.tenants.list():
        tenant_storage_url = bare_storage_url + tenant.id
        head = swiftclient.head_account(tenant_storage_url, token)
        total_size += int(head['x-account-bytes-used'])
        total_containers += int(head['x-account-container-count'])
        total_objects += int(head['x-account-object-count'])

    size = prettysize and prettysize(total_size) or total_size
    print "Total size: %s" % (size)
    print "Total containers: %d" % (total_containers)
    print "Total objects: %d" % (total_objects)

if __name__ == '__main__':
    main()
