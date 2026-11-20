#!/bin/sh
# One command: all unit tests + scenarios. Re-run after every phase.
cd "$(dirname "$0")/.." && python3 -m unittest discover -s tests -v
