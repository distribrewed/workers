import logging
import os
import time

import schedule
from distribrewed_core.base.worker import ScheduleWorker

log = logging.getLogger(__name__)


class DeviceWorker(ScheduleWorker):

    def __init__(self):
        super(DeviceWorker, self).__init__()
        self.devices = {}
        self.pausing_all_devices = False
        self.add_devices()
        self._start_all_devices()

    def worker_info(self):
        return {
            'id': self.name,
            'ip': self.ip,
            'type': self.__class__.__name__,
            'prometheus_scrape_port': self.prom_port,
            'number_of_devices': len(self.devices.values)
        }

    def add_devices(self):
        pass

    def _add_device(self, name, device):
        self.devices[name] = device

    def _get_device(self, name):
        return self.devices[name]

    def _start_all_devices(self):
        for name, device in self.devices.items():
            device.run_device()
        return

    def _is_any_device_enabled(self):
        for name, device in self.devices.items():
            if device.enabled:
                return True
        return False

    def _is_device_enabled(self, name):
        if len(self.devices) != 0:
            if self.devices[name].enabled:
                return True
        return False

    def _pause_all_devices(self):
        if self.pausing_all_devices:
            return
        self._pausing_all_devices = True
        while self._is_any_device_enabled():
            log.debug('Trying to pause all passive devices...')
            for device in self.devices.values():
                device.pause_device()
            time.sleep(1)
        log.debug('All passive devices paused')
        self._pausing_all_devices = False

    def _resume_all_devices(self):
        while self.pausing_all_devices:
            time.sleep(1)
        log.debug('Resuming all passive devices...')
        for device in self.devices.values():
            device.resume_device()
        log.debug('All passive devices resumed')
        self.pausing_all_devices = False

    def _stop_all_devices(self):
        for device in self.devices.values():
            device.stop_device()

    def _send_measurement(self, worker_measurement):
        pass # TODO: send to prometheus

    def start_worker(self, shcedule):
        pass

    def stop_worker(self):
        pass

    def pause_worker(self):
        pass

    def resume_worker(self):
        pass
