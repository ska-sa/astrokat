#!/usr/bin/env python
"""
Utility test script.

Utility test script to verify json configuration files
   Use after edit and before observation planning
"""
from pprint import pprint
import sys
import yaml


def main(yaml_config):
    """."""
    with open(yaml_config, 'r') as stream:
        try:
            data = yaml.safe_load(stream)
        except BaseException:
            raise
    pprint(data)


if __name__ == '__main__':
    main(sys.argv[-1])

# -fin-
