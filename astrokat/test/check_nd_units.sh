#! /bin/bash

python -m unittest astrokat.test.test_nd_timings.TestAstrokatYAML.test_nd_pattern_sim
python -m unittest astrokat.test.test_nd_timings.TestAstrokatYAML.test_nd_pattern_ants
python -m unittest astrokat.test.test_nd_timings.TestAstrokatYAML.test_nd_pattern_plus_off
python -m unittest astrokat.test.test_nd_timings.TestAstrokatYAML.test_nd_trigger_long
python -m unittest astrokat.test.test_nd_timings.TestAstrokatYAML.test_nd_trigger_short
