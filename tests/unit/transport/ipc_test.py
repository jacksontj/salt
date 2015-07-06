# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Mike Place <mp@saltstack.com>`
'''

# Import python libs
from __future__ import absolute_import
import os
import time
import logging
import threading

import tornado.gen
import tornado.ioloop

import salt.utils
import salt.config
import salt.exceptions
import salt.transport.ipc
import salt.transport.server
import salt.transport.client

from salt.ext.six.moves import range

# Import Salt Testing libs
import integration

from salttesting import TestCase
from salttesting.mock import MagicMock
from salttesting.helpers import ensure_in_syspath

log = logging.getLogger(__name__)

ensure_in_syspath('../')


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
        self.channel = salt.transport.ipc.IPCMessageClient(self.master_opts, socket_path=self.socket_path, io_loop=tornado.ioloop.IOLoop.instance())

    def tearDown(self):
        self.results = []
        self.server_channel.stream_handler = lambda reset_handler: None

    def test_basic_send(self):
        def server_stream_handler(payload):
            self.assertIn('test_basic_send', payload)
            tornado.ioloop.IOLoop.instance().stop()
        self.server_channel.stream_handler = server_stream_handler
        self.channel.send('test_basic_send')
        tornado.ioloop.IOLoop.instance().start()

    def test_many_send(self):
        msgs = []
        self.server_channel.stream_handler = MagicMock()

        for i in range(0, 1000):
            msgs.append('test_many_send_{0}'.format(i))

        for i in msgs:
            self.channel.send(i)
        # Because we're doing multiple sends here, we can't wait on a single callback
        # This is a little hacky, but works
        five_sec_timeout = time.time() + 5.0
        while self.channel.stream.writing():
            time.sleep(0.1)
            if time.time() > five_sec_timeout:
                break
        self.assertEqual(len(self.server_channel.stream_handler.mock_calls), len(msgs))

    def test_very_big_message(self):
        def server_stream_handler(payload):
            self.assertEqual(payload, long_str)
            tornado.ioloop.IOLoop.instance().stop()

        self.server_channel.stream_handler = server_stream_handler

        long_str = ''.join([str(num) for num in range(10**5)])
        self.channel.send(long_str)
        tornado.ioloop.IOLoop.instance().start()

    @classmethod
    def _handle_payload(cls, payload):
        log.warning('Using class payload handler. Override for test-specific instances.')
        cls.results.append(payload)


if __name__ == '__main__':
    from integration import run_tests
    run_tests(ClearReqTestCases, needs_daemon=False)
