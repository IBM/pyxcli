##############################################################################
# Copyright 2016 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################
""" IBM XCLI Client Pool Module

.. module: pool

:Description: Provides pool of XCLI Client instances to talk to the Spectrum
 Accelerate storage arrays.

"""

import time
from collections import namedtuple
from logging import getLogger
from pyxcli.client import XCLIClient
from pyxcli import XCLI_DEFAULT_LOGGER


xlog = getLogger(XCLI_DEFAULT_LOGGER)

PoolEntry = namedtuple("PoolEntry", "client,timestamp,user_clients")


class XCLIClientPool(object):
    """The XCLI client pool alleviates the need to open a new connection
    every time to need to send a single command, and reduces the system's
    load, as only a single connection is kept for every system. It uses
    the XCLIClient multiplexing abilities, so that only a single
    connection is opened to every system, over which different users can send
    their commands separately; and it's thread safe, as the underlying
    XCLIClient is thread safe (it will send only a single command over the
    transport at any point of time).

    The pool can be configured with a time-to-live for connections, so
    that connections older than this TTL will be flushed and reopened.

    To use the pull, import one of the built-in pool objects,
    ``xcli_ssl_pool`` and use the ``get`` method. For example::

        from pyxcli.pool import xcli_ssl_pool

        client = xcli_ssl_pool.get("admin", "mypass", "192.168.1.102")
        client.cmd.vol_list()

    """

    def __init__(self, connector, time_to_live=10 * 60):
        self.connector = connector
        self.time_to_live = time_to_live
        self.pool = {}

    def clear(self):
        for entry in self.pool.values():
            entry.client.close()
        self.pool.clear()

    def flush(self):
        """remove all stale clients from pool"""
        now = time.time()
        to_remove = []
        for k, entry in self.pool.items():
            if entry.timestamp < now:
                entry.client.close()
                to_remove.append(k)
        for k in to_remove:
            del self.pool[k]

    def get(self, user, password, endpoints):
        """Gets an existing connection or opens a new one
        """
        now = time.time()
        # endpoints can either be str or list
        if isinstance(endpoints, str):
            endpoints = [endpoints]
        for ep in endpoints:
            if ep not in self.pool:
                continue
            entry = self.pool[ep]
            if (not entry.client.is_connected() or
               entry.timestamp + self.time_to_live < now):
                    xlog.debug("XCLIClientPool: clearing stale client %s",
                               ep)
                    del self.pool[ep]
                    entry.client.close()
                    continue
            user_client = entry.user_clients.get(user, None)
            if not user_client or not user_client.is_connected():
                user_client = entry.client.get_user_client(user, password)
                entry.user_clients[user] = user_client
            return user_client

        xlog.debug("XCLIClientPool: connecting to %s", endpoints)
        client = self.connector(None, None, endpoints)
        user_client = {user: client.get_user_client(user, password)}
        for ep in endpoints:
            self.pool[ep] = PoolEntry(client, now, user_client)
        return user_client[user]


xcli_ssl_pool = XCLIClientPool(XCLIClient.connect_ssl)
