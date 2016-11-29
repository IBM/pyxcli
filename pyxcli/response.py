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
""" IBM XCLI response Module

.. module: response

:Description: Provides a response object for the IBM XCLI Client Classes. The
 object helps to analyse the results returned by the Accelerate storage
 arrays.

"""

from bunch import Bunch
from pyxcli.helpers import xml_util as etree


class XCLIResponse(object):
    RETURN_PATH = "return"

    def __init__(self, cmdroot):
        self.response_etree = cmdroot

    @classmethod
    def instantiate(cls, cmdroot, encoding):
        compressed = cmdroot.find("compressed_return")
        if compressed is not None:
            text = compressed.attrib["value"]
            raw = text.decode(encoding).decode("zlib")
            cmdroot.append(etree.fromstring("<return>%s</return>" % (raw,)))
            cmdroot.remove(compressed)

        return cls(cmdroot)

    @property
    def as_return_etree(self):
        return self.response_etree.find(self.RETURN_PATH)

    @property
    def contained_element_types(self):
        return set(subelement.tag for subelement in
                   self.as_return_etree.getchildren())

    # @ReservedAssignment
    def all(self, element_type=None, response_path=None):
        """
        Generates Bunches, each representing a single subelement of the
        response. If an element_type is requested, only elements whose
        tag matches the element_type are returned. If the response has no
        subelements (for example, in a <return>-less command), yields None.
        """
        path = self.RETURN_PATH
        if response_path is not None:
            path += "/" + response_path
        response_element = self.response_etree.find(path)
        if response_element is None:
            return
        for subelement in self.response_etree.find(path).getchildren():
            if element_type is None or subelement.tag == element_type:
                yield _populate_bunch_with_element(subelement)

    @property
    def as_single_element(self):
        """
        Processes the response as a single-element response,
        like config_get or system_counters_get.
        If there is more then one element in the response or no
        elements this raises a ResponseError
        """
        if self.as_return_etree is None:
            return None
        if len(self.as_return_etree.getchildren()) == 1:
            return _populate_bunch_with_element(self.as_return_etree.
                                                getchildren()[0])
        return _populate_bunch_with_element(self.as_return_etree)

    @property
    def as_list(self, element_type=None, response_path=None):
        return list(self.all(element_type, response_path))

    def as_dict(self, key, element_type=None, response_path=None):
        result = {}
        for element in self.all(element_type, response_path):
            result[getattr(element, key)] = element
        return result

    def __iter__(self):
        return self.all()

    def __len__(self):
        return len(self.as_list)

    def __getitem__(self, item):
        if isinstance(item, basestring):
            return self.all(item)
        elif isinstance(item, (int, long)):

            return list(self.all())[item]
        else:
            raise TypeError("'item' can be a string or an int", item)

    def __nonzero__(self):
        return any(self.all())
    __bool__ = __nonzero__

    def __str__(self):
        return etree.tostring(self.response_etree)


def _populate_bunch_with_element(element):
    """
    Helper function to recursively populates a Bunch from an XML tree.
    Returns leaf XML elements as a simple value, branch elements are returned
    as Bunches containing their subelements as value or recursively generated
    Bunch members.
    """
    if 'value' in element.attrib:
        return element.get('value')
    current_bunch = Bunch()

    if element.get('id'):
        current_bunch['nextra_element_id'] = element.get('id')
    for subelement in element.getchildren():
        current_bunch[subelement.tag] = _populate_bunch_with_element(
            subelement)
    return current_bunch
