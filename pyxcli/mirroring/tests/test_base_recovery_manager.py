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
from mock import MagicMock
from pyxcli.mirroring.mirrored_entities import \
    MirroredCachedEntities
from pyxcli.mirroring.errors import NoMirrorDefinedError
from pyxcli.mirroring.recovery_manager import \
    SlaveIsNotConsistentRecoveryException, \
    NoLastReplicatedSnapshotRecoveryException


class CIMCLIResponse(object):

    def __init__(self, generic_cim_objects):
        self.generic_cim_objects = generic_cim_objects

    def __iter__(self):
        return iter(self.generic_cim_objects)

    def __len__(self):
        return len(self.generic_cim_objects)

    @property
    def as_single_element(self):
        return (self.generic_cim_objects)[0]

    @property
    def as_list(self):
        return self.generic_cim_objects

    def as_dict(self, key_name):
        key_name = str(key_name)
        ret_dict = {}
        if(len(self.generic_cim_objects) > 0):
            single = self.generic_cim_objects[0]
            if (not hasattr(single, key_name)):
                raise Exception('%s is_not_a_valid_key' % key_name)
        for cim_obj in self.generic_cim_objects:
            ret_dict[getattr(cim_obj, key_name)] = cim_obj
        return ret_dict


class TestBaseRecoveryManager(unittest.TestCase):

    __test__ = False

    def setUpRecoveryManager(self):
        self.recovery_manager = None

    def set_mirror_list(self, cvolumes, ccgs):
        self.xcli_client_mock.cmd.mirror_list.return_value = cvolumes

    def set_main_mirror(self, vol1, cg1):
        self.xcli_mirror = vol1
        self.master = 'vol1'
        self.slave = 'vol2'

    def setUp(self):
        self.xcli_client_mock = MagicMock()
        self.mirrored_entities = MirroredCachedEntities(
            self.xcli_client_mock)
        self.setUpMirroredEntities()
        self.setUpRecoveryManager()
        self.recovery_manager.set_action_entities(self.mirrored_entities)

    def create_mock_host(self, name):
        host = MagicMock()
        host.name = name
        host.fc_ports = '11'
        host.cluster = ''
        return host

    def create_mock_resource(self, name, is_master, sync_state):
        vol = MagicMock()
        vol.name = name
        vol.local_peer_name = name
        vol.current_role = 'Master'
        if (not is_master):
            vol.current_role = 'Slave'
        vol.sync_state = sync_state
        vol.sync_type = 'sync_best_effort'
        vol.pool_name = "pool1"
        vol.pool = "pool1"
        vol.__str__.return_value = name + "," + \
            str(vol.current_role) + "," + vol.sync_type + "," + vol.sync_state
        return vol

    def create_mock_vol(self, name, is_master, sync_state):
        vol = self.create_mock_resource(name, is_master, sync_state)
        return vol

    def create_mock_cg(self, name, is_master, sync_state):
        cg = self.create_mock_resource(name, is_master, sync_state)
        return cg

    def create_mock_pool(self, name, snapshot_size=100, used_by_snapshots=0):
        pool = MagicMock()
        pool.name = name
        pool.snapshot_size = snapshot_size
        pool.used_by_snapshots = used_by_snapshots
        pool.__str__.return_value = name + "," + \
            str(pool.snapshot_size) + "," + str(pool.used_by_snapshots)
        pool.as_single.return_value = "blabla"
        return pool

    def setUpMirroredEntities(self):
        vol1 = self.create_mock_vol("vol1", True, "synched")
        self.xcli_mirror = vol1
        vol2 = self.create_mock_vol("vol2", False, "Initializing")
        volumes = [vol1, vol2]
        cvolumes = CIMCLIResponse(volumes)

        cg1 = self.create_mock_cg("cg1", True, "synched")
        cg2 = self.create_mock_cg("cg2", False, "Initializing")
        cgs = [cg1, cg2]
        ccgs = CIMCLIResponse(cgs)

        self.set_main_mirror(vol1, cg1)

        self.set_mirror_list(cvolumes, ccgs)
        self.xcli_client_mock.cmd.vol_list.return_value = cvolumes
        self.xcli_client_mock.cmd.cg_list.return_value = ccgs

        pool1 = self.create_mock_pool("pool1")
        pool2 = self.create_mock_pool("pool2", 0, 0)
        pools = [pool1, pool2]
        cpools = CIMCLIResponse(pools)
        self.xcli_client_mock.cmd.pool_list.return_value = cpools

        host1 = self.create_mock_host('host1')
        chosts = CIMCLIResponse([host1])
        self.xcli_client_mock.cmd.host_list.return_value = chosts

        return_value = CIMCLIResponse([])
        self.xcli_client_mock.cmd.cluster_list.return_value = return_value

    def test_verify_readiness_for_failover(self):
        self.assertRaises(
            NoMirrorDefinedError,
            self.recovery_manager.verify_readiness_for_failover, 'dummy')
        self.assertRaises(SlaveIsNotConsistentRecoveryException,
                          self.recovery_manager.verify_readiness_for_failover,
                          self.slave)
        self.recovery_manager.verify_readiness_for_failover(self.master)

    def test_promote_bad_id(self):
        self.assertRaises(NoMirrorDefinedError,
                          self.recovery_manager.promote, 'dummy')

    def test_failover_resource(self):
        self.recovery_manager.promote(self.master)
        self.recovery_manager.promote(self.slave)

    def test_test_promote_start(self):
        SNAP_TIME_FORMAT = "%Y-%m-%dT%H-%M-%S.0"
        self.recovery_manager.test_promote_start(
            self.master, 'test_snapshot_prefix', SNAP_TIME_FORMAT)

    def test_test_promote_stop(self):
        self.recovery_manager.test_promote_stop(
            self.master, 'test_snapshot_prefix')

    def test_prepare_reverse_replication(self):
        self.recovery_manager.prepare_reverse_replication(self.master)

    def test_reactivate_mirror(self):
        self.recovery_manager.reactivate_mirror(self.master)

    def test_start_async_job(self):
        self.recovery_manager.start_async_job(self.xcli_mirror)

    def test_snap_target_before_possible_override(self):
        self.recovery_manager.snap_target_before_possible_override(
            self.master, 'snapshot_name')

    def test_duplicate_target_snapshot_before_possible_override(self):
        # only to fit in pep8
        rec_man = self.recovery_manager
        self.assertRaises(
            NoLastReplicatedSnapshotRecoveryException,
            rec_man.duplicate_target_snapshot_before_possible_override,
            self.master, 'snapshot_name')

    def test_snapshot_name_format(self):
        self.assertEqual(
            self.recovery_manager._get_snapshot_name(
                'pre', 'resource', 'time'),
            'pre_resource_time')
