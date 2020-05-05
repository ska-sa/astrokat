"""Set up for noise diode."""
from __future__ import division
from __future__ import absolute_import

import numpy as np
import time

try:
    from katcorelib import user_logger
except ImportError:
    from .simulate import user_logger

# TODO: add this to __init__ (as well as the lead_time check)
_DEFAULT_LEAD_TIME = 3.0  # lead time [sec]


def _set_dig_nd_(kat,
                 timestamp,
                 nd_setup=None,  # no pattern set
                 switch=0,  # all nd off
                 cycle=False):

    if nd_setup is not None:
        # selected antennas for nd pattern
        nd_antennas = nd_setup['antennas'].split(",")
        # nd pattern length [sec]
        cycle_length = nd_setup['cycle_len']
        # on fraction of pattern length [%]
        on_fraction = nd_setup['on_frac']
        msg = ('Repeat noise diode pattern every {} sec, '
               'with {} sec on and apply pattern to {}'
               .format(cycle_length,
                       float(cycle_length) * float(on_fraction),
                       nd_antennas))
        user_logger.info(msg)
    else:
        nd_antennas = [ant.name for ant in kat.ants]
        cycle_length = 1.
        on_fraction = switch

    # Noise diodes trigger is evaluated per antenna
    timestamps = []
    for ant in sorted(nd_antennas):
        ped = getattr(kat, ant)
        try:
            reply = ped.req.dig_noise_source(timestamp,
                                             on_fraction,
                                             cycle_length)
        except ValueError as e:
            # we will not do anything, simply note
            user_logger.warn("{} : {}".format(ant, e))
            continue

        if not kat.dry_run:
            timestamps.append(_katcp_reply_({ant: reply}))
        else:
            msg = ('Dry-run: Set noise diode for antenna {} at '
                   'timestamp {}'.format(ant, timestamp))
            user_logger.debug(msg)

        if cycle:
            # add time [sec] to ensure all digitisers set at the same time
            timestamp += cycle_length * on_fraction

    # assuming ND for all antennas must be the same
    # only display single timestamp
    if not kat.dry_run:
        # test incorrect reply check
        if len(timestamps) < len(nd_antennas):
            err_msg = 'Noise diode activation not in sync'
            user_logger.error(err_msg)
        #         raise RuntimeError(err_msg)
        timestamp = np.mean(timestamps)
    msg = ('Set all noise diodes with timestamp {} ({})'
           .format(int(timestamp),
                   time.ctime(timestamp)))
    user_logger.info(msg)

    return timestamp


# def _katcp_reply_to_log_(dig_katcp_replies):
def _katcp_reply_(dig_katcp_replies):
    """ KATCP timestamp return logs"""
    for ant in sorted(dig_katcp_replies):
        reply, informs = dig_katcp_replies[ant]
        # test incorrect reply check
        if len(reply.arguments) < 2:
            msg = 'Unexpected response after noise diode instruction'
            user_logger.warn(msg.format(ant))
            user_logger.debug('DEBUG: {}'.format(reply.arguments))
            continue
        timestamp = _nd_log_msg_(ant, reply, informs)
    return timestamp


def _nd_log_msg_(ant,
                 reply,
                 informs):
    """construct debug log messages for noisediode"""
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
           .format(actual_on_frac * actual_cycle,
                   actual_cycle))
    user_logger.debug(msg)

    return actual_time


def _switch_on_off_(kat,
                    timestamp,
                    switch=0):  # false=off (default)
    """Switch noise-source on or off.

    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    timestamp : float, optional
        Time since the epoch as a floating point number [sec]
    switch: int, optional
        off = 0 (default), on = 1
    """

    on_off = {0: 'off', 1: 'on'}
    user_logger.trace('TRACE: ND {} @ {}s'
                      .format(on_off[switch], timestamp))
    msg = ('Request: Switch noise-diode {} at {}'
           .format(on_off[switch], timestamp))
    user_logger.info(msg)

    # Noise Diodes are triggered on all antennas in array simultaneously
    # add lead time to ensure all digitisers set at the same time
    timestamp = _set_dig_nd_(kat,
                             timestamp,
                             switch=switch)

    return timestamp


# switch noise-source on
def on(kat,
       timestamp=None,
       lead_time=_DEFAULT_LEAD_TIME):
    """Switch noise-source pattern on.

    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    timestamp : float, optional
        Time since the epoch as a floating point number [sec]
    lead_time : float, optional
        Lead time before the noisediode is switched on [sec]
    """

    # some calls may cause lead_time=None
    lead_time = float(lead_time or _DEFAULT_LEAD_TIME)
    user_logger.trace('TRACE: ND on with lead time {}s'
                      .format(lead_time))
    if timestamp is None:
        timestamp = time.time() + lead_time
    user_logger.trace('TRACE: nd on at {} ({})'
                      .format(timestamp,
                              time.ctime(timestamp)))

    true_timestamp = _switch_on_off_(kat,
                                     timestamp,
                                     switch=1)  # on

    sleeptime = true_timestamp - time.time()
    user_logger.debug('DEBUG: now {}, sleep {}'
                      .format(time.time(),
                              sleeptime))
    time.sleep(sleeptime)  # default sleep to see for signal to get through
    user_logger.debug('DEBUG: now {}, slept {}'
                      .format(time.time(),
                              sleeptime))
    msg = ('Report: noise-diode on at {}'
           .format(time.time()))
    user_logger.info(msg)
    return true_timestamp


# switch noise-source pattern off
def off(kat,
        timestamp=None,
        lead_time=_DEFAULT_LEAD_TIME):
    """Switch noise-source pattern off.

    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    timestamp : float, optional
        Time since the epoch as a floating point number [sec]
    lead_time : float, optional
        Lead time before the noisediode is switched off [sec]
    """

    # some calls may cause lead_time=None
    lead_time = float(lead_time or _DEFAULT_LEAD_TIME)
    user_logger.trace('TRACE: ND off with lead time {}s'
                      .format(lead_time))
    if timestamp is None:
        timestamp = time.time() + lead_time
    user_logger.trace('TRACE: nd off at {} ({})'
                      .format(timestamp,
                              time.ctime(timestamp)))
    true_timestamp = _switch_on_off_(kat, timestamp)  # default off
    return true_timestamp


# fire noise diode before track
def trigger(kat,
            duration=None,
            lead_time=None):
    """Fire the noise diode before track.

    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    duration : float, optional
        Duration that the noisediode will be active [sec]
    lead_time : float, optional
        Lead time before the noisediode is switched on [sec]
    """

    if duration is None:
        return True  # nothing to do

    # if not given, apply default value
    lead_time = float(lead_time or _DEFAULT_LEAD_TIME)

    msg = ('Firing noise diode for {}s before target observation'
           .format(duration))
    user_logger.info(msg)
    user_logger.info('Add lead time of {}s'
                     .format(lead_time))
    user_logger.debug('DEBUG: issue command to switch ND on @ {}'
                      .format(time.time()))
    user_logger.trace('TRACE: ts before issue nd on command {}'
                      .format(time.time()))
    if duration > lead_time:
        on_time = time.time() + lead_time
        on(kat, timestamp=on_time)
        now = time.time()
        user_logger.debug('DEBUG: on {} ({})'
                          .format(now,
                                  time.ctime(now)))
        user_logger.debug('DEBUG: fire nd for {}'
                          .format(duration))
        sleeptime = duration - lead_time
        user_logger.debug('DEBUG: sleeping for {} [sec]'
                          .format(sleeptime))
        time.sleep(sleeptime)
        user_logger.trace('TRACE: ts after issue nd on sleep {}'
                          .format(time.time()))
        off_time = time.time() + lead_time
    else:
        cycle_len = float(lead_time + duration)
        nd_setup = {'antennas': 'all',
                    'cycle_len': cycle_len,
                    'on_frac': float(duration) / cycle_len,
                    }
        user_logger.debug('DEBUG: fire nd for {} using pattern'
                          .format(duration))
        pattern(kat, nd_setup, lead_time=lead_time)
        now = time.time()
        user_logger.debug('DEBUG: pattern set {} ({})'
                          .format(now,
                                  time.ctime(now)))
        off_time = time.time() + lead_time

    user_logger.debug('DEBUG: off {} ({})'
                      .format(off_time,
                              time.ctime(off_time)))
    off(kat, timestamp=off_time)
    sleeptime = off_time - time.time()
    user_logger.debug('DEBUG: now {}, sleep {}'
                      .format(time.time(),
                              sleeptime))
    time.sleep(sleeptime)  # default sleep to see for signal to get through
    user_logger.debug('DEBUG: now {}, slept {}'
                      .format(time.time(),
                              sleeptime))
    msg = ('Report: noise-diode off at {}'
           .format(time.time()))
    user_logger.info(msg)
    return True


# set noise diode pattern
def pattern(kat,  # kat subarray object
            nd_setup,  # noise diode pattern setup
            lead_time=None,  # lead time [sec]
            ):
    """Start background noise diode pattern controlled by digitiser hardware.

    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    nd_setup : dict
        Noise diode pattern setup, with keys:
            'antennas':  options are 'all', or 'm062', or ....,
            'cycle_len': the cycle length [sec],
                           - must be less than 20 sec for L-band,
            etc., etc.
    lead_time : float, optional
        Lead time before digitisers pattern is set [sec]
    """
    # nd pattern length [sec]
    cycle_length = nd_setup['cycle_len']
    if not kat.dry_run:
        if (kat.sensor.sub_band.get_value() == 'l'
                and float(cycle_length) > 20.0):
            msg = 'Maximum cycle length of L-band is 20 seconds'
            raise RuntimeError(msg)

    # add special lead time option
    # if not given, apply default value
    lead_time = float(lead_time or _DEFAULT_LEAD_TIME)

    # Try to trigger noise diodes on all antennas in array simultaneously.
    # - use integer second boundary as that is most likely be an exact
    #   time that DMC can execute at, and also fit a unix epoch time
    #   into a double precision float accurately
    # - add a default lead time to ensure enough time for all digitisers
    #   to be set up
    timestamp = time.time() + lead_time
    msg = ('Request: Set noise diode pattern to activate at {} '
           '(includes {} sec lead time)'
           .format(timestamp,
                   lead_time))
    user_logger.warning(msg)

    nd_antennas = nd_setup['antennas']
    sb_ants = ",".join([str(ant.name) for ant in kat.ants])
    nd_setup['antennas'] = sb_ants
    if nd_antennas == 'all':
        cycle = False
    elif nd_antennas == 'cycle':
        cycle = True
    else:
        cycle = False
        nd_setup['antennas'] = ",".join([
            ant.strip() for ant in nd_antennas.split(",") if ant.strip() in sb_ants
        ])
    user_logger.info('Antennas found in subarray, setting ND: {}'
                     .format(nd_setup['antennas']))

    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    timestamp = _set_dig_nd_(kat,
                             timestamp,
                             nd_setup=nd_setup,
                             cycle=cycle)

    wait_time = timestamp - time.time()
    user_logger.trace('TRACE: set nd pattern at {} from now {}, sleep {}'
                      .format(timestamp,
                              time.time(),
                              wait_time))
    time.sleep(wait_time)
    msg = ('Report: pattern set at {}'
           .format(time.time()))
    user_logger.info(msg)
    user_logger.trace('TRACE: ts after wait period {}'
                      .format(time.time()))

    return True

# -fin-
