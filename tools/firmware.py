from __future__ import absolute_import
from __future__ import print_function

import os

from . import targets
from . import board
from . import library


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

        srcs = lib.srcs
        objs = []

        for s in srcs:
            name, ext = os.path.splitext(s)
            if os.path.isabs(name):
                name = name[1:]

            ofile = os.path.join(outputs, '%s.o' % name)
            depfile = os.path.join(outputs, '%s.d' % name)

            mkdir_p(os.path.dirname(ofile))

            print('%s from %s' % (ofile, s))
            self.board.compile_src(s, ofile, depfile, lib.cppflags)
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
        print(deps)

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
