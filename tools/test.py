from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess

from . import targets
from . import board
from . import library
from . import projectdir
from . import firmware


class UnitTest(firmware.Linkable):
    ''' Compile and run a unit test with the host compiler '''

    def __init__(self, name, srcs=None, deps=None, cppflags=None):
        cppflags = cppflags or []
        deps = deps or []
        deps.append('src/testing/lest:lest')
        super(UnitTest, self).__init__(name, board=board.HostCompiler(),
                                       srcs=srcs,
                                       deps=deps,
                                       cppflags=cppflags)

    def run_tests(self):
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        exe = os.path.join(outputs, '%s.elf' % self.name)
        print('Running %s' % exe)
        subprocess.check_call([exe])
