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
""" IBM XCLI transports Module

.. module: transports

:Description: These are the IBM XCLI Client transport Classes to enable
 connection over single and multiple connections.

"""

import socket
import ssl
from logging import getLogger
from pyxcli import XCLI_DEFAULT_LOGGER, XCLI_DEFAULT_PORT
from pyxcli.helpers.xml_util import XMLException
from pyxcli.helpers.xml_util import TerminationDetectingXMLParser
from pyxcli.helpers.exceptool import chained
from pyxcli.errors import TransportError
from pyxcli.errors import ConnectionError
from pyxcli.errors import CorruptResponse
from pyxcli.errors import BaseScsiException

xlog = getLogger(XCLI_DEFAULT_LOGGER)


class ClosedTransportError(IOError, TransportError):
    pass


class DisconnectedWhileReceivingData(TransportError):
    pass


class Transport(object):
    def close(self):
        raise NotImplementedError()

    def is_connected(self):
        raise NotImplementedError()

    def fileno(self):
        raise NotImplementedError()

    def send(self, data, timeout=None):
        raise NotImplementedError()

    def reconnect(self):
        raise NotImplementedError()


class ClosedTransport(Transport):
    __slots__ = []

    def __repr__(self):
        return "<closed transport>"

    def close(self):
        pass

    def is_connected(self):
        return False

    def fileno(self):
        raise ClosedTransportError()

    def send(self, *args):
        raise ClosedTransportError()

    def reconnect(self):
        raise ClosedTransportError()

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__


ClosedTransport = ClosedTransport()


class ClosedFile(object):
    closed = True

    def __repr__(self):
        return "<closed file>"

    def close(self):
        pass

    def fileno(self):
        raise IOError("closed file")

    def __getattr__(self, name):
        raise IOError("closed file")

    def __setattr__(self, name, value):
        raise IOError("closed file")

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__


ClosedFile = ClosedFile()


# ============================================================================
# Socket/SSL transport
# ============================================================================
class SocketTransport(object):
    MAX_IO_CHUNK = 16000

    def __init__(self, sock):
        self.sock = sock

        # The following host and port will be used for reconnect
        try:
            h, p = self.sock.getpeername()
            self.host = h
            self.port = p
            self.connect_timout = self.sock.gettimeout()
        except Exception as e:
            xlog.debug(e)
            raise e

    def __repr__(self):
        try:
            h, p = self.sock.getpeername()
        except IOError:
            return "<%s disconnected>" % (self.__class__.__name__,)
        else:
            ssl = "(ssl)" if hasattr(self.sock, "getpeercert") else "(no ssl)"
            return "<%s connected to %s:%s %s>" % (self.__class__.__name__,
                                                   h, p, ssl)

    @classmethod
    def connect(cls, hostname, port, timeout=5.0):
        xlog.debug("CONNECT (non SSL) %s:%s", hostname, port)
        sock = socket.socket()
        sock.settimeout(timeout)
        sock.connect((hostname, port))

        return cls(sock)

    @classmethod
    def _certificate_required(cls, hostname, port=XCLI_DEFAULT_PORT,
                              ca_certs=None, validate=None):
        '''
        returns true if connection should verify certificate
        '''
        if not ca_certs:
            return False

        xlog.debug("CONNECT SSL %s:%s, cert_file=%s",
                   hostname, port, ca_certs)
        certificate = ssl.get_server_certificate((hostname, port),
                                                 ca_certs=None)
        # handle XIV pre-defined certifications
        # if a validation function was given - we let the user check
        # the certificate himself, with the user's own validate function.
        # if the validate returned True - the user checked the cert
        # and we don't need check it, so we return false.
        if validate:
            return not validate(certificate)
        return True

    @classmethod
    def connect_ssl(cls, hostname, port=XCLI_DEFAULT_PORT, timeout=5.0,
                    ca_certs=None, validate=None):

        certificate_required = cls._certificate_required(hostname,
                                                         port, ca_certs,
                                                         validate)
        xlog.debug("CONNECT SSL %s:%s", hostname, port)

        if certificate_required:
            sock = ssl.wrap_socket(
                socket.socket(),
                ca_certs=ca_certs,
                cert_reqs=ssl.CERT_REQUIRED)
        else:
            sock = ssl.wrap_socket(socket.socket())
        sock.settimeout(timeout)
        sock.connect((hostname, port))

        return cls(sock)

    def close(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except IOError:
            pass
        self.sock.close()
        self.sock = ClosedFile

    def is_connected(self):
        try:
            self.sock.getpeername()
        except IOError:
            return False
        else:
            return True

    def fileno(self):
        return self.sock.fileno()

    def send(self, data, timeout=None):

        while data:
            chunk = data[:self.MAX_IO_CHUNK]
            sent = self.sock.send(chunk)
            data = data[sent:]

        parser = TerminationDetectingXMLParser()
        raw = ""
        try:
            while not parser.root_element_closed:
                chunk = self.sock.recv(self.MAX_IO_CHUNK)
                if not chunk:
                    break
                raw += chunk
                parser.feed(chunk)
            return parser.close()
        except XMLException as ex:
            xlog.exception("Termination-detecting parser failed, %s", ex)
            if not self.is_connected():
                ex = chained(DisconnectedWhileReceivingData())
            else:
                ex = chained(CorruptResponse(str(ex), raw))
            self.close()
            raise ex

    def reconnect(self):
        if self.is_connected():
            self.close()

        self.sock = ssl.wrap_socket(socket.socket())
        self.sock.settimeout(self.connect_timout)
        self.sock.connect((self.host, self.port))


# ============================================================================
# SingleEndpointTransport
# ============================================================================
def SingleEndpointTransport(connector, endpoints, ca_certs=None,
                            validate=None):
    exceptions = []
    xlog.debug("SingleEndpointTransport connecting %r to %r", connector,
               endpoints)
    for ep in endpoints:
        try:
            xlog.debug("Attempting %r", ep)
            if isinstance(ep, (list, tuple)):
                return connector(*ep, ca_certs=ca_certs, validate=validate)
            elif not ca_certs:
                return connector(ep, ca_certs=ca_certs, validate=validate)
            else:
                return connector(ep, ca_certs=ca_certs, validate=validate)
        except (TransportError, BaseScsiException, IOError, ValueError) as ex:
            exceptions.append((ep, ex))
            xlog.debug("SingleEndpointTransport Could not connect to %r", ep)

    raise ConnectionError("SingleEndpointTransport Could not connect to "
                          "any endpoint", exceptions)


# ============================================================================
# MultiEndpointTransport
# ============================================================================
class MultiEndpointTransport(Transport):
    def __init__(self, connector, endpoints, ca_certs=None,
                 validate=None):
        self.connector = connector
        self.available_endpoints = list(endpoints)
        self.transport = ClosedTransport
        self.ca_certs = ca_certs
        self.validate = validate

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.connector,
                               self.available_endpoints)

    def is_connected(self):
        return self.transport.is_connected()

    def fileno(self):
        return self.transport.fileno()

    def close(self):
        self.transport.close()
        self.transport = ClosedTransport
        self.connector = None

    def add_endpoints(self, endpoints):
        if isinstance(endpoints, basestring):
            endpoints = [endpoints]
        self.available_endpoints.extend(endpoints)

    def _connect(self):
        if not self.connector:
            raise ClosedTransportError()
        exceptions = []
        while True:
            if self.transport.is_connected():
                return self.transport
            self.transport = ClosedTransport
            if not self.available_endpoints:
                xlog.debug("MultiEndpointTransport: no more endpoints \
                           available")
                raise ClosedTransportError("Ran out of endpoints to \
                                           connect to", exceptions)

            ep = self.available_endpoints.pop(0)
            xlog.debug("MultiEndpointTransport: changing to \
                       endpoint %s", ep)
            try:
                if isinstance(ep, (tuple, list)):
                    self.transport = self.connector(*ep,
                                                    ca_certs=self.ca_certs,
                                                    validate=self.validate)
                else:
                    self.transport = self.connector(ep,
                                                    ca_certs=self.ca_certs,
                                                    validate=self.validate)
            except (TransportError, IOError) as ex:
                xlog.debug("MultiEndpointTransport: could not connect to %s",
                           ep)
                self.transport.close()
                self.transport = ClosedTransport
                exceptions.append((ep, ex))

    def send(self, *args):
        while True:
            self._connect()
            try:
                return self.transport.send(*args)
            except (TransportError, IOError):
                self.transport.close()
                self.transport = ClosedTransport
                xlog.debug("MultiEndpointTransport: sending over %s failed",
                           self.transport)
