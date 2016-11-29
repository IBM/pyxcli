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

from logging import getLogger
from pyxcli import XCLI_DEFAULT_LOGGER
from pyxcli.mirroring.recovery_manager import \
    RecoveryManager, CHAR_LIMIT, \
    InsufficientSnapshotSpaceRecoveryException, \
    NoLastReplicatedSnapshotRecoveryException

logger = getLogger(XCLI_DEFAULT_LOGGER + '.mirroring')


class VolumeRecoveryManager(RecoveryManager):

    def __init__(self, should_use_cache, xcli_client):
        super(VolumeRecoveryManager, self).__init__(
            should_use_cache, xcli_client)

    def get_mirror_resources(self):
        return self.action_entities.get_vol_mirrors()

    def get_type_str(self):
        return "volume"

    def _does_resource_have_mapped_test_snapshot(self, volume_name,
                                                 test_snapshot_prefix):
        snapshots = self.get_volume_snapshots_by_prefix(volume_name,
                                                        test_snapshot_prefix)
        for snapshot in snapshots:
            if self.is_volume_mapped(snapshot.name):
                return True
        return False

    def get_volume_snapshots_by_prefix(self, volume, test_snapshot_prefix):
        snapshots = list()
        for snapshot in self.xcli_client.cmd.snapshot_list(vol=volume):
            if snapshot.name.startswith(test_snapshot_prefix):
                snapshots.append(snapshot)
        return snapshots

    def _unmap_and_delete_test_snapshots(self, device_id,
                                         test_snapshot_prefix):
        snapshots = self.get_volume_snapshots_by_prefix(device_id,
                                                        test_snapshot_prefix)
        for snapshot in snapshots:
            self.unmap_and_delete_volume(snapshot.name)

    def _create_and_unlock_snapshot(self, vol, name, test_snapshot_prefix):
        existing_snapshots = self.get_volume_snapshots_by_prefix(
            vol, test_snapshot_prefix)
        if len(existing_snapshots) == 0:
            logger.debug("-> Creating and setting [r/w] attributes snapshot "
                         "[%s] for device [%s]." % (name, vol))
            xcli_mirror = self.get_mirror_resources()[vol]
            if self._is_sync_mirror(xcli_mirror):
                self.xcli_client.cmd.snapshot_create(vol=vol, name=name)
            else:
                self.xcli_client.cmd.snapshot_duplicate(
                    snapshot=self._get_last_replicated_snapshot_name(vol),
                    name=name)
            self.xcli_client.cmd.vol_unlock(vol=name)
        else:
            logger.debug("-> Setting [r/w] attributes for existing snapshot "
                         "[%s] of device [%s]." % (existing_snapshots[0].name,
                                                   vol))
            self.xcli_client.cmd.vol_unlock(vol=existing_snapshots[0].name)

    # ============================================ REVERSE REPLICATION =======

    # ================================================= MIRROR ACTIONS =======
    def create_mirror(self, resource_name, target_name, mirror_type,
                      slave_resource_name, create_slave='no', remote_pool=None,
                      rpo=None, remote_rpo=None, schedule=None,
                      remote_schedule=None, activate_mirror='no'):
        '''creates a mirror and returns a mirror object,
           target name must be a valid target from target_list,
           mirror type must be 'sync' or 'async',
           slave_resource_name would be the slave_vol name'''

        return self._create_mirror('vol', resource_name, target_name,
                                   mirror_type, slave_resource_name,
                                   create_slave=create_slave,
                                   remote_pool=remote_pool, rpo=rpo,
                                   remote_rpo=remote_rpo, schedule=schedule,
                                   remote_schedule=remote_schedule,
                                   activate_mirror=activate_mirror)

    def delete_mirror(self, resource_id):
        '''delete a mirror by mirror name'''
        self._delete_mirror(vol=resource_id)

    def activate_mirror(self, vol_id):
        self._activate_mirror(vol=vol_id)

    def deactivate_mirror(self, resource_id):
        self._deactivate_mirror(vol=resource_id)

    def _change_role(self, resource_id, role):
        self.xcli_client.cmd.mirror_change_role(vol=resource_id, new_role=role)

    def _switch_roles(self, resource_id):
        self.xcli_client.cmd.mirror_switch_roles(vol=resource_id)

    def _mirror_change_designation(self, resource_id, new_designation_str):
        self.xcli_client.cmd.mirror_change_designation(
            vol=resource_id, new_designation=new_designation_str)

    # =============================================== MAPPING ================
    def unmap_and_delete_volume(self, volume):
        self.unmap_volume(volume)
        self._delete_volume(volume)

    def unmap_all_volumes(self, resource_id):
        return self.unmap_volume(resource_id)

    def _delete_volume(self, volume):
        logger.debug("Deleting volume %s" % volume)
        self.xcli_client.cmd.vol_delete(vol=volume)

    # ================================================= SNAPSHOT =============

    def snap_target_before_possible_override(self, device_id,
                                             snapshot_name=None):
        if (snapshot_name is None):
            snapshot_name = ("temp_synced_%s" % device_id)[0:CHAR_LIMIT]
        logger.debug("-> Replica of device [%s] with key [%s] is being "
                     "cloned." % (device_id, snapshot_name) + "This is "
                     "the failsafe snapshot to use in case production "
                     "site had failed before replication has completed.")
        if self.action_entities.get_volume_by_name(snapshot_name) is None:
            self.xcli_client.cmd.snapshot_create(
                vol=device_id, name=snapshot_name)
        else:
            self.xcli_client.cmd.snapshot_create(
                vol=device_id, overwrite=snapshot_name)

    def duplicate_target_snapshot_before_possible_override(self, device_id,
                                                           snapshot_name=None):
        if (snapshot_name is None):
            snapshot_name = ("temp_synced_%s" % device_id)[0:CHAR_LIMIT]
        logger.debug("-> Replica of device [%s] with key [%s] is being "
                     "cloned." % (device_id, snapshot_name) + "This is "
                     "the failsafe snapshot to use in case production "
                     "site had failed before replication has completed.")
        if self.action_entities.get_volume_by_name(snapshot_name) is not None:
            self.xcli_client.cmd.snapshot_delete(snapshot=snapshot_name)
        self.xcli_client.cmd.snapshot_duplicate(
            snapshot=self._get_last_replicated_snapshot_name(device_id),
            name=snapshot_name)

    def _get_last_replicated_snapshot_name(self, volume):
        for snapshot in self.xcli_client.cmd.snapshot_list(vol=volume):
            if snapshot.name.startswith('last-replicated-'):
                return snapshot.name
        raise NoLastReplicatedSnapshotRecoveryException()

    def verify_snapshot_space_for_resource(self, device_id):
        pool_name = self.action_entities.get_volume_by_name(
            device_id).pool_name
        if not self._does_pool_have_required_space_for_snapshots(pool_name, 1):
            raise InsufficientSnapshotSpaceRecoveryException()

    # =================================== QUERIES ============================

    def is_async_job_running(self, device_id):
        return len(self.xcli_client.cmd.sync_job_list(vol=device_id)) > 0

    def is_resource_locked(self, volume_name):
        status = self.action_entities.get_volume_by_name(volume_name).locked
        return status == 'yes'

    # ====================================== ACTIONS =========================

    def is_cg_of_volume_replicated(self, volume_name):
        volume = self.action_entities.get_volume_by_name(volume_name)
        if volume.cg_name != '' and self.is_cg_replicated(volume.cg_name):
            return True
        return False
