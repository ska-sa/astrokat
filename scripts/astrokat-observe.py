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


# # switch noise-source pattern off
# def nd_on(mkat, logging=True):
#     if logging: user_logger.info('Switch noise-diode on')
#     # Noise Diodes are triggered on all antennas in array simultaneously
#     # add a second to ensure all digitisers set at the same time
#     timestamp = time.time() + 1
#     mkat.ants.req.dig_noise_source(timestamp, 1)

# # switch noise-source pattern off
# def nd_off(mkat, logging=True):
#     if logging: user_logger.info('Switch noise-diode off')
#     # Noise Diodes are triggered on all antennas in array simultaneously
#     # add a second to ensure all digitisers set at the same time
#     timestamp = time.time() + 1
#     mkat.ants.req.dig_noise_source(timestamp, 0)

# # fire noisediode before track
# def nd_fire(mkat, nd_setup):
#     cycle_length = nd_setup['cycle_len']
#     user_logger.info('Firing noise diode for {}s before track on target'.format(cycle_length))
#     nd_on(mkat, logging=False)
#     # TODO: add some overwrite func that will update the time for sims
#     time.sleep(float(cycle_length))
#     nd_off(mkat, logging=False)

# def set_nd_pattern(mkat, nd_pattern, cycle_length, on_fraction):
#     sub_ants = [ant.name for ant in mkat.ants]
#     if nd_pattern == 'all':
#         # Noise Diodes are triggered on all antennas in array simultaneously
#         # add a second to ensure all digitisers set at the same time
#         timestamp = time.time() + 1
#         msg = 'Set all noise diode with timestamp {} ({})'.format(
#                 int(timestamp), time.ctime(timestamp))
#         user_logger.info(msg)
#         mkat.ants.req.dig_noise_source(timestamp, on_fraction, cycle_length)
#     elif nd_pattern == 'cycle':
#         # Noise Diodes should trigger one after another, within reason
#         # add time [sec] to ensure all digitisers set at the same time
#         timestamp = time.time() + 2
#         for ant in sub_ants:
#             msg = 'Set noise diode for antenna {} with timestamp {}'.format(
#                     ant, timestamp)
#             user_logger.info(msg)
#             ped = getattr(mkat, ant)
#             ped.req.dig_noise_source(timestamp, on_fraction, cycle_length)
#             timestamp += cycle_length * on_fraction
#     elif nd_pattern in sub_ants:
#         # Noise Diodes are triggered for only one antenna in the array
#         ant_name = nd_pattern
#         user_logger.info('Set noise diode for antenna {}'.format(ant_name))
#         ped = getattr(mkat, ant_name)
#         ped.req.dig_noise_source('now', on_fraction, cycle_length)
#     else:
#         msg = 'Unknown ND cycle option, cannot apply requested pattern'
#         raise ValueError(msg)


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
        [name, target] = katpoint_target(target_item)
        names.append(name)
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
        target,
        duration_=None,  # overwrite user settings
        ):
    target_visible = False
    # TODO: you already have a catalogue of targets -- this must fit with that
    name_list = [name_.strip() for name_ in target['name'].split('|')]
    if len(name_list) > 1:
        target_name = filter(lambda x: x.startswith('*'), name_list)[0][1:]
    else:
        target_name = name_list[0]

    target_ = catalogue[target_name]
    duration = target['duration']
    type_ = target['obs_type']

    # functional overwrite of duration for system reasons
    if duration_ is not None:
        duration = duration_
    # simple way to get telescope to slew to target
    if duration <= 0:
        return session.track(target_, duration=duration_, announce=False)

    user_logger.info('{} {} {} for {} sec'.format(
        type_.capitalize(), target_.tags[1], target.name, duration))
    # TODO: add some delay for slew time
    # check if target is visible before doing any work
    if type_ == 'drift_scan' and session.track(target_, duration=0, announce=False):
        # set transit point as target
        target_ = drift_pointing_offset(target_, duration=duration)

    session.label('track')
    if session.track(target_, duration=duration):
        target_visible = True
        target['obs_cntr'] += 1

    target['last_observed'] = catalogue._antenna.observer.date.datetime()
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

class telescope:
    def __init__(self, opts, args=None):
        self.opts = opts
        # move this to a callable function, so do it only if worth while to
        # observe
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
        self.array = verify_and_connect(opts)
        # create single kat object, cannot repeatedly recreate

    def __enter__(self):
        ## System setup before observation
        user_logger.warning('Telescope __enter__, first verify_and_connect')
        # verify subarray setup correct for observation before doing any work
        if 'instrument' in self.opts.template.keys():
            self.subarray_setup(self.array, self.opts.template['instrument'])

        # Set up noise diode if requested
        if 'noise_diode' in self.opts.template.keys():
            self.noise_diode(self.array, self.opts.template['noise_diode'])
        else:
        # Ensure default setup before starting observation
            # switch noise-source pattern off (known setup starting observation)
            noisediode.off(self.array)

        # TODO: use sessions object, and remember to clean up when __exit__
        with start_session(self.array, **vars(self.opts)) as session:
            # Update correlator settings
            if self.feng is not None:
                set_fengines(session,
                             requant_gains=self.feng['requant_gain'],
                             fft_shift=self.feng['fft_shift'],
                             )
#         # Names of antennas to use for beamformer if not all is desirable
#         set_bf_weights(self.array, opts.bf_ants, opts.bf_weights)
        # return restore_values
        return self

    def __exit__(self, type, value, traceback):
        ## Ensure known exit state before quitting
        user_logger.warning('Telescope __exit__, third verify_and_connect')
        # print 'TODO: Restore defaults'
        # switch noise-source pattern off (ensure this after each observation)
        noisediode.off(self.array)
        self.array.disconnect()

    def subarray_setup(self, mkat, instrument):
        # current sensor list included in instrument
        # sub_ [
                # pool_resouces,  # ptuse or specific antennas
                # product,        # correlator product
                # dump_rate,      # dumprate
                # band,           # band
                # ]
        for key in instrument.keys():
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


    def noise_diode(self, mkat, nd_setup):
        cycle_length = nd_setup['cycle_len']
        on_fraction = nd_setup['on_fraction']
        noise_pattern = nd_setup['pattern']
        if on_fraction > 0:
            msg = 'Set noise source behaviour to {} sec period with {} on fraction and apply pattern to {}'.format(
                    cycle_length,
                    on_fraction,
                    noise_pattern)
            user_logger.info(msg)
            noisediode.pattern(mkat, noise_pattern, cycle_length, on_fraction)
        else:
            msg = 'Noise diode will be fired on {} antenna(s) for {} sec before each track or scan'.format(
                    noise_pattern,
                    cycle_length)
            user_logger.info(msg)
            noisediode.off(mkat, logging=False)



def run_observation(opts, mkat):

    # noise-source on, activated when needed
    if 'noise_diode' in opts.template.keys():
        nd_setup = opts.template['noise_diode']
    else:
        nd_setup = None

    user_logger.warning('Run observation __enter__, second verify_and_connect')

    # Each observation loop contains a number of observation cycles over LST ranges
    for observation_cycle in opts.template['observation_loop']:
        # Unpack all target information
        target_list = []
        obs_targets = []
        if 'target_list' in observation_cycle.keys():
            obs_targets = read_targets(observation_cycle['target_list'])
            target_list += obs_targets['target'].tolist()
        obs_calibrators = []
        if 'calibration_standards' in observation_cycle.keys():
            obs_calibrators = read_targets(observation_cycle['calibration_standards'])
            target_list += obs_calibrators['target'].tolist()
        catalogue = collect_targets(mkat.array, target_list)
        observer = catalogue._antenna.observer

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
        with start_session(mkat.array, **vars(opts)) as session:

            session.standard_setup(**vars(opts))
            session.capture_init()

            # If bandpass interval is specified,
            # force the first visit to be bandpass calibrator(s)
            target = None
            for cnt, calibrator in enumerate(obs_calibrators):
                if 'bpcal' in calibrator['target']:
                    target = calibrator
                    observe(session, catalogue, target)
            # Else go to first target
            if target is None:
                user_logger.info('Slewing to first target')
                for target in obs_targets:
                    if observe(session,
                              catalogue,
                              target,
                              duration_=0):
                        break
                # Only start capturing once we are on target
                session.capture_start()

            done = False
            # while not done:
            for cnt in range(4):

                # Cycle through target list in order listed
                targets_visible = False

                for target in obs_targets:
                    user_logger.warning('Tracking target {}'.format(target))
                    # noise diode fire should be corrected in sessions
                    if nd_setup: noisediode.trigger(mkat.array, nd_setup)
                    if observe(session, catalogue, target):
                        targets_visible = True

                    # Evaluate calibrator cadence
                    for calibrator in obs_calibrators:
                        if calibrator['cadence'] < 0:
                            continue
                        if calibrator['last_observed'] is None:
                            if observe(session, catalogue, calibrator):
                                targets_visible = True
                        else:
                            deltatime = observer.date.datetime() - calibrator['last_observed']
                            if deltatime.total_seconds() > calibrator['cadence']:
                                if observe(session, catalogue, calibrator):
                                    targets_visible = True

                # Cycle through calibrator list and evaluate those with
                # cadence, while observing those that don't
                for calibrator in obs_calibrators:
                    if calibrator['cadence'] < 0 or \
                            calibrator['last_observed'] is None:
                        if nd_setup: noisediode.trigger(mkat.array, nd_setup)
                        if observe(session, catalogue, calibrator):
                            targets_visible = True
                    else:
                        deltatime = observer.date.datetime() - calibrator['last_observed']
                        if deltatime.total_seconds() > calibrator['cadence']:
                            if observe(session, catalgoue, calibrator):
                                targets_visible = True

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
        if len(obs_targets) > 0:
            user_logger.info("Targets observed : {}".format(obs_targets['name']))
            user_logger.info('Time on target:')
            for target in obs_targets:
                user_logger.info('{} observed for {} seconds'.format(target['name'], float(target['obs_cntr'])*target['duration']))
        if len(obs_calibrators) > 0:
            user_logger.info("Calibrators observed : {}".format(obs_calibrators['name']))
            user_logger.info('Time on calibrator:')
            for target in obs_calibrators:
                user_logger.info('{} observed for {} seconds'.format(target['name'], float(target['obs_cntr'])*target['duration']))
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

    # package observation from template plan
    if opts.template:
        opts.template = read_yaml(opts.template)

    # setup and observation
    with telescope(opts, args_) as mkat:
        run_observation(opts, mkat)

# -fin-
