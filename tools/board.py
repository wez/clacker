from __future__ import absolute_import
from __future__ import print_function

from pprint import pprint
from glob import glob
import os
import subprocess
import shlex
import time

from . import arduino
from . import library
from . import projectdir


class Board(object):
    ''' Defines a board that we can deploy code to '''

    def compile_src(self, srcfile, objfile, depfile=None, cppflags=None):
        ''' compile srcfile and store the result into objfile.
            Optionally compute and store deps into depfile. '''
        raise NotImplementedError()

    def link_exe(self, exefile, objfiles):
        ''' link a set of objects and libraries together and store
            the result into exefile '''
        raise NotImplementedError()

    def exe_to_hex(self, exefile, hexfile):
        ''' transform an executable into a hex image '''
        raise NotImplementedError()

    def injected_deps(self):
        ''' If the board has some core libraries that must be implicitly
            included, return them here '''
        return []

    def upload(self, hexfile, port=None):
        ''' Upload the specified image to the device '''
        raise NotImplementedError()


class FQBN(Board):
    ''' Load a board from Arduino, using a Fully Qualified Board Name '''

    def __init__(self, fqbn, prefs=None):
        self.fqbn = fqbn
        self.prefs = prefs or {}

    def injected_deps(self):
        ''' Inject the core and variant libraries as dependencies when
            we compile with this board '''
        a = arduino.get()

        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)

        def make_lib(name, key):
            ''' collect all the c/cpp sources recursively under a dir
                and synthesize it into a library '''
            path = a.resolve_pref(key, prefs)
            if not path:
                ''' eg: teensy doesn't have a build.variant.path '''
                return None
            projectdir.set(path)
            srcs = []
            for d, _, files in os.walk(path):
                for f in files:
                    _, ext = os.path.splitext(f)
                    if ext == '.c' or ext == '.cpp':
                        srcs.append(os.path.join(d, f))
            return library.Library(name=name, srcs=srcs)

        libs = []
        for name, key in [
                ('core', 'build.core.path'),
                ('variant', 'build.variant.path')]:
            lib = make_lib(name, key)
            if lib:
                libs.append(lib)

        return libs

    def _cmd_split(self, args):
        ''' hoop jumping to make sure that -D options from the
            recipes can successfully be used to define quoted
            string '''
        args = shlex.split(args, posix=False)

        def dequote(s):
            ''' Remove single or double quotes from an argument,
                but only if they surround the string '''
            if s.startswith('"') and s.endswith('"'):
                return s[1:-1]
            if s.startswith("'") and s.endswith("'"):
                return s[1:-1]
            return s

        return [dequote(s) for s in args]

    def compile_src(self, srcfile, objfile, depfile=None, cppflags=None):
        a = arduino.get()

        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)

        flags = [cppflags or '']
        core_path = a.resolve_pref('build.core.path', prefs)
        if core_path:
            flags.append('-I%s' % core_path)
        variant_path = a.resolve_pref('build.variant.path', prefs)
        if variant_path:
            flags.append('-I%s' % variant_path)

        prefs['includes'] = ' '.join(flags)
        prefs['source_file'] = srcfile
        prefs['object_file'] = objfile

        _, ext = os.path.splitext(srcfile)
        if ext == '.s':
            ext = '.S'

        cmd = self._cmd_split(a.resolve_pref(
            'recipe%s.o.pattern' % ext, prefs))
        print(cmd)
        subprocess.check_call(cmd)

    def link_exe(self, exefile, objfiles):
        a = arduino.get()
        # The recipe adds .elf, so avoid doubling up
        exefile, _ = os.path.splitext(exefile)

        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)
        build_dir = os.path.dirname(exefile)
        prefs['build.path'] = build_dir
        prefs['build.project_name'] = os.path.basename(exefile)
        prefs['archive_file'] = os.path.relpath(objfiles[-1], build_dir)
        prefs['object_files'] = ' '.join(objfiles[0:-1])

        cmd = self._cmd_split(a.resolve_pref(
            'recipe.c.combine.pattern', prefs))
        # pprint(cmd)
        subprocess.check_call(cmd)

    def exe_to_hex(self, exefile, hexfile):
        a = arduino.get()
        # The recipe adds .elf, so avoid doubling up
        exefile, _ = os.path.splitext(exefile)

        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)
        build_dir = os.path.dirname(exefile)
        prefs['build.path'] = build_dir
        prefs['build.project_name'] = os.path.basename(exefile)

        cmd = self._cmd_split(a.resolve_pref(
            'recipe.objcopy.hex.pattern', prefs))
        print(cmd)
        subprocess.check_call(cmd)

        try:
            # We may also need to make a .bin file
            cmd = self._cmd_split(a.resolve_pref(
                'recipe.objcopy.bin.pattern', prefs))
            print(cmd)
            subprocess.check_call(cmd)
        except:
            pass

    def upload(self, hexfile, port=None):
        a = arduino.get()
        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)
        build_dir = os.path.dirname(hexfile)

        # The recipe adds .hex, so avoid doubling up
        hexfile, _ = os.path.splitext(hexfile)

        prefs['build.path'] = build_dir
        prefs['build.project_name'] = os.path.basename(hexfile)

        tool = prefs['upload.tool']

        params = {
            'arduino:avrdude': {
                'key': 'tools.avrdude',
                'port_glob': '/dev/cu.*',
                'need_port': True,
            },
            'nrfutil': {
                'key': 'tools.nrfutil',
                'port_glob': '/dev/cu.SLAB*',
                'need_port': True,
            },
            'teensyloader': {
                'key': 'tools.teensyloader',
                'port_glob': None,
                'need_port': False,
            },
        }

        params = params.get(tool, {
            'key': 'tools.%s' % tool,
            'need_port': True,
            'port_glob': '/dev/cu.*',
        })
        key = params['key']

        verbose = True
        prefs['upload.verbose'] = '{%s.upload.params.verbose}' % key \
            if verbose \
            else '{%s.upload.params.quiet}' % key

        if verbose:
            print('Dict for flashing')
            pprint(prefs)

        try:
            pref_serial_port = a.resolve_pref('serial.port', prefs)
        except KeyError:
            pref_serial_port = None

        while True:
            device = None

            if params['need_port']:
                if port:
                    device = port
                elif params['port_glob']:
                    devices = glob(params['port_glob'])
                    if len(devices) == 1:
                        device = devices[0]
                    elif len(devices) > 0:
                        print(
                            'Ambiguous set of devices; please reset the appropriate one manually!')
                        pprint(devices)
                        device = pref_serial_port

                if device:
                    prefs['serial.port'] = device
                    prefs['serial.port.file'] = device

                if device:
                    # try to persuade the device to jump to the bootloader
                    # (this doesn't seem to work with all hardware)
                    subprocess.call(['stty', '-f', device, '1200'])
                elif not pref_serial_port:
                    print('Waiting for device to appear')
                    time.sleep(1)
                    continue

            cmd = a.resolve_pref('%s.upload.pattern' % key, prefs)
            cmd = self._cmd_split(cmd)
            pprint(cmd)

            time.sleep(1)
            result = subprocess.call(cmd)
            if result == 0:
                break
            print('(Failed, will retry)')
