#!/usr/bin python
import logging
import os
from datetime import timedelta as timedelta
from datetime import datetime as datetime

from devices.probe import SimulationProbe
from devices.ssr import SimulationSSR
from utils.pid import PID
from workers.temperature import TemperatureWorker

log = logging.getLogger(__name__)


class DebugTemperatureWorker(TemperatureWorker):
    DEBUG_INIT_TEMP = 60.0
    DEBUG_CYCLE_TIME = 10.0
    DEBUG_DELAY = 4
    DEBUG_WATTS = 5500.0  # 1 x 5500.0
    DEBUG_LITERS = 50.0
    DEBUG_COOLING = 0.002
    DEBUG_TIME_DIVIDER = 60
    DEBUG_TIMEDELTA = 10  # seconds

    def __init__(self):
        TemperatureWorker.__init__(self)
        self.test_temperature = self.DEBUG_INIT_TEMP
        self.debug_timer = timedelta(0)

    def _create_ssr(self, name, io, active, cycle_time, callback):
        return SimulationSSR(name, io, active, cycle_time, callback, self)

    def _create_thermometer(self, name, io, active, cycle_time, callback):
        return SimulationProbe(name, io, active, cycle_time, callback, self)

    def _setup_worker_schedule(self, worker_schedule):
        TemperatureWorker._setup_worker_schedule(self, worker_schedule)
        seconds = self.current_hold_time
        seconds /= self.DEBUG_TIME_DIVIDER
        self._get_device(self.thermometer_name).test_temperature = self.DEBUG_INIT_TEMP
        self.current_hold_time = seconds

    def _temperature_callback_event(self, measured_value, measurement):
        self.debug_timer += timedelta(seconds=self.DEBUG_TIMEDELTA)

    def _ssr_callback_event(self, measured_value, measurement):
        measurement["debug_timer"] = self.debug_timer
        try:
            self._get_device(self.thermometer_name).test_temperature = \
                PID.calc_heating(self.current_temperature,
                                 self.DEBUG_WATTS,
                                 measured_value,
                                 (float)(self._get_device(self.ssr_name).cycle_time),
                                 self.DEBUG_LITERS,
                                 self.DEBUG_COOLING,
                                 self.DEBUG_DELAY,
                                 self.DEBUG_INIT_TEMP)
        except Exception as e:
            log.debug('DebugTemperatureWorker unable to update test temperature for debug: {0}'.format(e.args[0]))


if __name__ == "__main__":
    # Setup debug logging
    logging.getLogger().setLevel('DEBUG')
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(pathname)s:%(lineno)s: [%(levelname)s] %(message)s'))
    logging.getLogger().addHandler(h)

    worker = DebugTemperatureWorker()
    worker.start_worker('Debug Temperature Schedule', [
        ['1:00:00', 60.0]
    ])
