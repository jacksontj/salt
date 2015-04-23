# -*- coding: utf-8 -*-
'''
IPC transport classes
'''

# Import Python libs
from __future__ import absolute_import
import logging
import socket
import msgpack
import weakref

# Import Tornado libs
import tornado
import tornado.gen
import tornado.netutil
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

# Import Salt libs
import salt.transport.client
import salt.transport.frame

log = logging.getLogger(__name__)


class IPCServer(object):
    '''
    A Tornado IPC server very similar to Tornado's TCPServer class
    but using either UNIX domain sockets or TCP sockets
    '''
    def __init__(self, opts, io_loop=None, stream_handler=None):
        '''
        Create a new Tornado IPC server

        :param IOLoop io_loop: A Tornado ioloop to handle scheduling
        :param func stream_handler: A function to customize handling of an
                                    incoming stream.
        '''
        self.opts = opts
        self._started = False
        self.stream_handler = stream_handler

        # Placeholders for attributes to be populated by method calls
        self.stream = None
        self.sock = None
        self.io_loop = None

    def start(self, socket_path):
        '''
        Perform the work necessary to start up a Tornado IPC server

        Blocks until socket is established

        :param str socket_path: Path on the filesystem for the socket to bind to.
                                This socket does not need to exist prior to calling
                                this method, but parent directories should.
        '''
        # Start up the ioloop
        log.trace('IPCServer: binding to socket: {0}'.format(socket_path))
        self.sock = tornado.netutil.bind_unix_socket(socket_path)

        if self.io_loop is None:
            self.io_loop = IOLoop.current()

        tornado.netutil.add_accept_handler(
            self.sock,
            self.handle_connection,
            io_loop=self.io_loop,
        )
        self._started = True

    @tornado.gen.coroutine
    def handle_stream(self, stream):
        '''
        Override this to handle the streams as they arrive

        :param IOStream stream: An IOStream for processing

        See http://tornado.readthedocs.org/en/latest/iostream.html#tornado.iostream.IOStream
        for additional details.
        '''
        while True:
            framed_msg_len = yield stream.read_until(' ')
            framed_msg_raw = yield stream.read_bytes(int(framed_msg_len.strip()))
            framed_msg = msgpack.loads(framed_msg_raw)
            body = framed_msg['body']
            self.io_loop.spawn_callback(self.stream_handler, body)

    def handle_connection(self, connection, address):
        log.trace('IPCServer: Handling connection to address: {0}'.format(address))
        try:
            stream = IOStream(connection,
                              io_loop=self.io_loop,
                              )
            self.io_loop.spawn_callback(self.handle_stream, stream)
        except Exception as exc:
            log.error('IPC streaming error: {0}'.format(exc))

    def __del__(self):
        '''
        Routines to handle any cleanup before the instance shuts down.
        Sockets and filehandles should be closed explicitely, to prevent
        leaks.
        '''
        if hasattr(self.stream, 'close'):
            self.stream.close()
        if hasattr(self.sock, 'close'):
            self.sock.close()


class IPCClient(object):
    '''
    A Tornado IPC client very similar to Tornado's TCPClient class
    but using either UNIX domain sockets or TCP sockets

    This was written because Tornado does not have its own IPC
    server/client implementation.

    :param IOLoop io_loop: A Tornado ioloop to handle scheduling
    :param str socket_path: A path on the filesystem where a socket
                            belonging to a running IPCServer can be
                            found.
    '''

    # Create singleton map between two sockets
    instance_map = weakref.WeakKeyDictionary()

    def __new__(cls, io_loop=None, socket_path=None):
        io_loop = io_loop or tornado.ioloop.IOLoop.current()
        if io_loop not in IPCClient.instance_map:
            IPCClient.instance_map[io_loop] = weakref.WeakValueDictionary()
        loop_instance_map = IPCClient.instance_map[io_loop]

        # FIXME
        key = socket_path

        if key not in loop_instance_map:
            log.debug('Initializing new IPCClient for path: {0}'.format(key))
            new_client = object.__new__(cls)
            # FIXME
            new_client.__singleton_init__(io_loop=io_loop, socket_path=socket_path)
            loop_instance_map[key] = new_client
        else:
            log.debug('Re-using IPCClient for {0}'.format(key))
        return loop_instance_map[key]

    def __singleton_init__(self, io_loop=None, socket_path=None):
        '''
        Create a new IPC client

        IPC clients cannot bind to ports, but must connect to
        existing IPC servers. Clients can then send messages
        to the server.

        '''

        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.socket_path = socket_path

    def __init__(self, io_loop=None, socket_path=None):
        # Handled by singleton __new__
        pass

    # TODO: single connect for multiple callers (similar to auth)
    @tornado.gen.coroutine
    def connect(self, socket_path=None):
        '''
        Connect to a running IPCServer on a socket

        :param str socket_path: The path to a socket on a filesystem where a
                                IPServer is bound
        '''
        if not socket_path:
            socket_path = self.socket_path
        self.stream = IOStream(
            socket.socket(socket.AF_UNIX, socket.SOCK_STREAM),
            io_loop=self.io_loop,
        )
        yield self.stream.connect(socket_path)
        log.trace('IPCClient: Connecting to socket: {0}'.format(socket_path))

    def __del__(self):
        '''
        Routines to handle any cleanup before the instance shuts down.
        Sockets and filehandles should be closed explicitely, to prevent
        leaks.
        '''
        if hasattr(self, 'stream'):
            self.stream.close()


class IPCMessageClient(IPCClient):
    '''
    Salt IPC message client

    Create an IPC client to send messages to an IPC server

    An example of a very simple IPCMessageClient connecting to an IPCServer. This
    example assumes an already running IPCMessage server.

    IMPORTANT: The below example also assumes a running IOLoop process.

    # Import Tornado libs
    import tornado.ioloop

    # Import Salt libs
    import salt.config
    import salt.transport.ipc

    opts = salt.config.master_config()

    io_loop = tornado.ioloop.IOLoop.current()

    ipc_server_socket_path = '/var/run/ipc_server.ipc'

    ipc_client = salt.transport.ipc.IPCMessageClient(opts, io_loop=io_loop)

    # Connect to the server
    ipc_client.connect(ipc_server_socket_path)

    # Send some data
    ipc_client.send('Hello world')
    '''
    def __init__(self,
                 opts,
                 socket_path=None,
                 io_loop=None):
        '''
        Create an IPCMessageClient
        '''
        super(IPCMessageClient, self).__init__(io_loop=io_loop, socket_path=socket_path)
        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.socket_path = socket_path

    # FIXME timeout unimplemented
    @tornado.gen.coroutine
    def send(self, msg, timeout=None):
        '''
        Send a message to an IPC socket

        If the socket is not currently connected, a connection will be established.

        :param dict msg: The message to be sent
        :param int timeout: Timeout when sending message (Currently unimplemented)
        '''
        if not hasattr(self, 'stream'):
            yield self.connect()
        pack = salt.transport.frame.frame_msg(msg, raw_body=True)
        yield self.stream.write(pack)

    def close(self):
        if hasattr(self, 'stream'):
            self.stream.close()

    def __del__(self):
        '''
        Routines to handle any cleanup before the instance shuts down.
        Sockets and filehandles should be closed explicitely, to prevent
        leaks.
        '''
        if hasattr(self, 'stream'):
            self.close()


class IPCMessageServer(IPCServer):
    '''
    Salt IPC message server

    Creates a message server which can create and bind to a socket on a given
    path and then respond to messages asynchronously.

    An example of a very simple IPCServer which prints received messages to
    a console:

        # Import Tornado libs
        import tornado.ioloop

        # Import Salt libs
        import salt.transport.ipc
        import salt.config

        opts = salt.config.master_opts()

        io_loop = tornado.ioloop.IOLoop.current()
        ipc_server_socket_path = '/var/run/ipc_server.ipc'
        ipc_server = salt.transport.ipc.IPCMessageServer(opts, io_loop=io_loop
                                                         stream_handler=print_to_console)
        # Bind to the socket and prepare to run
        ipc_server.start(ipc_server_socket_path)

        # Start the server
        io_loop.start()

        # This callback is run whenever a message is received
        def print_to_console(payload):
            print(payload)

    See IPCMessageClient() for an example of sending messages to an IPCMessageServer instance
    '''
    def __init__(self, opts, socket_path=None, io_loop=None, stream_handler=None):
        '''
        Create an IPCMessageServer

        :param dict opts:           Salt options dictionary
        :param str socket_path:     Path on the filesystem to use for the IPC socket
        :param IOLoop io_loop:      Tornado IOLoop instance
        :param func stream_handler: Function to callback on message receipt
        '''
        super(IPCMessageServer, self).__init__(opts, io_loop=io_loop, stream_handler=stream_handler)
        self.io_loop = io_loop or tornado.ioloop.IOLoop.current()
        self.socket_path = socket_path
        self.stream_handler = stream_handler

    def pre_fork(self, process_manager):
        '''
        Do any work which is necessary prior to forking, such as setting up sockets
        '''
        self.start(self.socket_path)

    def post_fork(self, payload_handler, io_loop):
        '''
        Do any work which shoud happen per-process, such as spinning up event loops
        '''
        self.payload_handler = payload_handler
        self.io_loop = io_loop

    # TODO: don't stop the IOloop... this should stop this messageSrever from running
    def close(self):
        '''
        Shutdown the message server
        '''
        self.io_loop.stop()
