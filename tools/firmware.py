from __future__ import absolute_import
from __future__ import print_function

import os

from . import targets
from . import board
from . import library
from . import projectdir


def mkdir_p(d):
    if not os.path.isdir(d):
        os.makedirs(d)


class Firmware(targets.Target):
    ''' Compile code into a firmware image '''

    def __init__(self, name, board=None, srcs=None, deps=None, cppflags=None):
        super(Firmware, self).__init__(name)
        self.board = board
        self.lib = library.Library('%s-lib' % name,
                                   srcs=srcs,
                                   deps=deps,
                                   cppflags=cppflags)

    def get_deps(self):
        return [self.lib]

    def _build_library(self, lib, outputs):
        print('Build library %s' % lib.full_name)

        def check_depfile(objfile, depfile):
            ''' reads a makefile compatible dependency file.
                Returns True if the object needs to be compiled,
                False if it is up to date. '''
            try:
                obj_stat = os.lstat(objfile)
            except:
                # doesn't exist, so compile it
                return True

            if not os.path.exists(depfile):
                return True  # needs recompile

            with open(depfile, 'r') as f:
                lines = f.readlines()
                # The first line is our own object, the rest are the deps
                for depline in lines[1:]:
                    dep = depline.strip().rstrip('\\').strip()

                    try:
                        dep_stat = os.lstat(dep)
                        if dep_stat.st_mtime > obj_stat.st_mtime:
                            # It changed more recently, so recompile
                            return True
                    except:
                        # It doesn't exist, so recompile
                        return True

            # Up to date!
            return False

        srcs = lib.get_srcs(self.board)
        objs = []

        for s in srcs:
            name, ext = os.path.splitext(s)
            if os.path.isabs(name):
                name = name[1:]

            ofile = os.path.join(outputs, '%s.o' % name)
            depfile = os.path.join(outputs, '%s.d' % name)

            mkdir_p(os.path.dirname(ofile))

            if check_depfile(ofile, depfile):
                print('%s from %s' % (ofile, s))

                cppflags = ' '.join(lib.get_cppflags_for_compile(self.board) + [
                    '-I%s' % projectdir.Root])

                self.board.compile_src(s, ofile, depfile, cppflags)
            objs.append(ofile)

        return objs

    def build(self):
        print('Build %s' % self.full_name)

        # Compute outputs dir
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        mkdir_p(outputs)

        deps = self._expand_deps() + self.board.injected_deps()

        to_link = []
        for d in deps:
            if not isinstance(d, library.Library):
                raise Exception(
                    "Don't know how to build %r" % d)

            to_link += self._build_library(d, outputs)

        exe = os.path.join(outputs, '%s.elf' % self.name)
        self.board.link_exe(exe, to_link)

        hex = os.path.join(outputs, '%s.hex' % self.name)
        self.board.exe_to_hex(exe, hex)

    def upload(self, port=None):
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        hex = os.path.join(outputs, '%s.hex' % self.name)
        self.board.upload(hex, port=port)
