import random
import logging
import sys
import msgpack
import struct
from asyncio import get_event_loop, start_server, Task, coroutine, \
        open_connection, IncompleteReadError, sleep

log = logging.getLogger('clicky.messageio')

class Connection:
    def __init__(self, name, reader, writer):
        self.live = True
        self.name = name
        self.reader = reader
        self.writer = writer

class MessageIO:
    def __init__(self, client_mode=False):
        self.connections = []
        self.client_mode = client_mode

    def run(self, host='127.0.0.1', port=11000):
        coro = start_server(self.client_connected, host=host, port=port)
        loop = get_event_loop()
        loop.run_until_complete(coro)

    @coroutine
    def connect(self, host, port):
        log.info('connecting to {0}:{1}'.format(host, port))
        reader, writer = yield from open_connection(host, port)
        log.info('connected.')
        yield from self.new_connection(reader, writer)

    def client_connected(self, client_reader, client_writer):
        Task(self.new_connection(client_reader, client_writer))

    @coroutine
    def new_connection(self, reader, writer):
        name = writer.get_extra_info('peername', None)
        log.info('new connection {}'.format(name))
        # FIXME
        assert name is not None

        c = Connection(name, reader, writer)
        self.connections.append(c)
        Task(self.listen(c))

    @coroutine
    def listen(self, connection):
        while connection.live:
            log.info('listening to {} for msg'.format(connection.name))
            try:
                msg = yield from self.receive(connection.reader)
                Task(self.handle_message(connection, msg))
            except IncompleteReadError as e:
                log.info('Incomplete Read. {} set to dead'.format(
                    connection.name))
                connection.live = False
        log.info('removing {} from connections')

        # FIXME: O(n)! make connections a set
        self.connections.remove(connection)
    
    @coroutine
    def send(self, obj, connection=None, *, packed=False):
        if self.client_mode:
            yield from self.maybe_wait_for_connect()

        if not connection and self.client_mode:
            connection = self.connections[0]
        elif not connection and not self.client_mode:
            raise Exception('must specify connection in server mode!')
        
        if packed:
            m = obj
        else:
            m = msgpack.packb(obj, use_bin_type=True)

        L = len(m)
        log.debug('sending message length({0}) to {1}'.format(L, connection.name))
        try:
            connection.writer.write(struct.pack('>I',L))
            connection.writer.write(m)
            yield from connection.writer.drain()
        except ConnectionResetError as e:
            log.info('Connection Reset. {} set to dead'.format(
                connection.name))
            connection.live = False

    @coroutine
    def maybe_wait_for_connect(self):
        while self.client_mode and len(self.connections) == 0:
            log.debug('waiting...')
            yield from sleep(0.25)

    @coroutine
    def receive(self, reader):
        # read 4 bytes and interpret them as a big endian integer for 
        # length of the message to follow
        data = yield from reader.readexactly(4)
        log.debug('received {}'.format(data))
        length = struct.unpack('>I', data)[0]
        log.debug('incoming message of length {}'.format(length))

        # now read a message of this length and unpack it using msgpack
        data = yield from reader.readexactly(length)
        msg = msgpack.unpackb(data, encoding='utf-8')

        log.debug('got message of length {}'.format(length))
        return msg

    @coroutine
    def handle_message(self, connection, msg):
        log.info('received message from {}'.format(connection.name))


