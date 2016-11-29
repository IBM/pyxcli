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
from bunch import Bunch
from pyxcli import XCLI_DEFAULT_LOGGER

CG = "cg"


logger = getLogger(XCLI_DEFAULT_LOGGER + '.mirroring')


class MirroredEntities(object):

    xcli_client = None

    def __init__(self, xcli_client):
        self.xcli_client = xcli_client

    @classmethod
    def get_mirrored_object_name(cls, xcli_mirror, remote_name=False):
        if remote_name:
            return xcli_mirror.remote_peer_name
        return xcli_mirror.local_peer_name

    @classmethod
    def is_mirror_master(cls, xcli_mirror):
        return xcli_mirror.current_role == 'Master'

    @classmethod
    def is_target_connected(cls, xcli_mirror):
        return xcli_mirror.connected == 'yes'

    def get_mirror_resources_by_name_map(self, scope=None):
        """ returns a map volume_name -> volume, cg_name->cg
            scope is either None or CG or Volume
        """
        volumes_mirrors_by_name = dict()
        cgs_mirrors_by_name = dict()
        if ((scope is None) or (scope.lower() == 'volume')):
            mirror_list = self.xcli_client.cmd.mirror_list(scope='Volume')
            for xcli_mirror in mirror_list:
                name = MirroredEntities.get_mirrored_object_name(xcli_mirror)
                volumes_mirrors_by_name[name] = xcli_mirror
        if ((scope is None) or (scope.lower() == CG)):
            for xcli_mirror in self.xcli_client.cmd.mirror_list(scope='CG'):
                name = MirroredEntities.get_mirrored_object_name(xcli_mirror)
                cgs_mirrors_by_name[name] = xcli_mirror
        res = Bunch(volumes=volumes_mirrors_by_name, cgs=cgs_mirrors_by_name)
        return res

    def get_cg_mirrors(self):
        return self.get_mirror_resources_by_name_map(scope="CG").cgs

    def get_vol_mirrors(self):
        return self.get_mirror_resources_by_name_map(scope="Volume").volumes

    def get_volume_by_name_map(self):
        return self.xcli_client.cmd.vol_list().as_dict('name')

    def get_volume_by_name(self, vol_name):
        return self.xcli_client.cmd.vol_list(vol=vol_name).as_single_element

    def get_pool_by_name_map(self):
        return self.xcli_client.cmd.pool_list().as_dict('name')

    def get_pool_by_name(self, name):
        return self.xcli_client.cmd.pool_list(pool=name).as_single_element

    def get_hosts_by_name_map(self):
        return self.xcli_client.cmd.host_list().as_dict('name')

    def get_hosts_by_name(self, name):
        return self.xcli_client.cmd.host_list(host=name).as_single_element

    def get_hosts_by_clusters(self):
        clusters = dict()
        for cluster in self.xcli_client.cmd.cluster_list():
            host_list = cluster.hosts.split(',') if cluster.hosts != '' else []
            clusters[cluster.name] = host_list
        return clusters

    def get_hosts_by_ports(self):
        hosts_by_ports = dict()
        for host in self.xcli_client.cmd.host_list():
            for fc_port in host.fc_ports.split(','):
                hosts_by_ports[fc_port] = host
            for iscsi_port in host.iscsi_ports.split(','):
                hosts_by_ports[iscsi_port] = host
        return hosts_by_ports

    def get_snapshots_by_snap_groups(self):
        snap_groups = dict()
        for volume in self.get_volume_by_name_map().values():
            if volume.sg_name != '':
                if volume.sg_name not in snap_groups:
                    snap_groups[volume.sg_name] = list()
                snap_groups[volume.sg_name].append(volume.name)
        return snap_groups

    def get_host_port_names(self, host_name):
        """ return a list of the port names of XIV host """
        port_names = list()
        host = self.get_hosts_by_name(host_name)
        fc_ports = host.fc_ports
        iscsi_ports = host.iscsi_ports
        port_names.extend(fc_ports.split(',') if fc_ports != '' else [])
        port_names.extend(iscsi_ports.split(',') if iscsi_ports != '' else [])
        return port_names

    def get_cluster_port_names(self, cluster_name):
        """ return a list of the port names under XIV CLuster """
        port_names = list()
        for host_name in self.get_hosts_by_clusters()[cluster_name]:
            port_names.extend(self.get_hosts_by_name(host_name))
        return port_names


class MirroredCachedEntities(MirroredEntities):
    _cache = None

    def __init__(self, xcli_client):
        super(MirroredCachedEntities, self).__init__(xcli_client)
        self._cache = dict()

    @property
    def _cached_xcli_mirrors(self):
        cache_key = 'xcli_mirrors'
        if cache_key not in self._cache:
            self._cache[cache_key] = super(
                MirroredCachedEntities,
                self).get_mirror_resources_by_name_map()
        return self._cache[cache_key]

    def get_cg_mirrors(self):
        return self._cached_xcli_mirrors.cgs

    def get_vol_mirrors(self):
        return self._cached_xcli_mirrors.volumes

    def get_mirror_resources_by_name_map(self):
        return self._cached_xcli_mirrors

    @property
    def _cached_xcli_volumes(self):
        cache_key = 'xcli_volumes'
        if cache_key not in self._cache:
            vol_by_name = super(MirroredCachedEntities,
                                self).get_volume_by_name_map()
            self._cache[cache_key] = vol_by_name
        return self._cache[cache_key]

    def get_volume_by_name_map(self):
        return self._cached_xcli_volumes

    def get_volume_by_name(self, vol_id):
        if vol_id not in self._cached_xcli_volumes:
            return None
        return self._cached_xcli_volumes[vol_id]

    @property
    def _cached_hosts_by_ports(self):
        cache_key = 'hosts_by_ports'
        if cache_key not in self._cache:
            self._cache[cache_key] = super(
                MirroredCachedEntities, self).get_hosts_by_ports()
        return self._cache[cache_key]

    def get_hosts_by_ports(self):
        return self._cached_hosts_by_ports

    @property
    def _cached_hosts_by_clusters(self):
        cache_key = 'hosts_by_clusters'
        if cache_key not in self._cache:
            self._cache[cache_key] = super(
                MirroredCachedEntities, self).get_hosts_by_clusters()
        return self._cache[cache_key]

    def get_hosts_by_clusters(self):
        return self._cached_hosts_by_clusters

    @property
    def _cached_snapshots_by_snap_groups(self):
        cache_key = 'snapshots_by_snap_groups'
        if cache_key not in self._cache:
            self._cache[cache_key] = super(
                MirroredCachedEntities, self).get_snapshots_by_snap_groups()
        return self._cache[cache_key]

    def get_snapshots_by_snap_groups(self):
        return self._cached_snapshots_by_snap_groups

    @property
    def _cached_pool_by_name(self):
        cache_key = 'pool_by_name'
        if cache_key not in self._cache:
            self._cache[cache_key] = super(
                MirroredCachedEntities, self).get_pool_by_name_map()
        return self._cache[cache_key]

    def get_pool_by_name_map(self):
        return self._cached_pool_by_name

    def get_pool_by_name(self, name):
        if name not in self._cached_pool_by_name:
            return None
        return self._cached_pool_by_name[name]

    @property
    def _cached_hosts_by_name(self):
        cache_key = 'hosts_by_name'
        if cache_key not in self._cache:
            self._cache[cache_key] = super(
                MirroredCachedEntities, self).get_hosts_by_name_map()
        return self._cache[cache_key]

    def get_hosts_by_name_map(self):
        return self._cached_hosts_by_name

    def get_hosts_by_name(self, name):
        if name not in self._cached_hosts_by_name:
            return None
        return self._cached_hosts_by_name[name]
