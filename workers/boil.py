import logging
# noinspection PyPackageRequirements
from datetime import datetime, timedelta

import schedule
from distribrewed_core.base.worker import ScheduleWorker

log = logging.getLogger(__name__)


class TemperatureWorker(ScheduleWorker):
    @staticmethod
    def duration_str_to_delta(str):
        t = datetime.strptime(str, "%H:%M:%S")
        return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    def __init__(self):
        super(TemperatureWorker, self).__init__()

    def _setup_worker_schedule(self, worker_schedule):
        log.info('Received schedule: {0}'.format(worker_schedule))
        self.finish_time = datetime.now()
        temp_array = []
        for duration, temperature in worker_schedule:
            duration = self.duration_str_to_delta(duration)
            self.finish_time += duration
            temp_array.append((self.finish_time, temperature))
        schedule.every(3).seconds.do(self.do_some_work, temp_array)

    def do_some_work(self, temp_array):
        log.info('Boil stuff')
        if self.finish_time < datetime.now():
            log.info('Stopping')
            self._send_master_is_finished()
            self.stop_worker()
        else:
            for_how_long = None
            current_temp = None
            for time, temp in temp_array:
                if time > datetime.now():
                    for_how_long = time - datetime.now()
                    current_temp = temp
                    break
            log.info('Holding {0}°C for {1}'.format(current_temp, for_how_long))


if __name__ == "__main__":
    # Setup debug logging
    logging.getLogger().setLevel('DEBUG')
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(pathname)s:%(lineno)s: [%(levelname)s] %(message)s'))
    logging.getLogger().addHandler(h)

    worker = TemperatureWorker()
    worker.start_worker('asdasd', [
        ['0:00:15', 40.0],
        ['0:00:20', 50.0]
    ])
