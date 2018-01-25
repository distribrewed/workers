#!/usr/bin python
import logging
import time

from workers.devices.device import Device, DEVICE_DEBUG_CYCLE_TIME

log = logging.getLogger(__name__)


class Tilt(Device):
    def __init__(self, name, io, active, cycle_time, callback, owner=None):
        Device.__init__(self, name, io, active, cycle_time, callback, owner)
        self.test_temperature = 0.0

    def init(self):
        pass

    def register(self):
        log.error(
            "Can not register tilt sensor at \"{0}\"".format(
                self.io))

    def write(self, value):
        pass

    def read(self):
        with self.read_write_lock:
            fo = open(self.io, mode='r')
            probe_crc = fo.readline()[-4:].rstrip()
            if probe_crc != 'YES':
                log.debug('Temp reading wrong, do not update temp, wait for next reading')
            else:
                probe_heat = fo.readline().split('=')[1]
            temperature = float(probe_heat) / 1000
            fo.close()
        return temperature

    def run_cycle(self):
        read_value = self.read()
        measured_value = float(read_value)
        self.do_callback(measured_value)
        time.sleep(self.cycle_time)


class SimulationTilt(Tilt):
    def __init__(self, name, io, active, cycle_time, callback, owner=None):
        Tilt.__init__(self, name, io, active, cycle_time, callback, owner)

    def register(self):
        return True

    def check(self):
        return True

    def read(self):
        return self.test_temperature

    def run_cycle(self):
        read_value = self.read()
        measured_value = float(read_value)
        self.do_callback(measured_value)
        time.sleep(DEVICE_DEBUG_CYCLE_TIME)
