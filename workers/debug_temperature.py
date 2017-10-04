#!/usr/bin python
import logging
import os
from datetime import datetime as datetime
from datetime import timedelta as timedelta

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

    def add_devices(self):
        mash_name = os.environ.get(self.SSR_NAME)
        mash_io = os.environ.get(self.SSR_IO)
        mash_active = os.environ.get(self.SSR_ACTIVE, 'false').lower() in ['1', 'true']
        mash_cycle_time = os.environ.get(self.SSR_CYCLE_TIME)
        mash_callback = self._mash_debug_heating_callback
        mash = SimulationSSR(mash_name, mash_io, mash_active, mash_cycle_time, mash_callback, self)
        self._add_device(mash_name, mash)

        therm_name = os.environ.get(self.THERMOMETER_NAME)
        therm_io = os.environ.get(self.THERMOMETER_IO)
        therm_active = os.environ.get(self.THERMOMETER_ACTIVE, 'false').lower() in ['1', 'true']
        therm_cycle_time = os.environ.get(self.THERMOMETER_CYCLE_TIME)
        therm_callback = self._mash_debug_temperature_callback
        thermometer = SimulationProbe(therm_name, therm_io, therm_active, therm_cycle_time, therm_callback, self)
        self._add_device(therm_name, thermometer)

    def _setup_worker_schedule(self, worker_schedule):
        try:
            log.debug('Receiving schedule...')
            self.working = True
            self.hold_timer = None
            self.hold_pause_timer = None
            self.pause_time = timedelta(seconds=0)
        except Exception as e:
            log.debug('DebugTemperatureWorker failed to start work: {0}'.format(e.args[0]))
            self._stop_all_devices()
            return
        self._pause_all_devices()
        self.current_set_temperature = float(worker_schedule[0][1])
        self.hold_timer = None
        self.hold_pause_timer = None
        seconds = self.duration_str_to_delta(worker_schedule[0][0])
        seconds /= self.DEBUG_TIME_DIVIDER
        self._get_device(self.thermometer_name).test_temperature = self.DEBUG_INIT_TEMP
        self.current_hold_time = seconds
        cycle_time = float(self._get_device(self.thermometer_name).cycle_time)
        if self.pid is None:
            self.pid = PID(None, self.current_set_temperature, cycle_time)
        else:
            self.pid = PID(self.pid.pid_params, self.current_set_temperature, cycle_time)
        self._resume_all_devices()

    def _mash_debug_temperature_callback(self, measured_value):
        try:
            calc = 0.0
            if self.pid is not None:
                calc = self._calculate_pid(measured_value)
                log.debug('{0} reports measured value {1} and pid calculated {2}'.
                          format(self.name, measured_value, calc))
            else:
                log.debug('{0} reports measured value {1}'.format(self.name, measured_value))
            self.current_temperature = measured_value
            measurement = {}
            measurement["name"] = self.name
            measurement["device_name"] = self._get_device(self.thermometer_name).name
            measurement["value"] = self.current_temperature
            measurement["set_point"] = self.current_set_temperature
            if self.hold_timer is None:
                measurement["work"] = 'Current temperature'
                measurement["remaining"] = '{:.2f}'.format(self.current_temperature)
            else:
                measurement["work"] = 'Mashing'
                # measurement["remaining"] = self.remaining_time_info()
            self.test_temperature = self.current_temperature
            measurement["debug_timer"] = self.debug_timer
            self.debug_timer += timedelta(seconds=self.DEBUG_TIMEDELTA)
            self._send_measurement(measurement)
            if self.working and self.hold_timer is None and measured_value >= self.current_set_temperature:
                self.hold_timer = datetime.now()
            if self.is_done():
                self._finish()
            elif self.pid is not None:
                self._get_device(self.ssr_name).write(calc)
        except Exception as e:
            log.error('DebugTemperatureWorker unable to react to temperature update, shutting down: {0}'.format(e.args[0]))
            self._stop_all_devices()

    def _mash_debug_heating_callback(self, heating_time):
        try:
            log.debug('{0} reports heating time of {1} seconds'.format(self.name, heating_time))
            ssr_device = self._get_device(self.ssr_name)  # type: SSR
            measurement = {}
            measurement["name"] = self.name
            measurement["device_name"] = ssr_device.name
            measurement["value"] = heating_time
            measurement["set_point"] = ssr_device.cycle_time
            if self.hold_timer is None:
                measurement["work"] = 'Heating left'
                measurement["remaining"] = '{:.2f}'.format(self.current_set_temperature - self.current_temperature)
            else:
                measurement["work"] = 'Holding temperature'
                measurement["remaining"] = '{:.2f} -> {:.2f} ({:+.2f})'.format(
                    self.current_temperature,
                    self.current_set_temperature,
                    (self.current_temperature - self.current_set_temperature))
            measurement["debug_timer"] = self.debug_timer
            self._send_measurement(measurement)
            try:
                self._get_device(self.thermometer_name).test_temperature = \
                    PID.calc_heating(self.current_temperature,
                                     self.DEBUG_WATTS,
                                     heating_time,
                                     (float)(ssr_device.cycle_time),
                                     self.DEBUG_LITERS,
                                     self.DEBUG_COOLING,
                                     self.DEBUG_DELAY,
                                     self.DEBUG_INIT_TEMP)
            except Exception as e:
                log.debug('DebugTemperatureWorker unable to update test temperature for debug: {0}'.format(e.args[0]))
        except Exception as e:
            log.error('DebugTemperatureWorker unable to react to heating update, shutting down: {0}'.format(e.args[0]))
            self._stop_all_devices()


if __name__ == "__main__":
    # Setup debug logging
    logging.getLogger().setLevel('DEBUG')
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(pathname)s:%(lineno)s: [%(levelname)s] %(message)s'))
    logging.getLogger().addHandler(h)

    worker = DebugTemperatureWorker()
    worker.start_worker('Debug Temperature Schedule', [
        ['0:30:00', 65.0]
    ])
