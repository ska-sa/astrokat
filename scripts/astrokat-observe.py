# flake8: noqa
#!/usr/bin/env python
# Observation script and chronology check

import astrokat
import ephem
import katpoint
import os

import numpy as np

from astrokat import (
    NoTargetsUpError,
    NotAllTargetsUpError,
    read_yaml,
    katpoint_target,
    noisediode,
    correlator,
    )

libnames = ['collect_targets', 'user_logger', 'start_session', 'verify_and_connect']
try:
    lib = __import__('katcorelib', globals(), locals(), libnames, -1)
except ImportError:
    lib = __import__('astrokat', globals(), locals(), libnames, -1)
finally:
    for libname in libnames:
        globals()[libname] = getattr(lib, libname)


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
    target_list = np.recarray(ntargets, dtype=desc)
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
    session.label('track')
    if obs_type == 'drift_scan' and session.track(target, duration=0, announce=False):
        session.label('drift_scan')
        # set transit point as target
        target = drift_pointing_offset(target, duration=duration)

    if session.track(target, duration=duration):
        target_visible = True
        target_instructions['obs_cntr'] += 1

    target_instructions['last_observed'] = session.time
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


# finding each cadence target in order of target list
def cadence_target(session, observer, target_list):
    for target in target_list:
        if target['cadence'] > 0:
            if target['last_observed'] is None:
                return target

            delta_time = session.time - target['last_observed']
            if delta_time > target['cadence']:
                return target
    return False


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
            self.feng = correlator_config['Fengine']
            self.xeng = correlator_config['Xengine']
            self.beng = correlator_config['Bengine']
        # Check options and build KAT configuration,
        # connecting to proxies and devices
        # create single kat object, cannot repeatedly recreate
        self.array = verify_and_connect(opts)

    def __enter__(self):
        # Verify subarray setup correct for observation before doing any work
        if 'instrument' in self.opts.yaml.keys():
            if self.opts.yaml['instrument'] is not None:
                self.subarray_setup(self.array, self.opts.yaml['instrument'])

        # Set up noise diode if requested
        if 'noise_diode' in self.opts.yaml.keys():
            noise_pattern = self.opts.yaml['noise_diode']['pattern']
            cycle_length = self.opts.yaml['noise_diode']['cycle_len']
            on_fraction = self.opts.yaml['noise_diode']['on_fraction']
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
        # TODO: move this to a callable function, so do it only if worth while to observe and move back to body with session
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
        # Ensure known exit state before quitting
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
                sub_sensor = set(sub_sensor)
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
#     if 'noise_diode' in opts.yaml.keys():
#         nd_setup = opts.yaml['noise_diode']
#     else:
#         nd_setup = None

    # Each observation loop contains a number of observation cycles over LST ranges
    for observation_cycle in opts.yaml['observation_loop']:
        # Unpack all target information
        if not ('target_list' in observation_cycle.keys()):
            user_logger.warning('No targets provided - stopping script instead of hanging around')
            continue
        obs_targets = read_targets(observation_cycle['target_list'])
        target_list = obs_targets['target'].tolist()
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

        # Verify that it is worth while continuing with the observation
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

        # Description argument in instruction_set should be retired, but is needed by sessions
        # Assign proposal_description if available, else create a dummy
        if 'description' not in vars(opts):
            session_opts = vars(opts)
            description = 'Observation run'
            if 'proposal_description' in vars(opts):
                description = opts.proposal_description
            session_opts['description'] = description

        # Target observation loop
        with start_session(mkat.array, **vars(opts)) as session:
            session.standard_setup(**vars(opts))
            # Adding explicit init after "Capture-init failed" exception was encountered
            session.capture_init()

            # Go to first target before starting capture
            user_logger.info('Slewing to first target')
            observe(session, catalogue, obs_targets[0], _duration_=0)
            # Only start capturing once we are on target
            session.capture_start()

            # set up duration periods for observation control
            obs_duration = -1
            if 'durations' in opts.yaml:
                if 'obs_duration' in opts.yaml['durations']:
                    obs_duration = opts.yaml['durations']['obs_duration']

            done = False
            while not done:
                # # only a single run for dry-run at the moment, since timing calculation not sorted yet
                # if mkat.array.dry_run:
                #     done = True

                # Cycle through target list in order listed
                targets_visible = False

                for cnt, target in enumerate(obs_targets):
                    # check and observe all targets with cadences
                    while_cntr = 0
                    while True:
                        tgt = cadence_target(session, observer, obs_targets)
                        if not tgt:
                            break
                        if observe(session, catalogue, tgt):
                            targets_visible += True
                        while_cntr += 1
                        if while_cntr > len(obs_targets):
                            break

                    # # noise diode fire should be corrected in sessions
                    # if nd_setup: noisediode.trigger(mkat.array, nd_setup)
                    # observe non cadence target
                    if target['cadence'] < 0:
                        targets_visible = observe(session, catalogue, target)

                    # loop continuation checks
                    delta_time = session.time - session.start_time
                    if obs_duration > 0:
                        if delta_time >= obs_duration or \
                                (obs_duration-delta_time) < obs_targets[cnt]['duration']:
                            user_logger.info('Scheduled observation time lapsed - ending observation')
                            done = True
                            break
                    else:
                        user_logger.info('Observation list completed - ending observation')
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
            (session.time-session.start_time)))
        if len(obs_targets) > 0:
            user_logger.info("Targets observed :")
            for unique_target in np.unique(obs_targets['name']):
                cntrs = obs_targets[obs_targets['name'] == unique_target]['obs_cntr']
                durations = obs_targets[obs_targets['name'] == unique_target]['duration']
                user_logger.info('{} observed for {} seconds'.format(
                    unique_target,
                    np.sum(cntrs*durations)))
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

    # suppress the sessions noise diode, which is outdated
    # will use it again once functionality corrected
    # TODO: Currently the fire_noise_diode function in mkat_session.py is
    # outdated. This has to be updated to reflect the new noise diode pattern
    # implementation, and this default setting then removed.
    opts.nd_params = 'off'

    # get correlator settings from config files
    args_ = None
    if args:
        import argparse
        parser = argparse.ArgumentParser()
        for arg in args:
            # optsparser conversion does not handle description very well
            # corrections added here clears syntax errors that produce dry-run error in output
            if 'description' in arg:
                update_opts = vars(opts)
                update_opts[arg.split('=')[0].split('-')[-1]] = arg.split('=')[1]
            # catch other hidden arguments such as correlator settings
            if len(arg.split('=')[1]) > 1:
                arg = "{}='{}'".format(arg.split('=')[0], arg.split('=')[1])
            if arg.startswith(("-", "--")):
                parser.add_argument(arg)
        args_ = parser.parse_args(args)

    # unpack observation from observation plan
    if opts.yaml:
        opts.yaml = read_yaml(opts.yaml)
        # handle mapping of user friendly keys to CAM resource keys
        if 'instrument' in opts.yaml.keys():
            instrument = opts.yaml['instrument']
            if instrument is not None:
                if 'integration_period' in instrument.keys():
                    integration_period = float(instrument['integration_period'])
                    instrument['dump_rate'] = 1./integration_period
                    # remove integration_period here so as not to have to deal
                    # with it later in the observation structure

    # setup and observation
    with telescope(opts, args_) as mkat:
        run_observation(opts, mkat)

# -fin-
