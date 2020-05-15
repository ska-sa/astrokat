"""Set up for noise diode."""
from __future__ import division
from __future__ import absolute_import

import numpy as np
import time

try:
    from katcorelib import user_logger
except ImportError:
    from .simulate import user_logger
from . import _DEFAULT_LEAD_TIME
from . import max_cycle_len


def _get_max_cycle_len(kat):
    """Get maximum cycle length for noise diode switching
    """
    if not kat.dry_run:
        return max_cycle_len(kat.sensor.sub_band.get_value())
    else:
        return max_cycle_len('l')


def _get_nd_timestamp_(lead_time):
    """Timestamp for ND switch command with lead time
    """
    return time.time() + lead_time


def _set_dig_nd_(kat,
                 timestamp,
                 nd_setup=None,
                 switch=0,
                 cycle=False):
    """Setting and implementing digitiser noise diode command
    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    timestamp : float
        Linux timestamp in seconds at which to switch noise diode
    nd_setup : dict, optional (default = None, no pattern set)
        Noise diode pattern setup, with keys:
            'antennas':  options are 'all', or 'm062', or ....,
            'cycle_len': the cycle length [sec],
                           - must be less than 20 sec for L-band,
            etc., etc.
    switch : 0 or 1, optional (default = 0)
        Switch all noise diodes off (0) or on (1)

    Returns
    -------
    timestamp : float
        Linux timestamp reported by digitiser
    """

    if nd_setup is not None:
        # selected antennas for nd pattern
        nd_antennas = sorted(nd_setup['antennas'].split(","))
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
        nd_antennas = sorted(ant.name for ant in kat.ants)
        cycle_length = 1.
        on_fraction = switch

    # Noise diodes trigger is evaluated per antenna
    timestamps = []
    for ant in nd_antennas:
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
        timestamp = np.mean(timestamps)
    msg = ('Set all noise diodes with timestamp {} ({})'
           .format(int(timestamp),
                   time.ctime(timestamp)))
    user_logger.debug('DEBUG: {}'.format(msg))

    return timestamp


def _katcp_reply_(dig_katcp_replies):
    """ KATCP timestamp return logs"""
    ant_ts_list = []
    for ant in sorted(dig_katcp_replies):
        reply, informs = dig_katcp_replies[ant]
        if reply.reply_ok():
            ant_ts_list.append(_nd_log_msg_(ant, reply, informs))
        else:
            msg = 'Unexpected noise diode reply from ant {}'.format(ant)
            user_logger.warn(msg)
            user_logger.debug('DEBUG: {}'.format(reply.arguments))
            continue
    # assume all ND timestamps similar and return average
    return np.mean(ant_ts_list)


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

    if len(reply.arguments) < 4:
        msg = 'Unexpected number of return arguments\n'
        msg += '4 values expected: code time on-frac cycle-len'
        msg += 'Found {}'.format(len(reply.arguments))
        raise RuntimeError(msg)

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
                    switch=0):
    """Switch noise-source on or off.

    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    timestamp : float, optional
        Time since the epoch as a floating point number [sec]
    switch: int, optional
        off = 0 (default), on = 1

    Returns
    -------
    timestamp : float
        Linux timestamp reported by digitiser
    """

    on_off = {0: 'off', 1: 'on'}
    msg = ('Request switch noise-diode {} at {}'
           .format(on_off[switch], timestamp))
    user_logger.debug('DEBUG: {}'.format(msg))

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
    timestamp : float, optional (default = None)
        Time since the epoch as a floating point number [sec]
    lead_time : float, optional (default = system default lead time)
        Lead time before the noisediode is switched on [sec]

    Returns
    -------
    timestamp : float
        Linux timestamp reported by digitiser
    """

    if timestamp is None:
        timestamp = _get_nd_timestamp_(lead_time)

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
           .format(true_timestamp))
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
    timestamp : float, optional (default = None)
        Time since the epoch as a floating point number [sec]
    lead_time : float, optional (default = system default lead time)
        Lead time before the noisediode is switched off [sec]

    Returns
    -------
    timestamp : float
        Linux timestamp reported by digitiser
    """

    if timestamp is None:
        timestamp = _get_nd_timestamp_(lead_time)

    true_timestamp = _switch_on_off_(kat, timestamp)
    msg = ('Report: noise-diode off at {}'
           .format(true_timestamp))
    user_logger.info(msg)
    return true_timestamp


# fire noise diode before track
def trigger(kat,
            duration=None,
            lead_time=_DEFAULT_LEAD_TIME):
    """Fire the noise diode before track.

    Parameters
    ----------
    kat : session kat container-like object
        Container for accessing KATCP resources allocated to schedule block.
    duration : float, optional (default = None)
        Duration that the noisediode will be active [sec]
    lead_time : float, optional (default = system default lead time)
        Lead time before the noisediode is switched on [sec]
    """

    if duration is None:
        return True  # nothing to do

    msg = ('Firing noise diode for {}s before target observation'
           .format(duration))
    user_logger.info(msg)
    user_logger.info('Add lead time of {}s'
                     .format(lead_time))
    user_logger.debug('DEBUG: issue command to switch ND on @ {}'
                      .format(time.time()))
    if duration > lead_time:
        user_logger.trace('TRACE: Trigger duration > lead_time')
        # allow lead time for all to switch on simultaneously
        # timestamp on = now + lead
        on_time = on(kat, lead_time=lead_time)
        user_logger.debug('DEBUG: on {} ({})'
                          .format(on_time,
                                  time.ctime(on_time)))
        user_logger.debug('DEBUG: fire nd for {}'
                          .format(duration))
        sleeptime = min(duration - lead_time, lead_time)
        user_logger.trace('TRACE: sleep {}'
                          .format(sleeptime))
        off_time = on_time + duration
        user_logger.trace('TRACE: desired off_time {} ({})'
                          .format(off_time,
                                  time.ctime(off_time)))
        user_logger.trace('TRACE: delta {}'
                          .format(off_time - on_time))
        user_logger.debug('DEBUG: sleeping for {} [sec]'
                          .format(sleeptime))
        time.sleep(sleeptime)
        user_logger.trace('TRACE: ts after sleep {} ({})'
                          .format(time.time(),
                                  time.ctime(time.time())))
    else:
        user_logger.trace('TRACE: Trigger duration <= lead_time')
        cycle_len = _get_max_cycle_len(kat)
        nd_setup = {'antennas': 'all',
                    'cycle_len': cycle_len,
                    'on_frac': float(duration) / cycle_len,
                    }
        user_logger.debug('DEBUG: fire nd for {} using pattern'
                          .format(duration))
        on_time = pattern(kat, nd_setup, lead_time=lead_time)
        user_logger.debug('DEBUG: pattern set {} ({})'
                          .format(on_time,
                                  time.ctime(on_time)))
        off_time = _get_nd_timestamp_(lead_time)
        user_logger.trace('TRACE: desired off_time {} ({})'
                          .format(off_time,
                                  time.ctime(off_time)))

    user_logger.debug('DEBUG: off {} ({})'
                      .format(off_time,
                              time.ctime(off_time)))
    off_time = off(kat, timestamp=off_time)
    sleeptime = off_time - time.time()
    user_logger.debug('DEBUG: now {}, sleep {}'
                      .format(time.time(),
                              sleeptime))
    time.sleep(sleeptime)  # default sleep to see for signal to get through
    user_logger.debug('DEBUG: now {}, slept {}'
                      .format(time.time(),
                              sleeptime))


# set noise diode pattern
def pattern(kat,
            nd_setup,
            lead_time=_DEFAULT_LEAD_TIME,
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
    lead_time : float, optional (default = system default lead time)
        Lead time before digitisers pattern is set [sec]

    Returns
    -------
    timestamp : float
        Linux timestamp reported by digitiser
    """

    # nd pattern length [sec]
    max_cycle_len = _get_max_cycle_len(kat)
    if float(nd_setup['cycle_len']) > max_cycle_len:
        msg = 'Maximum cycle length is {} seconds'.format(max_cycle_len)
        raise RuntimeError(msg)

    user_logger.trace('TRACE: max cycle len {}'
                      .format(max_cycle_len))

    # Try to trigger noise diodes on specified antennas in array simultaneously.
    # - add a default lead time to ensure enough time for all digitisers
    #   to be set up
    start_time = _get_nd_timestamp_(lead_time)
    user_logger.trace('TRACE: desired start_time {} ({})'
                      .format(start_time,
                              time.ctime(start_time)))
    msg = ('Request: Set noise diode pattern to activate at {} '
           '(includes {} sec lead time)'
           .format(start_time,
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

    # Noise Diodes are triggered simultaneously
    # on specified antennas in the array
    timestamp = _set_dig_nd_(kat,
                             start_time,
                             nd_setup=nd_setup,
                             cycle=cycle)
    user_logger.trace('TRACE: now {} ({})'
                      .format(time.time(),
                              time.ctime(time.time())))
    user_logger.trace('TRACE: timestamp {} ({})'
                      .format(timestamp,
                              time.ctime(timestamp)))
    wait_time = timestamp - time.time()
    user_logger.trace('TRACE: delta {}'
                      .format(wait_time))
    time.sleep(wait_time)
    user_logger.trace('TRACE: set nd pattern at {}, slept {}'
                      .format(time.time(),
                              wait_time))
    msg = ('Report: Switch noise-diode pattern on at {}'
           .format(timestamp))
    user_logger.info(msg)
    return timestamp

# -fin-
