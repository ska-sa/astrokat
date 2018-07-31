# Take a catalogue file and construct
import argparse
import os
import sys


## parsing command line options and return arguments
def cli(prog):
    version = "{} 0.1".format(prog)
    usage = "{} [options] -i <full_path/cat_file.csv>".format(prog)
    description = "Construct a basic observation configuration file from an existing observation catalogue"
    parser = argparse.ArgumentParser(
        usage=usage,
        description=description)
    parser.add_argument(
        '--version',
        action='version',
        version=version)
    parser.add_argument(
        '-i',
        '--infile',
        type=str,
        required=True,
        help='Full path and name of catalogue file to convert (**required**)')
    parser.add_argument(
        '-o',
        '--outfile',
        type=str,
        help='Filename for output configuration file (default reuses input filename)')
    parser.add_argument(
        '--instrument',
        type=str,
        default='bc856M4k',
        help='Observation instrument configuration (default = %(default)s)')
    parser.add_argument(
        '--target-duration',
        type=int,
        default=300,
        help='Default target track duration [sec] (default = %(default)ss)')
    parser.add_argument(
        '--cal-duration',
        type=int,
        default=60,
        help='Default target track duration [sec] (default = %(default)ss)')

    args = parser.parse_args()
    if args.outfile is None:
        args.outfile = os.path.join(
                os.path.dirname(args.infile),
                os.path.splitext(os.path.basename(args.infile))[0]+'.yaml')
    return args


## Assume comma separated values
#  No header lines are allowed, only target information
#  Input format: name, tags, ra, dec
class unpack_catalogue:
    def __init__(self, filename):
        self.infile = filename

    # cleanup catalogue tags and construct expected tag format
    def tidy_tags(self, tags):
        # remove radec catalogue tag
        tags = tags.split()
        if 'radec' in tags: tags.remove('radec')
        # add target tag if not a calibrator
        if not any('cal' in tag for tag in tags):
            tags.append('target')
        return ' '.join(tags)

    # unpack all targets from catalogue files into list
    def read_catalogue(self,
            target_duration=300,
            cal_duration=60):
        target_list = []
        try:
            fin = open(self.infile, 'r')
        except:
            raise
        else:
            for line in fin.readlines():
                [name, tags, ra, dec] = line.strip().split(',')
                tags = self.tidy_tags(tags.strip())
                duration = cal_duration
                if 'target' in tags:
                    duration = target_duration
                target_item = 'name={}, radec={}, tags={}, duration={}'.format(
                        name.strip(),
                        ','.join([ra.strip(), dec.strip()]),
                        tags,
                        duration,
                        )
                target_list.append(target_item)
            fin.close()
        return target_list


## Create a default observation config file
#  Assume the format of a target in the list:
#  'name=<name>, radec=<HH:MM:SS.f>,<DD:MM:SS.f>, tags=<tags>, duration=<sec>'
class yaml_configuration:
    def __init__(self, target_list):
        self.target_list = target_list

    def write_yaml(self, instrument=None, outfile='obs_config.yaml'):
        try:
            fout = open(outfile, 'w')
        except:
            raise
        else:
            init_str = 'instrument: {}\n'.format(instrument)
            init_str += 'observation_loop:\n'
            init_str += "  - LST: 0-23\n"
            fout.write(init_str)
            fout.close()
        target_list = ''
        calibrator_list = ''
        for target in self.target_list:
            if 'target' in target:
                # find and list source targets
                target_list += '      - {}\n'.format(target)
            elif ('flux' in target) or ('bp' in target) or ('pol' in target):
                # find and list calibrator targets
                calibrator_list += '      - {}\n'.format(target)
            else:
                # gain and delay calibrators are associated with sources
                target_list += '      - {}\n'.format(target)
        fout = open(outfile, 'a')
        fout.write('    target_list:\n{}'.format(target_list))
        fout.write('    calibration_standards:\n{}'.format(calibrator_list))
        fout.close()

if __name__ == '__main__':
    args = cli(sys.argv[0])
    catalogue = unpack_catalogue(args.infile).read_catalogue(
            target_duration=args.target_duration,
            cal_duration=args.cal_duration)
    yaml_configuration(catalogue).write_yaml(
            instrument=args.instrument,
            outfile=args.outfile)

# -fin-
