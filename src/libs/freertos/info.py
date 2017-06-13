from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess
from glob import glob

'''
"/Applications/Arduino.app/Contents/Java/hardware/teensy/../tools/arm/bin/arm-none-eabi-gcc" -c -Os --specs=nano.specs -g -Wall -ffunction-sections -fdata-sections -nostdlib -MMD  -mthumb -mcpu=cortex-m0plus -fsingle-precision-constant -D__MKL26Z64__ -DTEENSYDUINO=136 -DARDUINO=10801 -DF_CPU=48000000 -DUSB_SERIAL_HID -DLAYOUT_US_ENGLISH -fno-lto -Isrc/libs/freertos/freertos.git/FreeRTOS/Source/include -Isrc/libs/freertos -Isrc/libs/freertos/freertos.git/FreeRTOS/Source/portable/GCC/ARM_CM0 -I/Applications/Arduino.app/Contents/Java/hardware/teensy/avr/cores/teensy3 "src/libs/freertos/freertos.git/FreeRTOS/Source/portable/GCC/ARM_CM0/port.c" -o "/Users/wez/src/clacker/outputs/src/firmware/blinky/teensy/src/libs/freertos/freertos.git/FreeRTOS/Source/portable/GCC/ARM_CM0/port.o"
'''

'''
"/Users/wez/Library/Arduino15/packages/arduino/tools/arm-none-eabi-gcc/4.8.3-2014q1/bin/arm-none-eabi-gcc" -mcpu=cortex-m0plus -mthumb -c -g -Os -w -std=gnu11 -ffunction-sections -fdata-sections -nostdlib --param max-inline-insns-single=500 -MMD -DF_CPU=48000000L -DARDUINO=10801 -DARDUINO_SAMD_FEATHER_M0 -DARDUINO_ARCH_SAMD  -DARDUINO_SAMD_ZERO -D__SAMD21G18A__ -DUSB_VID=0x239A -DUSB_PID=0x800B -DUSBCON '-DUSB_MANUFACTURER="Adafruit"' '-DUSB_PRODUCT="Feather M0"' "-I/Users/wez/Library/Arduino15/packages/arduino/tools/CMSIS/4.5.0/CMSIS/Include/" "-I/Users/wez/Library/Arduino15/packages/arduino/tools/CMSIS-Atmel/1.1.0/CMSIS/Device/ATMEL/" -fno-lto -Isrc/libs/freertos/freertos.git/FreeRTOS/Source/include -Isrc/libs/freertos -Isrc/libs/freertos/freertos.git/FreeRTOS/Source/portable/GCC/ARM_CM0 -I/Users/wez/Library/Arduino15/packages/adafruit/hardware/samd/1.0.17/cores/arduino "src/libs/freertos/freertos.git/FreeRTOS/Source/portable/GCC/ARM_CM0/port.c" -o "/Users/wez/src/clacker/outputs/src/firmware/blinky/feather-m0/src/libs/freertos/freertos.git/FreeRTOS/Source/portable/GCC/ARM_CM0/port.o"
'''


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
        raise Exception("what arch for %s" % board.fqbn)

    def get_srcs(self, board):
        upstream = os.path.join(self.dir, 'freertos.git')
        if not os.path.isdir(upstream):
            subprocess.check_call(['git', 'clone', '--depth', '1',
                                   self.url, upstream])

        core = glob('%s/FreeRTOS/Source/*.c' % upstream)
        port = []

        arch = self._board_arch(board)
        if arch == 'avr':
            port.append('%s/avr/port.c' % self.dir)
        elif arch == 'm0':
            port.append('%s/m0/port.c' % self.dir)

        port += glob('%s/*.c' % self.dir)

        return core + port

    def get_cppflags(self, board):
        upstream = os.path.join(self.dir, 'freertos.git')
        flags = [
            '-I%s' % os.path.join(upstream, 'FreeRTOS/Source/include'),
            '-I%s' % self.dir,
        ]
        arch = self._board_arch(board)
        if arch == 'avr':
            flags.append('-I%s/avr' % self.dir)
        elif arch == 'm0':
            flags.append('-I%s/m0' % self.dir)

        return flags

    def get_scoped_cppflags(self, board):
        return ['-fno-lto']


FreeRTOS()
