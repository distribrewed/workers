#!/usr/bin python
import logging
import os
import time
from datetime import datetime as datetime
from datetime import timedelta as timedelta

import schedule
from prometheus_client import Gauge

from device import DeviceWorker
from devices.probe import Probe
from devices.ssr import SSR
from utils.pid import PID

log = logging.getLogger(__name__)


class TemperatureWorker(DeviceWorker):
    SSR_NAME = "SSR_NAME"
    SSR_IO = "SSR_IO"
    SSR_ACTIVE = "SSR_ACTIVE"
    SSR_CYCLE_TIME = "SSR_CYCLE_TIME"
    THERMOMETER_NAME = "THERMOMETER_NAME"
    THERMOMETER_IO = "THERMOMETER_IO"
    THERMOMETER_ACTIVE = "THERMOMETER_ACTIVE"
    THERMOMETER_CYCLE_TIME = "THERMOMETER_CYCLE_TIME"

    def __init__(self):
        DeviceWorker.__init__(self)
        try:
            TemperatureWorker.PROM_HEATING_TIME = Gauge('HEATING_TIME', 'Heating time')
            TemperatureWorker.PROM_TEMPERATURE = Gauge('TEMPERATURE', 'Temperature')
        except ValueError:
            pass  # It is already defined
        self.working = False
        self.simulation = False
        self.schedule = None
        self.enabled = False
        self.active = False
        self.current_hold_time = timedelta(minutes=0)
        self.hold_timer = None
        self.hold_pause_timer = None
        self.paused = False
        self.pause_time = 0.0
        self.session_detail_id = 0
        self.ssr_name = os.environ.get(self.SSR_NAME)
        self.thermometer_name = os.environ.get(self.THERMOMETER_NAME)
        self.pid = None
        self.kpid = None
        self.current_temperature = 0.0
        self.current_set_temperature = 0.0

    @staticmethod
    def duration_str_to_delta(str):
        t = datetime.strptime(str, "%H:%M:%S")
        return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    def add_devices(self):
        mash_name = os.environ.get(self.SSR_NAME)
        mash_io = os.environ.get(self.SSR_IO)
        mash_active = os.environ.get(self.SSR_ACTIVE, 'false').lower() in ['1', 'true']
        mash_cycle_time = os.environ.get(self.SSR_CYCLE_TIME)
        mash_callback = self._mash_heating_callback
        mash = SSR(mash_name, mash_io, mash_active, mash_cycle_time, mash_callback, self)
        self._add_device(mash_name, mash)

        therm_name = os.environ.get(self.THERMOMETER_NAME)
        therm_io = os.environ.get(self.THERMOMETER_IO)
        therm_active = os.environ.get(self.THERMOMETER_ACTIVE, 'false').lower() in ['1', 'true']
        therm_cycle_time = os.environ.get(self.THERMOMETER_CYCLE_TIME)
        therm_callback = self._mash_temperature_callback
        thermometer = Probe(therm_name, therm_io, therm_active, therm_cycle_time, therm_callback, self)
        self._add_device(therm_name, thermometer)

    def _info(self):
        return {
            'schedule_id': self.schedule_id,
            'is_running': self.working,
            'is_paused': self.paused,
        }

    def _check_events(self):
        # The schedule ping this every 5 seconds
        pass

    def _finish(self):
        try:
            self._pause_all_devices()
            self.working = False
            return True
        except Exception as e:
            log.error('Error in cleaning up after work: {0}'.format(e.args[0]), True)
            return False

    def is_done(self):
        if self.hold_timer is None:
            return False
        finish = self.hold_timer + self.current_hold_time
        if finish is None:
            return False
        if finish >= datetime.now():
            return True
        log.debug('Time until work done: {0}'.format(work - finish), True)
        return False

    def _setup_worker_schedule(self, worker_schedule):
        try:
            log.debug('Receiving schedule...')
            self.working = True
            self.hold_timer = None
            self.hold_pause_timer = None
            self.pause_time = timedelta(seconds=0)
        except Exception as e:
            log.debug('Mash worker failed to start work: {0}'.format(e.args[0]))
            self._stop_all_devices()
            self.register()
            return
        self._pause_all_devices()
        self.current_set_temperature = float(worker_schedule[0][1])
        self.hold_timer = None
        self.hold_pause_timer = None
        seconds = self.duration_str_to_delta(worker_schedule[0][0])
        self.current_hold_time = seconds
        cycle_time = float(self._get_device(self.thermometer_name).cycle_time)
        if self.pid is None:
            self.pid = PID(None, self.current_set_temperature, cycle_time)
        else:
            self.pid = PID(self.pid.pid_params, self.current_set_temperature, cycle_time)
        self._resume_all_devices()
        schedule.every(5).seconds.do(self._check_events)

    def stop_worker(self):
        self._get_device(self.ssr_name).write(0.0)
        self.pause_all_devices()
        self.working = False
        self.enabled = False
        super(DeviceWorker, self).stop_worker()
        return True

    def pause_worker(self):
        log.debug('Pause {0}'.format(self), True)
        self._pause_all_devices()
        self.hold_pause_timer = datetime.now()
        self.paused = True
        super(DeviceWorker, self).pause_worker()
        return True

    def resume_worker(self):
        log.info('Resume {0}'.format(self), True)
        if self.hold_pause_timer is None:
            self.pause_time = timedelta(0)
        else:
            self.pause_time += (datetime.now() - self.hold_pause_timer)
        self._resume_all_devices()
        self.paused = False
        super(DeviceWorker, self).resume_worker()
        return True

    def _calculate_pid(self, measured_value):
        return self.pid.calculate(measured_value, self.current_set_temperature)

    def _mash_temperature_callback(self, measured_value):
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
            self._send_measurement(measurement)
            if self.working and self.hold_timer is None and measured_value >= self.current_set_temperature:
                self.hold_timer = time.now()
            if self.is_done():
                self._finish()
            elif self.pid is not None:
                self._get_device(self.ssr_name).write(calc)
        except Exception as e:
            log.error('TemperatureWorker unable to react to temperature update, shutting down: {0}'.format(e.args[0]))
            self._stop_all_devices()

    def _mash_heating_callback(self, heating_time):
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
            self._send_measurement(measurement)
        except Exception as e:
            log.error('TemperatureWorker unable to react to heating update, shutting down: {0}'.format(e.args[0]))
            self._stop_all_devices()

    def _send_measurement(self, worker_measurement):
        if worker_measurement.get('device_name', '') == os.environ.get(self.SSR_NAME):
            TemperatureWorker.PROM_HEATING_TIME.set(worker_measurement.get('value', -1))
        elif worker_measurement.get('device_name', '') == os.environ.get(self.THERMOMETER_NAME):
            TemperatureWorker.PROM_TEMPERATURE.set(worker_measurement.get('value', -1))
