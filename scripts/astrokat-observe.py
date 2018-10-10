# flake8: noqa
#!/usr/bin/env python
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
    noisediode,
    correlator,
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


# unpack targets to katpoint compatable format
# TODO: target description defined in function needs to be in configuration 
def read_targets(target_items):
    desc = {
            'names': (
                'name',
                'target',
                'duration',
                'cadence',
                'obs_type',
                'last_observed',
                'obs_cntr',
                ),
            'formats': (
                object,
                object,
                float,
                float,
                object,
                object,
                int,
                ),
            }
    ntargets = len(target_items)
    target_list = np.recarray(ntargets, dtype = desc)
    names = []
    targets = []
    durations = []
    cadences = []
    obs_types = []
    for target_item in target_items:
        [name_list, target] = katpoint_target(target_item)
        # When unpacking, katpoint's naming convention will be to use the first
        # name, or the name with the '*' if given. This unpacking mimics that
        # expected behaviour to ensure the target can be easily called by name
        name_list = [name.strip() for name in name_list.split('|')]
        prefered_name = filter(lambda x: x.startswith('*'), name_list)
        if prefered_name:
            target_name = prefered_name[0][1:]
        else:
            target_name = name_list[0]
        names.append(target_name)
        targets.append(target)
        target_ = [item.strip() for item in target_item.split(',')]
        cadence = -1  # default is to observe without cadence
        obs_type = 'track'  # assume tracking a target
        for item_ in target_:
            prefix = 'duration='
            if item_.startswith(prefix):
                duration = item_[len(prefix):]
            prefix = 'type='
            if item_.startswith(prefix):
                obs_type = item_[len(prefix):]
            prefix = 'cadence='
            if item_.startswith(prefix):
                cadence = item_[len(prefix):]
        durations.append(duration)
        obs_types.append(obs_type)
        cadences.append(cadence)
    target_list['name'] = names
    target_list['target'] = targets
    target_list['duration'] = durations
    target_list['cadence'] = cadences
    target_list['obs_type'] = obs_types
    target_list['last_observed'] = [None]*ntargets
    target_list['obs_cntr'] = [0]*ntargets

    # import pprint
    # pprint.pprint(target_list)
    return target_list


# target observation functionality
def observe(
        session,
        catalogue,
        target_instructions,
        _duration_=None,  # overwrite user settings
        ):
    target_visible = False

    target_name = target_instructions['name']
    target = catalogue[target_name]
    duration = target_instructions['duration']
    obs_type = target_instructions['obs_type']

    # functional overwrite of duration for system reasons
    if _duration_ is not None:
        duration = _duration_
    # simple way to get telescope to slew to target
    if duration <= 0:
        return session.track(target, duration=duration, announce=False)

    user_logger.info('{} {} {} for {} sec'.format(
        obs_type.capitalize(), target.tags[1], target_name, duration))

    # TODO: add some delay for slew time

    # do the different observations depending on requested type
    # check if target is visible before doing any work
    if obs_type == 'drift_scan' and session.track(target, duration=0, announce=False):
        # set transit point as target
        target = drift_pointing_offset(target, duration=duration)

    session.label('track')
    if session.track(target, duration=duration):
        target_visible = True
        target_instructions['obs_cntr'] += 1

    target_instructions['last_observed'] = catalogue._antenna.observer.date.datetime()
    return target_visible

def drift_pointing_offset(target, duration=60):
    try:
        obs_start_ts = target.antenna.observer.date
    except:
        obs_start_ts = katpoint.Timestamp()
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


class telescope(object):
    def __init__(self, opts, args=None):
        user_logger.info('Setting up telescope for observation')
        self.opts = opts
        # unpack user specified correlator setup values
        try:
            correlator_config = read_yaml(args.correlator)
        except AttributeError:
            self.feng = self.xeng = self.beng = None
        else:
            self.feng=correlator_config['Fengine']
            self.xeng=correlator_config['Xengine']
            self.beng=correlator_config['Bengine']
        # Check options and build KAT configuration,
        # connecting to proxies and devices
        # create single kat object, cannot repeatedly recreate
        self.array = verify_and_connect(opts)
        # create a single session to avoid bogus errors
        self.session = start_session(self.array, **vars(self.opts))

    def __enter__(self):
        # Verify subarray setup correct for observation before doing any work
        if 'instrument' in self.opts.template.keys():
            self.subarray_setup(self.array, self.opts.template['instrument'])

        # Set up noise diode if requested
        if 'noise_diode' in self.opts.template.keys():
            noise_pattern = self.opts.template['noise_diode']['pattern']
            cycle_length = self.opts.template['noise_diode']['cycle_len']
            on_fraction = self.opts.template['noise_diode']['on_fraction']
            noisediode.pattern(self.array, noise_pattern, cycle_length, on_fraction)

            msg = 'Set noise source behaviour to {} sec period with {} on fraction and apply pattern to {}'.format(
                    cycle_length,
                    on_fraction,
                    noise_pattern)
            user_logger.info(msg)
        else:
            # Ensure default setup before starting observation
            # switch noise-source pattern off (known setup starting observation)
            noisediode.off(self.array)

        # TODO: add part that implements noise diode fire per track
        # TODO: move this to a callable function, so do it only if worth while to observe
#         # Update correlator settings
#         if self.feng is not None:
#             set_fengines(self.session,
#                          requant_gains=self.feng['requant_gain'],
#                          fft_shift=self.feng['fft_shift'],
#                          )
# #         # Names of antennas to use for beamformer if not all is desirable
# #         set_bf_weights(self.array, opts.bf_ants, opts.bf_weights)
#         # keep restore_values
        return self

    def __exit__(self, type, value, traceback):
        user_logger.info('Returning telescope to startup state')
        ## Ensure known exit state before quitting
        # TODO: Return correlator settings to entry values
        # switch noise-source pattern off (ensure this after each observation)
        noisediode.off(self.array)
        self.array.disconnect()

    def subarray_setup(self, mkat, instrument):
        # current sensor list included in instrument
        # sub_ [
                # pool_resources,  # ptuse or specific antennas
                # product,        # correlator product
                # dump_rate,      # dumprate
                # band,           # band
                # ]
        # TODO: need to find a better way to implement the keyword mapping to
        # sensor data than these hard coded strings!!
        for key in instrument.keys():
            if key in ['integration_period']:
                continue  # pass over user specific option
            conf_param = instrument[key]
            sensor_name = 'sub_{}'.format(key)
            sub_sensor = mkat.sensor.get(sensor_name).get_value()
            if type(conf_param) is list:
                conf_param = set(conf_param)
            if type(sub_sensor) is list:
                sub_sensor= set(sub_sensor)
            if key == 'product' and conf_param in sub_sensor:
                continue
            elif key == 'pool_resources':
                pool_params = [str_.strip() for str_ in conf_param.split(',')]
                for param in pool_params:
                    if param not in sub_sensor:
                        raise RuntimeError('Subarray configation {} incorrect, {} required, {} found'.format(
                            sensor_name, param, sub_sensor))
            elif conf_param != sub_sensor:
                raise RuntimeError('Subarray configation {} incorrect, {} required, {} found'.format(
                    sensor_name, conf_param, sub_sensor))


#     def noise_diode(self, mkat, nd_setup):
#         if on_fraction > 0:
#         else:
#             msg = 'Noise diode will be fired on {} antenna(s) for {} sec before each track or scan'.format(
#                     noise_pattern,
#                     cycle_length)
#             user_logger.info(msg)
#             noisediode.off(mkat, logging=False)



def run_observation(opts, mkat):

    # TODO: undo outdated noise diode implementations
#     if 'nd-params' in vars(opts):
#         raise RuntimeError('Noide diode parameters to be check')
#     # noise-source on, activated when needed
#     if 'noise_diode' in opts.template.keys():
#         nd_setup = opts.template['noise_diode']
#     else:
#         nd_setup = None

    # Each observation loop contains a number of observation cycles over LST ranges
    for observation_cycle in opts.template['observation_loop']:
        # Unpack all target information
        if not ('target_list' in observation_cycle.keys()):
            user_logger.warning('No targets provided - stopping script instead of hanging around')
            continue
        obs_targets = read_targets(observation_cycle['target_list'])
        target_list = obs_targets['target'].tolist()
        # Extract targets with cadences
        cadence_list = []
        for target in obs_targets:
            if target['cadence'] > 0:
                cadence_list.append(target)
#         obs_calibrators = []
#         if 'calibration_standards' in observation_cycle.keys():
#             obs_calibrators = read_targets(observation_cycle['calibration_standards'])
#             target_list += obs_calibrators['target'].tolist()
        catalogue = collect_targets(mkat.array, target_list)
        observer = catalogue._antenna.observer

        # Only observe targets in valid LST range
        if 'LST' in observation_cycle.keys():
            [start_lst, end_lst] = np.asarray(
                    observation_cycle['LST'].strip().split('-'),
                    dtype=float)
        else:
            start_lst = 0.
            end_lst = 23.9
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
        if not mkat.array.dry_run:
            # Quit early if there are no sources to observe
            if len(catalogue.filter(el_limit_deg=opts.horizon)) == 0:
                raise NoTargetsUpError('No targets are currently visible - '
                                       'please re-run the script later')
            # Quit early if the observation requires all targets to be visible
            if opts.all_up and (len(catalogue.filter(el_limit_deg=opts.horizon)) != len(catalogue)):
                raise NotAllTargetsUpError('Not all targets are currently visible - '
                                           'please re-run the script with --visibility for information')
        user_logger.info('Imaging targets are [{}]'.format(
                         ', '.join([repr(target.name) for target in catalogue.filter(['~bpcal', '~gaincal'])])))
        user_logger.info("Bandpass calibrators are [{}]".format(
                         ', '.join([repr(bpcal.name) for bpcal in catalogue.filter('bpcal')])))
        user_logger.info("Gain calibrators are [{}]".format(
                         ', '.join([repr(gaincal.name) for gaincal in catalogue.filter('gaincal')])))

        if not 'description' in vars(opts):
            session_opts = vars(opts)
            description = 'Observation run'
            if 'proposal_description' in vars(opts):
                descrption = opts.proposal_description
            session_opts['description'] = description

        ## Target observation loop
        mkat.session.standard_setup(**vars(opts))
        mkat.session.capture_init()

        # If bandpass interval is specified,
        # force the first visit to be bandpass calibrator(s)
        bpcals_observed = False
        for cnt, source in enumerate(obs_targets):
            if 'bpcal' in source['target']:
                mkat.session.capture_start()
                bpcals_observed = observe(mkat.session, catalogue, source)
        # Else go to first target
        if not bpcals_observed:
            user_logger.info('Slewing to first target')
            for target in obs_targets:
                if observe(mkat.session,
                          catalogue,
                          target,
                          _duration_=0):
                    break
            # Only start capturing once we are on target
            mkat.session.capture_start()

        # set up duration periods for observation control
        obs_duration = -1
        if 'durations' in opts.template:
            if 'obs_duration' in opts.template['durations']:
                obs_duration = opts.template['durations']['obs_duration']
        shortest_target = np.min(obs_targets['duration'])
        start_time = observer.date.datetime()
        done = False
        while not done:

            # Cycle through target list in order listed
            targets_visible = False

            for target in obs_targets:
#                 # noise diode fire should be corrected in sessions
#                 if nd_setup: noisediode.trigger(mkat.array, nd_setup)
                # observe non cadence target
                if target['cadence'] < 0:
                    targets_visible = observe(mkat.session, catalogue, target)

                # Evaluate targets with cadence
                for cadence_source in cadence_list:
                    if cadence_source['last_observed'] is None:
                        targets_visible =  observe(mkat.session, catalogue, cadence_source)
                    else:
                        deltatime = observer.date.datetime() - cadence_source['last_observed']
                        if deltatime.total_seconds() > cadence_source['cadence']:
                            targets_visible = observe(mkat.session, catalogue, cadence_source)

                # loop continuation checks
                delta_time = (observer.date.datetime()-start_time).total_seconds()
                if obs_duration > 0:
                    if delta_time >= obs_duration or \
                        (obs_duration-delta_time) < shortest_target:
                        done = True
                        break
                else:
                    done = True

            # End if there is nothing to do
            if not targets_visible:
                user_logger.warning('No targets are currently visible - stopping script instead of hanging around')
                done = True
                # Verify the LST range is still valid
                local_lst = ephem.hours(observer.sidereal_time())
                if ephem.hours(local_lst) > ephem.hours(str(end_lst)):
                    done = True

        # display observation cycle statistics
        print
        user_logger.info("Observation loop statistics")
        user_logger.info("Total observation time {:.2f} seconds".format(
            (observer.date.datetime()-start_time).total_seconds()))
        if len(obs_targets) > 0:
            user_logger.info("Targets observed :")
            for target in obs_targets:
                user_logger.info('{} observation on {} observed for {} seconds'.format(
                    target['obs_type'],
                    target['name'],
                    float(target['obs_cntr'])*target['duration']))
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
            if 'description' in arg:
                update_opts = vars(opts)
                update_opts[arg.split('=')[0].split('-')[-1]] = arg.split('=')[1]
            if len(arg.split('=')[1]) > 1:
                arg = "{}='{}'".format(arg.split('=')[0],arg.split('=')[1])
            if arg.startswith(("-", "--")):
                parser.add_argument(arg)
        args_ = parser.parse_args(args)

    # unpack observation from template plan
    if opts.template:
        opts.template = read_yaml(opts.template)
        # handle mapping of user friendly keys to CAM resource keys
        if 'instrument' in opts.template.keys():
            instrument = opts.template['instrument']
            if 'integration_period' in instrument.keys():
                integration_period = float(instrument['integration_period'])
                instrument['dump_rate'] = 1./integration_period

    # setup and observation
    with telescope(opts, args_) as mkat:
        run_observation(opts, mkat)

# -fin-
