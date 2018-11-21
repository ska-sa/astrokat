from datetime import timedelta
import datetime
import katpoint
import numpy
import time
import yaml


class NotAllTargetsUpError(Exception):
    """Not all targets are above the horizon at the start of the observation."""


class NoTargetsUpError(Exception):
    """No targets are above the horizon at the start of the observation."""


# Read config .yaml file
def read_yaml(filename):
    with open(filename, 'r') as stream:
        data = yaml.safe_load(stream)
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
    if type(yaml_lst) is float:
        start_lst = yaml_lst
    elif type(yaml_lst) is str:
        [start_lst, end_lst]  = numpy.array(yaml_lst.strip().split('-'),
                                            dtype=float)
    else:
        raise RuntimeError('unexpected LST value')
    if end_lst is None:
        end_lst = (start_lst + 12.)%24.
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
    linefit = numpy.poly1d(numpy.polyfit(x,y,1))
    return datetime.datetime.utcfromtimestamp(linefit(req_lst))


# -fin-
