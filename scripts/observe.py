# Observation script and chronology check

import os
import astrokat
import ephem

import numpy as np
from itertools import chain
import time
from datetime import datetime, timedelta

from astrokat import (
    NoTargetsUpError,
    NotAllTargetsUpError,
    read_yaml,
    katpoint_target,
    Observatory,
    )

try:
    from katcorelib.observe import (
        collect_targets,
        user_logger,
        start_session,
        verify_and_connect)
    from katcorelib.observe import (
        SessionCBF,
        SessionSDP)
except ImportError:
    from astrokat import(
        collect_targets,
        user_logger,
        start_session,
        verify_and_connect,
        )
import katpoint


def set_nd_pattern(kat, nd_pattern, cycle_length, on_fraction):
    sub_ants = [ant.name for ant in kat.ants]
    if nd_pattern == 'all':
        # Noise Diodes are triggered on all antennas in array simultaneously
        # add a second to ensure all digitisers set at the same time
        timestamp = time.time() + 1
        msg = 'Set all noise diode with timestamp {} ({})'.format(
                int(timestamp), time.ctime(timestamp))
        user_logger.info(msg)
        kat.ants.req.dig_noise_source(timestamp, on_fraction, cycle_length)
    elif nd_pattern == 'cycle':
        # Noise Diodes should trigger one after another, within reason
        # add time [sec] to ensure all digitisers set at the same time
        timestamp = time.time() + 2
        for ant in sub_ants:
            msg = 'Set noise diode for antenna {} with timestamp {}'.format(
                    ant, timestamp)
            user_logger.info(msg)
            ped = getattr(kat, ant)
            ped.req.dig_noise_source(timestamp, on_fraction, cycle_length)
            timestamp += cycle_length * on_fraction
    elif nd_pattern in sub_ants:
        # Noise Diodes are triggered for only one antenna in the array
        ant_name = nd_pattern
        user_logger.info('Set noise diode for antenna {}'.format(ant_name))
        ped = getattr(kat, ant_name)
        ped.req.dig_noise_source('now', on_fraction, cycle_length)
    else:
        msg = 'Unknown ND cycle option, cannot apply requested pattern'
        raise ValueError(msg)


def set_fengines(session,
        requant_gains=None,
        fft_shift=None):
    if not session.cbf.fengine.inputs:
        msg = 'Failed to get correlator input labels, cannot set the F-engine gains'
        raise RuntimeError(msg)

    for inp in session.cbf.fengine.inputs:
        # Set the gain to a single non complex number if needed
        if requant_gains is not None:
            # TODO: read and store values before assignment
            session.cbf.fengine.req.gain(inp, requant_gains)
            msg = 'F-engine {} gain set to {}'.format(
                    str(inp), requant_gains)
            user_logger.info(msg)
        # Set the FFT-shift schedule
        if fft_shift is not None:
            # TODO: read and store values before assignment
            session.cbf.fengine.req.fft_shift(fft_shift)
            msg = 'F-engine FFT shift schedule set to {}'.format(fft_shift)
            user_logger.info(msg)
    # TODO: return input values


# unpack targets to katpoint compatable format
def read_targets(target_items):
    desc = {
            'names': ('target', 'duration', 'cadence', 'last_observed'),
            'formats': (object, float, float, object),
            }
    ntargets = len(target_items)
    target_list = np.recarray(ntargets, dtype = desc)
    targets = []
    durations = []
    cadences = []
    for target_item in target_items:
        targets.append(katpoint_target(target_item))
        target_ = [item.strip() for item in target_item.split(',')]
        for item_ in target_:
            prefix = 'duration='
            if item_.startswith(prefix):
                duration = item_[len(prefix):]
            prefix = 'cadence='
            if item_.startswith(prefix):
                cadence = item_[len(prefix):]
            else:
                cadence = -1  # default is to observe without cadence
        durations.append(duration)
        cadences.append(cadence)
    target_list['target'] = targets
    target_list['duration'] = durations
    target_list['cadence'] = cadences
    target_list['last_observed'] = [None]*ntargets

    # import pprint
    # pprint.pprint(target_list)
    return target_list


# target observation functionality
def observe_target(
        session,
        observer,
        target,
        duration_=None):  # overwrite user time
    target_visible = False
    target_ = katpoint.Target(target['target'])
    duration = target['duration']
    if duration_ is not None:
        duration = duration_
    user_logger.info('Tracking target {} for {} sec'.format(
        target_.name, duration))
    # TODO: add some delay for slew time
    session.label('track')
    if session.track(target, duration=duration):
        target_visible = True
    #             # Perform a drift scan if selected
    #             if opts.drift_scan:
    #                 # set transit point as target
    #                 target = drift_pointing(target, duration)
    target['last_observed'] = observer.date.datetime()
    return target_visible

# def drift_pointing(target, duration):
#     transit_time = katpoint.Timestamp() + duration / 2.0
#     # Stationary transit point becomes new target
#     az, el = target.azel(timestamp=transit_time)
#     target = katpoint.construct_azel_target(katpoint.wrap_angle(az), el)
#     return target

class telescope:
    def __init__(self, opts, args=None):
        self.opts = opts
        try:
            correlator_config = read_yaml(args.correlator)
        except AttributeError:
            self.feng = self.xeng = self.beng = None
        else:
            self.feng=correlator_config['Fengine']
            self.xeng=correlator_config['Xengine']
            self.beng=correlator_config['Bengine']

    def __enter__(self):
        ## System setup before observation
        with verify_and_connect(self.opts) as kat:
            # Set up noise diode if requested
            if self.opts.noise_source is not None:
                msg = 'Set noise source behaviour to {} sec period with {} on fraction and apply pattern to {}'.format(
                        self.opts.noise_source[0],
                        self.opts.noise_source[1],
                        self.opts.noise_pattern)
                user_logger.info(msg)
                cycle_length, on_fraction = self.opts.noise_source
                set_nd_pattern(kat, self.opts.noise_pattern, cycle_length, on_fraction)
            # Ensure default setup before starting observation
            else:
                # switch noise-source pattern off (known setup starting observation)
                user_logger.info('Initialising with noise-diode off')
                kat.ants.req.dig_noise_source('now', 0)

            with start_session(kat, **vars(self.opts)) as session:
                # Update correlator settings
                if self.feng is not None:
                    set_fengines(session,
                                 requant_gains=self.feng['requant_gain'],
                                 fft_shift=self.feng['fft_shift'],
                                 )
#         # Names of antennas to use for beamformer if not all is desirable
#         set_bf_weights(kat, opts.bf_ants, opts.bf_weights)
        # return restore_values

    def __exit__(self, type, value, traceback):
        ## Ensure known exit state before quitting
        print 'TODO: Restore defaults'
        with verify_and_connect(self.opts) as kat:
            # switch noise-source pattern off (ensure this after each observation)
            user_logger.info('Ensuring noise-diode off')
            kat.ants.req.dig_noise_source('now', 0)


def run_observation(opts):

    # Check options and build KAT configuration,
    # connecting to proxies and devices
    with verify_and_connect(opts) as kat:

        # TODO: verify instrument setup, etc
        # TODO: on dev system get sensor with instrument and compare
        print opts.profile['instrument']
        # TODO: noise diode settings

        # Each observation loop contains a number of observation cycles over
        # LST ranges
        for observation_cycle in opts.profile['observation_loop']:

            print

            # Unpack all target information
            target_list = read_targets(observation_cycle['target_list'])
            the_targets = target_list['target'].tolist()
            calibrators = []
            if observation_cycle['calibration_standards'] is not None:
                calibrators = read_targets(observation_cycle['calibration_standards'])
                the_targets += calibrators['target'].tolist()
            targets = collect_targets(kat,
                    the_targets,
                    )
            observer = targets._antenna.observer

            # Only observe targets in valid LST range
            [start_lst, end_lst] = np.asarray(
                    observation_cycle['LST'].strip().split('-'),
                    dtype=float)
            user_logger.info('Observing targets over LST range {}-{}'.format(
                start_lst, end_lst))

            # Verify that it is worth while continuing with the observation
            # Only observe targets in current LST range
            local_lst = ephem.hours(observer.sidereal_time())
            if ephem.hours(local_lst) < ephem.hours(str(start_lst)) \
                    or ephem.hours(local_lst) > ephem.hours(str(end_lst)):
                user_logger.warning('{} outside LST range {}-{}'.format(
                        local_lst, start_lst, end_lst))
                continue

            ## Verify that it is worth while continuing with the observation
            # The filter functions uses the current time as timestamps
            # and thus incorrectly set the simulation timestamp
            if not kat.dry_run:
                # Quit early if there are no sources to observe
                if len(targets.filter(el_limit_deg=opts.horizon)) == 0:
                    raise NoTargetsUpError('No targets are currently visible - '
                                           'please re-run the script later')
                # Quit early if the observation requires all targets to be visible
                if opts.all_up and (len(targets.filter(el_limit_deg=opts.horizon)) != len(targets)):
                    raise NotAllTargetsUpError('Not all targets are currently visible - '
                                               'please re-run the script with --visibility for information')
            # Ludwig stats -- not sure if need to keep these
            user_logger.info('Imaging targets are [{}]'.format(
                             ', '.join([repr(target.name) for target in targets.filter(['~bpcal', '~gaincal'])])))
            user_logger.info("Bandpass calibrators are [{}]".format(
                             ', '.join([repr(bpcal.name) for bpcal in targets.filter('bpcal')])))
            user_logger.info("Gain calibrators are [{}]".format(
                             ', '.join([repr(gaincal.name) for gaincal in targets.filter('gaincal')])))

            ## Target observation loop
            with start_session(kat, **vars(opts)) as session:

                session.standard_setup(**vars(opts))
                session.capture_init()

                # If bandpass interval is specified,
                # force the first visit to be bandpass calibrator(s)
                target = None
                for cnt, calibrator in enumerate(calibrators):
                    if 'bpcal' in calibrator['target']:
                        target = calibrator
                        session.capture_start()
                        observe_target(session, observer, target)
                # Else go to first target
                if target is None:
                    target = target_list[0]
                    user_logger.info('Slewing to first target')
                    observe_target(session, observer, target, duration_=0)
                    # Only start capturing once we are on target
                    session.capture_start()

                done = False
                while not done:

                    # Cycle through target list in order listed
                    targets_visible = False
                    for target in target_list:
                        if observe_target(session, observer, target):
                            targets_visible = True

                        # Evaluate calibrator cadence
                        for calibrator in calibrators:
                            if calibrator['cadence'] < 0:
                                continue
                            if calibrator['last_observed'] is None:
                                if observe_target(session, observer, calibrator):
                                    targets_visible = True
                            else:
                                deltatime = observer.date.datetime() - calibrator['last_observed']
                                if deltatime.total_seconds() > calibrator['cadence']:
                                    if observe_target(session, observer, calibrator):
                                        targets_visible = True

                    # Cycle through calibrator list and evaluate those with
                    # cadence, while observing those that don't
                    for calibrator in calibrators:
                        if calibrator['cadence'] < 0 or \
                                calibrator['last_observed'] is None:
                            if observe_target(session, observer, calibrator):
                                targets_visible = True
                        else:
                            deltatime = observer.date.datetime() - calibrator['last_observed']
                            if deltatime.total_seconds() > calibrator['cadence']:
                                if observe_target(session, observer, calibrator):
                                    targets_visible = True

                    # End if there is nothing to do
                    if not targets_visible:
                        user_logger.warning('No targets are currently visible - stopping script instead of hanging around')
                        done = True
                    # Verify the LST range is still valid
                    local_lst = ephem.hours(observer.sidereal_time())
                    if ephem.hours(local_lst) > ephem.hours(str(end_lst)):
                        done = True

#             user_logger.info("Targets observed : %d (%d unique)",
#                              len(targets_observed), len(set(targets_observed)))
#             # print out a sorted list of target durations
#             ind = np.argsort(target_total_duration)
#             for i in reversed(ind):
#                 user_logger.info('Source %s observed for %.2f hrs',
#                                  targets.targets[i].description, target_total_duration[i] / 3600.0)

    print



if __name__ == '__main__':
    (opts, args) = astrokat.cli(
        os.path.basename(__file__),
        # remove redundant KAT-7 options
        x_long_opts=['--mode',
                     '--dbe-centre-freq',
                     '--no-mask',
                     '--centre-freq',
                     '--description'])

    # get correlator settings from config files
    args_ = None
    if args:
        import argparse
        parser = argparse.ArgumentParser()
        for arg in args:
            if arg.startswith(("-", "--")):
                parser.add_argument(arg)
        args_ = parser.parse_args(args)

    # package observation from profile configuration
    if opts.profile:
        opts.profile = read_yaml(opts.profile)

    # setup and observation
    with telescope(opts, args_) as system:
        print 'run_observation'
        run_observation(opts)

# -fin-
