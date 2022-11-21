"""Provides skeleton for mimicking a live MeerKAT telescope system."""
from __future__ import division
from __future__ import absolute_import

import numpy as np
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

MEERKAT_REFERENCE_LOCATION = "ref, -30:42:39.8, 21:26:38.0, 1035.0, 0.0, , , 1.15"
ref_antenna = katpoint.Antenna(MEERKAT_REFERENCE_LOCATION)

# MeerKAT receptor parameters for azimuth and elevation slewing
# (some from specifications, some from empirical data - see JIRA MT-1206).
_DEFAULT_SLEW_TIME_SEC = 45.0
_SIM_OVERHEAD_SEC = 3.0
_SLEW_INIT_OVERHEAD = 2.3
_EL_SPEED_DEG_PER_SEC = 1.0
_EL_ACCEL_DEG_PER_SEC_SQ = 0.5
_EL_LONG_SLEW_DEG = 7.0
_EL_LONG_SLEW_SETTLE_TIME_SEC = 8.1
_AZ_SPEED_DEG_PER_SEC = 2.0
_AZ_ACCEL_DEG_PER_SEC_SQ = 1.0
_AZ_LONG_SLEW_DEG = 0.0
_AZ_LONG_SLEW_SETTLE_TIME_SEC = 6.1


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
        return

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
        self.capture_initialised = False

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
            global simobserver
            now = timestamp2datetime(self.time)
            simobserver.date = ephem.Date(now)

        time.sleep = simsleep

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

    def capture_init(self):
        """Simulate data capturing initialisation (if not already done)."""
        if not self.capture_initialised:
            user_logger.info("Waiting for observation setup")
            time.sleep(_SIM_OVERHEAD_SEC)
            user_logger.info('INIT')
            self.capture_initialised = True

    def track(self, target, duration=0, announce=False, slew_only=False):
        """Simulate the track source functionality during observations.

        Parameters
        ----------
        target: katpoint.Target
            The target to be tracked
        duration: int
            Duration of track
        announce : bool, optional
            True if start of action should be announced, with details of
            settings
        slew_only : bool, optional
                True if only the antenna slews should be performed.
        """
        self.track_ = True
        slew_time, az, el = self._fake_slew_(target)
        time.sleep(slew_time)
        user_logger.info("Slewed to %s at azel (%.1f, %.1f) deg", target.name, az, el)
        time.sleep(duration)
        user_logger.info("Tracked %s for %d seconds", target.name, duration)
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
        slew_time, az, el = self._fake_slew_(target)
        time.sleep(slew_time)
        user_logger.info("Slewed to %s at azel (%.1f, %.1f) deg", target.name, az, el)
        time.sleep(duration)
        return True

    def reference_pointing_scan(
        self, target=None, duration=5.0, extent=1, num_pointings=10
    ):
        """Simulate a collection of offset pointings on the nearest pointing
        calibrator.
        Sleep a `duration` seconds to pretend doing calculation of pointing cal solutions
        and storing them in telstate before reporting to have completed the task.

        Parameters
        ----------
        target: katpoint.Target object
        duration: int or float
            Duration of scan
        extent: int/float
            distance of offset from target, in degrees
        num_pointings: int
            Number of offset pointings
        """
        scan = np.linspace(-extent, extent, num_pointings // 2)
        offsets_along_x = np.c_[scan, np.zeros_like(scan)]
        offsets_along_y = np.c_[np.zeros_like(scan), scan]
        offsets = np.r_[offsets_along_y, offsets_along_x]
        offset_end_times = np.zeros(len(offsets))
        middle_time = 0.0
        weather = {}

        user_logger.info(
            "Initiating interferometric pointing scan on target "
            "'%s' (%d pointings of %g seconds each)",
            target.name,
            len(offsets),
            duration,
        )
        self.track(target, duration=0, announce=False)
        # Point to the requested offsets and collect extra data at middle time
        for n, offset in enumerate(offsets):
            user_logger.info("initiating track on offset of (%g, %g) degrees", *offset)
            self.track(target, duration, announce=False)
            offset_end_times[n] = time.time()
            if n == len(offsets) // 2 - 1:
                middle_time = offset_end_times[n]
                user_logger.info(
                    "reference time = %.1f, weather = %r", middle_time, weather)
        user_logger.info("returning to target to complete the scan")
        self.track(target, duration=0, announce=False)
        user_logger.info("Waiting for gains to materialise in cal pipeline")
        user_logger.info("Retrieving gains, fitting beams, storing offsets")

    def _target_azel(self, target):
        """Get azimuth and elevation co-ordinates for a target at the current time.

        Parameters
        ----------
        target: katpoint.Target
            The target of interest.

        Returns
        -------
        az: float
            The azimuth co-ordinate of the target in degrees.
        el: float
            The elevation co-ordinate of the target in degrees.

        """
        az, el = target.azel(simobserver.date)
        az = katpoint.rad2deg(az)
        el = katpoint.rad2deg(el)
        return az, el

    def _fake_slew_(self, target):
        slew_time = 0
        az, el = self._target_azel(target)
        if target != self.katpt_current:
            if self.katpt_current is None:
                slew_time = _DEFAULT_SLEW_TIME_SEC
            else:
                user_logger.debug("Slewing to {}".format(target.name))
                slew_time = self._slew_time(az, el)
            self.katpt_current = target
        return slew_time, az, el

    def _slew_time(self, new_az, new_el):
        """Get estimated slew time to next target.

        Parameters
        ----------
        new_az: float
            The azimuth co-ordinate of the new target in degrees.
        new_el: float
            The elevation co-ordinate of the new target in degrees.

        Returns
        -------
        slew_time: float
            The number of seconds it takes to slew.

        """
        current_az, current_el = self._target_azel(self.katpt_current)

        az_dist = numpy.abs(new_az - current_az)
        el_dist = numpy.abs(new_el - current_el)

        # wrap angle into +-180, ignoring receptor cable wrapping
        if az_dist > 180.0:
            az_dist = numpy.abs((az_dist + 180.) % 360. - 180.)

        # Time, t, to accelerate to full speed: v = u + at
        t_el = (_EL_SPEED_DEG_PER_SEC - 0.0) / _EL_ACCEL_DEG_PER_SEC_SQ
        t_az = (_AZ_SPEED_DEG_PER_SEC - 0.0) / _AZ_ACCEL_DEG_PER_SEC_SQ
        # Corresponding displacement to accelerate
        # up to full speed:  s = ut + (at^2)/2
        s_el = 0.0 * t_el + (_EL_ACCEL_DEG_PER_SEC_SQ * t_el ** 2) / 2.0
        s_az = 0.0 * t_az + (_AZ_ACCEL_DEG_PER_SEC_SQ * t_az ** 2) / 2.0

        # The factors of 2 account for acceleration and deceleration
        # i.e., ramping up to full speed, and then ramping down to stop
        if el_dist > 2.0 * s_el:
            el_left = el_dist - 2.0 * s_el
            el_slew_time = 2.0 * t_el + el_left / _EL_SPEED_DEG_PER_SEC
            if el_left > _EL_LONG_SLEW_DEG:
                el_slew_time = el_slew_time + _EL_LONG_SLEW_SETTLE_TIME_SEC
        else:
            # Time taken to cover distance: s = ut + (at^2)/2
            s_el = el_dist / 2.0
            el_slew_time = 2.0 * 2.0 * numpy.sqrt(s_el / _EL_ACCEL_DEG_PER_SEC_SQ)

        # The factors of 2 account for acceleration and deceleration
        if az_dist > 2.0 * s_az:
            az_left = az_dist - 2.0 * s_az
            az_slew_time = 2.0 * t_az + az_left / _AZ_SPEED_DEG_PER_SEC
            if az_left > _AZ_LONG_SLEW_DEG:
                az_slew_time = az_slew_time + _AZ_LONG_SLEW_SETTLE_TIME_SEC
        else:
            # Time taken to cover distance: s = ut + (at^2)/2
            s_az = az_dist / 2.0
            az_slew_time = 2.0 * 2.0 * numpy.sqrt(s_az / _AZ_ACCEL_DEG_PER_SEC_SQ)

        # Add additional overhead between initialising and slewing
        az_slew_time += _SLEW_INIT_OVERHEAD
        el_slew_time += _SLEW_INIT_OVERHEAD

        return max([az_slew_time, el_slew_time])


def start_session(kat, **kwargs):
    """Start the observation simulation.

    Parameters
    ----------
    kat: session kat container-like object

    """
    return SimSession(kat, **kwargs)


# -fin-
