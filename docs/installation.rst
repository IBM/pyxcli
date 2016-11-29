Installing / Upgrading
======================
.. highlight:: bash


**pyxcli** is in the `Python Package Index
<http://pypi.python.org/pypi/pyxcli/>`_.

Installing with pip
-------------------

We prefer `pip <http://pypi.python.org/pypi/pip>`_
to install **pyxcli** on platforms other than Windows::

  $ pip install pyxcli

To upgrade using pip::

  $ pip install --upgrade pyxcli

Installing with easy_install
----------------------------

If you must install pyxcli using
`setuptools <http://pypi.python.org/pypi/setuptools>`_ do::

  $ easy_install pyxcli

To upgrade do::

  $ easy_install -U pyxcli


Installing from source
----------------------

If you'd rather install directly from the source (i.e. to stay on the
bleeding edge), then check out the latest source from github and 
install the driver from the resulting tree::

  $ git clone https://github.com/ibm/pyxcli.git
  $ cd pyxcli
  $ pip install .

Uninstalling an old client
--------------------------

If the older **pyxcli** was installed on the system already it
will need to be removed. Run the following command to remove it::

  $ sudo pip uninstall pyxcli
