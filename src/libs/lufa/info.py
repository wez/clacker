from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess
from glob import glob


class LUFA(Library):
    url = 'https://github.com/abcminiuser/lufa.git'

    def __init__(self):
        super(LUFA, self).__init__('lufa', deps=['src/libs/tasks:tasks'])

    def get_srcs(self, board):
        upstream = os.path.join(self.dir, 'lufa.git')
        if not os.path.isdir(upstream):
            subprocess.check_call(['git', 'clone', '--depth', '1',
                                   self.url, upstream])

        srcs = [os.path.join(self.dir, s)
                for s in ['LufaUSB.cpp', 'data.c', 'log.cpp']]
        for d in ['LUFA/Drivers/USB/Core/AVR8',
                  'LUFA/Drivers/USB/Core',
                  'LUFA/Drivers/Peripheral/AVR8',
                  'LUFA/Drivers/USB/Class/Device']:
            srcs += glob('%s/%s/*.c' % (os.path.join(self.dir, 'lufa.git'), d))
        return srcs

    def get_cppflags(self, board):
        return [
            '-DF_USB=F_CPU',
            '-DUSE_STATIC_OPTIONS=(USB_DEVICE_OPT_FULLSPEED|USB_OPT_REG_ENABLED|USB_OPT_AUTO_PLL)',
            '-DUSB_DEVICE_ONLY',
            '-DUSE_FLASH_DESCRIPTORS',
            '-DFIXED_CONTROL_ENDPOINT_SIZE=8',
            '-DFIXED_NUM_CONFIGURATIONS=1',
            '-I%s' % os.path.join(self.dir, 'lufa.git'),
        ]


LUFA()
