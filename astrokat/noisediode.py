"""Set up for noise diode."""
from __future__ import division
from __future__ import absolute_import

import numpy as np
import time

try:
    from katcorelib import user_logger
except ImportError:
    from .simulate import user_logger


_DEFAULT_LEAD_TIME = 5.0  # lead time [sec]


def _nd_log_msg_(ant,
                 reply,
                 informs):

    user_logger.debug('DEBUG: reply = {}'
                      .format(reply))
    user_logger.debug('DEBUG: arguments ({})= {}'
                      .format(len(reply.arguments),
                              reply.arguments))
    user_logger.debug('DEBUG: informs = {}'
                      .format(informs))

    actual_time = float(reply.arguments[1])
    actual_on_frac = float(reply.arguments[2])
    actual_cycle = float(reply.arguments[3])
    msg = ('Noise diode for antenna {} set at {}. '
           .format(ant,
                   actual_time))
    user_logger.debug(msg)
    msg = ('Pattern set as {} sec ON for {} sec cycle length'
           .format(actual_on_frac*actual_cycle,
                   actual_cycle))
    user_logger.debug(msg)

    return actual_time


def _katcp_reply_to_log_(dig_katcp_replies):
    for ant in sorted(dig_katcp_replies):
        reply, informs = dig_katcp_replies[ant]
        # assuming ND for all antennas set at the same time
        # only return timestamp of the last antenna set
        timestamp = _nd_log_msg_(ant, reply, informs)
    return timestamp


def on(kat, timestamp=None, lead_time=_DEFAULT_LEAD_TIME):
    """Switch noise-source pattern on.

    Parameters
    ----------
    kat : Session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    timestamp : float, optional
        Time since the epoch as a floating point number [sec]
    lead_time : float, optional
        Lead time before the noisediode is switched on [sec]

    """
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add some lead to ensure all digitisers set at the same time
    if timestamp is None:
        user_logger.trace(
            "TRACE: ts + leadtime = {} + {}".format(time.time(), lead_time)
        )
        timestamp = np.ceil(time.time() + lead_time)
    user_logger.trace(
        "TRACE: nd on at {} ({})".format(timestamp, time.ctime(timestamp))
    )
    msg = "Request: Switch noise-diode on at {}".format(timestamp)
    user_logger.info(msg)

    replies = kat.ants.req.dig_noise_source(timestamp, 1)
    if not kat.dry_run:
        timestamp = _katcp_reply_to_log_(replies)
    else:
        # - use integer second boundary as that is most likely be an exact
        #   time that DMC can execute at
        msg = "Dry-run: Set all noise diodes with timestamp {} ({})".format(
            np.ceil(timestamp), time.ctime(timestamp)
        )
        user_logger.info(msg)

    return timestamp


# switch noise-source pattern off
def off(kat, timestamp=None, lead_time=_DEFAULT_LEAD_TIME):
    """Switch noise-source pattern off.

    Parameters
    ----------
    kat : Session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    timestamp : float, optional
        Time since the epoch as a floating point number [sec]
    lead_time : float, optional
        Lead time before the noisediode is switched off [sec]

    """
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add some lead to ensure all digitisers set at the same time
    if timestamp is None:
        user_logger.trace(
            "TRACE: ts + leadtime = {} + {}".format(time.time(), lead_time)
        )
        timestamp = np.ceil(time.time() + lead_time)
    user_logger.trace(
        "TRACE: nd off at {} ({})".format(timestamp, time.ctime(timestamp))
    )
    msg = "Request: Switch noise-diode off at {}".format(timestamp)
    user_logger.info(msg)

    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    replies = kat.ants.req.dig_noise_source(timestamp, 0)
    if not kat.dry_run:
        timestamp = _katcp_reply_to_log_(replies)
    else:
        # - use integer second boundary as that is most likely be an exact
        #   time that DMC can execute at
        msg = "Dry-run: Set all noise diodes with timestamp {} ({})".format(
            np.ceil(timestamp), time.ctime(timestamp)
        )
        user_logger.info(msg)

    return timestamp


# fire noise diode before track
def trigger(kat, session, duration=None):
    """Fire the noise diode before track.

    Parameters
    ----------
    kat : Session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    session : katcorelib.CaptureSession-like object
    duration : float, optional
        Duration that the noisediode will be active [sec]

    """
    if duration is None:
        return True  # nothing to do
    msg = "Firing noise diode for {}s before target observation".format(duration)
    user_logger.info(msg)
    user_logger.debug("DEBUG: issue command to switch ND on @ {}".format(time.time()))
    user_logger.trace("TRACE: ts before issue nd on command {}".format(time.time()))
    timestamp_on_set = on(kat)
    user_logger.debug(
        "DEBUG: on {} ({})".format(timestamp_on_set, time.ctime(timestamp_on_set))
    )
    user_logger.debug("DEBUG: fire nd for {}".format(duration))
    sleeptime = timestamp_on_set - time.time() + duration
    time.sleep(sleeptime)  # default sleep to see for signal to get through
    user_logger.trace("TRACE: ts after issue nd on sleep {}".format(time.time()))
    timestamp_off_set = off(kat)
    user_logger.debug(
        "DEBUG: off {} ({})".format(timestamp_off_set, time.ctime(timestamp_off_set))
    )
    sleeptime = timestamp_off_set - time.time()
    user_logger.debug("DEBUG: now {}, sleep {}".format(time.time(), sleeptime))
    time.sleep(sleeptime)  # default sleep to see for signal to get through
    user_logger.debug("DEBUG: now {}, slept {}".format(time.time(), sleeptime))
    return True


def pattern(kat, session, nd_setup, lead_time=_DEFAULT_LEAD_TIME):
    """Start background noise diode pattern controlled by digitiser hardware.

    Parameters
    ----------
    kat : Session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    session : katcorelib.CaptureSession-like object
    nd_setup: dict
        Noise diode pattern setup, with keys:
            'antennas':  options are `ants`, or 'm062',...
            'cycle_len': the cycle length [sec], - must be less than 20 sec for L-band
    lead_time : float, optional
                Lead time before digitisers pattern is set [sec]

    """
    nd_antennas = nd_setup["antennas"]  # selected antennas for nd pattern
    cycle_length = nd_setup["cycle_len"]  # nd pattern length [sec]
    on_fraction = nd_setup["on_frac"]  # on fraction of pattern length [%]
    msg = (
        "Repeat noise diode pattern every {} sec, with {} sec on and apply pattern to"
        " {}".format(cycle_length, float(cycle_length) * float(on_fraction), nd_antennas)
    )
    user_logger.info(msg)

    if not kat.dry_run:
        if kat.sensor.sub_band.get_value() == "l" and float(cycle_length) > 20.0:
            msg = "Maximum cycle length of L-band is 20 seconds"
            raise RuntimeError(msg)
        # Set noise diode period to multiple of correlator integration time.
        dump_period = session.cbf.correlator.sensor.int_time.get_value()
        user_logger.warning(
            "Correlator integration time {} [sec]".format(1.0 / dump_period)
        )
        cycle_length = int(cycle_length / dump_period) * dump_period
        msg = "Set noise diode period to multiple of correlator dump period:"
        msg += " cycle length = {} [sec]".format(cycle_length)
        user_logger.warning(msg)

    # Try to trigger noise diodes on all antennas in array simultaneously.
    # - use integer second boundary as that is most likely be an exact
    #   time that DMC can execute at, and also fit a unix epoch time
    #   into a double precision float accurately
    # - add a default lead time to ensure enough time for all digitisers
    #   to be set up
    timestamp = np.ceil(time.time() + lead_time)
    msg = (
        "Request: Set noise diode pattern to activate at {} "
        "(includes {} sec lead time)".format(timestamp, lead_time)
    )
    user_logger.warning(msg)

    if nd_antennas == "all":
        # Noise Diodes are triggered on all antennas in array simultaneously
        # add a second to ensure all digitisers set at the same time
        replies = kat.ants.req.dig_noise_source(timestamp, on_fraction, cycle_length)
        if not kat.dry_run:
            timestamp = _katcp_reply_to_log_(replies)
        else:
            msg = "Dry-run: Set all noise diodes with timestamp {} ({})".format(
                int(timestamp), time.ctime(timestamp)
            )
            user_logger.info(msg)
    else:
        sb_ants = [ant.name for ant in kat.ants]
        if "cycle" not in nd_antennas:
            sb_ants = [
                ant.strip() for ant in nd_antennas.split(",") if ant.strip() in sb_ants
            ]
            user_logger.info(
                "Antennas found in subarray, setting ND: {}".format(",".join(sb_ants))
            )
        # Noise Diodes are triggered for selected antennas in the array
        for ant in sb_ants:
            ped = getattr(kat, ant)
            the_reply = ped.req.dig_noise_source(timestamp, on_fraction, cycle_length)
            if not kat.dry_run:
                timestamp = _katcp_reply_to_log_({ant: the_reply})
            else:
                msg = (
                    "Dry-run: Set noise diode for antenna"
                    "{} with timestamp {}".format(ant, timestamp)
                )
                user_logger.info(msg)
            if nd_antennas == "cycle":
                # add time [sec] to ensure all digitisers set at the same time
                timestamp += cycle_length * on_fraction

    wait_time = timestamp - time.time()
    user_logger.trace(
        "TRACE: set nd pattern at "
        "{} from now {}, sleep {}".format(timestamp, time.time(), wait_time)
    )
    time.sleep(wait_time)
    user_logger.trace("TRACE: ts after wait period {}".format(time.time()))


# -fin-
