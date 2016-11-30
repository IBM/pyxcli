"""
Usage examples of the XCLIClient.
"""

from pyxcli.client import XCLIClient

# Connect SSL to an XIV-Storage.
xcli_client = XCLIClient.connect_ssl('username', 'password', "mgmt_ip")

# extracting Volume list from XIV-Storage
# as list - getting all the volumes as a list element
volumes = xcli_client.cmd.vol_list().as_list
for vol in volumes:
    print (vol.name)

# Getting all of the pools
pools = xcli_client.cmd.pool_list().as_list
for pool in pools:
    print (pool.name)

# Create volume - return value is an XML object indicating if the
# command succeeded.
vol_result = xcli_client.cmd.vol_create(pool="pool_name", size=301,
                                        vol="vol_name")

# Add volume to performance class (return value is an XML object)
perf_class_result = xcli_client.cmd.perf_class_add_vol(perf_class="perf_class",
                                                       vol="vol_name")
