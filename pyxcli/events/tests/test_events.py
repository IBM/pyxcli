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

import ast
import unittest
from mock import patch, Mock
from pyxcli.events import events
from pyxcli.errors import UnrecognizedCommandError
from pyxcli.errors import OperationForbiddenForUserCategoryError


class TestSendEvent(unittest.TestCase):

    test_actions = (
        'REGISTERED', 'REVOKED', 'UPGRADE', 'ADD_ARRAY', 'REMOVE_ARRAY',
        'ADD_VCENTER', 'REMOVE_VCENTER', 'ATTACH_ARRAY', 'DETACH_ARRAY',
        'ATTACH_POOL', 'DETACH_POOL')

    @patch.object(events, 'getfqdn')
    @patch.object(events, 'get_platform_details')
    def test_all_actions_with_custom_event(self, gethostname_mock,
                                           get_platform_details_mock):
        gethostname_mock.return_value = 'test_hostname'
        get_platform_details_mock.return_value = 'test_platform'
        xcli_mock = Mock()
        xcli_mock.cmd.css_product_event = Mock(
            side_effect=OperationForbiddenForUserCategoryError(
                'test_code',
                'test_status',
                'test_xml'))
        ev_mgr = events.EventsManager(
            xcli_mock, 'test_product_name', 'test_product_ver')
        xcli_mock.cmd.css_product_event = Mock(
            side_effect=UnrecognizedCommandError(
                'test_code',
                'test_status',
                'test_xml'))
        ev_mgr = events.EventsManager(
            xcli_mock, 'test_product_name', 'test_product_ver')

        expected_severity = 'Informational'
        expected_description = {
            'Product': 'test_product_name',
            'Version': 'test_product_ver',
            'Server': 'test_platform',
            'Platform': 'test_hostname',
            'Properties': {}}
        for (num, action) in enumerate(self.test_actions):
            ev_mgr.send_event(action, None)
            expected_description['Action'] = action
            called_severity = xcli_mock.cmd.custom_event.call_args_list[
                num][1].get('severity')
            called_description = xcli_mock.cmd.custom_event.call_args_list[
                num][1].get('description')
            expected_description_prefix = ev_mgr._get_description_prefix()
            called_description_prefix = called_description[
                :len(expected_description_prefix)]
            called_description_suffix = called_description[
                len(expected_description_prefix):]
            called_description_dict = ast.literal_eval(
                called_description_suffix)
            self.assertEqual(called_severity, expected_severity)
            self.assertEquals(called_description_prefix,
                              expected_description_prefix)
            self.assertEqual(sorted(called_description_dict.items()),
                             sorted(expected_description.items()))

    @patch.object(events, 'getfqdn')
    @patch.object(events, 'get_platform_details')
    def test_all_actions_with_css_product_event(self, gethostname_mock,
                                                get_platform_details_mock):
        gethostname_mock.return_value = 'test_hostname'
        get_platform_details_mock.return_value = 'test_platform'
        xcli_mock = Mock()
        ev_mgr = events.EventsManager(
            xcli_mock,
            'test_product_name',
            'test_product_ver')
        for action in self.test_actions:
            mock_css_prod_event = xcli_mock.cmd.css_product_event
            ev_mgr.send_event(action, None)
            mock_css_prod_event.assert_called_with(action=action,
                                                   platform='test_hostname',
                                                   product='test_product_name',
                                                   properties={},
                                                   server='test_platform',
                                                   severity='Informational',
                                                   version='test_product_ver')

    @patch.object(events, 'getfqdn')
    @patch.object(events, 'get_platform_details')
    def test_bad_init(self, gethostname_mock, get_platform_details_mock):
        gethostname_mock.return_value = 'test_hostname'
        get_platform_details_mock.return_value = 'test_platform'
        xcli_mock = Mock()
        self.assertRaises(ValueError, events.EventsManager,
                          xcli_mock, '', 'test_product_ver')
        self.assertRaises(ValueError, events.EventsManager,
                          xcli_mock, 'test_product_name', '')

    @patch.object(events, 'getfqdn')
    @patch.object(events, 'get_platform_details')
    def test_bad_properties(self, gethostname_mock, get_platform_details_mock):
        gethostname_mock.return_value = 'test_hostname'
        get_platform_details_mock.return_value = 'test_platform'
        xcli_mock = Mock()
        ev_mgr = events.EventsManager(
            xcli_mock, 'test_product_name', 'test_product_ver')
        self.assertRaises(TypeError, ev_mgr.send_event,
                          self.test_actions[0], 'test_properties')
