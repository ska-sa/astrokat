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



def _nd_switch_(mkat, switch):
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    timestamp = time.time() + lead_time
    mkat.ants.req.dig_noise_source(timestamp, 1)
    if not mkat.dry_run:
        time.sleep(float(lead_time))


# switch noise-source pattern off
def on(mkat, lead_time=2., logging=True):
    if logging:
        user_logger.info('Switch noise-diode on')
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    timestamp = time.time() + lead_time
    mkat.ants.req.dig_noise_source(timestamp, 1)
    if not mkat.dry_run:
        time.sleep(float(lead_time))
    return True


# switch noise-source pattern off
def off(mkat, lead_time=2., logging=True):
    if logging:
        user_logger.info('Switch noise-diode off')
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    timestamp = time.time() + lead_time
    mkat.ants.req.dig_noise_source(timestamp, 0)
    return True

# fire noise diode before track
def trigger(mkat, duration=None):
    if duration is None:
        return True  # nothing to do
    msg = 'Firing noise diode for {}s before target observation'.format(
            duration)
    user_logger.info(msg)
    on(mkat, logging=False)
    # TODO: add some overwrite func that will update the time for sims
    if not mkat.dry_run:
        time.sleep(float(duration))
    off(mkat, logging=False)
    return True

# set noise diode pattern
def pattern(mkat,  # mkat subarray object
            nd_antennas,  # antennas the nd pattern must be set on
            cycle_length,  # nd pattern length [sec]
            on_fraction,  # on fraction of pattern lenght [%]
            lead_time=2.0,  # lead time [sec]
            ):

    def nd_log_msg(reply, informs):
        actual_time = float(reply.arguments[1])
        actual_on_frac = float(reply.arguments[2])
        actual_cycle = float(reply.arguments[3])
        msg = 'Noise diode for antenna {} set at {}. '.format(
                ant, actual_time)
        msg += 'Pattern set as {} sec on of {} sec cycle length'.format(
                actual_on_frac*actual_cycle, actual_cycle)
        user_logger.info(msg)


    if not mkat.dry_run:
        if mkat.sensor.sub_band.get_value() == 'l' and \
                float(cycle_length) > 20.:
                    msg = 'Maximum cycle length of L-band is 20 seconds'
                    raise RuntimeError(msg)
        # Improvement by Anton
        # Set noise diode period to multiple of the correlator integration time.
        dump_period = session.cbf.correlator.sensor.int_time.get_value()
        cycle_length = (round(cycle_length / dump_period) * dump_period)

    msg = '\
Initialising noise diode pattern for {} sec period \
with {} on fraction and apply pattern to {}'.format(
            cycle_length,
            on_fraction,
            nd_antennas)
    user_logger.info(msg)

    # Improvement by Anton
    # Try to trigger noise diodes on all antennas in array simultaneously.
            # - use integer second boundary as that is most likely be an exact
            #   time that DMC can execute at, and also fit a unix epoch time
            #   into a double precision float accurately
            # - add a default (2 second) lead time so enough time for all digitisers
            #   to be set up
    timestamp = np.ceil(time.time()) + lead_time

    if nd_antennas == 'all':
        # Noise Diodes are triggered on all antennas in array simultaneously
        # add a second to ensure all digitisers set at the same time
        replies = mkat.ants.req.dig_noise_source(timestamp, on_fraction, cycle_length)
        if not mkat.dry_run:
            for ant in sorted(replies):
                reply, informs = replies[ant]
                nd_log_msg(replies[ant])
        else:
            msg = 'Set all noise diodes with timestamp {} ({})'.format(
                    int(timestamp), time.ctime(timestamp))
            user_logger.info(msg)
    else:
        sub_ants = [ant.name for ant in mkat.ants]
        if not 'cycle' in nd_antennas:
            sub_ants = [ant.strip() for ant in nd_antennas.split(',') if ant.strip() in sub_ants]
        # Noise Diodes are triggered for selected antennas in the array
        for ant in sub_ants:
            ped = getattr(mkat, ant)
            the_reply = ped.req.dig_noise_source(timestamp, on_fraction, cycle_length)
            if not mkat.dry_run:
                reply, informs = the_reply
                nd_log_msg(reply, informs)
            else:
                msg = 'Set noise diode for antenna {} with timestamp {}'.format(
                        ant, timestamp)
                user_logger.info(msg)
            if nd_antennas == 'cycle':
                # add time [sec] to ensure all digitisers set at the same time
                timestamp += cycle_length * on_fraction

# -fin-
