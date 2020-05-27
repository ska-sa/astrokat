"""Update MeerKAT antenna position file"""

from __future__ import print_function
import argparse
import glob
import os
import sys
import yaml

from astrokat import __version__


def cli(prog):
    usage = "{} [options]".format(prog)
    description = 'Update antenna ENU positions from katconfig'

    parser = argparse.ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--version",
        action="version",
        version=__version__)
    parser.add_argument(
        '--config',
        type=str,
        default='katconfig/user/delay-models/mkat/',
        help='path to delay models if not using katconfig symlink in workdir')
    parser.add_argument(
        '--yaml',
        type=str,
        required=True,
        help='YAML file with antenna ENU positions')
    obs_bands = ['l', 'u', 's', 'x']
    parser.add_argument(
        '--band',
        type=str,
        choices=obs_bands,
        default='l',
        help='Selected band for antenna delay files')
    args = parser.parse_args()
    return args


def read_delay_file(filename):
    files = glob.glob(filename)
    if len(files) < 1:
        raise RuntimeError('No delay models for antenna {}'
                           .format(ant_['name']))
    if len(files) > 1:
        raise RuntimeError('Multiple files named {}'
                           .format(filename))

    with open(files[0], 'r') as fin:
        model = fin.readline().strip()
    [E, N, U, H, V, _] = model.split()
    return E, N, U


def antenna_line_(ant_):
    txt_line = ('name={}, diameter=13.5, '
                'east={}, north={}, up={}'.format(ant_['name'],
                                                  ant_['east'],
                                                  ant_['north'],
                                                  ant_['up']))
    return txt_line


if __name__ == '__main__':
    args = cli(sys.argv[0])

    # read yaml file
    with open(args.yaml, "r") as stream:
        data = yaml.safe_load(stream)

    # update for each antenna in yaml file
    for idx, antenna in enumerate(data['antennas']):
        # read current antenna position
        ant_ = {'name': None,
                'east': None,
                'north': None,
                'up': None}
        items_ = [item.strip() for item in antenna.split(",")]
        for prefix_ in ant_.keys():
            for item_ in items_:
                if item_.startswith(prefix_):
                    ant_[prefix_] = item_.split('=')[-1].strip()

        # read updated delay model values
        filename = '{}_{}.txt'.format(ant_['name'], args.band)
        filename = os.path.join(args.config, filename)
        [E, N, U] = read_delay_file(filename)
        ant_['east'] = E
        ant_['north'] = N
        ant_['up'] = U
        data['antennas'][idx] = antenna_line_(ant_)

    # write updated yaml file
    with open(args.yaml, 'w') as fout:
        yaml.dump(data, fout, default_flow_style=False)

# -fin-
