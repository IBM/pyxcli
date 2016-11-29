:mod:`client` -- IBM XCLI Client
===========================================

.. automodule:: pyxcli.client
   :synopsis: IBM XCLI Client

   .. autoclass:: pyxcli.client.XCLIClient(transport, user, password, populate=True)

      .. automethod:: is_connected
      .. automethod:: close
      .. automethod:: reconnect
      .. automethod:: connect_ssl
      .. automethod:: connect_multiendpoint_ssl
      .. automethod:: execute_remote
      .. automethod:: get_user_client
      .. automethod:: get_remote_client
      .. automethod:: as_user


   .. autoclass:: pyxcli.client.BaseXCLIClient()

      .. automethod:: is_connected
      .. automethod:: close
      .. automethod:: execute
      .. automethod:: execute_remote
      .. automethod:: options
      .. automethod:: get_option
      .. automethod:: set_options
