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
""" IBM XCLI Client Module

.. module: client

:Description: These are the IBM XCLI Client Classes to talk to the Spectrum
 Accelerate storage arrays.

"""

import itertools
from contextlib import contextmanager
from logging import getLogger
from threading import Lock
from weakref import proxy as weakproxy
from pyxcli.helpers.xml_util import ElementNotFoundException
from pyxcli.helpers import xml_util as etree
from pyxcli import XCLI_DEFAULT_LOGGER
from pyxcli.errors import CommandExecutionError
from pyxcli.errors import CommandFailedAServerError
from pyxcli.errors import CorruptResponse
from pyxcli.transports import SocketTransport
from pyxcli.transports import ClosedTransport
from pyxcli.transports import SingleEndpointTransport
from pyxcli.transports import MultiEndpointTransport
from pyxcli.response import XCLIResponse
from pyxcli.helpers.exceptool import chained

xlog = getLogger(XCLI_DEFAULT_LOGGER)


class ClosedXCLIClientError(IOError):
    pass


class CommandNamespace(object):
    def __init__(self, client):
        self._client = client

    def __getattr__(self, name):
        if name == "trait_names":
            raise AttributeError(name)
        if name.startswith("_"):
            raise AttributeError(name)

        def invoker(**kwargs):
            return self._client.execute(name, **kwargs)
        invoker.__name__ = "CommandInvoker<%r>" % (name,)
        setattr(self, name, invoker)
        return invoker

    # to make RPyC happy
    _rpyc_getattr = getattr


class BaseXCLIClient(object):
    DEFAULT_OPTIONS = {}

    def __init__(self):
        self._contexts = [self.DEFAULT_OPTIONS.copy()]
        self.cmd = CommandNamespace(weakproxy(self))

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self.close()

    def _populate_commands(self):
        for info in self.execute("help"):
            invoker = getattr(self.cmd, info.name)
            invoker.__doc__ = info.description + "\nUsage: " + info.syntax
            invoker.syntax = info.syntax
            setattr(self.cmd, info.name, invoker)

    def is_connected(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def execute(self, cmd, **kwargs):
        """Executes command (with the arguments) on the connected machine"""
        return self.execute_remote(None, cmd, **kwargs)

    def execute_remote(self, remote_target, cmd, **kwargs):
        """
        Executes the given command (with the given arguments)
        on the given remote target of the connected machine
        """
        raise NotImplementedError()

    @contextmanager
    def options(self, **options):
        """A context-manager for setting connection options; the original
        values of the options will be restored when the context-manager exits.
        For example::

            with c.options(gui_mode = False):
                 c.cmd.vol_list()
        """
        self._contexts.append(self._contexts[-1].copy())
        self.set_options(**options)
        try:
            yield
        finally:
            self._contexts.pop(-1)

    def get_option(self, name):
        """Returns the value of the given option
        (or a ``KeyError`` if it does not exist)
        """
        return self._contexts[-1].get(name)

    def set_options(self, **options):
        """Sets the value of the given options (as keyword arguments).
        Note that underscored in the option's name will be replaced with
        hyphens (i.e., ``c.set_options(gui_mode = True)``
        will set the option ``gui-mode``)
        """
        opt2 = self._contexts[-1]
        for k, v in options.items():
            k2 = k.replace("_", "-")
            if v is None:
                opt2.pop(k2, None)
            else:
                opt2[k2] = v


class XCLIClient(BaseXCLIClient):
    """
    The class implementing the XCLI client. Use the class' factory methods
    (``connect_ssl``, etc.) to create an XCLI client.
    Client objects have a special attribute named ``cmd``, which can be used
    to represent XCLI commands as python functions (this is the recommened way
    to use this class). For example::

        client = XCLIClient.connect_ssl("admin", "mypass", "192.168.1.102")
        results = client.cmd.vol_list(pool = "foobar")
    """
    DEFAULT_OPTIONS = {
        "i-am-sure": "yes",
        "gui-mode": "yes",
        "force-output": "yes",
        "print-header": "no",
        "compress-output": "base64",
    }

    def __init__(self, transport, user, password, populate=True):
        """
        Initializes an XCLI client over the given transport object; do not
        use this directly (unless you know what you're doing) -- use one of
        the factory methods.

        If ``user`` is not given (``None``), the XIV machine will
        not be queried (``version_get``, etc.) and the ``cmd``
        namespace will not be populated. If ``populate`` is False, the
        ``cmd`` namespace will not be populated (by running ``help``).
        """
        BaseXCLIClient.__init__(self)
        self.transport = transport
        self._lock = Lock()
        self._cmdindex = itertools.count(1)
        if user is not None:
            self.set_options(user=user, password=password)
            if populate:
                self._populate_commands()

    def is_connected(self):
        return self.transport.is_connected()

    def close(self):
        """
        Closes the client
        """
        self.transport.close()
        self.transport = ClosedTransport

    def reconnect(self):
        """
        Reconnect as last valid connection
        """
        self.transport.reconnect()

    @classmethod
    def connect_ssl(cls, user, password, endpoints,
                    ca_certs=None, validate=None):
        """
        Creates an SSL transport to the first endpoint (aserver) to which
        we successfully connect
        """
        if isinstance(endpoints, basestring):
            endpoints = [endpoints]
        transport = SingleEndpointTransport(
            SocketTransport.connect_ssl, endpoints, ca_certs=ca_certs,
            validate=validate)
        return cls(transport, user, password)

    @classmethod
    def connect_multiendpoint_ssl(cls, user, password, endpoints,
                                  auto_discover=True, ca_certs=None,
                                  validate=None):
        """
        Creates a MultiEndpointTransport, so that if the current endpoint
        (aserver) fails, it would automatically move to the next available
        endpoint.

        If ``auto_discover`` is ``True``, we will execute ipinterface_list
        on the system to discover all management IP interfaces and add them
        to the list of endpoints
        """
        if isinstance(endpoints, basestring):
            endpoints = [endpoints]
        client, transport = cls._initiate_client_for_multi_endpoint(user,
                                                                    password,
                                                                    endpoints,
                                                                    ca_certs,
                                                                    validate)
        if auto_discover and user:
            all_endpoints = [ipif.address for ipif in
                             client.cmd.ipinterface_list()
                             if ipif.type.lower() == "management"]
            transport.add_endpoints(all_endpoints)
        return client

    @classmethod
    def _initiate_client_for_multi_endpoint(cls, usr, pwd, endpoints,
                                            ca_certs, validate):
        while True:
            try:
                transport = MultiEndpointTransport(SocketTransport
                                                   .connect_ssl,
                                                   endpoints,
                                                   ca_certs=ca_certs,
                                                   validate=validate)
                client = cls(transport, usr, pwd)
                return client, transport
            except CommandFailedAServerError:
                return cls._initiate_client_for_multi_endpoint(usr, pwd,
                                                               endpoints[1:],
                                                               ca_certs,
                                                               validate)

    def _dump_xcli(self, obj):
        if isinstance(obj, bool):
            return "yes" if obj else "no"
        return str(obj)

    def _build_command(self, cmd, params, options, remote_target=None):
        root = etree.Element("command", id=str(self._cmdindex.next()),
                             type=cmd, close_on_return="no")
        if remote_target:
            root.attrib["remote_target"] = remote_target

        for k, v in options.items():
            root.append(etree.Element("option", name=self._dump_xcli(k),
                                      value=self._dump_xcli(v)))
        for k, v in params.items():
            root.append(etree.Element("argument", name=self._dump_xcli(k),
                                      value=self._dump_xcli(v)))
        data = etree.tostring(root)
        anon = data.replace(options["password"],
                            "XXX") if "password" in options else data
        xlog.debug("SEND %s" % (anon))
        return data

    def _build_response(self, rootelem):

        # "/command/aserver/@status"
        aserver = etree.xml_find(rootelem, "aserver", "status")
        if aserver != "DELIVERY_SUCCESSFUL":
            raise CommandFailedAServerError.instantiate(aserver, rootelem)
        try:
            # "/command/administrator/command"
            cmdroot = etree.xml_find(rootelem, "administrator/command")
        except ElementNotFoundException:
            # "/command/command/administrator/command"
            cmdroot = etree.xml_find(rootelem, "command/administrator/command")

        # "code/@value"
        code = etree.xml_find(cmdroot, "code", "value")
        encoding = self.get_option("compress-output")

        if code != "SUCCESS":
            raise CommandExecutionError.instantiate(rootelem,
                                                    cmdroot, encoding)

        return XCLIResponse.instantiate(cmdroot, encoding)

    def execute_remote(self, remote_target, cmd, **kwargs):
        """
        Executes the given command (with the given arguments)
        on the given remote target of the connected machine
        """
        data = self._build_command(cmd, kwargs, self._contexts[-1],
                                   remote_target)
        with self._lock:
            rootelem = self.transport.send(data)
        try:
            return self._build_response(rootelem)
        except ElementNotFoundException:
            xlog.exception("XCLIClient.execute")
            raise chained(CorruptResponse(rootelem))
        except Exception as e:
            xlog.exception("XCLIClient.execute")
            raise e

    def get_user_client(self, user, password, populate=True):
        """
        Returns a new client for the given user. This is a lightweight
        client that only uses different credentials and shares the transport
        with the underlying client
        """
        return XCLIClientForUser(weakproxy(self), user, password,
                                 populate=populate)

    def get_remote_client(self, target_name, user=None, password=None):
        """
        Returns a new client for the remote target. This is a lightweight
        client that only uses different credentials and shares the transport
        with the underlying client
        """
        if user:
            base = self.get_user_client(user, password, populate=False)
        else:
            base = weakproxy(self)
        return RemoteXCLIClient(base, target_name, populate=True)

    @contextmanager
    def as_user(self, user, password):
        """
        A context-manager for ``get_user_client``. Allows the execution
        of commands as a different user with ease.

        Example:

        >>> c.cmd.vol_list()
        >>> with c.as_user("user", "password"):
        ...     c.cmd.vol_list()

        """

        with self.options(user=user, password=password):
            yield self


class ClosedXCLIClient(object):

    def close(self):
        pass

    def is_connected(self):
        return False

    def __getattr__(self, name):
        raise ClosedXCLIClientError()


ClosedXCLIClient = ClosedXCLIClient()


class LayeredXCLIClient(BaseXCLIClient):

    def __init__(self, client):
        BaseXCLIClient.__init__(self)
        self._client = client

    def close(self):
        self._client = ClosedXCLIClient

    def is_connected(self):
        return self._client.is_connected()

    def execute_remote(self, target_name, cmd, **kwargs):
        with self._client.options(**self._contexts[-1]):
            return self._client.execute_remote(target_name, cmd, **kwargs)

    @property
    def transport(self):
        return self._client.transport


class XCLIClientForUser(LayeredXCLIClient):

    def __init__(self, client, user, password, populate=True):
        LayeredXCLIClient.__init__(self, client)
        self.set_options(user=user, password=password)
        if populate:
            self._populate_commands()


class RemoteXCLIClient(LayeredXCLIClient):

    def __init__(self, client, target_name, populate=True):
        LayeredXCLIClient.__init__(self, client)
        self._target_name = target_name
        if populate:
            self._populate_commands()

    def execute(self, cmd, **kwargs):
        with self._client.options(**self._contexts[-1]):
            return self._client.execute_remote(self._target_name,
                                               cmd, **kwargs)

    def execute_remote(self, *args, **kwargs):
        # you can't chain clients, a limitation of the XIV machine
        raise NotImplementedError()
