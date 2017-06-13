Firmware(
    name='teensy',
    board=FQBN('teensy:avr:teensyLC:usb=serialhid,speed=48,opt=osstd,keys=en-us'),
    deps=['src/libs/tasks:tasks'],
    srcs=['main.cpp'])

Firmware(
    name='feather',
    board=FQBN('adafruit:avr:feather32u4'),
    deps=['src/libs/tasks:tasks'],
    srcs=['main.cpp'])

Firmware(
    name='feather-m0',
    board=FQBN('adafruit:samd:adafruit_feather_m0'),
    deps=['src/libs/tasks:tasks'],
    srcs=['main.cpp'])

Firmware(
    name='nrf52',
    board=FQBN('adafruit:nrf52:feather52:debug=l0'),
    deps=['src/libs/tasks:tasks'],
    srcs=['main.cpp'])
