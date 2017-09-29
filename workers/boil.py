import logging

# noinspection PyPackageRequirements
import schedule
from distribrewed_core.base.worker import ScheduleWorker

log = logging.getLogger(__name__)


class TemperatureWorker(ScheduleWorker):
    def __init__(self):
        super(TemperatureWorker, self).__init__()

    def _setup_worker_schedule(self, worker_schedule):
        log.info('Received schedule: {0}'.format(worker_schedule))
        schedule.every(2).seconds.do(self.do_some_work)

    @staticmethod
    def do_some_work():
        log.info('Boil stuff')


if __name__ == "__main__":
    # Setup debug logging
    logging.getLogger().setLevel('DEBUG')
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(pathname)s:%(lineno)s: [%(levelname)s] %(message)s'))
    logging.getLogger().addHandler(h)

    worker = TemperatureWorker()
    worker.start_worker([
        (1, 40.0),
        (2, 50.0)
    ])
