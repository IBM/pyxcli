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

import pyxcli

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

install_requires = ['bunch']

setup(
    name='pyxcli',
    version=pyxcli.version,
    description="IBM Python XCLI Client",
    author="Tzur Eliyahu, Alon Marx",
    author_email="tzure@il.ibm.com",
    maintainer="Tzur Eliyahu, Alon Marx",
    keywords=["IBM", "XIV", "Spectrum Accelerate", "A9000", "A9000R"],
    requires=install_requires,
    install_requires=install_requires,
    tests_require=['nose', 'mock'],
    license="Apache License, Version 2.0",
    packages=find_packages(),
    provides=['pyxcli'],
    url="https://github.com/IBM/pyxcli",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ])
