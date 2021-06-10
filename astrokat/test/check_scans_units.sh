#! /bin/bash
python -m unittest astrokat.test.test_scans.TestAstrokatYAML.test_drift_scan_basic_sim
python -m unittest astrokat.test.test_scans.TestAstrokatYAML.test_raster_scan_basic_sim
python -m unittest astrokat.test.test_scans.TestAstrokatYAML.test_scan_basic_sim
