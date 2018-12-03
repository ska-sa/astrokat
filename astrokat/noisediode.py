# flake8: noqa
import numpy as np
import time
libnames = ['user_logger']
try:
    lib = __import__('katcorelib', globals(), locals(), libnames, -1)
except ImportError:
    lib = __import__('simulate', globals(), locals(), libnames, -1)
finally:
    for libname in libnames:
        globals()[libname] = getattr(lib, libname)


def _nd_log_msg_(ant, reply, informs, verbose=False):
    actual_time = float(reply.arguments[1])
    actual_on_frac = float(reply.arguments[2])
    actual_cycle = float(reply.arguments[3])
    msg = 'Noise diode for antenna {} set at {}. '.format(
            ant, actual_time)
    if verbose:
        msg += 'Pattern set as {} sec ON for {} sec cycle length'.format(
                actual_on_frac*actual_cycle, actual_cycle)
    user_logger.info(msg)

# def _nd_switch_(mkat, switch):
#     # Noise Diodes are triggered on all antennas in array simultaneously
#     # add a second to ensure all digitisers set at the same time
#     timestamp = time.time() + lead_time
#     mkat.ants.req.dig_noise_source(timestamp, 1)
#     if not mkat.dry_run:
#         time.sleep(float(lead_time))


# switch noise-source on
def on(mkat, lead_time=3.):
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    timestamp = np.ceil(time.time() + lead_time)
    msg = 'Switch noise-diode on at {}'.format(timestamp)
    user_logger.info(msg)

    replies = mkat.ants.req.dig_noise_source(timestamp, 1)
    if not mkat.dry_run:
        for ant in sorted(replies):
            reply, informs = replies[ant]
            # devcomm is still simm, but will not be dry-run
            if len(reply.arguments) > 2:
                _nd_log_msg_(ant, reply, informs, verbose=False)

    return timestamp


# switch noise-source pattern off
def off(mkat, timestamp=None, lead_time=3.):
    if timestamp is None:
        timestamp = np.ceil(time.time() + lead_time)
#     else:
#         timestamp = np.ceil(timestamp)
    msg = 'Switch noise-diode off at {}'.format(timestamp)
    user_logger.info(msg)

    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    replies = mkat.ants.req.dig_noise_source(timestamp, 0)
#     print replies
    if not mkat.dry_run:
        for ant in sorted(replies):
            reply, informs = replies[ant]
#             print 'reply', reply
#             print 'arguments', len(reply.arguments), reply.arguments
#             print 'informs', informs
            # devcomm is still simm, but will not be dry-run
            if len(reply.arguments) > 2:
                _nd_log_msg_(ant, reply, informs, verbose=False)

    return timestamp


# fire noise diode before track
def trigger(mkat, session, duration=None):
    if duration is None:
        return True  # nothing to do
    msg = 'Firing noise diode for {}s before target observation'.format(
            duration)
    user_logger.info(msg)
    timestamp_on_set = on(mkat)
    user_logger.warning('DEBUG: on {} ({})'.format(timestamp_on_set, time.ctime(timestamp_on_set)))
    user_logger.warning('DEBUG: default sleep for {}'.format(duration))
    time.sleep(duration) # default sleep to see if the signal gets through
    timestamp = timestamp_on_set + duration
    timestamp_off_set = off(mkat, timestamp=timestamp)
    user_logger.warning('DEBUG: default sleep for {}'.format('1'))
    time.sleep(1)
    user_logger.warning('DEBUG: off {} ({})'.format(timestamp_off_set, time.ctime(timestamp_off_set)))
    # wait for duration + lead time
    delta_time = timestamp_off_set - time.time()
    user_logger.warning('DEBUG: now {}, sleep {}'.format(time.time(), delta_time))
    if not mkat.dry_run:
        user_logger.warning('DEBUG: this is not a dry-run')
        delta_time = timestamp_off_set - time.time()
        user_logger.warning('DEBUG: now {}, sleep {}'.format(time.time(), np.ceil(delta_time)))
        time.sleep(np.ceil(delta_time))
        user_logger.warning('DEBUG: now {}, slept {}'.format(time.time(), delta_time))
    else:
        delta_time = timestamp_off_set - session.time
        session.time = np.ceil(session.time + delta_time)
    return True


# set noise diode pattern
def pattern(mkat,  # mkat subarray object
            session,  # session object for correcting the time (only for now)
            nd_setup,  # noise diode pattern setup
            lead_time=3.0,  # lead time [sec]
            ):

    nd_antennas = nd_setup['antennas']  # antennas the nd pattern must be set on
    cycle_length = nd_setup['cycle_len']  # nd pattern length [sec]
    on_fraction = nd_setup['on_frac']  # on fraction of pattern lenght [%]
    msg = '\
Request noise diode pattern to repeat every {} sec, \
with {} sec on and apply pattern to {}'.format(
            cycle_length,
            float(cycle_length)*float(on_fraction),
            nd_antennas)
    user_logger.info(msg)

    if not mkat.dry_run:
        if mkat.sensor.sub_band.get_value() == 'l' and \
                float(cycle_length) > 20.:
                    msg = 'Maximum cycle length of L-band is 20 seconds'
                    raise RuntimeError(msg)
        # Improvement by Anton
        # Set noise diode period to multiple of the correlator integration time.
        dump_period = session.cbf.correlator.sensor.int_time.get_value()
        user_logger.warning('Correlator integration time {} [sec]'.format(1./dump_period))
        cycle_length = (round(cycle_length / dump_period) * dump_period)
        msg = 'Set noise diode period to multiple of correlator integration time:'
        msg += ' cycle length = {} [sec]'.format(cycle_length)
        user_logger.warning(msg)

    # Improvement by Anton
    # Try to trigger noise diodes on all antennas in array simultaneously.
    # - use integer second boundary as that is most likely be an exact
    #   time that DMC can execute at, and also fit a unix epoch time
    #   into a double precision float accurately
    # - add a default (3 second) lead time so enough time for all digitisers
    #   to be set up
    timestamp = np.ceil(time.time() + lead_time)
    msg = 'Set noise diode pattern to trigger at {}, with {} sec lead time'.format(
          timestamp, lead_time)
    user_logger.warning(msg)

    if nd_antennas == 'all':
        # Noise Diodes are triggered on all antennas in array simultaneously
        # add a second to ensure all digitisers set at the same time
        replies = mkat.ants.req.dig_noise_source(timestamp, on_fraction, cycle_length)
        if not mkat.dry_run:
            for ant in sorted(replies):
                reply, informs = replies[ant]
                # devcomm is still simm, but will not be dry-run
                if len(reply.arguments) > 2:
                    _nd_log_msg_(ant, reply, informs, verbose=True)
        else:
            msg = 'Set all noise diodes with timestamp {} ({})'.format(
                    int(timestamp), time.ctime(timestamp))
            user_logger.info(msg)
    else:
        sub_ants = [ant.name for ant in mkat.ants]
        if 'cycle' not in nd_antennas:
            sub_ants = [ant.strip() for ant in nd_antennas.split(',') if ant.strip() in sub_ants]
            user_logger.info('Antennas found in subarray, setting ND: {}'.format(','.join(sub_ants)))
        # Noise Diodes are triggered for selected antennas in the array
        for ant in sub_ants:
            ped = getattr(mkat, ant)
            the_reply = ped.req.dig_noise_source(timestamp, on_fraction, cycle_length)
            if not mkat.dry_run:
                reply, informs = the_reply
                # devcomm is still simm, but will not be dry-run
                if len(reply.arguments) > 2:
                    _nd_log_msg_(ant, reply, informs, verbose=True)
            else:
                msg = 'Set noise diode for antenna {} with timestamp {}'.format(
                        ant, timestamp)
                user_logger.info(msg)
            if nd_antennas == 'cycle':
                # add time [sec] to ensure all digitisers set at the same time
                timestamp += cycle_length * on_fraction

    # wait out the time needed to set the noise diode
#     delta_time = timestamp - time.time()
    if not mkat.dry_run:
        delta_time = timestamp - time.time()
        time.sleep(np.ceil(delta_time))
    else:
        delta_time = timestamp - session.time
        session.time = np.ceil(session.time + delta_time)

# -fin-
