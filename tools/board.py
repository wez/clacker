from __future__ import absolute_import
from __future__ import print_function

from pprint import pprint
from glob import glob
import os
import re
import subprocess
import shlex
import time

from . import arduino
from . import library
from . import projectdir


def _cmd_split(args):
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

    def link_lib(self, libfile, objfiles):
        ''' link a set of objects together and store
            the result into libfile '''
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


class HostCompiler(Board):
    ''' Placeholder for when we build unit tests with the host
        compiler '''

    def __init__(self):
        self.fqbn = 'host'

    def compile_src(self, srcfile, objfile, depfile=None, cppflags=None):
        cppflags = _cmd_split(cppflags or '')
        cppflags.append('-D__CLACKER_HOST_BOARD')
        if srcfile.endswith('.cpp'):
            subprocess.check_call(
                ['g++', '-g', '-c', '-std=c++11', '-MMD', '-o', objfile, srcfile] + cppflags)
        else:
            subprocess.check_call(
                ['gcc', '-g', '-c', '-MMD', '-o', objfile, srcfile] + cppflags)

    def link_exe(self, exefile, objfiles):
        subprocess.check_call(['g++', '-o', exefile] + objfiles)
        print('OK: %s' % exefile)

    def link_lib(self, libfile, objfiles):
        subprocess.check_call(['ar', 'rcs', libfile] + objfiles)

    def exe_to_hex(self, exefile, hexfile):
        pass


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

        srcs = []

        def find_srcs(path):
            ''' collect all the c/cpp sources recursively under a dir
                and synthesize it into a library '''
            srcs = []
            for d, _, files in os.walk(path):
                for f in files:
                    _, ext = os.path.splitext(f)
                    if ext == '.c' or ext == '.cpp' or ext == '.S':
                        srcs.append(os.path.join(d, f))
            return srcs

        libs = []
        core_path = a.resolve_pref('build.core.path', prefs)
        srcs += find_srcs(core_path)
        variant_path = a.resolve_pref('build.variant.path', prefs)
        if variant_path:
            srcs += find_srcs(variant_path)

        projectdir.set(core_path)
        libs.append(library.Library(name='core', srcs=srcs))

        return libs

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

        cmd = _cmd_split(a.resolve_pref(
            'recipe%s.o.pattern' % ext, prefs))
        # print(cmd)
        subprocess.check_call(cmd)

    def link_lib(self, libfile, objfiles):
        ''' link a set of objects together and store
            the result into libfile '''

        # Remove the library first, as we may have removed an input
        # object file and we don't want to allow that to mess with
        # linking later on
        if os.path.exists(libfile):
            os.unlink(libfile)

        a = arduino.get()

        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)
        # pprint(prefs)
        build_dir = os.path.dirname(libfile)
        prefs['build.path'] = build_dir
        prefs['archive_file'] = libfile
        prefs['archive_file_path'] = libfile

        # fixup what looks like a bogus config for teensy
        prefs['recipe.ar.pattern'] = prefs['recipe.ar.pattern'].replace(
            '{build.path}/core/{archive_file}', '{archive_file_path}')

        for obj in objfiles:
            prefs['object_file'] = obj
            cmd = _cmd_split(a.resolve_pref(
                'recipe.ar.pattern', prefs))
            # pprint(cmd)
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

        cmd = _cmd_split(a.resolve_pref(
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

        def size():
            cmd = a.resolve_pref('recipe.size.pattern', prefs)
            try:
                output = subprocess.check_output(_cmd_split(cmd))

                size_re = a.resolve_pref('recipe.size.regex', prefs)
                data_re = a.resolve_pref('recipe.size.regex.data', prefs)
                eeprom_re = a.resolve_pref('recipe.size.regex.eeprom', prefs)
                data = 0
                eeprom = 0
                size = 0
                for line in output.split('\n'):
                    m = re.search(size_re, line)
                    if m:
                        size += int(m.group(1))
                    m = re.search(data_re, line)
                    if m:
                        data += int(m.group(1))
                    m = re.search(eeprom_re, line)
                    if m:
                        eeprom_re += int(m.group(1))

                return {
                    'size': size,
                    'data': data,
                    'eeprom': eeprom,
                }
            except:
                return None

        for obj in ('hex', 'bin', 'zip'):
            try:
                cmd = _cmd_split(a.resolve_pref(
                    'recipe.objcopy.%s.pattern' % obj, prefs))
                subprocess.check_call(cmd)
            except:
                pass

        print('%s: %r' % (hexfile, size()))

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
            cmd = _cmd_split(cmd)
            pprint(cmd)

            time.sleep(1)
            result = subprocess.call(cmd)
            if result == 0:
                break
            print('(Failed, will retry)')


class AVRBoard(Board):
    ''' Vanilla AVR-libc target '''

    def __init__(self, mcu, clock):
        self.mcu = mcu
        self.clock = clock
        self.fqbn = 'avr-libc:%s:%s' % (mcu, clock)

    def compile_src(self, srcfile, objfile, depfile=None, cppflags=None):
        cppflags = [
            '-g',
            '-c',
            '-Os',
            '-MMD',
            '-ffunction-sections',
            '-fdata-sections',
            '-mmcu={mcu}'.format(mcu=self.mcu),
            '-DF_CPU={clock}UL'.format(clock=self.clock),
        ] + _cmd_split(cppflags or '')

        if srcfile.endswith('.cpp'):
            cppflags = [
                '-std=gnu++11',
                '-fno-exceptions',
                '-fno-threadsafe-statics',
            ] + cppflags
            subprocess.check_call(
                ['avr-g++'] + cppflags + ['-o', objfile, srcfile])
        else:
            subprocess.check_call(
                ['avr-gcc'] + cppflags + ['-o', objfile, srcfile])

    def link_lib(self, libfile, objfiles):
        subprocess.check_call(['avr-ar', 'rcs', libfile] + objfiles)

    def link_exe(self, exefile, objfiles):
        subprocess.check_call(['avr-g++', '-Os', '-mmcu=%s' %
                               self.mcu, '-Wl,--gc-sections', '-o', exefile] + objfiles)
        subprocess.check_call(['avr-size', exefile])

    def exe_to_hex(self, exefile, hexfile):
        subprocess.check_call(
            ['avr-objcopy', '-O', 'ihex', '-R', '.eeprom', exefile, hexfile])

    def upload(self, hexfile, port=None):
        cmd = [
            'avrdude',
            '-p',
            self.mcu,
            '-U',
            'flash:w:%s:i' % hexfile,
            '-cavr109',
            '-b57600',
            '-D']
        if port:
            cmd.append('-P%s' % port)
        subprocess.check_call(cmd)
