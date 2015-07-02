# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Thomas Jackson <jacksontj.89@gmail.com>`
'''

# Import python libs
from __future__ import absolute_import
import os
import threading
import time

import tornado.gen
import tornado.ioloop

import salt.config
import salt.utils
import salt.transport.server
import salt.transport.client
import salt.transport.ipc
import salt.exceptions

# Import Salt Testing libs
from salt.ext.six.moves import range
from salttesting import TestCase
from salttesting.helpers import ensure_in_syspath
ensure_in_syspath('../')
import integration


# TODO: move to a library?
def get_config_file_path(filename):
    return os.path.join(integration.TMP, 'config', filename)


class BaseIPCReqCase(TestCase):
    '''
    Test the req server/client pair
    '''
    @classmethod
    def setUpClass(cls):
        cls.master_opts = salt.config.master_config(get_config_file_path('master'))
        cls.minion_opts = salt.config.minion_config(get_config_file_path('minion'))

        cls.socket_path = os.path.join(integration.TMP, 'ipc_test.ipc')

        cls.io_loop = tornado.ioloop.IOLoop()

        cls.results = []

        cls.process_manager = salt.utils.process.ProcessManager(name='ReqServer_ProcessManager')

        cls.server_channel = salt.transport.ipc.IPCMessageServer(cls.master_opts, socket_path=cls.socket_path, io_loop=cls.io_loop, stream_handler=cls._handle_payload)

        cls.server_channel.pre_fork(cls.process_manager)
        cls.server_channel.post_fork(cls._handle_payload, io_loop=cls.io_loop)

        cls.server_thread = threading.Thread(target=cls.io_loop.start)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.io_loop.stop()
        cls.server_thread.join()
        cls.process_manager.kill_children()
        cls.server_channel.close()
        del cls.server_channel


class ClearReqTestCases(BaseIPCReqCase):
    '''
    Test all of the clear msg stuff
    '''
    def setUp(self):
        self.channel = salt.transport.ipc.IPCMessageClient(self.master_opts, socket_path=self.socket_path)

    def tearDown(self):
        self.results = []

    def test_basic_send(self):
        self.channel.send('test_basic_send')
        time.sleep(0.1)
        self.assertIn('test_basic_send', self.results)

    def test_many_send(self):
        msgs = []
        for i in range(0, 1000):
            msgs.append('test_many_send_{0}'.format(i))

        for i in msgs:
            self.channel.send(i)
        time.sleep(0.5)
        self.assertTrue(set(self.results).issuperset(msgs))

    def test_very_big_message(self):
        long_str = ''.join([str(num) for num in range(10**5)])
        self.channel.send(long_str)
        time.sleep(1)
        self.assertIn(long_str, self.results)

    @classmethod
    def _handle_payload(cls, payload):
        cls.results.append(payload)


if __name__ == '__main__':
    from integration import run_tests
    run_tests(ClearReqTestCases, needs_daemon=False)
