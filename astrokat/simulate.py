"""Provides skeleton for mimicking a live MeerKAT telescope system."""
from __future__ import division
from __future__ import absolute_import

import ephem
import logging
import numpy
import time
import sys
import katpoint

from collections import namedtuple

from .utility import get_lst, datetime2timestamp, timestamp2datetime

global simobserver
simobserver = ephem.Observer()

_DEFAULT_SLEW_TIME = 45.0  # [sec]
SIM_OVERHEAD = 3


def setobserver(update):
    """Simulate and update the observer location.

    An `Observer` object to compute the positions of celestial bodies
    as seen from a particular latitude and longitude on the Earth surface.

    Parameters
    ----------
    update: ephem.Observer object
            The observer object to be set
    Returns
    -------
        ephem.Observer object

    """
    global simobserver
    simobserver = update


def sim_time(record, datefmt=None):
    """Simulate the time of the observer object.

    The year, month, dat, hour, minute and seconds string
    describing the current time at the observer's location

    """
    now = simobserver.date.datetime()
    return now.strftime("%Y-%m-%d %H:%M:%SZ")


# Fake user logger prints out to screen
logging.TRACE = 5
logging.addLevelName(logging.TRACE, "TRACE")


def trace(self, message, *args, **kws):
    """Trace logs."""
    if self.isEnabledFor(logging.TRACE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(logging.TRACE, message, args, **kws)


logging.Logger.trace = trace

user_logger = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(message)s")
formatter.formatTime = sim_time
out_hdlr.setFormatter(formatter)
out_hdlr.setLevel(logging.TRACE)
user_logger.addHandler(out_hdlr)
user_logger.setLevel(logging.INFO)


class Fakr(namedtuple("Fakr", "priv_value")):
    def get_value(self):
        return self.priv_value


class SimKat(object):
    """Fake telescope connection."""

    def __init__(self, opts):
        kwargs = vars(opts)
        self.dry_run = True
        self.obs_params = kwargs["obs_plan_params"]
        self._lst, _ = get_lst(self.obs_params["observation_loop"][0]["LST"])
        self._sensors = self.fake_sensors(kwargs)
        self._session_cnt = 0
        self._ants = ["m011", "m022", "m033", "m044"]

    def __enter__(self):
        return self

    def __getattr__(self, key):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __iter__(self):
        Ant = namedtuple("Ant", ["name"])
        for ant in self._ants:
            yield Ant(ant)
        raise StopIteration

    def __exit__(self, type, value, traceback):
        pass

    def get(self, sensorname):
        """Get sensor name."""
        return self._sensors.get(sensorname)

    def fake_sensors(self, kwargs):
        """Fake sensors."""
        _sensors = {}
        if "instrument" not in self.obs_params.keys():
            return _sensors
        if self.obs_params["instrument"] is None:
            return _sensors
        for key in self.obs_params["instrument"].keys():
            fakesensor = "sub_{}".format(key)
            _sensors[fakesensor] = Fakr(self.obs_params["instrument"][key])
        return _sensors


def verify_and_connect(opts):
    """Verify and connect simulation."""
    return SimKat(opts)


class SimSession(object):
    """Fake an observation session."""

    def __init__(self, kat, **kwargs):
        self.kwargs = kwargs
        self.obs_params = kat.obs_params
        self.kat = kat
        self.track_ = False
        self.start_time = datetime2timestamp(simobserver.date.datetime())
        if "durations" in self.obs_params:
            if "start_time" in self.obs_params["durations"]:
                self.start_time = datetime2timestamp(
                    self.obs_params["durations"]["start_time"]
                )
        self.time = self.start_time
        self.katpt_current = None

        # Taken from mkat_session.py to ensure similar behaviour than site
        # systems
        self._realtime, self._realsleep = time.time, time.sleep
        time.time = lambda: self.time

        def simsleep(seconds):
            """Simulate sleep.

            Simulate the sleep functionality, a wait for a specified
            number of seconds until next telescope action

            """
            self.time += seconds

        time.sleep = simsleep
        user_logger.info("Waiting for observation setup")
        time.sleep(SIM_OVERHEAD)

    def __enter__(self):
        return self

    def __getattr__(self, key):
        self._key = key
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __nonzero__(self):
        return True

    def __iter__(self):
        yield self
        raise StopIteration

    def __exit__(self, type, value, traceback):
        # TODO: self.track_ cleanup for multiple obs loops
        if self.track_:
            self.kat._session_cnt += 1
        if self.kat._session_cnt < len(self.obs_params["observation_loop"]):
            self.kat._lst, _ = get_lst(
                self.obs_params["observation_loop"][self.kat._session_cnt]["LST"]
            )

    def _fake_slew_(self, target):
        slew_details = []
        if not (target == self.katpt_current):
            if self.katpt_current is None:
                slew_details = [_DEFAULT_SLEW_TIME]
            else:
                user_logger.debug("Slewing to {}".format(target.name))
                slew_details = list(self.slew_time(target))
        return slew_details

    def track(self, target, duration=0, announce=False):
        """Simulate the track source functionality during observations.

        Parameters
        ----------
        target: katpoint.Target
            The target to be tracked
        duration: int
            Duration of track

        """
        self.track_ = True
        #if len(self._fake_slew_(target)[0] > 0):
        try:
            time.sleep(self._fake_slew_(target)[0])
        except IndexError:
            pass # When the list is empty
        now = timestamp2datetime(self.time)
        simobserver.date = ephem.Date(now)
        if len(self._fake_slew_(target)[1:]) == 2:
            az, el = self._fake_slew_(target)[1:]
            user_logger.info("Slewed to %s at azel (%.1f, %.1f) deg", target.name, az, el)
        else:
            user_logger.info("Slewed to: %s", target.name)
        time.sleep(duration)
        now = timestamp2datetime(self.time)
        simobserver.date = ephem.Date(now)
        user_logger.info("Tracked %s for %d seconds", target.name, duration)
        self.katpt_current = target
        return True

    def raster_scan(
        self,
        target,
        num_scans=3,
        scan_duration=30.0,
        scan_extent=6.0,
        scan_spacing=0.5,
        scan_in_azimuth=True,
        projection="zenithal-equidistant",
        announce=True,
    ):
        """Simulate raster scan.

        Parameters
        ----------
        target: katpoint.Target object
        num_scans: Number of scans
        scan_duration: float
            Duration of scan (s)
        scan_extent: float
            time allocated to group of scans
        scan_spacing: float
            time between scans
        scan_in_azimuth: float
            Scan in azimuth direction
        projection: projection
        announce: bool

        """
        duration = scan_duration * num_scans
        time.sleep(duration)
        now = timestamp2datetime(self.time)
        simobserver.date = ephem.Date(now)
        return True

    def scan(
        self,
        target,
        duration=30.0,
        start=(-3.0, 0.0),
        end=(3.0, 0.0),
        index=-1,
        projection="zenithal-equidistant",
        announce=True,
    ):
        """Simulate scan functionality during observations.

        Parameters
        ----------
        target: katpoint.Target object
        duration: Duration of scan
        start:
        end:
        index:
        projection:
        announce:

        """
        time.sleep(duration)
        now = timestamp2datetime(self.time)
        simobserver.date = ephem.Date(now)
        return True

    def slew_time(self, target):
        """Get slew time.

        How long in seconds, it took for the antennas to move
        from current target to the next.

        Notes:
            The slew time is calculated with consideration of az-el motion
            of antennas instead of the current angular distance between sources,
            assuming a slew_speed 2 deg/s. Antennas slew at 2 deg/s in az while
            moving at 1 deg/s in el. There is about 2.5 seconds for overhead

        Parameters
        ----------
         target: katpoint.Target
             a description which contains parameters such as the
             target name, position, flux model.

        Returns
        -------
        slew_time: float
            The number of seconds it takes to slew
        azimuth:
            The azimuth co-ordinates
        elevation:
            The elevation co-ordinates
        """
        try:
            now = timestamp2datetime(self.time)
            az1, el1 = self.katpt_current.azel(ephem.Date(now))
            az2, el2 = target.azel(ephem.Date(now))

            az1 = katpoint.rad2deg(az1)
            el1 = katpoint.rad2deg(el1)
            azimuth = katpoint.rad2deg(az2)
            elevation = katpoint.rad2deg(el2)

            az_dist = numpy.abs(azimuth - az1)
            el_dist = numpy.abs(elevation - el1)

            az_dist = az_dist if az_dist < 180. else 360. - az_dist
            az_speed = 2.0  # deg/sec
            el_speed = 1.0  # deg/sec
            overhead = 2.5  # sec
            slew_time = max(az_dist / az_speed, el_dist / el_speed) + overhead

            return slew_time, azimuth, elevation
        except AttributeError:
            return slew_time


def start_session(kat, **kwargs):
    """Start the observation simulation.

    Parameters
    ----------
    kat: session kat container-like object

    """
    return SimSession(kat, **kwargs)


# -fin-
