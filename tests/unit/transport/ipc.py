# -*- coding: utf-8 -*-
'''
    :codeauthor: :email: `Mike Place <mp@saltstack.com>`
'''

# Import Python libs
from __future__ import absolute_import
# import os
# import threading

# Import tornado libs
import tornado
import tornado.testing


# Import Salt libs
import salt.config
import salt.transport.ipc
import salt.utils.process

# Import Salt Testing libs
# import tests.integration

# from salttesting import TestCase
from salttesting.helpers import ensure_in_syspath

# from tests.unit.transport.req_test import ReqChannelMixin

ensure_in_syspath('../')


#class TornadoIPCCase(TestCase):
#    '''
#    Test the Tornado IPC server and client
#    '''
#    def setUp(self):
#        self.master_opts = salt.config.master_config(os.path.join(tests.integration.TMP, 'config', 'master'))
#
#    def test_server_bind(self):
#        '''
#        Verify that when an IPC server starts up that it will create a UXD
#        '''
#        socket_path = os.path.join(tests.integration.TMP, 'ipc_server_test.ipc')
#        ipc_server = salt.transport.ipc.IPCServer(self.master_opts)  # No event loop provided
#        ipc_server.start(socket_path)
#
#        # Verify that we have at least have a file created
#        self.assertTrue(os.path.exists(socket_path))

#class BaseIPCTestCase(TestCase):
#    @classmethod
#    def setUpClass(cls):
#        cls.master_opts = salt.config.master_config(os.path.join(tests.integration.TMP, 'config', 'master'))
#
#        cls.process_manager = salt.utils.process.ProcessManager(name='IPCServer')
#
#        cls.pull_channel = salt.transport.client.PullChannel.factory(cls.master_opts, socket_path='/tmp/t.ipc')
#        cls.pull_channel.pre_fork(cls.process_manager)
#
#        cls.push_channel = salt.transport.client.PushChannel.factory(cls.master_opts, socket_path='/tmp/t.ipc')
#        cls.push_channel.pre_fork(cls.process_manager)
#
#        cls.io_loop = tornado.ioloop.IOLoop()
#        cls.pull_channel.post_fork(cls._handle_payload, io_loop=cls.io_loop)
#        cls.push_channel.post_fork(cls._handle_payload, io_loop=cls.io_loop)
#
#        cls.server_thread = threading.Thread(target=cls.io_loop.start)
#        cls.server_thread.daemon = True
#        cls.server_thread.start()
#
#    @classmethod
#    def tearDownClass(cls):
#        cls.io_loop.stop()
#        cls.server_thread.join()
#        cls.process_manager.kill_children()
#        cls.pull_channel.close()
#        cls.push_channel.close()
#        del cls.pull_channel
#        del cls.push_channel


class PushPullTestCases(tornado.testing.AsyncTestCase):
    '''
    Test push/pull IPC socket behaviour

    Push: client
    Pull: server
    '''
#    def setUp(self):
#        self.channel = salt.transport.client.PushChannel.factory(self.master_opts, socket_path='/tmp/t.ipc')

#    @classmethod
#    @tornado.gen.coroutine
#    def _handle_payload(cls, payload):
#        print('Received payload: {0}'.format(payload))
#        raise tornado.gen.Return((payload, {'fun': 'send_ipc'}))
#
#    def test_simple_push(self):
#        self.push_channel.send('Hello world')

    @tornado.testing.gen_test
    def test_async(self):
        pull_channel = salt.transport.ipc.IPCServer({}, io_loop=self.io_loop)
        pull_channel.start('/tmp/t.ipc')

        push_channel = salt.transport.ipc.IPCMessageClient({}, socket_path='/tmp/t.ipc', io_loop=self.io_loop)  # pylint: disable=E1124
        push_channel.connect()
        push_channel.send('Hello world')


if __name__ == '__main__':
    from tests.integration import run_tests
#    run_tests(TornadoIPCCase, needs_daemon=False)
    run_tests(PushPullTestCases, needs_daemon=False)
