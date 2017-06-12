#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function

import argparse
import os
import sys
import subprocess

from tools import (
    infofile,
    firmware,
    projectdir,
    targets,
    tidy
)

projectdir.Root = os.path.realpath(os.path.dirname(__file__))

infofile.load_info_files('src')

parser = argparse.ArgumentParser(description='''
    build keyboard firmware
    ''')
parser.add_argument('--build', metavar='firmware',
                    help='which firmware to build')
parser.add_argument('--flash', help='flash the device', action='store_true')
parser.add_argument('--verbose', help='verbose build', action='store_true')
parser.add_argument('--port', help='override port for flashing')
parser.add_argument('--list-firmware', action='store_true',
                    help='list available firmware')
parser.add_argument('--tidy', action='store_true',
                    help='auto format and tidy code')

args = parser.parse_args()

if args.tidy:
    tidy.tidy(projectdir.Root)
    sys.exit(0)

if args.list_firmware:
    firmware = [f for f in targets.Targets.values()
                if isinstance(f, firmware.Firmware)]
    print('\n'.join(sorted([f.full_name for f in firmware])))

if args.build:
    f = targets.Targets.get(args.build)
    if not isinstance(f, firmware.Firmware):
        sys.stderr.write('%s is not a firmware target\n' % args.build)
        sys.exit(1)
    f.build()
