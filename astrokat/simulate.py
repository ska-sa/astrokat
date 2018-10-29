# Provides skeleton for faking live system
import ephem
import logging
import sys

from collections import namedtuple
from datetime import datetime, timedelta

global simobserver
simobserver = ephem.Observer()


def setobserver(update):
    global simobserver
    simobserver = update


def sim_time(record, datefmt=None):
    now = simobserver.date.datetime()
    return now.strftime('%Y-%m-%d %H:%M:%SZ')


# Fake user logger prints out to screen
user_logger = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(message)s')
formatter.formatTime = sim_time
out_hdlr.setFormatter(formatter)
out_hdlr.setLevel(logging.INFO)
user_logger.addHandler(out_hdlr)
user_logger.setLevel(logging.INFO)


class Fakr(namedtuple('Fakr', 'priv_value')):
    def get_value(self):
        return self.priv_value


# Fake telescope connection
class verify_and_connect:
    def __init__(self, dummy):
        kwargs = vars(dummy)
        self.dry_run = True
        self._lst = kwargs['yaml']['observation_loop'][0]['LST'].split('-')[0].strip()
        self._sensors = self.fake_sensors(kwargs)
        self._session_cnt = 0
        self._ants = ['m011', 'm022', 'm033', 'm044']

    def __enter__(self):
        return self

    def __getattr__(self, key):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __repr__(self):
        return 'A representation'

    def __str__(self):
        return 'A string'

    def __iter__(self):
        Ant = namedtuple('Ant', ['name'])
        for ant in self._ants:
            yield Ant(ant)
        raise StopIteration

    def __exit__(self, type, value, traceback):
        pass

    def get(self, sensorname):
        return self._sensors[sensorname]

    def fake_sensors(self, kwargs):
        _sensors = {}
        if 'instrument' not in kwargs['yaml'].keys():
            return _sensors
        if kwargs['yaml']['instrument'] is None:
            return _sensors
        for key in kwargs['yaml']['instrument'].keys():
            fakesensor = 'sub_{}'.format(key)
            _sensors[fakesensor] = Fakr(kwargs['yaml']['instrument'][key])
        return _sensors


# Fake observation session
class start_session:
    def __init__(self, dummy_kat, **kwargs):
        self.kwargs = kwargs
        self.obs_params = kwargs
        # self.track_ = False
        # self.raster_scan_ = False
        # self.scan_ = False
        self.kat = dummy_kat
        self.start_time = (datetime.now() - datetime(1970, 1, 1)).total_seconds()
        self.time = self.start_time

    def __enter__(self):
        return self

    def __getattr__(self, key):
        self._key = key
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __str__(self):
        return 'A string'

    def __nonzero__(self):
        # return 1
        return True

    def __iter__(self):
        yield self
        raise StopIteration

    def __exit__(self, type, value, traceback):
        if self.track_:
            self.kat._session_cnt += 1
        if self.kat._session_cnt < len(self.kwargs['yaml']['observation_loop']):
            self.kat._lst = self.kwargs['yaml']['observation_loop'][self.kat._session_cnt]['LST'].split('-')[0].strip()

    def track(self, target, duration=0, announce=False):
        self.track_ = True
        self.time += duration
        now = simobserver.date.datetime()
        then = now + timedelta(seconds=duration)
        simobserver.date = ephem.Date(then)
        return True
        # return self.track_

    def raster_scan(self, target,
                    num_scans=3,
                    scan_duration=30.0,
                    scan_extent=6.0,
                    scan_spacing=0.5,
                    scan_in_azimuth=True,
                    projection='zenithal-equidistant',
                    announce=True):
        self.raster_scan_ = True
        duration = scan_duration * num_scans
        self.time += duration
        now = simobserver.date.datetime()
        then = now + timedelta(seconds=duration)
        simobserver.date = ephem.Date(then)
        return True
        # return self.raster_scan_

    def scan(self, target,
             duration=30.0,
             start=(-3.0, 0.0),
             end=(3.0, 0.0),
             index=-1,
             projection='zenithal-equidistant',
             announce=True):
        self.scan_ = True
        self.time += duration
        now = simobserver.date.datetime()
        then = now + timedelta(seconds=duration)
        simobserver.date = ephem.Date(then)
        # return self.scan_
        return True

# -fin-
