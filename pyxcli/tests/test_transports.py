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

import unittest
from mock import patch, Mock

from pyxcli.helpers.xml_util import XMLException
from pyxcli.transports import SocketTransport, DisconnectedWhileReceivingData
from pyxcli.errors import CorruptResponse


class TestSocketTransport(unittest.TestCase):

    @patch('pyxcli.transports.TerminationDetectingXMLParser')
    @patch.object(SocketTransport, 'is_connected')
    def test_send_raises_error_on_disconnection(self, is_conneced_mock,
                                                ParserMock):
        sock_mock = Mock()
        sock_mock.send.return_value = 1
        sock_mock.getpeername.return_value = (Mock(), Mock())

        parser_mock = Mock()
        parser_mock.close.side_effect = XMLException('Fake XML Exception')
        ParserMock.return_value = parser_mock

        transport = SocketTransport(sock_mock)
        self.assertTrue(transport.is_connected())
        with self.assertRaises(DisconnectedWhileReceivingData):
            is_conneced_mock.return_value = False
            transport.send('fake_stream' * 10)

    @patch('pyxcli.transports.TerminationDetectingXMLParser')
    def test_send_raises_error_on_failed_xml_termination_detection(
            self, ParserMock):
        sock_mock = Mock()
        sock_mock.send.return_value = 1
        sock_mock.getpeername.return_value = (Mock(), Mock())
        parser_mock = Mock()
        parser_mock.close.side_effect = XMLException('Fake XML Exception')
        ParserMock.return_value = parser_mock
        transport = SocketTransport(sock_mock)
        with self.assertRaises(CorruptResponse):
            transport.send('fake_stream' * 10)
            self.assertTrue(transport.is_connected())


if __name__ == "__main__":
    unittest.main()
