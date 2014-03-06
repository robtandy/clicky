from autobahn.asyncio.websocket import WebSocketServerProtocol, \
                                               WebSocketServerFactory
import logging
import sys
import json
import msgpack
from asyncio import get_event_loop, Task, coroutine, sleep
from ..util import run_loop
from ..messageio import MessageIO

log = logging.getLogger(__name__)

class ClientMessageIO(MessageIO):
    def __init__(self, handler):
        super().__init__(client_mode=True)
        self.handler = handler

    @coroutine
    def handle_message(self, connection, msg):
        if self.handler: 
            self.handler.on_server_message(msg, connection)


class MessageIOWSProtocol(WebSocketServerProtocol):

    def __init__(self):
        super().__init__()
        self.messageio = ClientMessageIO(self)
        Task(self.messageio.connect(game_host, game_port))
    
    def on_server_message(self, msg, connection):
        #
        # FIXME: need to implement listening for a server message that is 
        # still msgpacked so we can pass it through!!
        #
        # keep up the good work!
        #

        #log.debug('server msg {}'.format(msg))
        p = msgpack.packb(msg)
        #self.sendMessage(json.dumps(msg).encode('utf-8'), False)
        self.sendMessage(p, True)
    
    def onConnect(self, request):
        log.info("Client connecting: {0}".format(request.peer))
    
    def onOpen(self):
        log.info("WebSocket connection open.")

    @coroutine
    def onMessage(self, payload, isBinary):
        if isBinary:
            log.debug("websocket binary message received")
            yield from self.messageio.send(payload, packed=True)
        else:
            m = json.loads(payload.decode('utf-8'))
            log.debug("websocket message received: {0}".format(m))
            yield from self.messageio.send(m)


    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                format='%(asctime)s | %(levelname)s | %(message)s')

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--port', default=9201)
    p.add_argument('--host', default='0.0.0.0')
    p.add_argument('--game_port', default=11000)
    p.add_argument('--game_host', default='127.0.0.1')

    args = p.parse_args()

    global game_host, game_port
    game_host = args.game_host
    game_port = args.game_port

    factory = WebSocketServerFactory(
            'ws://{0}:{1}'.format(args.host, args.port), 
            debug=False)
    factory.protocol = MessageIOWSProtocol


    loop = get_event_loop()
    coro = loop.create_server(factory, args.host, args.port)
    #server = loop.run_until_complete(coro)
    Task(coro)
   
    run_loop()
    coro.close()
