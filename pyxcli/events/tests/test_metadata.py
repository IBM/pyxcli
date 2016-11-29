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
from pyxcli.events import platform_info
from pyxcli.events.platform_info import get_platform_details
from pyxcli.events.platform_info import SAFE_LENGTH

META_DATA_RETURN_VALUE = 'AIX_7.1_TL_1_SP_4'


class TestPlatformDetails(unittest.TestCase):

    @patch.object(platform_info, 'platform')
    def test_arch_detail_is_not_repeated_when_using_safe_metadata_set(
            self, platform_mock):
        platform_mock.platform.return_value = 'fakelongstring' * 100

        machine = 'x86_64'
        release = 'release.{machine}'.format(machine=machine)
        platform_mock.system.return_value = 'system'
        platform_mock.release.return_value = release
        platform_mock.machine.return_value = machine
        platform_mock.linux_distribution.return_value = (
            'distname', 'distversion', 'distid')
        get_platform_details(safe_metadata_set=True)
        platform_mock._platform.assert_called_once_with(
            'system', 'release', machine, 'distname', 'distversion')

    @patch.object(platform_info, 'platform')
    def test_len_of_os_string_is_metadata_safe_by_default(self, platform_mock):
        longstr = 'fakelongstring' * 100
        platform_mock.platform.return_value = longstr
        platform_mock._platform.return_value = longstr
        platform_mock.linux_distribution.return_value = (
            Mock(), Mock(), Mock())
        self.assertEqual(SAFE_LENGTH, len(get_platform_details()))

    @patch('pyxcli.events.platform_info.get_aix_version')
    @patch.object(platform_info, 'platform')
    def test_get_platform_details_when_os_is_aix(self, platform_mock,
                                                 get_aix_version_mock):
        platform_mock.system.return_value = 'AIX'
        get_aix_version_mock.return_value = (7, 1, 0, 1, 4, 1216)
        result = get_platform_details()
        message = ('expected : %s, returned : %s' %
                   (META_DATA_RETURN_VALUE, result))
        self.assertEqual(result, META_DATA_RETURN_VALUE, message)
