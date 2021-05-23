"""Scan observations."""
from __future__ import division
from __future__ import absolute_import

import katpoint

from .noisediode import trigger

import time

try:
    from katcorelib import user_logger
except ImportError:
    from .simulate import user_logger


def drift_pointing_offset(target, duration=60.0):
    """Drift pointing offset observation.

    Parameters
    ----------
    target: katpoint.Target
    duration: float

    """
    obs_start_ts = target.antenna.observer.date
    transit_time = obs_start_ts + duration / 2.0
    # Stationary transit point becomes new target
    antenna = target.antenna
    az, el = target.azel(timestamp=transit_time)
    target = katpoint.construct_azel_target(katpoint.wrap_angle(az), el)
    # katpoint destructively set dates and times during calculation
    # restore datetime before continuing
    target.antenna = antenna
    target.antenna.observer.date = obs_start_ts
    return target


def drift_scan(session, target, duration=60.0, nd_period=None, lead_time=None):
    """Drift scan observation.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    duration: float
        scan duration
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    target = drift_pointing_offset(target, duration=duration)
    user_logger.info("Drift_scan observation for {} sec".format(duration))
    return session.track(target, duration=duration)


def raster_scan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Raster scan observation.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    # TODO: ignoring raster_scan, not currently working robustly
    # TODO: there are errors in raster scan calculations, need some review
    #     session.raster_scan(target,num_scans=2,
    #                             scan_duration=120,
    #                             scan_extent=10,
    #                             scan_spacing=0.5,
    #                             scan_in_azimuth=True,
    #                             projection='plate-carree')
    return session.raster_scan(target, **kwargs)


def scan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Run basic scan observation.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    try:
        timestamp = session.time
    except AttributeError:
        timestamp = time.time()
    user_logger.debug("DEBUG: Starting scan across target: {}".format(timestamp))
    return session.scan(target, **kwargs)


def forwardscan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Forward scan observation.

    Call to `scan` method described in this module

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period

    """
    target_visible = scan(session,
                          target,
                          nd_period=nd_period,
                          lead_time=lead_time,
                          **kwargs)
    return target_visible


def reversescan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Reverse scan observation.

    Call to `scan` method described in this module

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period

    """
    returnscan = dict(kwargs)
    returnscan["start"] = kwargs["end"]
    returnscan["end"] = kwargs["start"]
    target_visible = scan(session,
                          target,
                          nd_period=nd_period,
                          lead_time=lead_time,
                          **returnscan)
    return target_visible


def return_scan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Return scan observation.

    A temporary fix until raster scan can be fixed

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period

    """
    # set up 2way scan
    user_logger.info("Forward scan over target")
    target_visible = forwardscan(session,
                                 target,
                                 nd_period=nd_period,
                                 lead_time=lead_time,
                                 **kwargs)

    user_logger.info("Reverse scan over target")
    target_visible += reversescan(session,
                                  target,
                                  nd_period=nd_period,
                                  lead_time=lead_time,
                                  **kwargs)
    return target_visible


# -fin-
