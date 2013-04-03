#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Fabien Boucher <fabien.boucher@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
from swift.common.utils import get_logger
from swift.common.swob import wsgify
from swift.common.wsgi import make_pre_authed_request


class LastModifiedMiddleware(object):
    """
    LastModified is a middleware that add a meta to a container
    when that container and/or objects in it are modified. The meta
    data will contains the epoch timestamp. This middleware aims
    to be used with the synchronizer. It limits the tree parsing
    by giving a way to know a container has been modified since the
    last container synchronization.

    Actions that lead to the container meta modification :
    - POST/PUT on container
    - POST/PUT/DELETE on object in it

    The following shows an example of proxy-server.conf:
    [pipeline:main]
    pipeline = catch_errors cache tempauth last-modified proxy-server

    [filter:last-modified]
    use = egg:swift#last_modified
    key_name = Last-Modified
    """

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(self.conf, log_route='last_modified')
        self.key_name = conf.get('key_name', 'Last-Modified').replace(' ', '-')

    def update_last_modified_meta(self, req, env):
        vrs, account, container, obj = req.split_path(1, 4, True)
        path = env['PATH_INFO']
        if obj:
            path = path.split('/%s' % obj)[0]
        metakey = 'X-Container-Meta-%s' % self.key_name
        headers = {metakey: str(time.time())}
        set_meta_req = make_pre_authed_request(env,
                                               method='POST',
                                               path=path,
                                               headers=headers,
                                               swift_source='lm')
        return set_meta_req.get_response(self.app)

    def req_passthrough(self, req):
        return req.get_response(self.app)

    @wsgify
    def __call__(self, req):
        vrs, account, container, obj = req.split_path(1, 4, True)
        if (req.method in ('POST', 'PUT') and
                container or req.method == 'DELETE' and obj):
            new_env = req.environ.copy()
            # Keep it simple and do not check original request
            # response status before updating the container meta
            user_resp = self.req_passthrough(req)
            self.update_last_modified_meta(req, new_env)
            return user_resp
        return self.app


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    return lambda app: LastModifiedMiddleware(app, conf)
