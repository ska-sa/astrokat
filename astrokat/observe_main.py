# Observation script and chronology check

import ephem
import logging
import numpy as np
import os
import time

import astrokat
from astrokat.utility import datetime2timestamp, timestamp2datetime
from astrokat import (
    NoTargetsUpError,
    NotAllTargetsUpError,
    read_yaml,
    get_lst,
    katpoint_target,
    noisediode,
    # correlator,
    scans,
    )

libnames = ['collect_targets', 'user_logger', 'start_session', 'verify_and_connect']
try:
    lib = __import__('katcorelib', globals(), locals(), libnames, -1)
except ImportError:
    lib = __import__('astrokat', globals(), locals(), libnames, -1)
finally:
    for libname in libnames:
        globals()[libname] = getattr(lib, libname)


# unpack targets to katpoint compatible format
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
            # TODO: need to add 'duration =' as well for user stupidity
            prefix = 'duration='
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
        target_info,
        **kwargs):
    target_visible = False

    target_name = target_info['name']
    target = target_info['target']
    duration = target_info['duration']
    obs_type = target_info['obs_type']

    # simple way to get telescope to slew to target
    if 'slewonly' in kwargs:
        return session.track(target, duration=0., announce=False)

    msg = 'Initialising {} {} {}'.format(
        obs_type.capitalize(), target.tags[1], target_name)
    if not np.isnan(duration):  # scan types do not have durations
        msg += ' for {} sec'.format(duration)
    if np.isnan(duration) or duration > 1:
        user_logger.info(msg)

    # implement target specific noise diode behaviour
    nd_setup = None
    nd_period = None
    if target_info['noise_diode'] is not None:
        if 'off' in target_info['noise_diode']:
            # if pattern specified, remember settings to reset
            if 'noise_diode' in kwargs:
                if kwargs['noise_diode'] is not None:
                    nd_setup = kwargs['noise_diode']
            # disable noise diode pattern for target
            noisediode.off(session.kat)
        else:
            nd_period = float(target_info['noise_diode'])

    # do the different observations depending on requested type
    session.label(obs_type.strip())
    user_logger.trace('TRACE: performing {} observation on {}'
                      .format(obs_type,
                              target))
    if 'scan' in obs_type:  # compensating for ' and spaces around key values
        if 'drift_scan' in obs_type:
            scan_func = scans.drift_scan
        # TODO: fix raster scan and remove this scan hack
        elif 'forwardscan' in obs_type:
            scan_func = scans.forwardscan
            obs_type = 'scan'
        elif 'reversescan' in obs_type:
            scan_func = scans.reversescan
            obs_type = 'scan'
        elif 'return_scan' in obs_type:
            scan_func = scans.return_scan
            obs_type = 'scan'
        elif 'raster_scan' in obs_type:
            scan_func = scans.raster_scan
        else:
            scan_func = scans.scan
        if obs_type in kwargs:  # user settings other than defaults
            target_visible = scan_func(session,
                                       target,
                                       nd_period=nd_period,
                                       **kwargs[obs_type])
        else:
            target_visible = scan_func(session,
                                       target,
                                       nd_period=nd_period)
    else:  # track is default
        if nd_period is not None:
            user_logger.trace('TRACE: ts before nd trigger {} for {}'
                              .format(time.time(),
                                      nd_period))
            noisediode.trigger(session.kat, session, duration=nd_period)
            user_logger.trace('TRACE: ts after nd trigger {}'
                              .format(time.time()))
        user_logger.debug('DEBUG: Starting {}s track on target: {} ({})'
                          .format(duration,
                                  time.time(),
                                  time.ctime(time.time())))
        if session.track(target, duration=duration):
            target_visible = True
    user_logger.trace('TRACE: ts after {} {}'
                      .format(obs_type,
                              time.time()))

    if nd_setup is not None:
        # restore pattern if programmed at setup
        noisediode.pattern(session.kat, session, nd_setup)

    return target_visible


# finding each cadence target in order of target list
def cadence_target(target_list):
    for target in target_list:
        if target['cadence'] > 0:
            if target['last_observed'] is None:
                return target
            delta_time = time.time() - target['last_observed']
            if delta_time > target['cadence']:
                return target
    return False


# check target visibility
def above_horizon(katpt_target, horizon=20.):
    [azim, elev] = katpt_target.azel(time.time())
    return (elev >= ephem.degrees(str(horizon)))


class Telescope(object):
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
        if 'instrument' in self.opts.obs_plan_params.keys():
            self.subarray_setup(self.opts.obs_plan_params['instrument'])

        # TODO: noise diode implementations should be moved to sessions
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
        if self.opts.obs_plan_params['instrument'] is None:
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
                        raise RuntimeError('Subarray configuration {} error, '
                                           '{} required, {} found'
                                           .format(sensor_name,
                                                   param,
                                                   sub_sensor))
            elif conf_param != sub_sensor:
                raise RuntimeError('Subarray configuration {} error, '
                                   '{} required, {} found'
                                   .format(sensor_name,
                                           conf_param,
                                           sub_sensor))


def run_observation(opts, kat):

    # extract control and observation information provided in observation file
    obs_plan_params = opts.obs_plan_params
    # remove observation specific instructions housed in YAML file
    del opts.obs_plan_params

    # set up duration periods for observation control
    obs_duration = -1
    if 'durations' in obs_plan_params:
        if 'obs_duration' in obs_plan_params['durations']:
            obs_duration = obs_plan_params['durations']['obs_duration']

    # Each observation loop contains a number of observation cycles over LST ranges
    # For a single observation loop, only a start LST and duration is required
    for observation_cycle in obs_plan_params['observation_loop']:
        # Unpack all target information
        if not ('target_list' in observation_cycle.keys()):
            user_logger.error('No targets provided - '
                              'stopping script instead of hanging around')
            continue
        obs_targets = read_targets(observation_cycle['target_list'])
        target_list = obs_targets['target'].tolist()
        # build katpoint catalogues for tidy handling of targets
        catalogue = collect_targets(kat.array, target_list)
        for tgt in obs_targets:
            tgt['target'] = catalogue[tgt['name']]
        # observer object handle to track the observation timing in a more user friendly way
        observer = catalogue._antenna.observer

        # Only observe targets in valid LST range
        [start_lst, end_lst] = get_lst(observation_cycle['LST'])


        # Verify that it is worth while continuing with the observation
        # The filter functions uses the current time as timestamps
        # and thus incorrectly set the simulation timestamp
        if not kat.array.dry_run:
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
        with start_session(kat.array, **vars(opts)) as session:
            session.standard_setup(**vars(opts))
            start_datetime = timestamp2datetime(time.time())
            observer.date = ephem.Date(start_datetime)
            user_logger.trace('TRACE: requested start time ({}) {}'
                              .format(datetime2timestamp(start_datetime),
                                      start_datetime))

            user_logger.trace('TRACE: observer at start\n {}'
                              .format(observer))

            # Verify the observation is in a valid LST range
            # and that it is worth while continuing with the observation
            # Do not use float() values, ephem.hours does not convert as expected
            local_lst = observer.sidereal_time()
            # Only observe targets in current LST range
            if start_lst < end_lst:
                in_range = ((ephem.hours(local_lst) >= ephem.hours(str(start_lst)))
                            and (ephem.hours(local_lst) < ephem.hours(str(end_lst))))
                if not in_range:
                    user_logger.error('Local LST outside LST range {}-{}'
                                      .format(ephem.hours(str(start_lst)),
                                              ephem.hours(str(end_lst))))
                    continue
            else:
                # else assume rollover at midnight to next day
                out_range = ((ephem.hours(local_lst) < ephem.hours(str(start_lst)))
                             and (ephem.hours(local_lst) > ephem.hours(str(end_lst))))
                if out_range:
                    user_logger.error('Local LST outside LST range {}-{}'
                                      .format(ephem.hours(str(start_lst)),
                                              ephem.hours(str(end_lst))))
                    continue
            # TODO: setup of noise diode pattern should be moved to sessions so it happens in the line above
            if 'noise_diode' in obs_plan_params.keys():
                noisediode.pattern(kat.array, session, obs_plan_params['noise_diode'])

            # Adding explicit init after "Capture-init failed" exception was encountered
            session.capture_init()
            user_logger.debug('DEBUG: Initialise capture start with timestamp {} ({})'
                              .format(int(time.time()),
                                      timestamp2datetime(time.time())))

            # Go to first target before starting capture
            user_logger.info('Slewing to first target')
            observe(session, obs_targets[0], slewonly=True)
            # Only start capturing once we are on target
            session.capture_start()
            user_logger.trace('TRACE: capture start time after slew ({}) {}'
                              .format(time.time(),
                                      timestamp2datetime(time.time())))
            user_logger.trace('TRACE: observer after slew\n {}'
                              .format(observer))

            done = False
            sanity_cntr = 0
            while not done:
                # small errors can cause an infinite loop here
                # preventing infinite loops
                sanity_cntr += 1
                if sanity_cntr > 100000:
                    user_logger.error('While limit counter has reached {}, exiting'
                                      .format(sanity_cntr))
                    break

                # Cycle through target list in order listed
                targets_visible = False
                time_remaining = obs_duration

                for cnt, target in enumerate(obs_targets):
                    katpt_target = target['target']
                    user_logger.debug('DEBUG: {} {}'
                                      .format(cnt, target))
                    user_logger.trace('TRACE: initial observer for target\n {}'
                                      .format(observer))
                    # check target visible before doing anything
                    if not above_horizon(katpt_target, horizon=opts.horizon):
                        show_horizon_status = True
                        # warning for cadence targets only when they are due
                        if (target['cadence'] > 0 and
                                target['last_observed'] is not None):
                            delta_time = time.time() - target['last_observed']
                            show_horizon_status = (delta_time >= target['cadence'])
                        if show_horizon_status:
                            user_logger.warn('Target {} below {} deg horizon, continuing'
                                             .format(target['name'], opts.horizon))
                        continue
                    user_logger.trace('TRACE: observer after horizon check\n {}'
                                      .format(observer))

                    # check and observe all targets with cadences
                    while_cntr = 0
                    cadence_targets = list(obs_targets)
                    while True:
                        tgt = cadence_target(cadence_targets)
                        if not tgt:
                            break
                        # check enough time remaining to continue
                        if (obs_duration > 0 and
                                time_remaining < tgt['duration']):
                            done = True
                            break
                        # check target visible before doing anything
                        user_logger.trace('TRACE: cadence target\n {}\n {}'
                                          .format(tgt,
                                                  catalogue[tgt['name']]))
                        user_logger.trace('TRACE: initial observer for cadence target\n {}'
                                          .format(observer))
                        user_logger.trace('TRACE: observer before track\n {}'
                                          .format(observer))
                        user_logger.trace('TRACE: target observation # {} last observed {}'
                                          .format(tgt['obs_cntr'],
                                                  tgt['last_observed']))
                        if above_horizon(catalogue[tgt['name']], horizon=opts.horizon):
                            if observe(session, tgt, **obs_plan_params):
                                targets_visible += True
                                tgt['obs_cntr'] += 1
                                tgt['last_observed'] = time.time()
                            else:
                                # target not visibile to sessions anymore
                                cadence_targets.remove(tgt)
                            user_logger.trace('TRACE: observer after track\n {}'
                                              .format(observer))
                            user_logger.trace('TRACE: target observation # {} last observed {}'
                                              .format(tgt['obs_cntr'],
                                                      tgt['last_observed']))
                        else:
                            cadence_targets.remove(tgt)
                        while_cntr += 1
                        if while_cntr > len(obs_targets):
                            break
                    if done:
                        break
                    user_logger.trace('TRACE: observer after cadence\n {}'
                                      .format(observer))

                    # observe non cadence target
                    if target['cadence'] < 0:
                        user_logger.trace('TRACE: normal target\n {}'
                                          .format(target))
                        user_logger.trace('TRACE: observer before track\n {}'
                                          .format(observer))
                        user_logger.trace('TRACE: ts before observe {}'
                                          .format(time.time()))
                        user_logger.trace('TRACE: target last observed {}'
                                          .format(target['last_observed']))

                        targets_visible += observe(
                                session,
                                target,
                                **obs_plan_params)

                        user_logger.trace('TRACE: observer after track\n {}'
                                          .format(observer))
                        user_logger.trace('TRACE: ts after observe {}'
                                          .format(time.time()))
                        if targets_visible:
                            target['obs_cntr'] += 1
                            target['last_observed'] = time.time()
                        user_logger.trace('TRACE: target observation # {} last observed {}'
                                          .format(target['obs_cntr'],
                                                  target['last_observed']))
                        user_logger.trace('TRACE: observer after track\n {}'
                                          .format(observer))

                    # loop continuation checks
                    delta_time = time.time() - session.start_time
                    user_logger.trace('TRACE: time elapsed {} sec'
                                      .format(delta_time))
                    user_logger.trace('TRACE: total obs duration {} sec'
                                      .format(obs_duration))
                    if obs_duration > 0:
                        time_remaining = obs_duration - delta_time
                        user_logger.trace('TRACE: time remaining {} sec'
                                          .format(time_remaining))
                        next_target = obs_targets[(cnt+1) % len(obs_targets)]
                        for next_tgt_idx in range(cnt+1, len(obs_targets)):
                            next_target = obs_targets[next_tgt_idx % len(obs_targets)]
                            user_logger.trace('TRACE: time needed for next obs {} sec'
                                              .format(next_target['cadence']))
                            if next_target['cadence'] > 0:
                                continue
                            user_logger.trace('TRACE: time needed for next obs {} sec'
                                              .format(next_target['duration']))
                        if time_remaining < 1. or \
                                time_remaining < next_target['duration']:
                            user_logger.info('Scheduled observation time lapsed - ending observation')
                            done = True
                            break

                # during dry-run when sessions exit time is reset so will be incorrect outside the loop
                observation_timer = time.time()

                if obs_duration < 0:
                    user_logger.info('Observation list completed - ending observation')
                    done = True

                # End if there is nothing to do
                if not targets_visible:
                    user_logger.warning('No more targets to observe - stopping script instead of hanging around')
                    done = True

        user_logger.trace('TRACE: observer at end\n {}'
                          .format(observer))
        # display observation cycle statistics
        print
        user_logger.info("Observation loop statistics")
        # total_obs_time = time.time() - session.start_time
        total_obs_time = observation_timer - session.start_time
        if obs_duration < 0:
            user_logger.info('Single run through observation target list')
        else:
            user_logger.info("Desired observation time {:.2f} sec ({:.2f} min)"
                             .format(obs_duration, obs_duration/60.))
        user_logger.info("Total observation time {:.2f} sec ({:.2f} min)"
                         .format(total_obs_time, total_obs_time/60.))
        if len(obs_targets) > 0:
            user_logger.info("Targets observed :")
            for unique_target in np.unique(obs_targets['name']):
                cntrs = obs_targets[obs_targets['name'] == unique_target]['obs_cntr']
                durations = obs_targets[obs_targets['name'] == unique_target]['duration']
                if np.isnan(durations).any():
                    user_logger.info('{} observed {} times'
                                     .format(unique_target,
                                             np.sum(cntrs)))
                else:
                    user_logger.info('{} observed for {} sec'
                                     .format(unique_target,
                                             np.sum(cntrs*durations)))
        print


def main(args):
    (opts, args) = astrokat.cli(
        os.path.basename(__file__),
        # remove redundant KAT-7 options
        x_long_opts=['--mode',
                     '--dbe-centre-freq',
                     '--no-mask',
                     '--centre-freq'],
        args=args)

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
            # catch other hidden arguments such as correlator settings
            if len(arg.split('=')[1]) > 1:
                arg = "{}='{}'".format(arg.split('=')[0], arg.split('=')[1])
            if arg.startswith(("-", "--")):
                parser.add_argument(arg)
        args_ = parser.parse_args(args)

    # unpack observation from observation plan
    if opts.yaml:
        opts.obs_plan_params = read_yaml(opts.yaml)

    if opts.debug:
        user_logger.setLevel(logging.DEBUG)
    if opts.trace:
        user_logger.setLevel(logging.TRACE)

    # setup and observation
    with Telescope(opts, args_) as kat:
        run_observation(opts, kat)


# -fin-
