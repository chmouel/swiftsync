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
import logging
import urlparse

import swiftclient

import swsync.containers

import tests.units.base as test_base
import tests.units.fakes as fakes


class TestContainers(test_base.TestCase):
    def setUp(self):
        super(TestContainers, self).setUp()
        self.container_cls = swsync.containers.Containers()

        self.tenant_name = 'foo1'
        self.tenant_id = fakes.TENANTS_LIST[self.tenant_name]['id']
        self.orig_storage_url = '%s/AUTH_%s' % (fakes.STORAGE_ORIG,
                                                self.tenant_id)
        self.orig_storage_cnx = (urlparse.urlparse(self.orig_storage_url),
                                 None)
        self.dest_storage_url = '%s/AUTH_%s' % (fakes.STORAGE_DEST,
                                                self.tenant_id)
        self.dest_storage_cnx = (urlparse.urlparse(self.dest_storage_url),
                                 None)

    def test_sync_when_container_nothere(self):
        get_cnt_called = []

        def put_container(*args, **kwargs):
            get_cnt_called.append(args)

        def head_container(*args, **kwargs):
            raise swiftclient.client.ClientException('Not Here')

        def get_container(_, token, name, **kwargs):
            for clist in fakes.CONTAINERS_LIST:
                if clist[0]['name'] == name:
                    return (fakes.CONTAINER_HEADERS, clist[1])

        self.stubs.Set(swiftclient, 'get_container', get_container)
        self.stubs.Set(swiftclient, 'put_container', put_container)
        self.stubs.Set(swiftclient, 'head_container', head_container)

        self.container_cls.sync(
            self.orig_storage_cnx, self.orig_storage_url, 'token',
            self.dest_storage_cnx, self.dest_storage_url, 'token',
            'cont1'
        )
        self.assertEqual(len(get_cnt_called), 1)

    def test_sync_when_container_nothere_raise_when_cant_create(self):
        put_cnt_called = []
        called_info = []

        def fake_info(self, *args):
            called_info.append("called")
        self.stubs.Set(logging, 'info', fake_info)

        def put_container(*args, **kwargs):
            put_cnt_called.append("TESTED")
            raise swiftclient.client.ClientException('TESTED')

        def get_container(_, token, name, **kwargS):
            for clist in fakes.CONTAINERS_LIST:
                if clist[0]['name'] == name:
                    return (fakes.CONTAINER_HEADERS, clist[1])

        def head_container(*args, **kwargs):
            raise swiftclient.client.ClientException('Not Here')

        self.stubs.Set(swiftclient, 'get_container', get_container)
        self.stubs.Set(swiftclient, 'put_container', put_container)
        self.stubs.Set(swiftclient, 'head_container', head_container)

        self.container_cls.sync(
            self.orig_storage_cnx, self.orig_storage_url, 'token',
            self.dest_storage_cnx, self.dest_storage_url, 'token',
            'cont1'
        )
        self.assertEqual(len(put_cnt_called), 1)
        self.assertEqual(len(called_info), 1)

    def test_delete_dest(self):
        # probably need to change that to mox properly
        get_cnt_called = []
        sync_object_called = []
        delete_object_called = []

        def delete_object(*args, **kwargs):
            delete_object_called.append((args, kwargs))
        self.stubs.Set(swsync.objects.swiftclient,
                       'delete_object', delete_object)

        def head_container(*args, **kwargs):
            return True
        self.stubs.Set(swiftclient, 'head_container', head_container)

        def get_container(*args, **kwargs):
            # MASTER
            if not get_cnt_called:
                cont = fakes.CONTAINERS_LIST[0][0]
                objects = list(fakes.CONTAINERS_LIST[0][1])
                get_cnt_called.append(True)
            # TARGET
            else:
                cont = fakes.CONTAINERS_LIST[0][0]
                objects = list(fakes.CONTAINERS_LIST[0][1])
                # Add an object to target.
                objects.append(fakes.gen_object('NEWOBJ'))

            return (cont, objects)

        def sync_object(*args, **kwargs):
            sync_object_called.append(args)

        self.stubs.Set(swiftclient, 'get_container', get_container)

        self.container_cls.sync_object = sync_object

        self.container_cls.sync(
            self.orig_storage_cnx,
            self.orig_storage_url,
            'token',
            self.dest_storage_cnx,
            self.dest_storage_url,
            'token',
            'cont1')

        self.assertEqual(len(sync_object_called), 0)
        self.assertEqual(len(delete_object_called), 1)

    def test_sync(self):
        get_cnt_called = []
        sync_object_called = []

        def head_container(*args, **kwargs):
            pass

        def get_container(*args, **kwargs):
            # MASTER
            if not get_cnt_called:
                cont = fakes.CONTAINERS_LIST[0][0]
                objects = list(fakes.CONTAINERS_LIST[0][1])
                objects.append(fakes.gen_object('NEWOBJ'))
                get_cnt_called.append(True)
            # TARGET
            else:
                cont = fakes.CONTAINERS_LIST[0][0]
                objects = list(fakes.CONTAINERS_LIST[0][1])

            return (cont, objects)

        def sync_object(*args, **kwargs):
            sync_object_called.append(args)

        self.stubs.Set(swiftclient, 'head_container', head_container)
        self.stubs.Set(swiftclient, 'get_container', get_container)
        self.container_cls.sync_object = sync_object

        self.container_cls.sync(
            self.orig_storage_cnx,
            self.orig_storage_url,
            'token',
            self.dest_storage_cnx,
            self.dest_storage_url,
            'token',
            'cont1')

        self.assertEqual(sync_object_called[0][-1][1], 'NEWOBJ')

    def test_sync_raise_exceptions_get_container_on_orig(self):
        called = []

        def get_container(*args, **kwargs):
            called.append("TESTED")
            raise swiftclient.client.ClientException("TESTED")

        self.stubs.Set(swiftclient, 'get_container', get_container)
        self.container_cls.sync(
            self.orig_storage_cnx,
            self.orig_storage_url,
            'token',
            self.dest_storage_cnx,
            self.dest_storage_url,
            'token',
            'cont1')
        self.assertEqual(len(called), 1)

    def test_sync_raise_exceptions_get_container_on_dest(self):
        called = []
        called_on_dest = []

        def get_container(*args, **kwargs):
            #ORIG
            if len(called) == 0:
                called.append("TESTED")
                return ({}, [{'name': 'PARISESTMAGIQUE',
                              'last_modified': '2010'}])
            #DEST
            else:
                called_on_dest.append("TESTED")
                raise swiftclient.client.ClientException("TESTED")

        def head_container(*args, **kwargs):
            pass

        self.stubs.Set(swiftclient, 'head_container', head_container)
        self.stubs.Set(swiftclient, 'get_container', get_container)
        self.container_cls.sync(
            self.orig_storage_cnx,
            self.orig_storage_url,
            'token',
            self.dest_storage_cnx,
            self.dest_storage_url,
            'token',
            'cont1')
        self.assertEqual(len(called_on_dest), 1)
        self.assertEqual(len(called), 1)

    def test_delete_container(self):
        delete_called = []
        orig_containers = [{'name': 'foo'}]
        dest_containers = [{'name': 'foo'}, {'name': 'bar'}]

        def get_container(*args, **kwargs):
            return ({}, [{'name': 'PARISESTMAGIQUE', 'last_modified': '2010'}])

        def delete(*args, **kwargs):
            delete_called.append("TESTED")

        self.container_cls.delete_object = delete
        self.stubs.Set(swiftclient, 'delete_container', delete)
        self.stubs.Set(swiftclient, 'get_container', get_container)

        self.container_cls.delete_container(
            "cnx1", "token1", orig_containers, dest_containers)

        self.assertEqual(len(delete_called), 2)

    def test_delete_container_raise_exception(self):
        called = []
        orig_containers = [{'name': 'foo'}]
        dest_containers = [{'name': 'foo'}, {'name': 'bar'}]

        def get_container(*args, **kwargs):
            called.append("TESTED")
            raise swiftclient.client.ClientException("TESTED")

        self.stubs.Set(swiftclient, 'get_container', get_container)

        self.container_cls.delete_container(
            "cnx1", "token1", orig_containers, dest_containers)

        self.assertEqual(len(called), 1)
