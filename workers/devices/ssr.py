#!/usr/bin python
import logging
import re
import time

from workers.devices.device import Device, DEVICE_DEBUG_CYCLE_TIME

log = logging.getLogger(__name__)


class SSR(Device):

    def __init__(self, name, io, active, cycle_time, callback, owner = None):
        Device.__init__(self, name, io, active, cycle_time, callback, owner)
        self.on_percent = 0.0
        self.last_on_time = 0.0

    def init(self):
        pass

    def register(self):
        found = re.search('\d{1,2}', self.io)
        gpio_numb = found.group()
        #log.debug(gpio_numb)

        #log.debug(self.io[:16]+"export")
        #log.debug(self.io[:23]+"direction")

        try:
            fo = open(self.io[:16]+"export", mode='w')
            fo.write(gpio_numb)
            fo.close()
            fo = open(self.io[:23]+"direction", mode='w')
            fo.write("out")
            fo.close()
            return True
        except Exception:
            raise Exception("Cannot register gpio{0}".format(gpio_numb))
        return False

    def write(self, value):
        self.on_percent = value
        if self.on_percent > 1.0:
            self.on_percent = 1.0
        elif self.on_percent < 0.0:
            self.on_percent = 0.0
        return True

    def set_ssr_state(self, on = False):
        with self.read_write_lock:
            fo = open(self.io, mode='w')
            if on:
                fo.write('1')
            else:
                fo.write('0')
            fo.close()
            ok = True
        return ok

    def read(self):
        with self.read_write_lock:
            fo = open(self.io, mode='r')
            value = fo.read()
            fo.close()
        return value

    def run_cycle(self):
        # grab the current value if it should be changed during the cycle
        on_percent = self.on_percent
        on_time = on_percent * (float)(self.cycle_time)
        if self.on_percent > 0.0:
            self.set_ssr_state(True)
            time.sleep(on_time)
        if self.on_percent < 1.0:
            self.set_ssr_state(False)
            time.sleep((1.0-on_percent)*(float)(self.cycle_time))
        self.do_callback(on_time)

class SimulationSSR(SSR):
    def __init__(self, name, io, active, cycle_time, callback, owner = None):
        SSR.__init__(self, name, io, active, cycle_time, callback, owner)

    def register(self):
        return True

    def check(self):
        return True

    def read(self):
        return 1

    def run_cycle(self):
        on_percent = self.on_percent
        on_time = on_percent * (float)(self.cycle_time)
        time.sleep(DEVICE_DEBUG_CYCLE_TIME)
        self.do_callback(on_time)
        return

    def set_ssr_state(self, on = False):
        return True