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
def get_targets(obs_loop):
    targets = []
    for key in obs_loop.keys():
        if key not in ['target_list', 'calibration_standards']:
            continue
        if obs_loop[key] is None: continue
        for target_item in obs_loop[key]:
            targets.append(katpoint_target(target_item))
    return targets

# def observe_targets(target, duration):

# def observation_loop(opts):

# def track_pointing(target, duration):

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
# #         set_bf_weights(kat, opts.bf_ants, opts.bf_weights)
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

        # TODO: LST calculation only relevant if not on live system
        observer = Observatory().get_observer(horizon=opts.horizon)
        # TODO: get desired start time from CAM
        desired_start_time = None
        for observation_cycle in opts.profile['observation_loop']:

            # Verify that it is worth while continuing with the observation
            targets = collect_targets(kat,
                    get_targets(observation_cycle),
                    )
            # Quit early if there are no sources to observe
            if len(targets.filter(el_limit_deg=opts.horizon)) == 0:
                raise NoTargetsUpError('No targets are currently visible - '
                                       'please re-run the script later')
            # Quit early if the observation requires all targets to be visible
            if opts.all_up and (len(targets.filter(el_limit_deg=opts.horizon)) != len(targets)):
                raise NotAllTargetsUpError('Not all targets are currently visible - '
                                           'please re-run the script with --visibility for information')


            # Only observe targets in valid LST range
            [start_lst, end_lst] = np.asarray(observation_cycle['LST'].strip().split('-'),
                    dtype=float)
            user_logger.info('Observing targets over LST range {}-{}'.format(
                start_lst, end_lst))

            # TODO: setting a fake datetime only for simulation
            if desired_start_time is None:
                observer.date = Observatory().lst2utc(start_lst)

            local_lst = ephem.hours(observer.sidereal_time())
            if ephem.hours(local_lst) < ephem.hours(str(start_lst)) \
                    or ephem.hours(local_lst) > ephem.hours(str(end_lst)):
                user_logger.warning('{} outside LST range {}-{}'.format(
                        local_lst, start_lst, end_lst))
                continue


            # Ludwig stats -- not sure if need to keep these
            user_logger.info('Imaging targets are [{}]'.format(
                             ', '.join([repr(target.name) for target in targets.filter(['~bpcal', '~gaincal'])])))
            user_logger.info("Bandpass calibrators are [{}]".format(
                             ', '.join([repr(bpcal.name) for bpcal in targets.filter('bpcal')])))
            user_logger.info("Gain calibrators are [{}]".format(
                             ', '.join([repr(gaincal.name) for gaincal in targets.filter('gaincal')])))


#         targets_observed = []
#         target_total_duration = [0.0] * len(targets)
#         targets_ = [target for target in targets.filter(['~bpcal', '~gaincal'])]

            ## Target observation loop
            with start_session(kat, **vars(opts)) as session:

                session.standard_setup(**vars(opts))
                session.capture_init()
                # Go to first target
                target = targets.targets[0]
                session.track(target, duration=0)

                # Only start capturing once we are on target
                session.capture_start()

    #             # Perform a drift scan if selected
    #             if opts.drift_scan:
    #                 # only select first target for now
    #                 targets = targets.targets[0]
    #                 # set transit point as target
    #                 target = drift_pointing(targets, opts.target_duration)

                done = False
                while not done:

    #             # If bandpass interval is specified, force the first visit to be to the bandpass calibrator(s)
    #             time_of_last_bpcal = 0

                    # Cycle through target list in order listed
                    targets_visible = False
                    print targets_visible
                    print observer.date
                    for target in observation_cycle['target_list']:
                        target_meta = Observatory().unpack_target(target)
                        target = katpoint.Target(katpoint_target(target))
                        duration = float(target_meta['duration'])

                        user_logger.info('Tracking target {} for {} sec'.format(
                            target.name, duration))
                        # TODO: add some delay for slew time
                        session.label('track')
                        if session.track(target, duration=duration):
                            targets_visible = True
                            observer.date = observer.date.datetime() + timedelta(seconds=duration)
    #                          targets_observed.append(target.description)
    #                          target_total_duration[n] += duration

                    # Cycle through calibrator list and evaluate those with
                    # cadence, while observing those that don't
                    for calibrator in observation_cycle['calibration_standards']:
                        calibrator_meta = Observatory().unpack_target(calibrator)
                        calibrator = katpoint.Target(katpoint_target(calibrator))
                        duration = float(calibrator_meta['duration'])
                        if 'cadence' in calibrator_meta.keys():
                            # TODO: evaluate cadence timedelta
                            continue

                        user_logger.info('Tracking calibrator {} for {} sec'.format(
                            calibrator.name, duration))
                        # TODO: add some delay for slew time
                        session.label('track')
                        if session.track(calibrator, duration=duration):
                            targets_visible = True
                            observer.date = observer.date.datetime() + timedelta(seconds=duration)

                    # End if there is nothing to do
                    if not targets_visible:
                        user_logger.warning('No targets are currently visible - stopping script instead of hanging around')
                        done = True
                    # Verify the LST range is still valid
                    local_lst = ephem.hours(observer.sidereal_time())
                    if ephem.hours(local_lst) > ephem.hours(str(end_lst)):
                        done = True

                    print targets_visible
                    print observer.date

                    # done = True
                print


#             # Loop through all targets to track
#                  for n, target in enumerate(targets):
#                      # If it is time for a bandpass calibrator to be visited on an interval basis, do so
#                      if opts.bpcal_interval is not None and time.time() - time_of_last_bpcal >= opts.bpcal_interval:
#                          time_of_last_bpcal = time.time()
#                          for bpcal in targets.filter('bpcal'):
#                              session.label('track')
#                              session.track(bpcal, duration=opts.bpcal_duration)
#                              target_total_duration[n] += opts.bpcal_duration
#                      # Visit source if it is not a bandpass calibrator
#                      # (or bandpass calibrators are not treated specially)
#                      # If there are no targets specified, assume the calibrators are the targets, else
#                      if opts.bpcal_interval is None or 'bpcal' not in targets.tags or not targets_:
#                          # Set the default track duration for a target with no recognised tags
#                          track_duration = opts.target_duration
#                          for tag in targets.tags:
#                              track_duration = duration.get(tag, track_duration)
#                      session.label('track')
# #                      session.track(target, duration=opts.target_duration)
#                      if session.track(target, duration=track_duration):
#                          targets_visible = True
#                          targets_observed.append(target.description)
#                          target_total_duration[n] += duration

#                 if not targets_visible:
#                     user_logger.warning('No targets are currently visible - '
#                                         'stopping script instead of hanging around')
#                     done = True

#             user_logger.info("Targets observed : %d (%d unique)",
#                              len(targets_observed), len(set(targets_observed)))
#             # print out a sorted list of target durations
#             ind = np.argsort(target_total_duration)
#             for i in reversed(ind):
#                 user_logger.info('Source %s observed for %.2f hrs',
#                                  targets.targets[i].description, target_total_duration[i] / 3600.0)


# def run_observation(opts, Feng=None, Xeng=None, Beng=None):
#     # Check options and build KAT configuration, connecting to proxies and devices
#     with verify_and_connect(opts) as kat:
# ## Ensure default setup before starting observation
#         # switch noise-source pattern off (known setup starting observation)
#         user_logger.info('Initialising with noise-diode off')
#         kat.ants.req.dig_noise_source('now', 0)

# ## Verify that it is worth while continuing with the observation
#         targets = collect_targets(kat, opts)
#         user_logger.info("Imaging targets are [%s]",
#                          ', '.join([repr(target.name) for target in targets.filter(['~bpcal', '~gaincal'])]))
#         user_logger.info("Bandpass calibrators are [%s]",
#                          ', '.join([repr(bpcal.name) for bpcal in targets.filter('bpcal')]))
#         user_logger.info("Gain calibrators are [%s]",
#                          ', '.join([repr(gaincal.name) for gaincal in targets.filter('gaincal')]))
#         targets_observed = []
#         target_total_duration = [0.0] * len(targets)
#         targets_ = [target for target in targets.filter(['~bpcal', '~gaincal'])]

#         # Quit early if there are no sources to observe
#         if len(targets.filter(el_limit_deg=opts.horizon)) == 0:
#             raise NoTargetsUpError('No targets are currently visible - '
#                                    'please re-run the script later')
#         # Quit early if the observation requires all targets to be visible
#         if opts.all_up and (len(targets.filter(el_limit_deg=opts.horizon)) != len(targets)):
#             raise NotAllTargetsUpError('Not all targets are currently visible - '
#                                        'please re-run the script with --visibility for information')

# ## System setup before observation
#         # Names of antennas to use for beamformer if not all is desirable
#         set_bf_weights(kat, opts.bf_ants, opts.bf_weights)

#         # Set up noise diode if requested
#         if opts.noise_source is not None:
#             user_logger.info('Set noise-source pattern')
#             cycle_length, on_fraction = opts.noise_source
#             set_nd_pattern(kat, opts.noise_pattern, cycle_length, on_fraction)


# ## Target observation loop
#         with start_session(kat, **vars(opts)) as session:

#             # Update correlator settings
#             if feng is not None:
#                 set_f_engines(session,
#                               requant_gains=feng['requant-gain'],
#                               fft_shift=feng['fft-shift'],
#                               )

#             session.standard_setup(**vars(opts))
#             session.capture_init()

#             # First target to visit
#             target = targets.targets[0]
#             # Perform a drift scan if selected
#             if opts.drift_scan:
#                 # only select first target for now
#                 targets = targets.targets[0]
#                 # set transit point as target
#                 target = drift_pointing(targets, opts.target_duration)

#             # Go to first target
#             session.track(target, duration=0)
#             # If bandpass interval is specified, force the first visit to be to the bandpass calibrator(s)
#             time_of_last_bpcal = 0
#             # Only start capturing once we are on target
#             session.capture_start()
#             # Loop through all targets to track
#             done = False
#             while not done:
#                  # cycle through list of targets
#                  for n, target in enumerate(targets):
#                      # If it is time for a bandpass calibrator to be visited on an interval basis, do so
#                      if opts.bpcal_interval is not None and time.time() - time_of_last_bpcal >= opts.bpcal_interval:
#                          time_of_last_bpcal = time.time()
#                          for bpcal in targets.filter('bpcal'):
#                              session.label('track')
#                              session.track(bpcal, duration=opts.bpcal_duration)
#                              target_total_duration[n] += opts.bpcal_duration
#                      # Visit source if it is not a bandpass calibrator
#                      # (or bandpass calibrators are not treated specially)
#                      # If there are no targets specified, assume the calibrators are the targets, else
#                      if opts.bpcal_interval is None or 'bpcal' not in targets.tags or not targets_:
#                          # Set the default track duration for a target with no recognised tags
#                          track_duration = opts.target_duration
#                          for tag in targets.tags:
#                              track_duration = duration.get(tag, track_duration)

#                     done = True

#             user_logger.info("Targets observed : %d (%d unique)",
#                              len(targets_observed), len(set(targets_observed)))
#             # print out a sorted list of target durations
#             ind = np.argsort(target_total_duration)
#             for i in reversed(ind):
#                 user_logger.info('Source %s observed for %.2f hrs',
#                                  targets.targets[i].description, target_total_duration[i] / 3600.0)



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
        user_logger.info('This is my time %s', str(ephem.now()))
        run_observation(opts)

# -fin-
