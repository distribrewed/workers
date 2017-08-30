import logging

from distribrewed_core.base.worker import BaseWorker

log = logging.getLogger(__name__)

class BoilWorker(BaseWorker):
    def __init__(self):
        super(BoilWorker, self).__init__()
        log.info('Finson......take it away!')
