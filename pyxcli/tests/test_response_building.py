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

import os
import unittest
import codecs
from mock import Mock
from pyxcli.client import XCLIClient
from pyxcli.errors import CommandExecutionError
from pyxcli.response import XCLIResponse
from pyxcli.helpers.xml_util import fromstring


class XCLIResponseBuildingTest(unittest.TestCase):

    def _readfile(self, fname):
        fullname = os.path.join(os.path.dirname(__file__), 'response', fname)
        with codecs.open(fullname, encoding='utf-8') as text:
            return text.read()

    def readresponses(self):
        if getattr(self, 'XCLI_XML_RESULT_SUCCESS_CODES', None):
            return
        self.XCLI_XML_RESULT_SUCCESS_CODES = [self._readfile('success.txt')]
        self.XCLI_XML_RESULT_ERROR_CODES = [self._readfile('error.txt')]
        self.XCLI_XML_RESULT_ERROR_CODES_WITH_RETURN = [
            self._readfile('error_w_return1.txt'),
            self._readfile('error_w_return2.txt')]

    def setUp(self):
        self.readresponses()
        self.xcli_client = XCLIClient(
            Mock(), 'user', 'password', populate=False)

    def test_build_response_returns_xcli_response_upon_getting_success(self):
        for xcli_xml_result in self.XCLI_XML_RESULT_SUCCESS_CODES:
            response = self.xcli_client._build_response(
                fromstring(xcli_xml_result))
            self.assertIsInstance(response, XCLIResponse)
            self.assertGreater(len(response.as_list), 0)

    def test_build_response_raises_error_with_empty_return_value(self):
        for xcli_xml_result in self.XCLI_XML_RESULT_ERROR_CODES:
            try:
                self.xcli_client._build_response(fromstring(xcli_xml_result))
                self.fail('Should have raised an exception.')
            except CommandExecutionError as e:
                self.assertTrue(e.code is not None)
                self.assertIsInstance(e.return_value, XCLIResponse)
                self.assertEqual(len(e.return_value.as_list), 0)

    def test_build_response_raises_error_with_correctly_parsed_return(self):
        for xcli_xml_result in self.XCLI_XML_RESULT_ERROR_CODES_WITH_RETURN:
            try:
                self.xcli_client._build_response(fromstring(xcli_xml_result))
                self.fail('Should have raised an exception.')
            except CommandExecutionError as e:
                self.assertTrue(e.code is not None)
                self.assertIsInstance(e.return_value, XCLIResponse)
                self.assertGreater(len(e.return_value.as_list), 0)
