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
import tornado.testing

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


class BaseIPCReqCase(tornado.testing.AsyncTestCase):
    '''
    Test the req server/client pair
    '''
    def setUp(self):
        super(BaseIPCReqCase, self).setUp()
        self.socket_path = os.path.join(integration.TMP, 'ipc_test.ipc')

        self.server_channel = salt.transport.ipc.IPCMessageServer(
            self.socket_path,
            io_loop=self.io_loop,
            payload_handler=self._handle_payload,
        )
        self.server_channel.start()

        self.payloads = []

    def tearDown(self):
        super(BaseIPCReqCase, self).tearDown()
        self.server_channel.close()
        os.unlink(self.socket_path)

    def _handle_payload(self, payload):
        self.payloads.append(payload)
        if payload.get('stop'):
            self.stop()

class ClearReqTestCases(BaseIPCReqCase):
    '''
    Test all of the clear msg stuff
    '''
    def setUp(self):
        super(ClearReqTestCases, self).setUp()
        self.channel = salt.transport.ipc.IPCMessageClient(
            socket_path=self.socket_path,
            io_loop=self.io_loop,
        )
        self.channel.connect(callback=self.stop)
        self.wait()

    def tearDown(self):
        super(ClearReqTestCases, self).setUp()
        self.channel.close()

    def test_basic_send(self):
        msg = {'foo': 'bar', 'stop': True}
        self.channel.send(msg)
        self.wait()
        self.assertEqual(self.payloads[0], msg)

    def test_many_send(self):
        msgs = []
        self.server_channel.stream_handler = MagicMock()

        for i in range(0, 1000):
            msgs.append('test_many_send_{0}'.format(i))

        for i in msgs:
            self.channel.send(i)
        self.channel.send({'stop': True})
        self.wait()
        self.assertEqual(self.payloads[:-1], msgs)

    def test_very_big_message(self):
        long_str = ''.join([str(num) for num in range(10**5)])
        msg = {'long_str': long_str, 'stop': True}
        self.channel.send(msg)
        self.wait()
        self.assertEqual(msg, self.payloads[0])


if __name__ == '__main__':
    from integration import run_tests
    run_tests(ClearReqTestCases, needs_daemon=False)
