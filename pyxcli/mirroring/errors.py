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

ERR_STR_VOL_DOESNT_EXIST = "volume name does not exist"
ERR_STR_VOL_IS_SLAVE = "local peer is not the master"
ERR_STR_VOL_MIRROR_NOT_DEFINED = \
    "local volume does not have remote mirroring definitions"


class MirroringException(Exception):
    pass


class NoMirrorDefinedError(MirroringException):
    pass


class MirrorInactiveError(MirroringException):
    pass


class RetriesExhausted(MirroringException):
    pass


class NoMatchingHostFound(MirroringException):
    pass
