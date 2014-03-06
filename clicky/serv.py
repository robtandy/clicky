import random
import logging
import sys
import msgpack
import struct
from asyncio import get_event_loop, start_server, Task, coroutine, \
        open_connection, IncompleteReadError, sleep

from .util import run_loop
from .core import Pixel, Game
from .messageio import MessageIO

log = logging.getLogger('clicky.serv')

class Serv(MessageIO):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.subscriptions = {}

    @coroutine
    def new_connection(self, reader, writer):
        yield from super().new_connection(reader, writer)
        # add on an list to hold clicks
        self.connections[-1].clicks = []
        # and a place to put a list of subscribed pixels
        self.connections[-1].subscribed_to = []
        # and a random connection identifier
        self.connections[-1].client_id = random.randint(0, 2**32)
        # by default assume connection supports binary
        self.connections[-1].supports_binary = True

    @coroutine
    def handle_message(self, connection, msg):
        log.debug('handling message {}'.format(msg))
        if msg['message_name'] == 'get_region':
            Task(self.do_get_region(msg, connection))
        elif msg['message_name'] == 'get_region_nb':
            # mark connection as nb=no binary, ie, javascript clients whose
            # message pack dont support bin type, so we will send
            # regions the old way
            Task(self.do_get_region(msg, connection))
            connection.supports_binary = False
        elif msg['message_name'] == 'subscribe_region':
            connection.supports_binary = False
            Task(self.do_subscribe_region(msg, connection))
        elif msg['message_name'] == 'clicks':
            Task(self.do_clicks(msg, connection))
        elif msg['message_name'] == 'game_info':
            Task(self.do_game_info(msg, connection))

    @coroutine
    def do_game_info(self, msg, connection):
        reply = {'message_name':'game_info', 'id':1,
                 'width':self.game.W, 'height':self.game.H,
                 'power':self.game.power}

        yield from self.send(reply, connection)

    
    @coroutine
    def do_clicks(self, msg, connection):
        g = self.game
        for c in msg['clicks']:
            x, y = c['pixel']
            n = int(c['num'])

            R, G, B = c['rgb']

            if not (0 <= R <= 255 and 0 <= G <= 255 and 0 <= B <= 255):
                log.error('invalid colors received {}'.format(c))
                return
            
            for i in range(n):
                g.click(x, y, R, G, B)

            # check for subscribers, this will get SLOW fast
            key = '{:d},{:d}'.format(x,y)
            p = g.get(x, y)
            if key in self.subscriptions:
                log.debug('{0} subs for {1}'.format(len(self.subscriptions[key]),key))
                click = {'pixel':c['pixel'], 'num':c['num'],
                         'rgb':[p.red, p.green, p.blue],
                         'defense':p.defense}  
                for sub_connection in self.subscriptions[key]:
                    if sub_connection.client_id == connection.client_id:
                        # dont send own clicks back to client
                        continue
                    sub_connection.clicks.append(click)
            

    @coroutine 
    def do_get_region(self, msg, connection, sub=False):
        start_x, start_y = msg['region']['top_left']
        end_x, end_y = msg['region']['bottom_right']

        pixels = []
        defense = []

        for y in range(start_y, end_y+1):
            for x in range(start_x, end_x+1):
                p = self.game.get(x, y)

                pixels.append(p.red)
                pixels.append(p.green)
                pixels.append(p.blue)
                if p.defense > 0:
                    defense.append([x, y, p.defense])

        if connection.supports_binary:
            pixels = bytes(pixels)

        reply = {'id':msg['id'], 'message_name':'region', 
                 'region':{'top_left':msg['region']['top_left'], 
                           'bottom_right':msg['region']['bottom_right']},
                 'pixels':pixels, 'defense':defense}

        yield from self.send(reply, connection)
 
    @coroutine 
    def do_subscribe_region(self, msg, connection):
        # clear last sub
        if len(connection.subscribed_to) > 0:
            for p in connection.subscribed_to:
                key = '{:d},{:d}'.format(p.x,p.y)
                self.subscriptions[key].remove(connection)

        connection.subscribed_to = []       
        connection.sub_id = msg['id']

        start_x, start_y = msg['region']['top_left']
        end_x, end_y = msg['region']['bottom_right']

        for y in range(start_y, end_y+1):
            for x in range(start_x, end_x+1):
                p = self.game.get(x, y)
                key = '{:d},{:d}'.format(p.x,p.y)
                if not key in self.subscriptions:
                    self.subscriptions[key] = set()
                self.subscriptions[key].add(connection)
                connection.subscribed_to.append(p)

        get_event_loop().call_later(0.25, self.serv_subscription, connection)
    
    def serv_subscription(self, connection):
        if len(connection.clicks) > 0:
            log.debug('SERVING sub for {}'.format(connection.name))
            Task(self.send({'message_name':'click_update', 
                'id':connection.sub_id, 
                'clicks':connection.clicks}, connection))
            connection.clicks = []
        
        if connection.live:
            get_event_loop().call_later(0.25, self.serv_subscription, connection)
        else:
            log.debug('connection dead. cancelling subscription')



if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                format='%(asctime)s | %(levelname)s | %(message)s')
    logging.getLogger('clicky').setLevel(logging.DEBUG)

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--width', required=True, type=int)
    p.add_argument('--height', required=True, type=int)
    p.add_argument('--port', default=11000)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--power', default=10)

    args = p.parse_args()

    g = Game(args.width, args.height, args.power)
    
    Serv(g).run(args.host, args.port)
    run_loop()
    
