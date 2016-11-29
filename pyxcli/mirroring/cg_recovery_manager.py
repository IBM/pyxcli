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
    RecoveryManager, NoLastReplicatedSnapshotRecoveryException, CHAR_LIMIT, \
    InsufficientSnapshotSpaceRecoveryException
from pyxcli.mirroring.mirrored_entities import CG
from pyxcli.mirroring.errors import NoMirrorDefinedError


logger = getLogger(XCLI_DEFAULT_LOGGER + '.mirroring')


class CGRecoveryManager(RecoveryManager):

    # ================================================= INIT =================

    def __init__(self, should_use_cache, xcli_client):
        super(CGRecoveryManager, self).__init__(
            should_use_cache, xcli_client)

    def get_mirror_resources(self):
        return self.action_entities.get_cg_mirrors()

    def get_type_str(self):
        return CG

    def _does_resource_have_mapped_test_snapshot(self, group_id,
                                                 test_snapshot_prefix):
        # Mapped is when all snapshots are mapped
        groups = self.get_target_group_test_snap_groups(group_id,
                                                        test_snapshot_prefix)
        for snap_group in groups:
            logger.debug("Found snap group %s for cg %s" %
                         (snap_group.name, group_id))
            all_mapped = True
            snaps = self.action_entities.get_snapshots_by_snap_groups()
            for snapshot in snaps[snap_group.name]:
                if not self.is_volume_mapped(snapshot):
                    all_mapped = False
            if all_mapped:
                logger.debug(
                    "All snapshots in snap group %s are "
                    "mapped" % snap_group.name)
                return True
        return False

    def _unmap_and_delete_test_snapshots(self, group_id, test_snapshot_prefix):
        groups = self.get_target_group_test_snap_groups(group_id,
                                                        test_snapshot_prefix)
        for snap_group in groups:
            snapshots = self.action_entities.get_snapshots_by_snap_groups()
            for snapshot in snapshots[snap_group.name]:
                self.unmap_volume(snapshot)
            self.delete_snap_group(snap_group.name)

    def _create_and_unlock_snapshot(self, cg, snap_group,
                                    test_snapshot_prefix):
        existing_snap_groups = self.get_target_group_test_snap_groups(
            cg, test_snapshot_prefix)
        if len(existing_snap_groups) == 0:
            logger.debug(
                "creating and unlocking snap group"
                "%s for cg %s" % (snap_group, cg))
            xcli_mirror = self.get_mirror_resources()[cg]
            if self._is_sync_mirror(xcli_mirror):
                self.xcli_client.cmd.cg_snapshots_create(
                    cg=cg, snap_group=snap_group)
            else:
                self.xcli_client.cmd.snap_group_duplicate(
                    snap_group=self._get_last_replicated_snapshot_name(cg),
                    new_snap_group=snap_group)
            self.xcli_client.cmd.snap_group_unlock(snap_group=snap_group)
        else:
            logger.debug("unlocking previously existing snap group"
                         "%s for cg %s" % (existing_snap_groups[0].name, cg))
            self.xcli_client.cmd.snap_group_unlock(
                snap_group=existing_snap_groups[0].name)

    def get_target_group_test_snap_groups(self, group_id,
                                          test_snapshot_prefix):
        snap_groups = list()
        for snap_group in self.xcli_client.cmd.snap_group_list(cg=group_id):
            if snap_group.name.startswith(test_snapshot_prefix):
                snap_groups.append(snap_group)
        return snap_groups

    # ============================================ REVERSE REPLICATION =======
    # ================================================= MIRROR ACTIONS =======
    def create_mirror(self, resource_name, target_name, mirror_type,
                      slave_resource_name, rpo=None, remote_rpo=None,
                      schedule=None, remote_schedule=None,
                      activate_mirror='no'):
        '''creates a mirror and returns a mirror object.
           target name must be a valid target from target_list,
           mirror type must be 'sync' or 'async',
           slave_resource_name would be the slave_cg name'''

        return self._create_mirror('cg', resource_name, target_name,
                                   mirror_type, slave_resource_name, rpo=rpo,
                                   remote_rpo=remote_rpo, schedule=schedule,
                                   remote_schedule=remote_schedule,
                                   activate_mirror=activate_mirror)

    def delete_mirror(self, resource_id):
        '''delete a mirror by resource_id'''
        self._delete_mirror(cg=resource_id)

    def activate_mirror(self, resource_id):
        self._activate_mirror(cg=resource_id)

    def deactivate_mirror(self, resource_id):
        self._deactivate_mirror(cg=resource_id)

    def _change_role(self, resource_id, role):
        self.xcli_client.cmd.mirror_change_role(cg=resource_id, new_role=role)

    def _switch_roles(self, resource_id):
        self.xcli_client.cmd.mirror_switch_roles(cg=resource_id)

    def _mirror_change_designation(self, resource_id, new_designation_str):
        self.xcli_client.cmd.mirror_change_designation(
            cg=resource_id, new_designation=new_designation_str)

    # =============================================== MAPPING ================
    def unmap_all_volumes(self, group_id):
        for volume in self.get_cg_volumes(group_id):
            self.unmap_volume(volume)

    # ================================================= SNAPSHOT =============
    def snap_target_before_possible_override(self, cg_id,
                                             snap_group_name=None):
        if (snap_group_name is None):
            snap_group_name = ("temp_synced_%s" % cg_id)[0:CHAR_LIMIT]
        logger.debug("-> Replica of consistency group [%s] with key [%s] is "
                     "being cloned." % (cg_id, snap_group_name) +
                     "This is the failsafe snapshot to use in case production "
                     "site had failed before replication has completed."
                     )
        snap_groups = self.action_entities.get_snapshots_by_snap_groups()
        if snap_group_name not in snap_groups:
            self.xcli_client.cmd.cg_snapshots_create(
                cg=cg_id, snap_group=snap_group_name)
        else:
            self.xcli_client.cmd.cg_snapshots_create(
                cg=cg_id, overwrite=snap_group_name)

    def duplicate_target_snapshot_before_possible_override(
            self, cg_id, snap_group_name=None):
        if snap_group_name is None:
            snap_group_name = ("temp_synced_%s" % cg_id)[0:CHAR_LIMIT]
        logger.debug("-> Replica of consistency group [%s] with key [%s] is "
                     "being cloned." % (cg_id, snap_group_name) +
                     "This is the failsafe snapshot to use in case production "
                     "site had failed before replication has completed."
                     )
        snap_groups = self.action_entities.get_snapshots_by_snap_groups()
        if snap_group_name in snap_groups:
            self.xcli_client.cmd.snap_group_delete(snap_group=snap_group_name)
        self.xcli_client.cmd.snap_group_duplicate(
            snap_group=self._get_last_replicated_snapshot_name(cg_id),
            new_snap_group=snap_group_name)

    def delete_snap_group(self, snap_group_name):
        logger.debug("Deleting snap group %s" % snap_group_name)
        self.xcli_client.cmd.snap_group_delete(snap_group=snap_group_name)

    def _get_last_replicated_snapshot_name(self, cg):
        for snap_group in self.xcli_client.cmd.snap_group_list(cg=cg):
            if snap_group.name.startswith('last-replicated-'):
                return snap_group.name
        raise NoLastReplicatedSnapshotRecoveryException()

    def verify_snapshot_space_for_resource(self, group_id):
        number_of_volumes = len(self.xcli_client.cmd.vol_list(cg=group_id))
        pool_name = self.xcli_client.cmd.cg_list(
            cg=group_id).as_single_element.pool
        if not self._does_pool_have_required_space_for_snapshots(
                pool_name, number_of_volumes):
            raise InsufficientSnapshotSpaceRecoveryException()

    def is_async_job_running(self, group_id):
        return len(self.xcli_client.cmd.sync_job_list(cg=group_id)) > 0

    def is_resource_locked(self, group_id):
        for volume in self.get_cg_volumes(group_id):
            if self._is_vol_locked(volume):
                return True
        return False

    def get_cg_volumes(self, group_id):
        """ return all non snapshots volumes in cg """
        for volume in self.xcli_client.cmd.vol_list(cg=group_id):
            if volume.snapshot_of == '':
                yield volume.name

    def verify_devices_in_cg(self, devices, group):
        for device in devices:
            logger.debug('Verify volume %s is in cg %s' % (device, group))
            if device not in self.get_cg_volumes(group):
                logger.error("Device %s is not in cg %s" % (device, group))
                raise NoMirrorDefinedError()
