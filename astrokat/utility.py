from datetime import datetime, timedelta
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
        for coord in coords:
            prefix = coord+'='
            if item_.startswith(prefix):
                ctag = coord
                x = item_[len(prefix):].split()[0].strip()
                y = item_[len(prefix):].split()[1].strip()
                break
    target = '{}, {} {}, {}, {}'.format(
        name, ctag, tags, x, y)
    return name, target


# find when is LST for date given, else for today
def lst2utc(req_lst, ref_location, date=None):
    def get_lst_range(date):
        time_range = katpoint.Timestamp(time.mktime(date.timetuple())).secs + \
                numpy.arange(0, 24.*3600., 60)
        lst_range = katpoint.rad2deg(target.antenna.local_sidereal_time(time_range)) / 15.
        return time_range, lst_range

    req_lst = float(req_lst)
    cat = katpoint.Catalogue(add_specials=True)
    # TODO: ref this back to observatory object
    # ref_location = 'ref, -30:42:47.4, 21:26:38.0, 1060.0, 0.0, , , 1.15'
    cat.antenna = katpoint.Antenna(ref_location)
    target = cat['Zenith']
    if date is None:  # find the best UTC for today
        [time_range, lst_range] = get_lst_range(datetime.now())
        dh = req_lst - lst_range[0]
        date = datetime.now()+timedelta(hours=dh)
    [time_range, lst_range] = get_lst_range(date)
    lst_idx = numpy.abs(lst_range-req_lst).argmin()
    lst_idx = numpy.min((lst_idx+1, len(time_range)-1))
    return datetime.utcfromtimestamp(time_range[lst_idx])


# -fin-
