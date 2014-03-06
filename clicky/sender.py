import sys
import asyncio
import msgpack
import json
import struct
import logging
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from .serv import MessageIO, run_loop

log = logging.getLogger(__name__)

class MyMessageIO(MessageIO):
    def __init__(self):
        super().__init__(client_mode=True)
        self.t = Thread(target=self.get_and_send)
        self.t.start()

    @asyncio.coroutine
    def handle_message(self, connection, msg):
        log.info('<< {}'.format(msg))

    def get_and_send(self):
        loop = asyncio.new_event_loop()
        while True:
            r = input('>>>')
            try:
                toks = r.strip().split()
                if toks[0] == 'r':
                    m = {"message_name":"get_region", 
                            "region": {"top_left":[int(toks[1]),int(toks[2])],
                                       "bottom_right":[int(toks[3]),int(toks[4])]},
                                       "id":toks[5]}
                elif toks[0] == 'rnb':
                    m = {"message_name":"get_region_nb", 
                            "region": {"top_left":[int(toks[1]),int(toks[2])],
                                       "bottom_right":[int(toks[3]),int(toks[4])]},
                                       "id":toks[5]}
 
                elif toks[0] == 's':
                    m = {"message_name":"subscribe_region", 
                            "region": {"top_left":[int(toks[1]),int(toks[2])],
                                       "bottom_right":[int(toks[3]),int(toks[4])]},
                                       "id":toks[5]}

                elif toks[0] == 'c':
                    m = {"message_name":"clicks",
                        "clicks":[{'pixel':[int(toks[1]),int(toks[2])], 
                                    'name':toks[3], 
                                    'rgb':[int(toks[4]),int(toks[5]),int(toks[6])],
                                    'num':int(toks[7])}]}
                elif toks[0] == 'g':
                    m = {'message_name':'game_info', 'id':1}
                                    
                loop.run_until_complete(self.send(m))
            except Exception as e:
                log.exception(e)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                format='%(asctime)s | %(levelname)s | %(message)s')
   
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--port', default=11000)
    p.add_argument('--host', default='127.0.0.1')

    args = p.parse_args()

    m = MyMessageIO()
    asyncio.Task(m.connect(args.host, args.port))
    run_loop()



