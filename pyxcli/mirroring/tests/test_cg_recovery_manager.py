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

from pyxcli.mirroring.tests.test_base_recovery_manager \
    import TestBaseRecoveryManager
from pyxcli.mirroring.cg_recovery_manager \
    import CGRecoveryManager


class TestCGRecoveryManager(TestBaseRecoveryManager):
    __test__ = True

    def setUpRecoveryManager(self):
        self.recovery_manager = CGRecoveryManager(True, self.xcli_client_mock)

    def set_mirror_list(self, cvolumes, ccgs):
        self.xcli_client_mock.cmd.mirror_list.return_value = ccgs

    def set_main_mirror(self, vol1, cg1):
        self.xcli_mirror = vol1
        self.master = 'cg1'
        self.slave = 'cg2'

    def test_create_mirror(self):
        mirror = self.recovery_manager.create_mirror('cg1', 'target_xiv',
                                                     'sync', 'cg2', rpo=30,
                                                     remote_rpo=30,
                                                     schedule='never',
                                                     activate_mirror='no')
        self.assertEqual(mirror.local_peer_name, 'cg1')
        with self.assertRaises(TypeError):
            self.recovery_manager.create_mirror('cg1', 'target_xiv', 'sync',
                                                'cg2', rpo=30,
                                                create_slave='yes',
                                                remote_rpo=30,
                                                schedule='never',
                                                activate_mirror='no')
