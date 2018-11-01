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
    get_lst,
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
                'noise_diode',
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
    nds = []
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
        duration = np.nan
        cadence = -1  # default is to observe without cadence
        obs_type = 'track'  # assume tracking a target
        nd = None
        for item_ in target_:
            prefix = 'duration='  # need to add 'duration =' as well for user stupidity
            if item_.startswith(prefix):
                duration = item_[len(prefix):]
            prefix = 'type='
            if item_.startswith(prefix):
                obs_type = item_[len(prefix):]
            prefix = 'cadence='
            if item_.startswith(prefix):
                cadence = item_[len(prefix):]
            prefix = 'nd='
            if item_.startswith(prefix):
                nd = item_[len(prefix):]
        durations.append(duration)
        obs_types.append(obs_type)
        cadences.append(cadence)
        nds.append(nd)
    target_list['name'] = names
    target_list['target'] = targets
    target_list['duration'] = durations
    target_list['cadence'] = cadences
    target_list['obs_type'] = obs_types
    target_list['noise_diode'] = nds
    target_list['last_observed'] = [None]*ntargets
    target_list['obs_cntr'] = [0]*ntargets

    return target_list


# target observation functionality
def observe(
        session,
        catalogue,
        target_instructions,
        **kwargs):
    target_visible = False

    target_name = target_instructions['name']
    target = catalogue[target_name]
    duration = target_instructions['duration']
    obs_type = target_instructions['obs_type']

    # functional overwrite of duration for system reasons
    if 'duration' in kwargs:
        duration = kwargs['duration']

    # simple way to get telescope to slew to target
    if duration < 0:
        return session.track(target, duration=0, announce=False)

    msg = '{} {} {}'.format(
        obs_type.capitalize(), target.tags[1], target_name)
    if not np.isnan(duration):  # scan types do not have durations
        msg += ' for {} sec'.format(duration)
    if np.isnan(duration) or duration > 1:
        user_logger.info(msg)

    # implement target specific noise diode behaviour
    # TODO: noise diode fire should be corrected in sessions
    # if nd_setup: noisediode.trigger(mkat.array, nd_setup)
    nd_setup = None
    if target_instructions['noise_diode'] is not None:
        if 'off' in target_instructions['noise_diode']:
            # if pattern specified, remember settings to reset
            if 'noise_diode' in kwargs and \
                    kwargs['noise_diode'] is not None:
                nd_setup = kwargs['noise_diode']
            # disable noise diode pattern for target
            noisediode.off(session.kat)
        else:
            noisediode.trigger(session.kat,
                    float(target_instructions['noise_diode']))

    # do the different observations depending on requested type
    # check if target is visible before doing any work
    if 'raster_scan' in obs_type or \
            'scan' in obs_type:  # compensating for ' and spaces around key values
        session.label(obs_type.strip())
        if 'raster_scan' in obs_type:
            scan_func = session.raster_scan
        else:
            scan_func = session.scan
        if obs_type in kwargs:  # user settings other than defaults
            target_visible = scan_func(target, **kwargs[obs_type])
        else:
            target_visible = scan_func(target)
        if target_visible:
            target_instructions['obs_cntr'] += 1
    else:
        session.label('track')
        if 'drift_scan' in obs_type and \
                session.track(target, duration=0, announce=False):
            session.label('drift_scan')
            # set transit point as target
            target = drift_pointing_offset(target, duration=duration)
        if session.track(target, duration=duration):
            target_visible = True
            target_instructions['obs_cntr'] += 1

    if nd_setup is not None:
        # restore pattern if programmed at setup
        noisediode.pattern(session.kat,
                nd_setup['antennas'],
                nd_setup['cycle_len'],
                nd_setup['on_frac'])

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
            self.subarray_setup(self.opts.yaml['instrument'])

        # TODO: noise diode implementations should be moved to sessions
        # Set up noise diode if requested
        if 'noise_diode' in self.opts.yaml.keys():
            self.noisediode_setup(self.opts.yaml['noise_diode'])
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

    def subarray_setup(self, instrument):
        # current sensor list included in instrument
        # sub_ [
                # pool_resources,  # ptuse or specific antennas
                # product,        # correlator product
                # dump_rate,      # dumprate
                # band,           # band
                # ]
        if self.opts.yaml['instrument'] is None:
            return
        for key in instrument.keys():
            conf_param = instrument[key]
            sensor_name = 'sub_{}'.format(key)
            sub_sensor = self.array.sensor.get(sensor_name).get_value()
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
                        raise RuntimeError('Subarray configuration {} incorrect, {} required, {} found'.format(
                            sensor_name, param, sub_sensor))
            elif conf_param != sub_sensor:
                raise RuntimeError('Subarray configuration {} incorrect, {} required, {} found'.format(
                    sensor_name, conf_param, sub_sensor))

    # set the noise diode pattern for the duration of the observation
    def noisediode_setup(self, nd_setup):
        if nd_setup is not None:
            noisediode.pattern(
                    self.array,
                    nd_setup['antennas'],
                    nd_setup['cycle_len'],
                    nd_setup['on_frac'],
                    )



def run_observation(opts, mkat):

    # extract control and observation information provided in observation file
    obs_plan_params = vars(opts)['yaml']
    # set up duration periods for observation control
    obs_duration = -1
    if 'durations' in obs_plan_params.keys():
        if 'obs_duration' in obs_plan_params.keys():
            obs_duration = obs_plan_params['durations']['obs_duration']

    # Each observation loop contains a number of observation cycles over LST ranges
    # For a single observation loop, only a start LST and duration is required
    for observation_cycle in obs_plan_params['observation_loop']:
        # Unpack all target information
        if not ('target_list' in observation_cycle.keys()):
            user_logger.warning('No targets provided - stopping script instead of hanging around')
            continue
        obs_targets = read_targets(observation_cycle['target_list'])
        target_list = obs_targets['target'].tolist()
        catalogue = collect_targets(mkat.array, target_list)
        observer = catalogue._antenna.observer

        # Only observe targets in valid LST range
        [start_lst, end_lst] = get_lst(observation_cycle['LST'])
        # Verify that it is worth while continuing with the observation
        # Only observe targets in current LST range
        local_lst = ephem.hours(observer.sidereal_time())
        if ephem.hours(local_lst) < ephem.hours(str(start_lst)):
            user_logger.warning('{} to early LST start {}'.format(
                    local_lst, start_lst))
            continue
        else:
            if end_lst is not None:
                if ephem.hours(local_lst) > ephem.hours(str(end_lst)):
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

        # TODO: the description requirement in sessions should be re-evaluated
        # since the schedule block has the description
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
            observe(session, catalogue, obs_targets[0], duration=-1)
            # Only start capturing once we are on target
            session.capture_start()

            done = False
            while not done:

                # Cycle through target list in order listed
                targets_visible = False

                for cnt, target in enumerate(obs_targets):
                    # TODO: add some delay for slew time

                    # check and observe all targets with cadences
                    while_cntr = 0
                    while True:
                        tgt = cadence_target(session, observer, obs_targets)
                        if not tgt:
                            break
                        if observe(session, catalogue, tgt, **obs_plan_params):
                            targets_visible += True
                        while_cntr += 1
                        if while_cntr > len(obs_targets):
                            break

                    # observe non cadence target
                    if target['cadence'] < 0:
                        targets_visible = observe(
                                session,
                                catalogue,
                                target,
                                **obs_plan_params)

                    # loop continuation checks
                    delta_time = session.time - session.start_time
                    if obs_duration > 0:
                        if delta_time >= obs_duration or \
                                (obs_duration-delta_time) < obs_targets[cnt]['duration']:
                            user_logger.info('Scheduled observation time lapsed - ending observation')
                            done = True
                            break

                if obs_duration < 0:
                    user_logger.info('Observation list completed - ending observation')
                    done = True

                # End if there is nothing to do
                if not targets_visible:
                    user_logger.warning('No targets are currently visible - stopping script instead of hanging around')
                    done = True
                # Verify the LST range is still valid
                local_lst = ephem.hours(observer.sidereal_time())
                if end_lst is not None:
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
                if np.isnan(durations).any():
                    user_logger.info('{} observed {} times'.format(
                        unique_target,
                        np.sum(cntrs)))
                else:
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
                    del instrument['integration_period']
        # verify required information in observation loop before continuing
        if 'durations' in opts.yaml.keys():
            if opts.yaml['durations'] is None:
                msg = 'durations primary key cannot be empty in observation YAML file'
                raise RuntimeError(msg)
        if 'observation_loop' not in opts.yaml.keys():
            raise RuntimeError('Nothing to observer, exiting')
        if opts.yaml['observation_loop'] is None:
            raise RuntimeError('Empty observation loop, exiting')
        for obs_loop in opts.yaml['observation_loop']:
            if type(obs_loop) is str:
                raise RuntimeError('Expected observation list, got string')
            if 'LST' not in obs_loop.keys():
                raise RuntimeError('Observation LST not provided, exiting')
            if 'target_list' not in obs_loop.keys():
                raise RuntimeError('Empty target list, exiting')

    # setup and observation
    with telescope(opts, args_) as mkat:
        run_observation(opts, mkat)

# -fin-
