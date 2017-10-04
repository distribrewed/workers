import logging

from workers.debug_temperature import DebugTemperatureWorker
from workers.temperature import TemperatureWorker

log = logging.getLogger(__name__)


class BoilWorker(TemperatureWorker):
    def __init__(self):
        super(TemperatureWorker, self).__init__()

    def _pid_calculate(self, measured_value):
        return 1.0  # Just boil as high as we can


class DebugBoilWorker(DebugTemperatureWorker):
    def __init__(self):
        super(DebugTemperatureWorker, self).__init__()

    def _pid_calculate(self, measured_value):
        return 1.0  # Just boil as high as we can


if __name__ == "__main__":
    # Setup debug logging
    logging.getLogger().setLevel('DEBUG')
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(pathname)s:%(lineno)s: [%(levelname)s] %(message)s'))
    logging.getLogger().addHandler(h)

    worker = DebugBoilWorker()
    worker.start_worker('Debug Boil Schedule', [
        ['0:00:15', 40.0],
        ['0:00:20', 50.0]
    ])
