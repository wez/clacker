from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess
from glob import glob


class FreeRTOS(Library):
    url = 'https://github.com/cjlano/freertos.git'

    def __init__(self):
        super(FreeRTOS, self).__init__('freertos')

    def _board_arch(self, board):
        if 'teensyLC' in board.fqbn:
            return 'm0'
        if 'adafruit_feather_m0' in board.fqbn:
            return 'm0'
        if 'avr' in board.fqbn:
            return 'avr'
        if 'nrf52' in board.fqbn:
            return 'nrf52'
        if board.fqbn == 'host':
            return 'posix'
        raise Exception("what arch for %s" % board.fqbn)

    def get_srcs(self, board):
        upstream = os.path.join(self.dir, 'freertos.git')
        if not os.path.isdir(upstream):
            subprocess.check_call(['git', 'clone', '--depth', '1',
                                   self.url, upstream])

        arch = self._board_arch(board)
        port = []
        if arch == 'nrf52':
            # We need to use the slightly older version of freertos
            # that is provided by adafruit as it has special changes
            # in order to support running with the softdevice required
            # to run the radios.  The code for this is compiled as part
            # of the arduino core, so we have no sources to inject
            # here.
            core = []
        else:
            core = glob('%s/FreeRTOS/Source/*.c' % upstream)

            port += glob('%s/%s/*.c' % (self.dir, arch))
            port += glob('%s/%s/*.cpp' % (self.dir, arch))
            port += glob('%s/*.c' % self.dir)
            port += glob('%s/*.cpp' % self.dir)

        return core + port

    def get_cppflags(self, board):
        arch = self._board_arch(board)
        if arch == 'nrf52':
            flags = []
        else:
            upstream = os.path.join(self.dir, 'freertos.git')
            flags = [
                '-I%s' % os.path.join(upstream, 'FreeRTOS/Source/include'),
                '-I%s' % self.dir,
            ]
            flags.append('-I%s/%s' % (self.dir, arch))

        return flags

    def get_scoped_cppflags(self, board):
        return ['-fno-lto']


FreeRTOS()
