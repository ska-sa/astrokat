## Utility test script to verify json configuration files after edit and before observation planning
import json
import sys
from collections import OrderedDict

def main(json_config):
    with open(json_config, 'r') as observation_prms:
        data = json.load(observation_prms, object_pairs_hook=OrderedDict)
    print json.dumps(data, indent=2)

if __name__ == '__main__':
    main(sys.argv[-1])

# -fin-
