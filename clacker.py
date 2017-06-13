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


def do_build(args):
    f = targets.Targets.get(args.firmware)
    if not isinstance(f, firmware.Firmware):
        sys.stderr.write('%s is not a firmware target\n' % args.build)
        sys.exit(1)
    f.build()


def do_upload(args):
    do_build(args)
    pass


def do_tidy(args):
    tidy.tidy(projectdir.Root)


def do_list(args):
    avail = [f for f in targets.Targets.values()
             if isinstance(f, firmware.Firmware)]
    print('\n'.join(sorted([f.full_name for f in avail])))


projectdir.Root = os.path.realpath(os.path.dirname(__file__))

infofile.load_info_files('src')

parser = argparse.ArgumentParser(description='''
    build keyboard firmware
    ''')

subparsers = parser.add_subparsers(
    title='subcommands', description='Available subcommands')
build_parser = subparsers.add_parser('build', help='Build firmware',
                                     description='''
    Builds the source code for the specified firmware.
    ''')
build_parser.add_argument('firmware', help='which firmware to build')
build_parser.set_defaults(func=do_build)

upload_parser = subparsers.add_parser('upload',
                                      help='Upload firmware to device',
                                      description='''
    Ensures that the specified firmware is built and then uploads
    it to the device
    ''')
upload_parser.add_argument('firmware', help='which firmware to build')
upload_parser.add_argument('--port', help='override port for flashing')
upload_parser.set_defaults(func=do_upload)

tidy_parser = subparsers.add_parser('tidy', help='Tidy up code formatting',
                                    description='''
    Tidies up the C, C++ and Python source code in the repo to keep it
    looking reasonably uniform
    ''')
tidy_parser.set_defaults(func=do_tidy)

list_parser = subparsers.add_parser('list-firmware',
                                    help='List firmware projects',
                                    description='''
    Shows a list of all available firmware projects.
    These are defined by Firmware objects in the info.py files found
    throughout this source tree.
    ''')
list_parser.set_defaults(func=do_list)

args = parser.parse_args()
args.func(args)
