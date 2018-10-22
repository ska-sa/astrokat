import time

from simulate import user_logger


# switch noise-source pattern off
def on(mkat, logging=True):
    if logging:
        user_logger.info('Switch noise-diode on')
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    timestamp = time.time() + 1
    mkat.ants.req.dig_noise_source(timestamp, 1)


# switch noise-source pattern off
def off(mkat, logging=True):
    if logging:
        user_logger.info('Switch noise-diode off')
    # Noise Diodes are triggered on all antennas in array simultaneously
    # add a second to ensure all digitisers set at the same time
    timestamp = time.time() + 1
    mkat.ants.req.dig_noise_source(timestamp, 0)


# fire noisediode before track
def trigger(mkat, nd_setup):
    cycle_length = nd_setup['cycle_len']
    user_logger.info('Firing noise diode for {}s before track on target'.format(cycle_length))
    on(mkat, logging=False)
    # TODO: add some overwrite func that will update the time for sims
    time.sleep(float(cycle_length))
    off(mkat, logging=False)


def pattern(mkat, nd_pattern, cycle_length, on_fraction):
    sub_ants = [ant.name for ant in mkat.ants]
    if nd_pattern == 'all':
        # Noise Diodes are triggered on all antennas in array simultaneously
        # add a second to ensure all digitisers set at the same time
        timestamp = time.time() + 1
        msg = 'Set all noise diode with timestamp {} ({})'.format(
                int(timestamp), time.ctime(timestamp))
        user_logger.info(msg)
        mkat.ants.req.dig_noise_source(timestamp, on_fraction, cycle_length)
    elif nd_pattern == 'cycle':
        # Noise Diodes should trigger one after another, within reason
        # add time [sec] to ensure all digitisers set at the same time
        timestamp = time.time() + 2
        for ant in sub_ants:
            msg = 'Set noise diode for antenna {} with timestamp {}'.format(
                    ant, timestamp)
            user_logger.info(msg)
            ped = getattr(mkat, ant)
            ped.req.dig_noise_source(timestamp, on_fraction, cycle_length)
            timestamp += cycle_length * on_fraction
    elif nd_pattern in sub_ants:
        # Noise Diodes are triggered for only one antenna in the array
        ant_name = nd_pattern
        user_logger.info('Set noise diode for antenna {}'.format(ant_name))
        ped = getattr(mkat, ant_name)
        ped.req.dig_noise_source('now', on_fraction, cycle_length)
    else:
        msg = 'Unknown ND cycle option, cannot apply requested pattern'
        raise ValueError(msg)

# -fin-
