import yaml

class NotAllTargetsUpError(Exception):
    """Not all targets are above the horizon at the start of the observation."""


class NoTargetsUpError(Exception):
    """No targets are above the horizon at the start of the observation."""


# Read config .yaml file
def read_yaml(filename):
    with open(filename, 'r') as stream:
        try:
            data = yaml.safe_load(stream)
        except:
            raise
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
        prefix = 'duration='
        if item_.startswith(prefix):
            duration = item_[len(prefix):]
        prefix = 'cadence='
        if item_.startswith(prefix):
            cadence = item_[len(prefix):]
        else:
            cadence = None
    target = '{}, {} {}, {}, {}'.format(
        name, ctag, tags, x, y)
    return target  #, duration, cadence


# -fin-
