#!/usr/bin/env python
"""Regenerate every model's validation figures. Thin wrapper over the CLI.

    python scripts/reproduce.py [slug]
"""

import sys

from inflect_models_db.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["reproduce", *sys.argv[1:]]))
