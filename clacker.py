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
    tidy,
    test,
)


def do_setup(args=None):
    subprocess.check_call(
        ['pip', 'install', '-r', 'requirements.txt', '--isolated', '--root', 'pydeps'])


def munge_path():
    ''' Find our locally installed deps '''
    depdir = os.path.join(os.path.dirname(__file__), 'pydeps')
    for root, dirs, files in os.walk(depdir):
        if 'site-packages' in dirs:
            sys.path.insert(1, os.path.join(root, 'site-packages'))
            return True

    return False


if not munge_path():
    do_setup()
    munge_path()


def list_firmware():
    return [f for f in targets.Targets.values() if isinstance(f, firmware.Firmware)]


def list_tests():
    return [f for f in targets.Targets.values() if isinstance(f, test.UnitTest)]


def do_build(args):
    if args.firmware:
        to_build = [targets.Targets.get(name) for name in args.firmware]

        for f in to_build:
            if not isinstance(f, firmware.Firmware):
                sys.stderr.write('%s is not a firmware target\n' % f.full_name)
                sys.exit(1)

    else:
        to_build = list_firmware()

    for f in to_build:
        f.build()


def do_upload(args):
    f = targets.Targets.get(args.firmware)
    if not isinstance(f, firmware.Firmware):
        sys.stderr.write('%s is not a firmware target\n' % f.full_name)
        sys.exit(1)
    f.build()
    f.upload(args.port)


def do_tidy(args):
    tidy.tidy(projectdir.Root)


def do_list(args):
    avail = list_firmware()
    print('\n'.join(sorted([f.full_name for f in avail])))


def do_list_test(args):
    avail = list_tests()
    print('\n'.join(sorted([f.full_name for f in avail])))


def do_tests(args):
    if args.test:
        to_build = [targets.Targets.get(name) for name in args.test]

        for f in to_build:
            if not isinstance(f, test.UnitTest):
                sys.stderr.write('%s is not a test target\n' % f.full_name)
                sys.exit(1)

    else:
        to_build = list_tests()

    for f in to_build:
        f.build()
        f.run_tests()


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
    If no firmware is specified, builds all of them.
    You may run `clacker.py list-firmware` to see a list of
    firmware projects that can be passed to the build command.
    ''')
build_parser.add_argument(
    'firmware', help='which firmware to build', nargs='*')
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

list_test_parser = subparsers.add_parser('list-tests',
                                         help='List tests',
                                         description='''
    Shows a list of all available tests.
    These are defined by UnitTest objects in the info.py files found
    throughout this source tree.
    ''')
list_test_parser.set_defaults(func=do_list_test)

run_test_parser = subparsers.add_parser('test', help='Run tests',
                                        description='''
    Builds and run tests.
    If no tests are specified, builds all of them.
    You may run `clacker.py list-tests` to see a list of
    tests that can be passed to the test command.
    ''')
run_test_parser.add_argument(
    'test', help='which tests to build and run', nargs='*')
run_test_parser.set_defaults(func=do_tests)

setup_parser = subparsers.add_parser('setup', help='Setup clacker',
                                     description='''
    Ensures that you have all of the required dependencies available
    to run the clacker utils.
    ''')

setup_parser.set_defaults(func=do_setup)

args = parser.parse_args()
args.func(args)
