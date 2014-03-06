import random
import logging
import sys
import msgpack
import struct
from asyncio import get_event_loop, start_server, Task, coroutine, \
        open_connection, IncompleteReadError

log = logging.getLogger('clicky.core')

class Pixel:
    def __init__(self, x, y):
        self.defense = 0
        self.x = x
        self.y = y
        self.red = random.randint(0,255)
        self.blue = random.randint(0,255)
        self.green = random.randint(0,255)

    def __repr__(self):
        return 'X:{0} Y:{1} R:{2} G:{3} B:{4} D:{5}'.format(self.x, self.y,
                self.red, self.green, self.blue, self.defense)


class Game:
    def __init__(self, W, H, power):
        self.W = W  
        self.H = H
        self.power = power

        self.board = []
        for y in range(self.H):
            for x in range(self.W):
                self.board.append(Pixel(x, y))
        
    def get(self, x, y):
        return self.board[x + y*self.H]

    def click(self, x, y, red, green, blue):
        for i in range(self.power):
            self._click(x, y, red, green, blue)

    def _click(self, x, y, red, green, blue):
        p = self.get(x, y)
        log.debug('pre click {0} with {1} {2} {3}'.format(p, red, green, blue))
        if p.red == red and p.blue == blue and p.green == green:
            p.defense += 1
            return
        elif p.defense >= 1:
            p.defense -= 1
            return

        # if we got here defense is zero, and we need to adjust color
        if p.red > red:
            p.red -= 1
        elif p.red < red:
            p.red += 1
        if p.blue > blue:
            p.blue -= 1
        elif p.blue < blue:
            p.blue += 1
        if p.green > green:
            p.green -= 1
        elif p.green < green:
            p.green += 1

        log.debug('clicked {}'.format(p))

