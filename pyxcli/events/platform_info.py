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
""" IBM XCLI Client Events platform_info Module

.. module: platform_info

:Description: Provides platform information for use in the IBM XCLI events
 to the Spectrum Accelerate storage arrays.

"""

import platform
from subprocess import Popen, PIPE

SAFE_LENGTH = 63

OSLEVEL_S = ["/usr/bin/oslevel", "-s"]


def get_aix_version():
    version_strings = []
    proc = Popen(OSLEVEL_S, **{"stdout": PIPE})
    oslevel_command, err = proc.communicate()
    for line in oslevel_command.splitlines():
        if "-" in line:
            try:
                major_minor_sub_minor, tl, sp, year_week = line.split('-')
                major, minor, sub_minor = (major_minor_sub_minor[0],
                                           major_minor_sub_minor[1],
                                           major_minor_sub_minor[2:])
                version_strings = [major, minor, sub_minor, tl, sp, year_week]
            except ValueError:
                pass
    if version_strings:
        aix_version_tuple = tuple([int(version_string)
                                   for version_string in version_strings])
        return aix_version_tuple
    else:
        return None


def get_platform_details(safe_metadata_set=True):

    if platform.system().lower() == 'aix':
        version = get_aix_version()
        version_str = "AIX_{major}.{minor}_TL_{tl}_SP_{sp}"
        return version_str.format(major=str(version[0]),
                                  minor=str(version[1]),
                                  tl=str(version[3]),
                                  sp=str(version[4]))
    retval = platform.platform()
    if safe_metadata_set and len(retval) > SAFE_LENGTH:
        system = platform.system()
        release = platform.release()
        machine = platform.machine()

        # Some platforms already include the architecture in the release string
        release = release.replace(machine, "").strip(".")

        # Platform other than Linux, simply return empty strings
        distname, distversion, _ = platform.linux_distribution(
            full_distribution_name=False)

        # No need to include distid (Santiago, Maverick, etc) is enough with
        # distro version number
        retval = platform._platform(system, release, machine,
                                    distname, distversion)

        if len(retval) > SAFE_LENGTH:
            retval = retval[0:SAFE_LENGTH]
    return retval
