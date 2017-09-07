#!/usr/bin python
import time

from workers.devices.device import Device, DEVICE_DEBUG_CYCLE_TIME
import logging
import os


log = logging.getLogger(__name__)


class Probe(Device):

    NAME =          "DEVICE_PROBE_NAME"
    IO =            "DEVICE_PROBE_IO"
    ACTIVE =        "DEVICE_PROBE_ACTIVE"
    CYCLE_TIME =    "DEVICE_PROBE_CYCLE_TIME"
    CALLBACK_NAME = "DEVICE_PROBE_CALLBACK_NAME"
    CALLBACK =      "DEVICE_PROBE_CALLBACK"

    def __init__(self, owner=None):
        self.test_temperature = 0.0
        Device.__init__(self, owner)
        self.name = os.environ.get(self.NAME)
        self.io = os.environ.get(self.IO)
        self.active = os.environ.get(self.ACTIVE)
        self.cycle_time = os.environ.get(self.CYCLE_TIME)
        self.callback_name = os.environ.get(self.CALLBACK_NAME)
        self.callback = os.environ.get(self.CALLBACK)

    def init(self):
        pass

    def register(self):
        log.error("Can not register probe at \"{0}\", try to run \"sudo modprobe w1-gpio && sudo modprobe w1_therm\" in commandline or check your probe connections".format(self.io))

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
            temperature = float(probe_heat)/1000
            fo.close()
        return temperature

    def run_cycle(self):
        read_value = self.read()
        measured_value = float(read_value)
        self.do_callback(measured_value)
        time.sleep(self.cycle_time)

class SimulationProbe(Probe):
    def __init__(self, owner=None):
        super(Probe, self).__init__()

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