#! /bin/bash
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_targets_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_two_calib_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_image_single_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_image_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_solar_body
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_below_horizon
