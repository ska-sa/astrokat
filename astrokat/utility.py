import datetime
import katpoint
import numpy
import time
import yaml


class NotAllTargetsUpError(Exception):
    """
    Not all targets are above the horizon at the start of the observation.
    """


class NoTargetsUpError(Exception):
    """No targets are above the horizon at the start of the observation."""


# Read config .yaml file
def read_yaml(filename):
    with open(filename, 'r') as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.parser.ParserError:
            return {}

    if not isinstance(data, dict):
        # not a yaml file, suspected csv file, returning False
        return {}

    # handle mapping of user friendly keys to CAM resource keys
    if 'instrument' in data.keys():
        instrument = data['instrument']
        if instrument is not None:
            if 'integration_time' in instrument.keys():
                integration_time = float(instrument['integration_time'])
                instrument['dump_rate'] = 1./integration_time
                del instrument['integration_time']

    # verify required information in observation loop before continuing
    if 'durations' in data.keys():
        if data['durations'] is None:
            msg = 'durations primary key cannot be empty in YAML file'
            raise RuntimeError(msg)
        if 'start_time' in data['durations']:
            start_time = data['durations']['start_time']
            if type(start_time) is str:
                data['durations']['start_time'] = \
                        datetime.datetime.strptime(start_time,
                                                   '%Y-%m-%d %H:%M')
    if 'observation_loop' not in data.keys():
        raise RuntimeError('Nothing to observe, exiting')
    if data['observation_loop'] is None:
        raise RuntimeError('Empty observation loop, exiting')
    for obs_loop in data['observation_loop']:
        if type(obs_loop) is str:
            raise RuntimeError('Incomplete observation input: '
                               'LST range and at least one target required.')
        # TODO: correct implementation for single vs multiple observation loops
        # -> if len(obs_loop) > 0:
        if 'LST' not in obs_loop.keys():
            raise RuntimeError('Observation LST not provided, exiting')
        if 'target_list' not in obs_loop.keys():
            raise RuntimeError('Empty target list, exiting')

    if 'scan' in data.keys():
        if 'start' in data['scan'].keys():
            scan_start = data['scan']['start'].split(',')
            data['scan']['start'] = numpy.array(scan_start, dtype=float)
        if 'end' in data['scan'].keys():
            scan_end = data['scan']['end'].split(',')
            data['scan']['end'] = numpy.array(scan_end, dtype=float)

    return data


# Safely convert a datetime object to a timestamp
# UTC seconds since epoch
def datetime2timestamp(datetime_obj):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (datetime_obj - epoch).total_seconds()


# Safely convert a timestamp to UTC datetime object
def timestamp2datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp)


# construct an expected katpoint target string
def katpoint_target(target_item):
    coords = ['radec', 'azel', 'gal']
    # input string format: name=, radec=, tags=, duration=, ...
    target_ = [item.strip() for item in target_item.split(',')]
    for item_ in target_:
        prefix = 'name='
        if item_.startswith(prefix):
            name = item_[len(prefix):]
        prefix = 'tags='
        if item_.startswith(prefix):
            tags = item_[len(prefix):]
        prefix = 'model='
        if item_.startswith(prefix):
            fluxmodel = item_[len(prefix):]
        else:
            fluxmodel = ()
        for coord in coords:
            prefix = coord+'='
            if item_.startswith(prefix):
                ctag = coord
                x = item_[len(prefix):].split()[0].strip()
                y = item_[len(prefix):].split()[1].strip()
                break
    target = '{}, {} {}, {}, {}, {}'.format(
        name, ctag, tags, x, y, fluxmodel)
    return name, target


# extract lst range from YAML key
def get_lst(yaml_lst):
    start_lst = None
    end_lst = None
    # YAML input without quotes will calc this integer
    if type(yaml_lst) is int:
        HH = int(yaml_lst/60)
        MM = yaml_lst - (HH*60)
        yaml_lst = '{}:{}'.format(HH, MM)
    # floating point hour format
    if type(yaml_lst) is float:
        HH = int(yaml_lst)
        MM = int(60 * (yaml_lst - HH))
        yaml_lst = '{}:{}'.format(HH, MM)

    err_msg = 'Format error reading LST range in observation file.'
    if type(yaml_lst) is not str:
        raise RuntimeError(err_msg)

    nvals = len(yaml_lst.split('-'))
    if nvals < 2:
        start_lst = yaml_lst
    elif nvals > 2:
        raise RuntimeError(err_msg)
    else:
        start_lst, end_lst = [lst_val.strip() for lst_val in yaml_lst.split('-')]
    if ':' in start_lst:
        time_ = datetime.datetime.strptime('{}'.format(start_lst), '%H:%M').time()
        start_lst = time_.hour + time_.minute/60.

    if end_lst is None:
        end_lst = (start_lst + 24.) % 24.
        if numpy.abs(end_lst - start_lst) < 1.:
            end_lst = 24.
    elif ':' in end_lst:
        time_ = datetime.datetime.strptime('{}'.format(end_lst), '%H:%M').time()
        end_lst = time_.hour + time_.minute/60.
    else:
        end_lst = float(end_lst)

    return start_lst, end_lst


# find when is LST for date given, else for today
def lst2utc(req_lst, ref_location, date=None):
    def get_lst_range(date):
        date_timestamp = time.mktime(date.timetuple())  # this will be local time
        time_range = katpoint.Timestamp(date_timestamp).secs + \
            numpy.arange(0, 24.*3600., 60)
        lst_range = numpy.degrees(target.antenna.local_sidereal_time(time_range)) / 15.
        return time_range, lst_range

    req_lst = float(req_lst)
    cat = katpoint.Catalogue(add_specials=True)
    cat.antenna = katpoint.Antenna(ref_location)
    target = cat['Zenith']
    if date is None:  # find the best UTC for today
        date = datetime.date.today()
    else:
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    [time_range, lst_range] = get_lst_range(date)
    lst_idx = numpy.abs(lst_range-req_lst).argmin()
    if lst_range[lst_idx] < req_lst:
        x = lst_range[lst_idx:lst_idx+2]
        y = time_range[lst_idx:lst_idx+2]
    else:
        x = lst_range[lst_idx-1:lst_idx+1]
        y = time_range[lst_idx-1:lst_idx+1]
    linefit = numpy.poly1d(numpy.polyfit(x, y, 1))
    return datetime.datetime.utcfromtimestamp(linefit(req_lst))


# -fin-
