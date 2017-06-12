from __future__ import absolute_import
from __future__ import print_function

import glob
import os
import subprocess
import shlex

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


class FQBN(Board):
    ''' Load a board from Arduino, using a Fully Qualified Board Name '''

    def __init__(self, fqbn, prefs=None):
        self.fqbn = fqbn
        self.prefs = prefs or {}

    def compile_src(self, srcfile, objfile, depfile=None, cppflags=None):
        a = arduino.get()

        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)
        prefs['includes'] = '%s -I{build.core.path}' % (cppflags or '')
        prefs['source_file'] = srcfile
        prefs['object_file'] = objfile

        _, ext = os.path.splitext(srcfile)
        if ext == '.s':
            ext = '.S'

        cmd = a.resolve_pref('recipe%s.o.pattern' % ext, prefs)

        print(cmd)
        subprocess.check_call(shlex.split(cmd))

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

        cmd = a.resolve_pref('recipe.c.combine.pattern', prefs)
        print(cmd)
        subprocess.check_call(shlex.split(cmd))

    def exe_to_hex(self, exefile, hexfile):
        a = arduino.get()
        # The recipe adds .elf, so avoid doubling up
        exefile, _ = os.path.splitext(exefile)

        prefs = a.board_prefs(self.fqbn)
        prefs.update(self.prefs)
        build_dir = os.path.dirname(exefile)
        prefs['build.path'] = build_dir
        prefs['build.project_name'] = os.path.basename(exefile)

        cmd = a.resolve_pref('recipe.objcopy.hex.pattern', prefs)
        print(cmd)
        subprocess.check_call(shlex.split(cmd))
