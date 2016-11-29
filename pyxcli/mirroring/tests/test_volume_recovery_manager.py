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
from pyxcli.mirroring.volume_recovery_manager \
    import VolumeRecoveryManager


class TestVolumeRecoveryManager(TestBaseRecoveryManager):

    __test__ = True

    def setUpRecoveryManager(self):
        self.recovery_manager = VolumeRecoveryManager(
            True, self.xcli_client_mock)

    def set_mirror_list(self, cvolumes, ccgs):
        self.xcli_client_mock.cmd.mirror_list.return_value = cvolumes

    def set_main_mirror(self, vol1, cg1):
        self.xcli_mirror = vol1
        self.master = 'vol1'
        self.slave = 'vol2'

    def test_create_mirror(self):
        mirror = self.recovery_manager.create_mirror('vol1', 'target_xiv',
                                                     'sync', 'vol2',
                                                     create_slave='no',
                                                     remote_pool=None,
                                                     rpo=30, remote_rpo=30,
                                                     schedule='never',
                                                     remote_schedule='never',
                                                     activate_mirror='no')
        self.assertEqual(mirror.local_peer_name, 'vol1')
        with self.assertRaises(TypeError):
            self.recovery_manager.create_mirror('a', 'vol1', 'target_xiv',
                                                'sync', 'vol2',
                                                create_slave='no',
                                                remote_pool=None, rpo=30,
                                                remote_rpo=30,
                                                schedule='never',
                                                remote_schedule='never',
                                                activate_mirror='no')

    def test_delete_mirror(self):
        self.recovery_manager.delete_mirror('vol1')
