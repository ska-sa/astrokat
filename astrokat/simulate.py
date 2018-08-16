# Scripts that can be run independently of the observation system to allow easy observation planning
import katpoint
import numpy as np
import ephem
import logging
import sys

from collections import namedtuple

# Fake user logger prints out to screen
user_logger = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
# TODO: add timestamp input for LST playback
out_hdlr.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
out_hdlr.setLevel(logging.INFO)
user_logger.addHandler(out_hdlr)
user_logger.setLevel(logging.INFO)


# Fake telescope connection
class verify_and_connect:
    def __init__(self, dummy):
        kwargs = vars(dummy)
        self._ants = kwargs['noise_pattern'] if 'noise_pattern' in kwargs else []
    def __enter__(self):
        return self
    def __getattr__(self, key):
        return self
    def __call__(self, *args, **kwargs):
        return self
    def __iter__(self):
        Ant = namedtuple('Ant', ['name'])
        yield Ant(self._ants)
        raise StopIteration
    def __exit__(self, type, value, traceback):
        pass

# Fake observation session
class start_session:
    def __init__(self, dummy_kat, **kwargs):
        pass
    def __enter__(self):
        return self
    def __getattr__(self, key):
        self._key = key
        return self # key
    def __call__(self, *args, **kwargs):
        return self
    def __str__(self):
        return 'A string'
    def __nonzero__(self):
        return 1
    def __iter__(self):
        yield self
        raise StopIteration
    def __exit__(self, type, value, traceback):
        pass

# -fin-
