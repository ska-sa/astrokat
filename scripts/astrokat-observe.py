#!/usr/bin/env python
"""Main astrokat observation script."""
import sys
from astrokat.observe_main import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# -fin-
