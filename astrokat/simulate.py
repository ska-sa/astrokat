# Provides skeleton for faking live system
import ephem
import logging
import sys
import numpy
import time

from collections import namedtuple
from datetime import timedelta
from utility import get_lst, datetime2timestamp

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
        self._lst, _ = get_lst(kwargs['yaml']['observation_loop'][0]['LST'])
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
        self.kat = dummy_kat
        # simobserver.horizon = ephem.degrees(str(kwargs['horizon']))
        self.start_time = datetime2timestamp(simobserver.date.datetime())
        self.time = self.start_time
        self.katpt_current = None

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
        return True

    def __iter__(self):
        yield self
        raise StopIteration

    def __exit__(self, type, value, traceback):
        if self.track_:
            self.kat._session_cnt += 1
        if self.kat._session_cnt < len(self.kwargs['yaml']['observation_loop']):
            # self.kat._lst =            self.kwargs['yaml']['observation_loop'][self.kat._session_cnt]['LST'].split('-')[0].strip()
            self.kat._lst, _ = get_lst(self.kwargs['yaml']['observation_loop'][self.kat._session_cnt]['LST'])

    def _update_fake_time_(self, addtime):
        self.time += addtime
        now = simobserver.date.datetime()
        then = now + timedelta(seconds=addtime)
        simobserver.date = ephem.Date(then)

    def _fake_slew_(self, target):
        slew_time = 0
        if not (target == self.katpt_current):
            if self.katpt_current is None:
                slew_time = 45.  # s
            else:
                # if verbose: user_logger.info('Slewing to {}'.format(target.name))
                slew_time = self.slew_time(target)
        return slew_time

    def track(self, target, duration=0, announce=False):
        self._update_fake_time_(self._fake_slew_(target))
        # if duration > 0:
            # if verbose: user_logger.info('Tracking {}'.format(target.name))
        self._update_fake_time_(duration)
        self.katpt_current = target
        return True

    def raster_scan(self, target,
                    num_scans=3,
                    scan_duration=30.0,
                    scan_extent=6.0,
                    scan_spacing=0.5,
                    scan_in_azimuth=True,
                    projection='zenithal-equidistant',
                    announce=True):
        duration = scan_duration * num_scans
        self.time += duration
        now = simobserver.date.datetime()
        then = now + timedelta(seconds=duration)
        simobserver.date = ephem.Date(then)
        return True

    def scan(self, target,
             duration=30.0,
             start=(-3.0, 0.0),
             end=(3.0, 0.0),
             index=-1,
             projection='zenithal-equidistant',
             announce=True):
        self.time += duration
        now = simobserver.date.datetime()
        then = now + timedelta(seconds=duration)
        simobserver.date = ephem.Date(then)
        return True

    def slew_time(self, target):
        slew_speed = 2.  # degrees / sec
        self.katpt_current.body.compute(self.katpt_current.antenna.observer)
        target.body.compute(target.antenna.observer)
        separation_angle = ephem.separation(self.katpt_current.body,
                                            target.body)
        # separation_angle = first_target.separation(second_target,
        #                                            timestamp=timestamp,
        #                                            antenna=antenna)
        duration = numpy.degrees(separation_angle)/slew_speed
        return duration

# -fin-
