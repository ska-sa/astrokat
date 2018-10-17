# Provides skeleton for faking live system
import ephem
import logging
import sys

from collections import namedtuple
from datetime import timedelta

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
        self._ants = kwargs['noise_pattern'] if 'noise_pattern' in kwargs else []
        self._lst = kwargs['template']['observation_loop'][0]['LST'].split('-')[0].strip()
        self._sensors = self.fake_sensors(kwargs)
        self._session_cnt = 0

    def __enter__(self):
        return self

    def __getattr__(self, key):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __str__(self):
        return 'A string'

    def __iter__(self):
        Ant = namedtuple('Ant', ['name'])
        yield Ant(self._ants)
        raise StopIteration

    def __exit__(self, type, value, traceback):
        pass

    def get(self, sensorname):
        return self._sensors[sensorname]

    def fake_sensors(self, kwargs):
        _sensors = {}
        if not 'instrument' in kwargs['template'].keys():
            return _sensors
        if kwargs['template']['instrument'] is None:
            return _sensors
        for key in kwargs['template']['instrument'].keys():
            fakesensor = 'sub_{}'.format(key)
            _sensors[fakesensor] = Fakr(kwargs['template']['instrument'][key])
        return _sensors


# Fake observation session
class start_session:
    def __init__(self, dummy_kat, **kwargs):
        self.kwargs = kwargs
        self.track_ = False
        self.kat = dummy_kat

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
        return 1

    def __iter__(self):
        yield self
        raise StopIteration

    def __exit__(self, type, value, traceback):
        if self.track_:
            self.kat._session_cnt += 1
        if self.kat._session_cnt < len(self.kwargs['template']['observation_loop']):
            self.kat._lst = self.kwargs['template']['observation_loop'][self.kat._session_cnt]['LST'].split('-')[0].strip()

    def track(self, target, duration=0, announce=False):
        self.track_ = True
        now = simobserver.date.datetime()
        then = now + timedelta(seconds=duration)
        simobserver.date = ephem.Date(then)
        return self.track_

# -fin-
