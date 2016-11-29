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

import time
from logging import getLogger

from pyxcli import XCLI_DEFAULT_LOGGER
from pyxcli.mirroring.mirrored_entities import MirroredEntities
from pyxcli.mirroring.mirrored_entities import MirroredCachedEntities
from pyxcli.errors import XCLIError
from pyxcli.errors import CommandExecutionError
from pyxcli.errors import SyncAlreadyActiveError
from pyxcli.errors import SyncAlreadyInactiveError
from pyxcli.mirroring.errors import MirroringException
from pyxcli.mirroring.errors import NoMirrorDefinedError
from pyxcli.mirroring.errors import MirrorInactiveError

CHAR_LIMIT = 60


class RecoveryMethodNotImplementedException(MirroringException):
    pass


class SlaveIsNotConsistentRecoveryException(MirroringException):
    pass


class NoMirrorConnectivityRecoveryException(MirroringException):
    pass


class InsufficientSnapshotSpaceRecoveryException(MirroringException):
    pass


class LunNumberRecoveryException(MirroringException):
    pass


class AlreadyInTestFailoverStartRecoveryException(MirroringException):
    pass


class NoLastReplicatedSnapshotRecoveryException(MirroringException):
    pass


# ========================================================================
#     Base class for volume and consistency-group recovery managers
# ========================================================================

logger = getLogger(XCLI_DEFAULT_LOGGER + '.mirroring')


class RecoveryManager(object):
    xcli_client = None
    action_entities = None

    # ============================================ INIT =================
    def __init__(self, should_use_cache, xcli_client):
        self.xcli_client = xcli_client

        if (should_use_cache):
            self.action_entities = MirroredCachedEntities(
                xcli_client)
        else:
            self.action_entities = MirroredEntities(xcli_client)

    def set_action_entities(self, action_entities):
        self.action_entities = action_entities

    def get_mirror_resources(self):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def get_type_str(self):
        return " - "

    def get_target_by_system_id(self, system_id):
        target_names = [target.name for target in
                        self.xcli_client.cmd.target_list().as_list
                        if target.system_id == system_id]
        return target_names[0] if len(target_names) >= 1 else None

    # ========================================== FAILOVER =============
    def switch_roles(self, resource_id):
        self._switch_roles(resource_id)

    def verify_readiness_for_failover(self, resource_id):
        logger.debug("Verify failover readiness for %s %s" %
                     (self.get_type_str(), resource_id))
        self.verify_mirror_existence(resource_id)
        self.verify_slave_consistency(resource_id)

    def promote(self, resource_id):
        self.verify_mirror_existence(resource_id)
        xcli_mirror = self.get_mirror_resources()[resource_id]
        self._promote_resource(xcli_mirror, resource_id)

    def _promote_resource(self, xcli_mirror, resource_id):
        type_str = self.get_type_str()
        if not MirroredEntities.is_mirror_master(xcli_mirror):
            logger.debug("-> Promoting and setting [r/w] attributes "
                         "for %s [%s]." % (type_str, resource_id,))
            try:
                if self._is_sync_mirror(xcli_mirror):
                    self.snap_target_before_possible_override(resource_id)
                else:
                    self.duplicate_target_snapshot_before_possible_override(
                        resource_id)
            except CommandExecutionError as e:
                logger.warning("Failed to create failsafe snap group "
                               "for %s [%s]." % (type_str,
                                                 resource_id, str(e)))
            except Exception as e:
                logger.error("Unexpected exception %s", e)
                raise e
            self.change_role_to_master(resource_id)
        else:
            logger.warning("-> %s [%s] is already promoted to "
                           "Read-Write" % (type_str, resource_id,))

    # =============================================== TEST FAILOVER ==========
    def _get_snapshot_name(self, test_snapshot_prefix, resource_id,
                           snap_time_format):
        time_tuple = time.localtime()
        str_time = time.strftime(snap_time_format, time_tuple)
        snapshot_name = ("%s_%s_%s" % (test_snapshot_prefix,
                                       resource_id,
                                       str_time))[0:CHAR_LIMIT]
        return snapshot_name

    def test_promote_start(self, resource_id,
                           test_snapshot_prefix, snap_time_format):
        logger.info(
            "Commence: Temporary Snapshot Copy of [%s] on array is "
            "being created for testFailoverStart request" % (resource_id))
        self.verify_mirror_existence(resource_id)
        self._verify_resource_not_in_test_failover(
            resource_id, test_snapshot_prefix)
        self.verify_slave_consistency(resource_id)
        self.verify_snapshot_space_for_resource(resource_id)

        snapshot_name = self._get_snapshot_name(test_snapshot_prefix,
                                                resource_id, snap_time_format)
        self._create_and_unlock_snapshot(resource_id,
                                         snapshot_name,
                                         test_snapshot_prefix)

    def test_promote_stop(self, resource_id, test_snapshot_prefix):
        logger.info("Commence: Deletion of temporary Snapshot "
                    "%s Copy of [%s] for testFailoverStop"
                    "request." % (self.get_type_str(), resource_id,))
        self.verify_mirror_existence(resource_id)
        self._unmap_and_delete_test_snapshots(
            resource_id, test_snapshot_prefix)

    def _verify_resource_not_in_test_failover(self, resource_id,
                                              test_snapshot_prefix):
        if self._does_resource_have_mapped_test_snapshot(resource_id,
                                                         test_snapshot_prefix):
            raise AlreadyInTestFailoverStartRecoveryException()

    def _does_resource_have_mapped_test_snapshot(self, resource_id,
                                                 test_snapshot_prefix):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def _create_and_unlock_snapshot(self, resource_id,
                                    snapshot_name, test_snapshot_prefix):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def _unmap_and_delete_test_snapshots(self, resource_id,
                                         test_snapshot_prefix):
        raise RecoveryMethodNotImplementedException("Unsupported")

    # ============================================ REVERSE REPLICATION =======
    def prepare_reverse_replication(self, resource_id, should_unmap=False):

        # This method should be called on Primary before reverse_replication

        logger.info("Commence: %s [%s] is being set as target for replication "
                    "for prepareReverseReplication"
                    "request." % (self.get_type_str(), resource_id,))
        self.verify_mirror_existence(resource_id)
        self.verify_snapshot_space_for_resource(resource_id)
        self.snap_and_change_role_to_slave(resource_id)
        if should_unmap:
            self.unmap_all_volumes(resource_id)

    def reverse_replication(self, resource_id):

        # This method should be called on Secondary for reverse_replication

        logger.info("Commence: Establish replication for "
                    "%s [%s] with Primary role for reverseReplication "
                    "request." % (self.get_type_str(), resource_id,))
        self.verify_mirror_existence(resource_id)
        self.verify_mirror_connectivity(resource_id)

        self.reactivate_mirror(resource_id)
        logger.debug("-> Setting Primary role for "
                     "%s [%s]." % (self.get_type_str(), resource_id,))
        self._mirror_change_designation(resource_id, 'Primary')

    # ================================================= MIRROR ACTIONS =======

    def delete_mirror(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def activate_mirror(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def deactivate_mirror(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def is_mirror_active(self, resource_id):
        xcli_mirror = self.get_mirror_resources()[resource_id]
        return self._is_mirror_active(xcli_mirror)

    def reactivate_mirror(self, resource_id):
        logger.debug("-> Reactivating mirror for %s %s" %
                     (self.get_type_str(), resource_id))
        self.verify_mirror_existence(resource_id)
        xcli_mirror = self.get_mirror_resources()[resource_id]
        if self._is_mirror_active(xcli_mirror):
            self.deactivate_mirror(resource_id)
        self.activate_mirror(resource_id)

    def change_role_to_master(self, resource_id):
        self._change_role(resource_id, 'Master')

    def change_role_to_slave(self, resource_id):
        self._change_role(resource_id, 'Slave')

    def start_async_job(self, xcli_mirror):
        logger.debug("Starting manual sync job for %s => %s" % (
            xcli_mirror.local_peer_name, xcli_mirror.remote_peer_name))
        temp_schedule_name = ('temp_manual_%s' %
                              (xcli_mirror.local_peer_name,))[0:CHAR_LIMIT]
        current_schedule = xcli_mirror.schedule_name
        try:
            self.xcli_client.cmd.schedule_create(
                schedule=temp_schedule_name, type='manual')
            self._set_mirror_schedule(xcli_mirror, temp_schedule_name)
            self.xcli_client.cmd.schedule_create_tick(
                schedule=temp_schedule_name)
        except Exception as e:
            logger.error("Failed to start manual sync job for %s => %s."
                         " Reason: %s" % (xcli_mirror.local_peer_name,
                                          xcli_mirror.remote_peer_name,
                                          str(e)))
            raise (e)
        finally:
            self._set_mirror_schedule(xcli_mirror, current_schedule)
            self.xcli_client.cmd.schedule_delete(schedule=temp_schedule_name)

    def is_async_job_running(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def _create_mirror(self, resource_type, resource_name, target_name,
                       mirror_type, slave_resource_name, create_slave='no',
                       remote_pool=None, rpo=None, remote_rpo=None,
                       schedule=None, remote_schedule=None,
                       activate_mirror='no'):
        '''creates a mirror and returns a mirror object.
            resource_type must be 'vol' or 'cg',
            target name must be a valid target from target_list,
            mirror type must be 'sync' or 'async',
            slave_resource_name would be the slave_vol or slave_cg name'''

        kwargs = {
            resource_type: slave_resource_name,
            'target': target_name,
            'type': mirror_type,
            'slave_' + resource_type: slave_resource_name,
            'create_slave': create_slave,
            'remote_pool': remote_pool,
            'rpo': rpo,
            'remote_rpo': remote_rpo,
            'schedule': schedule,
            'remote_schedule': remote_schedule
        }

        if mirror_type == 'sync':
            kwargs['type'] = 'sync_best_effort'
            kwargs['rpo'] = None
        else:
            kwargs['type'] = 'async_interval'
            if kwargs['remote_schedule'] is None:
                kwargs['remote_schedule'] = kwargs['schedule']

        # avoids a python3 issue of the dict changing
        # during iteration
        keys = set(kwargs.keys()).copy()
        for k in keys:
            if kwargs[k] is None:
                kwargs.pop(k)

        logger.info('creating mirror with arguments: %s' % kwargs)
        self.xcli_client.cmd.mirror_create(**kwargs)

        if activate_mirror == 'yes':
            logger.info('Activating mirror %s' % resource_name)
            self.activate_mirror(resource_name)

        return self.get_mirror_resources()[resource_name]

    def _set_mirror_schedule(self, xcli_mirror, new_schedule):
        is_cg = (xcli_mirror.mirror_object == 'CG')
        if is_cg:
            self.xcli_client.cmd.mirror_change_schedule(
                cg=xcli_mirror.local_peer_name, schedule=new_schedule)
        else:
            self.xcli_client.cmd.mirror_change_schedule(
                vol=xcli_mirror.local_peer_name, schedule=new_schedule)

    def _is_mirror_active(self, xcli_mirror):
        return xcli_mirror.active == "yes"

    def _delete_mirror(self, **kwargs):
        logger.info('Deleting mirror %s' % kwargs)
        self.xcli_client.cmd.mirror_delete(**kwargs)

    def _deactivate_mirror(self, **kwargs):
        # if we get SYNC_ALREADY_INACTIVE (status 3) it is safe to ignore it
        try:
            self.xcli_client.cmd.mirror_deactivate(**kwargs)
        except SyncAlreadyInactiveError:
            logger.warning("_deactivate_mirror got an error, "
                           "Synchronization is already inactive")

    def _activate_mirror(self, **kwargs):
        # if we get SYNC_ALREADY_ACTIVE (status 3) it is safe to ignore it
        try:
            self.xcli_client.cmd.mirror_activate(**kwargs)
        except SyncAlreadyActiveError:
            logger.warning("_activate_mirror got an error, "
                           "Synchronization is already active")

    def _change_role(self, resource_id, role):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def _switch_roles(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def _mirror_change_designation(self, resource_id, new_designation_str):
        raise RecoveryMethodNotImplementedException("Unsupported")

    # =============================================== MAPPING ================

    def unmap_all_volumes(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def unmap_volume(self, volume_name):
        logger.info("-> Remove all mappings of volume %s" % volume_name)
        for mapping in self.xcli_client.cmd.vol_mapping_list(vol=volume_name):
            if mapping.type == 'cluster':
                ports = self.action_entities.get_cluster_port_names(
                    mapping.host)
                logger.debug("-> Volume / Snapshot [%s] is being masked "
                             "from XIV cluster [%s]. Ports "
                             "contained %s." % (volume_name, mapping.host,
                                                ports))
                try:
                    self.xcli_client.cmd.unmap_vol(
                        vol=volume_name, cluster=mapping.host)
                except XCLIError as e:
                    logger.error(e)
                    raise e
            else:
                ports = self.action_entities.get_host_port_names(mapping.host)
                logger.debug("-> Volume / Snapshot [%s] is being masked from"
                             " XIV host [%s]. Ports "
                             "contained %s." % (volume_name, mapping.host,
                                                ports))
                self.xcli_client.cmd.unmap_vol(vol=volume_name,
                                               host=mapping.host)

    def is_volume_mapped(self, volume_name):
        logger.debug("Testing if volume %s is mapped" % volume_name)
        if len(self.xcli_client.cmd.vol_mapping_list(vol=volume_name)) > 0:
            logger.debug("Volume %s is mapped" % volume_name)
            return True
        logger.debug("Volume %s is not mapped" % volume_name)
        return False

    def _is_vol_locked(self, volume_name):
        status = self.action_entities.get_volume_by_name(volume_name).locked
        return status == 'yes'

    # ================================================= SNAPSHOT =============

    def snap_target_before_possible_override(self, resource_id,
                                             snap_name=None):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def duplicate_target_snapshot_before_possible_override(self, resource_id,
                                                           snapshot_name=None):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def snap_and_change_role_to_slave(self, resource_id):
        xcli_mirror = self.get_mirror_resources()[resource_id]
        type_str = self.get_type_str()
        if MirroredEntities.is_mirror_master(xcli_mirror):
            self.snap_target_before_possible_override(resource_id)
            logger.debug(
                "-> Setting %s [%s] as replication target." % (type_str,
                                                               resource_id))
            if self._is_mirror_active(xcli_mirror):
                self.deactivate_mirror(resource_id)
            self.change_role_to_slave(resource_id)
        else:
            logger.warning("-> %s [%s] is already a replication target "
                           "target" % (type_str, resource_id))

    def verify_snapshot_space_for_resource(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    # ================================================= QUERIES ==============

    def is_resource_locked(self, resource_id):
        raise RecoveryMethodNotImplementedException("Unsupported")

    def is_mirror_slave_ready_for_failover(self, resource_id):
        xcli_mirror = self.get_mirror_resources()[resource_id]
        return self._is_mirror_slave_ready_for_promote(xcli_mirror)

    def _is_mirror_slave_ready_for_promote(self, xcli_mirror):
        return xcli_mirror.sync_state != 'Initializing'

    def _is_sync_mirror(self, xcli_mirror):
        return xcli_mirror.sync_type == 'sync_best_effort'

    def verify_mirror_existence(self, resource_id):
        if resource_id not in self.get_mirror_resources():
            raise NoMirrorDefinedError()

    def verify_slave_consistency(self, resource_id):
        xcli_mirror = self.get_mirror_resources()[resource_id]
        if not self._is_slave_consistent(xcli_mirror):
            raise SlaveIsNotConsistentRecoveryException()

    def is_slave_consistent(self, resource_id):
        xcli_mirror = self.get_mirror_resources()[resource_id]
        return self._is_slave_consistent(xcli_mirror)

    def _is_slave_consistent(self, xcli_mirror):
        if not MirroredEntities.is_mirror_master(xcli_mirror):
            if not self._is_mirror_slave_ready_for_promote(xcli_mirror):
                return False
        return True

    def verify_mirror_is_active(self, resource_id):
        xcli_mirror = self.get_mirror_resources()[resource_id]
        self._verify_mirror_is_active(xcli_mirror)

    def _verify_mirror_is_active(self, xcli_mirror):
        if not self._is_mirror_active(xcli_mirror):
            if xcli_mirror.mirror_error == 'No_Error':
                msg = 'Deactivated by an admin'
            else:
                msg = xcli_mirror.mirror_error
            raise MirrorInactiveError(msg)

    def verify_mirror_connectivity(self, resource_id):
        xcli_mirror = self.get_mirror_resources()[resource_id]
        self._verify_mirror_connectivity(xcli_mirror)

    def _verify_mirror_connectivity(self, xcli_mirror):
        if not MirroredEntities.is_target_connected(xcli_mirror):
            raise NoMirrorConnectivityRecoveryException()

    def _does_pool_have_required_space_for_snapshots(self, pool_name,
                                                     num_of_volumes):
        pool = self.action_entities.get_pool_by_name(pool_name)
        snapshot_size = int(pool.snapshot_size)
        used_by_snapshots = int(pool.used_by_snapshots)
        # A new snapshot requires up to 17 GB per volume in an
        # XIV/Spectrum Accelerate system. The size is smaller for A9000.
        if snapshot_size > used_by_snapshots + num_of_volumes * 17 + 17:
            return True
        return False

    # ================================================= Actions ==============

    def is_cg_replicated(self, local_cg_id):
        return local_cg_id in self.action_entities.get_cg_mirrors()
