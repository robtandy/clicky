import logging
from asyncio import get_event_loop

log = logging.getLogger(__name__)

def run_loop(loop=None):
    if not loop:
        loop = get_event_loop()
    try:
        log.info('starting loop {}'.format(loop))
        loop.run_forever()
    except KeyboardInterrupt as k:
        log.info('received keyboard interrupt, stopping loop')
    finally:
        loop.close()


