#!/usr/bin python
import logging
import os
from datetime import datetime as datetime
from datetime import timedelta as timedelta

from distribrewed_core.base.worker import ScheduleWorker
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

    EVENT_ON_TEMPERATURE_REACHED = "on_temperature_reached"

    def __init__(self):
        DeviceWorker.__init__(self)
        self.working = False
        self.simulation = False
        self.schedule = None
        self.enabled = False
        self.active = False
        self.hold_pause_timer = None
        self.paused = False
        self.pause_time = None
        self.ssr_name = os.environ.get(self.SSR_NAME)
        self.thermometer_name = os.environ.get(self.THERMOMETER_NAME)
        self.pid = None
        self.kpid = None
        self.current_temperature = 0.0
        self.current_set_temperature = 0.0
        self.current_hold_time = timedelta(minutes=0)
        self.start_time = None
        self.stop_time = None
        self.start_hold_timer = None
        self._setup_prometheus()

    @staticmethod
    def duration_str_to_delta(str):
        t = datetime.strptime(str, "%H:%M:%S")
        return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

    def _events(self):
        events = ScheduleWorker._events(self)
        events.append(self.EVENT_ON_TEMPERATURE_REACHED)
        return events

    def add_devices(self):
        ssr_name = os.environ.get(self.SSR_NAME)
        ssr_io = os.environ.get(self.SSR_IO)
        ssr_active = os.environ.get(self.SSR_ACTIVE, 'false').lower() in ['1', 'true']
        ssr_cycle_time = int(os.environ.get(self.SSR_CYCLE_TIME))
        ssr_callback = self._ssr_callback
        ssr = self._create_ssr(ssr_name, ssr_io, ssr_active, ssr_cycle_time, ssr_callback)
        self._add_device(ssr_name, ssr)

        therm_name = os.environ.get(self.THERMOMETER_NAME)
        therm_io = os.environ.get(self.THERMOMETER_IO)
        therm_active = os.environ.get(self.THERMOMETER_ACTIVE, 'false').lower() in ['1', 'true']
        therm_cycle_time = int(os.environ.get(self.THERMOMETER_CYCLE_TIME))
        therm_callback = self._temperature_callback
        thermometer = self._create_thermometer(therm_name, therm_io, therm_active, therm_cycle_time, therm_callback)
        self._add_device(therm_name, thermometer)

    def _create_ssr(self, name, io, active, cycle_time, callback):
        return SSR(name, io, active, cycle_time, callback, self)

    def _create_thermometer(self, name, io, active, cycle_time, callback):
        return Probe(name, io, active, cycle_time, callback, self)

    def _check_events(self):
        # The schedule ping this every 5 seconds
        pass

    def _calculate_finish_time(self):
        return self.start_hold_timer + (self.current_hold_time + self.pause_time)

    def _is_done(self):
        if self.start_hold_timer is None:
            return False
        finish = self._calculate_finish_time()
        now = datetime.now()
        if finish <= now:
            return True
        log.debug('Time until work done: {0}'.format(str(finish - now)))
        return False

    def _setup_worker_schedule(self, worker_schedule):
        log.debug('Receiving schedule...')
        self._pause_all_devices()
        self.current_set_temperature = float(worker_schedule[0][1])
        self.current_hold_time = self.duration_str_to_delta(worker_schedule[0][0])
        self.working = True
        self.start_time = datetime.now()
        self.start_hold_timer = None
        self.hold_pause_timer = None
        self.pause_time = timedelta(seconds=0)
        cycle_time = float(self._get_device(self.thermometer_name).cycle_time)
        if self.pid is None:
            self.pid = PID(None, self.current_set_temperature, cycle_time)
        else:
            self.pid = PID(self.pid.pid_params, self.current_set_temperature, cycle_time)
        self._resume_all_devices()
        #schedule.every(5).seconds.do(self._check_events)

    def stop_worker(self):
        self._get_device(self.ssr_name).write(0.0)
        self._pause_all_devices()
        self.working = False
        self.enabled = False
        self.stop_time = datetime.now()
        super(DeviceWorker, self).stop_worker()
        return True

    def pause_worker(self):
        log.debug('Pause {0}'.format(self))
        self._pause_all_devices()
        if self.start_hold_time is not None:
            self.hold_pause_timer = datetime.now()
        self.paused = True
        super(DeviceWorker, self).pause_worker()
        return True

    def resume_worker(self):
        log.info('Resume {0}'.format(self))
        if self.hold_pause_timer is not None and self.start_hold_time is not None:
            self.pause_time += (datetime.now() - self.hold_pause_timer)
        self.hold_pause_timer = None
        self._resume_all_devices()
        self.paused = False
        super(DeviceWorker, self).resume_worker()
        return True

    def _calculate_pid(self, measured_value):
        return self.pid.calculate(measured_value, self.current_set_temperature)

    def _create_measurement(self, name, device_name, value, set_point, work, remaining):
        measurement = {}
        measurement["name"] = name
        measurement["device_name"] = device_name
        measurement["value"] = value
        measurement["set_point"] = set_point
        measurement["work"] = work
        measurement["remaining"] = remaining
        return measurement

    def _temperature_callback_event(self, measured_value, measurement):
        pass

    def _ssr_callback_event(self, measured_value, measurement):
        pass

    def _temperature_callback(self, measured_value):
        try:
            calc = 0.0
            self.current_temperature = measured_value
            if self.pid is not None:
                calc = self._calculate_pid(measured_value)
                log.debug('{0} reports measured value {1} ({2}) and pid calculated {3}'.
                          format(self.name, round(measured_value, 1), measured_value, calc))
            else:
                log.debug('{0} reports measured value {1} ({2})'.format(self.name, round(measured_value, 1), measured_value))
            if self.start_hold_timer is None:
                work = 'Reaching temperature {:.2f}'.format(self.current_set_temperature)
            else:
                work = 'Holding temperature at {:.2f}'.format(self.current_set_temperature)
            measurement = self._create_measurement(
                self.name,
                self._get_device(self.thermometer_name).name,
                self.current_temperature,
                self.current_set_temperature,
                work,
                '{:.2f}'.format(self.current_set_temperature - self.current_temperature)
            )
            self._temperature_callback_event(measurement, measured_value)
            self._send_measurement(measurement)
            if self.working and self.start_hold_timer is None and round(measured_value, 1) >= self.current_set_temperature:
                self.start_hold_timer = datetime.now()
                self._send_event_to_master(self.EVENT_ON_TEMPERATURE_REACHED)
            if self._is_done():
                self.stop_worker()
                self._send_master_is_finished()
            elif self.pid is not None:
                self._get_device(self.ssr_name).write(calc)
        except Exception as e:
            log.error('TemperatureWorker unable to react to temperature update, shutting down: {0}'.format(e.args[0]))
            self._stop_all_devices()

    def _ssr_callback(self, heating_ratio):
        device = self._get_device(self.ssr_name)
        try:
            log.debug('{0} reports heating ratio of {1} percent'.format(self.name, heating_ratio))
            if self.start_hold_timer is None:
                work = 'Reaching temperature {:.2f}'.format(self.current_set_temperature)
                remaining = 'Unknown'
            else:
                work = 'Holding temperature at {:.2f}'.format(self.current_set_temperature)
                remaining = (self._calculate_finish_time() - datetime.now())
            measurement = self._create_measurement(
                self.name,
                device.name,
                heating_ratio,
                self.current_hold_time,
                work,
                remaining
            )
            self._ssr_callback_event(heating_ratio, measurement)
            self._send_measurement(measurement)
        except Exception as e:
            log.error('TemperatureWorker unable to react to heating update, shutting down: {0}'.format(e.args[0]))
            self._stop_all_devices()

    def _setup_prometheus(self):
        try:
            labels = ['name', "device_name", 'device_type']
            TemperatureWorker.PROM_HEATING_RATIO = Gauge('HEATING_RATIO', 'Heating ratio', labels)
            TemperatureWorker.PROM_TEMPERATURE = Gauge('TEMPERATURE', 'Temperature', labels)
        except ValueError:
            pass  # It is already defined

    def _send_measurement(self, worker_measurement):
        log.info('Send measurement triggered')
        if worker_measurement.get('device_name', '') == os.environ.get(self.SSR_NAME):
            TemperatureWorker.PROM_HEATING_RATIO.labels(self.name, self.ssr_name, 'SSR').set(worker_measurement.get('value', -1))
            log.info('Sending heating ratio to Prometheus')
        elif worker_measurement.get('device_name', '') == os.environ.get(self.THERMOMETER_NAME):
            TemperatureWorker.PROM_TEMPERATURE.labels(self.name, self.thermometer_name, 'Thermometer').set(worker_measurement.get('value', -1))
            log.info('Sending temperature to Prometheus')
        log.info('{0}: {1} - work {2} - remaining {3}'.format(
            worker_measurement.get('device_name'),
            worker_measurement.get('value'),
            worker_measurement.get('work'),
            worker_measurement.get('remaining')))

    def _get_grafana_rows(self):
        # 1. Define the panel in grafana
        # 2. View panel json i.e. https://imgur.com/HcsW9sf
        # 3. Paste JSON and convert to python dict
        # This example only has 1 row with 1 panel
        panels = [
            {
                "panels": [
                    {
                        "aliasColors": {},
                        "bars": False,
                        "dashLength": 10,
                        "dashes": False,
                        "datasource": "Distribrewed",
                        "fill": 1,
                        "id": 1,
                        "legend": {
                            "avg": False,
                            "current": False,
                            "max": False,
                            "min": False,
                            "show": True,
                            "total": False,
                            "values": False
                        },
                        "lines": True,
                        "linewidth": 1,
                        "links": [],
                        "nullPointMode": "null",
                        "percentage": False,
                        "pointradius": 5,
                        "points": False,
                        "renderer": "flot",
                        "seriesOverrides": [
                            {
                                "alias": "Heating Time",
                                "yaxis": 2
                            }
                        ],
                        "spaceLength": 10,
                        "span": 12,
                        "stack": False,
                        "steppedLine": False,
                        "targets": [
                            {
                                "expr": "TEMPERATURE{name=\"" + self.name + "\"}",
                                "format": "time_series",
                                "instant": False,
                                "interval": "",
                                "intervalFactor": 2,
                                "legendFormat": "Temperature",
                                "refId": "A",
                                "step": 1
                            },
                            {
                                "expr": "HEATING_RATIO{name=\"" + self.name + "\"}",
                                "format": "time_series",
                                "instant": False,
                                "intervalFactor": 2,
                                "legendFormat": "Heating Time",
                                "refId": "B",
                                "step": 1
                            }
                        ],
                        "thresholds": [],
                        "timeFrom": None,
                        "timeShift": None,
                        "title": self.name,
                        "tooltip": {
                            "shared": True,
                            "sort": 0,
                            "value_type": "individual"
                        },
                        "type": "graph",
                        "xaxis": {
                            "buckets": None,
                            "mode": "time",
                            "name": None,
                            "show": True,
                            "values": []
                        },
                        "yaxes": [
                            {
                                "format": "celsius",
                                "label": None,
                                "logBase": 1,
                                "max": None,
                                "min": None,
                                "show": True
                            },
                            {
                                "decimals": None,
                                "format": "percent",
                                "label": "",
                                "logBase": 1,
                                "max": None,
                                "min": None,
                                "show": True
                            }
                        ]
                    }
                ]
            }
        ]
        return panels
