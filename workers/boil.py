#!/usr/bin python
import os
import time
from datetime import timedelta as timedelta
from prometheus_client import Counter
import logging
from device import DeviceWorker
from devices.probe import Probe
from devices.ssr import SSR
from utils.pid import PID

log = logging.getLogger(__name__)

class BoilWorker(DeviceWorker):

    BOILER_NAME =               "BOILER_NAME"
    BOILER_IO =                 "BOILER_IO"
    BOILER_ACTIVE =             "BOILER_ACTIVE"
    BOILER_CYCLE_TIME =         "BOILER_CYCLE_TIME"
    THERMOMETER_NAME =           "THERMOMETER_NAME"
    THERMOMETER_IO =             "THERMOMETER_IO"
    THERMOMETER_ACTIVE =         "THERMOMETER_ACTIVE"
    THERMOMETER_CYCLE_TIME =     "THERMOMETER_CYCLE_TIME"

    def __init__(self):
        DeviceWorker.__init__(self)
        self.working = False
        self.simulation = False
        self.schedule = None
        self.enabled = False
        self.active = False
        self.current_hold_time = timedelta(minutes=0)
        self.hold_timer = None
        self.hold_pause_timer = None
        self.pause_time = 0.0
        self.session_detail_id = 0
        self.boiler_name = os.environ.get(self.BOILER_NAME)
        self.thermometer_name = os.environ.get(self.THERMOMETER_NAME)
        self.current_temperature = 0.0
        self.current_set_temperature = 0.0

    def add_devices(self):
        boil_name = os.environ.get(self.BOILER_NAME)
        boil_io = os.environ.get(self.BOILER_IO)
        boil_active = os.environ.get(self.BOILER_ACTIVE)
        boil_cycle_time = os.environ.get(self.BOILER_CYCLE_TIME)
        boil_callback = os.environ.get(self.boil_heating_callback)
        boiler = SSR(boil_name, boil_io, boil_active, boil_cycle_time, boil_callback, self)
        self.add_device(boil_name, boiler)

        therm_name = os.environ.get(self.THERMOMETER_NAME)
        therm_io = os.environ.get(self.THERMOMETER_IO)
        therm_active = os.environ.get(self.THERMOMETER_ACTIVE)
        therm_cycle_time = os.environ.get(self.THERMOMETER_CYCLE_TIME)
        therm_callback = os.environ.get(self.boil_temperature_callback())
        thermometer = Probe(therm_name, therm_io, therm_active, therm_cycle_time, therm_callback, self)
        self.add_device(therm_name, thermometer)

    def start_worker(self, shedule):
        log.debug('Starting {0}'.format(self), True)
        try:
            log.debug('Receiving boil schedule...')
            self.working = True
            self.hold_timer = None
            self.hold_pause_timer = None
            self.pause_time = timedelta(seconds=0)
        except Exception as e:
            log.debug('Boil worker failed to start work: {0}'.format(e.args[0]))
            self.stop_all_devices()
            return
        self.pause_all_devices()
        self.current_set_temperature = float(shedule["target"])
        self.hold_timer = None
        self.hold_pause_timer = None
        seconds = float(shedule.hold_time) * float(shedule.time_unit_seconds)
        self.current_hold_time = timedelta(seconds=seconds)
        cycle_time = float(self.get_device[self.thermometer_name].cycle_time)
        self.resume_all_devices()
        return True

    def stop_worker(self):
        self.get_device[self.boiler_name].write(0.0)
        self.stop_all_devices()
        self.enabled = False
        return True

    def pause_worker(self):
        log.debug('Pause {0}'.format(self), True)
        self.pause_all_devices()
        self.hold_pause_timer = time.now()
        return True

    def resume_worker(self):
        log.info('Resume {0}'.format(self), True)
        self.pause_time += (time.now() - self.hold_pause_timer)
        self.resume_all_devices()
        return True

    def boil_temperature_callback(self, measured_value):
        try:
            calc = 1.0
            log.debug('{0} reports measured value {1}'.format(self.name, measured_value))
            self.current_temperature = measured_value
            therm = self.get_device(self.thermometer_name)
            measurement = {}
            measurement["name"] = self.name
            measurement["device_name"] = therm.name
            measurement["value"] = self.current_temperature
            measurement["set_point"] = self.current_set_temperature
            if self.hold_timer is None:
                measurement["work"] = 'Current temperature'
                measurement["remaining"] = '{:.2f}'.format(self.current_temperature)
            else:
                measurement["work"] = 'Boiling left'
                measurement["remaining"] = self.remaining_time_info()
            self.send_measurement(measurement)
            # Failsafe - start hold timer at 99.0 if reaching 100.0 is difficult
            # due to thermal sensor placement
            if self.working and self.hold_timer is None and \
                    (measured_value >= self.current_set_temperature or measured_value >= 99.0):
                self.hold_timer = time.now()
            if self.is_done():
                self.finish()
            else:
                self.get_device[self.boiler_name].write(calc)
        except Exception as e:
            log.error('Boil worker unable to react to temperature update, shutting down: {0}'.format(e.args[0]))
            self.stop_all_devices()

    def boil_heating_callback(self, heating_time):
        try:
            log.debug('{0} reports heating time of {1} seconds'.format(self.name, heating_time))
            boiler = self.devices[self.boiler_name]
            measurement = {}
            measurement["name"] = self.name
            measurement["device_name"] = boiler.name
            measurement["value"] = heating_time
            measurement["set_point"] = boiler.cycle_time
            if self.hold_timer is None:
                measurement["work"] = 'Bringing to boil'
                measurement["remaining"] = '{:.2f}'.format(self.current_set_temperature - self.current_temperature)
            else:
                measurement["work"] = 'Holding boil'
                measurement["remaining"] = '{:.2f} -> {:.2f} ({:+.2f})'.format(
                    self.current_temperature,
                    self.current_set_temperature,
                    self.current_temperature - self.current_set_temperature)
            self.send_measurement(measurement)
        except Exception as e:
            log.error('Boil worker unable to react to heating update, shutting down: {0}'.format(e.args[0]))
            self.stop_all_devices()


class DebugBoilWorker(BoilWorker):

    BOIL_DEBUG_INIT_TEMP = 60.0
    BOIL_DEBUG_CYCLE_TIME = 10.0
    BOIL_DEBUG_DELAY = 4
    BOIL_DEBUG_WATTS = 5500.0  # 1 x 5500.0
    BOIL_DEBUG_LITERS = 50.0
    BOIL_DEBUG_COOLING = 0.002
    BOIL_DEBUG_TIME_DIVIDER = 60
    BOIL_DEBUG_TIMEDELTA = 10  # seconds

    def __init__(self, name):
        BoilWorker.__init__(self, name)
        self.test_temperature = self.BOIL_DEBUG_INIT_TEMP
        self.debug_timer = None

    def start_worker(self, shedule):
        log.debug('Starting {0}'.format(self), True)
        try:
            log.debug('Receiving boil schedule...')
            self.working = True
            self.hold_timer = None
            self.hold_pause_timer = None
            self.pause_time = timedelta(seconds=0)
        except Exception as e:
            log.debug('Boil worker failed to start work: {0}'.format(e.args[0]))
            self.stop_all_devices()
            return
        self.pause_all_devices()
        self.current_set_temperature = float(shedule["target"])
        self.hold_timer = None
        self.hold_pause_timer = None
        seconds = float(shedule.hold_time) * float(shedule.time_unit_seconds)
        seconds /= self.BOIL_DEBUG_TIME_DIVIDER
        self.get_device[self.thermometer_name].test_temperature = self.BOIL_DEBUG_INIT_TEMP
        self.current_hold_time = timedelta(seconds=seconds)
        cycle_time = float(self.get_device[self.thermometer_name].cycle_time)
        self.resume_all_devices()
        return True

    def boil_temperature_callback(self, measured_value):
        try:
            calc = 1.0
            log.debug('{0} reports measured value {1}'.format(self.name, measured_value))
            self.current_temperature = measured_value
            therm = self.get_device(self.thermometer_name)
            measurement = {}
            measurement["name"] = self.name
            measurement["device_name"] = therm.name
            measurement["value"] = self.current_temperature
            measurement["set_point"] = self.current_set_temperature
            if self.hold_timer is None:
                measurement["work"] = 'Current temperature'
                measurement["remaining"] = '{:.2f}'.format(self.current_temperature)
            else:
                measurement["work"] = 'Boiling left'
                measurement["remaining"] = self.remaining_time_info()
            self.test_temperature = self.current_temperature
            measurement["debug_timer"] = self.debug_timer
            self.debug_timer += timedelta(seconds = self.BOIL_DEBUG_TIMEDELTA)
            self.send_measurement(measurement)
            # Failsafe - start hold timer at 99.0 if reaching 100.0 is difficult
            # due to thermal sensor placement
            if self.working and self.hold_timer is None and \
                    (measured_value >= self.current_set_temperature or measured_value >= 99.0):
                self.hold_timer = time.now()
            if self.is_done():
                self.finish()
            else:
                self.get_device[self.boiler_name].write(calc)
        except Exception as e:
            log.error('Boil worker unable to react to temperature update, shutting down: {0}'.format(e.args[0]))
            self.stop_all_devices()

    def boil_heating_callback(self, heating_time):
        try:
            log.debug('{0} reports heating time of {1} seconds'.format(self.name, heating_time))
            boiler = self.devices[self.boiler_name]
            measurement = {}
            measurement["name"] = self.name
            measurement["device_name"] = boiler.name
            measurement["value"] = heating_time
            if self.hold_timer is None:
                measurement["work"] = 'Bringing to boil'
                measurement["remaining"] = '{:.2f}'.format(self.current_set_temperature - self.current_temperature)
            else:
                measurement["work"] = 'Holding boil'
                measurement["remaining"] = '{:.2f} -> {:.2f} ({:+.2f})'.format(
                    self.current_temperature,
                    self.current_set_temperature,
                    self.current_temperature - self.current_set_temperature)
            measurement["debug_timer"] = self.debug_timer
            self.send_measurement(measurement)
            try:
                self.devices[self.thermometer_name].test_temperature = \
                    PID.calc_heating(self.current_temperature,
                                     self.BOIL_DEBUG_WATTS,
                                     heating_time,
                                     boiler.cycle_time,
                                     self.BOIL_DEBUG_LITERS,
                                     self.BOIL_DEBUG_COOLING,
                                     self.BOIL_DEBUG_DELAY,
                                     self.BOIL_DEBUG_INIT_TEMP)
            except Exception as e:
                log.debug('Boil worker unable to update test temperature for debug: {0}'.format(e.args[0]))
        except Exception as e:
            log.error('Boil worker unable to react to heating update, shutting down: {0}'.format(e.args[0]))
            self.stop_all_devices()