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
""" IBM XCLI Client Events Module

.. module: client

:Description: Enables sending a notification event to the Spectrum Accelerate
 storage arrays.

"""

import json
from socket import getfqdn
from bunch import Bunch
from logging import getLogger
from pyxcli import XCLI_DEFAULT_LOGGER
from pyxcli.events.platform_info import get_platform_details
from pyxcli.errors import UnrecognizedCommandError
from pyxcli.errors import OperationForbiddenForUserCategoryError

log = getLogger(XCLI_DEFAULT_LOGGER + ".events")

HOST_PRODUCT = 'HostProduct: '
EVENT_SEVERITY = 'Informational'
CSS_PRODUCT_EVENT = 'css_product_event'


class EventsManager(object):
    """
    Handle CSS event sending to XIV
    """

    def __init__(self, xcli, product_name, product_version):
        """
        init an EventsManager
        Args:
            xcli (XCLIClient): xcli client to send the event
            product_name (string): the sending product's name
            product_version (string): the sending product's version
        Raises:
            ValueError: if missing product_name or product_version
        """
        self.xcli = xcli
        self.product_name = product_name
        self.product_version = product_version
        self.server_name = getfqdn()
        self.platform = get_platform_details()
        # verify init params
        if not self.product_name:
            raise ValueError('product_name is empty')
        if not self.product_version:
            raise ValueError('product_version is empty')

    @staticmethod
    def _get_description_prefix():
        return HOST_PRODUCT

    def send_event(self, action, properties, event_severity=EVENT_SEVERITY):
        """
        send css_event and if fails send custom_event instead
        Args:
            action (ACTIONS): the action causing the event
            properties (dict): the action additional properties
            event_severity (string): the event severity
        Raises:
            XCLIError: if the xcli.cmd.custom_event failed
            KeyError: if action wasn't predefined
            TypeError: if properties is not None or dict
        """
        # verify properties
        event_properties = dict() if (properties is None) else properties
        if type(event_properties) is not dict:
            raise TypeError('properties is not dict')

        # prepare event
        event_bunch = Bunch(
            Product=self.product_name,
            Version=self.product_version,
            Server=self.server_name,
            Platform=self.platform,
            Action=action,
            Properties=event_properties)
        event_description = self._get_description_prefix() + \
            json.dumps(event_bunch)

        use_custom_event = True
        if CSS_PRODUCT_EVENT in dir(self.xcli.cmd):
            try:
                # send css product event
                log.debug("sending css_product_event "
                          "description=%s severity=%s",
                          event_description, event_severity)
                self.xcli.cmd.css_product_event(severity=event_severity,
                                                product=self.product_name,
                                                version=self.product_version,
                                                server=self.server_name,
                                                platform=self.platform,
                                                action=action,
                                                properties=event_properties)
                use_custom_event = False
            except (UnrecognizedCommandError,
                    OperationForbiddenForUserCategoryError):
                log.warning("failed css_product_event "
                            "description=%s severity=%s",
                            event_description, event_severity)
        if use_custom_event:
            # send custom event
            log.debug("sending custom_event description=%s severity=%s",
                      event_description, event_severity)
            self.xcli.cmd.custom_event(
                description=event_description, severity=event_severity)
