import logging
import os
import time

from distribrewed_core.base.worker import BaseWorker
import telepot

log = logging.getLogger(__name__)


class DeviceWorker(BaseWorker):

    def __init__(self):
        super(DeviceWorker, self).__init__()
        self.devices = {}
        self.pausing_all_devices = False
        self.add_devices()
        self.start_all_devices()

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

    def add_device(self, name, device):
        self.inputs[name] = device

    def get_device(self, name):
        return self.devices[name]

    def start_all_devices(self):
        for device in self.devices.values:
            device.run_device()
        return

    def is_any_device_enabled(self):
        for device in self.devices.values():
            if device.enabled:
                return True
        return False

    def is_device_enabled(self, name):
        if len(self.devices) != 0:
            if self.devices[name].enabled:
                return True
        return False

    def pause_all_devices(self):
        if self.pausing_all_devices:
            return
        self.pausing_all_devices = True
        while self.is_any_device_enabled():
            log.debug('Trying to pause all passive devices...')
            for device in self.devices.values():
                device.pause_device()
            time.sleep(1)
        log.debug('All passive devices paused')
        self.pausing_all_devices = False

    def resume_all_devices(self):
        while self.pausing_all_devices:
            time.sleep(1)
        log.debug('Resuming all passive devices...')
        for device in self.devices.values():
            device.resume_device()
        log.debug('All passive devices resumed')
        self.pausing_all_devices = False

    def stop_all_devices(self):
        for device in self.devices.values():
            device.stop_device()

    def send_measurement(self, worker_measurement):
        pass # send to prometheus

    def start_worker(self, shcedule):
        pass

    def stop_worker(self):
        pass

    def pause_worker(self):
        pass

    def resume_worker(self):
        pass
