Firmware(
    name='teensy',
    board=FQBN('teensy:avr:teensyLC:usb=serialhid,speed=48,opt=osstd,keys=en-us'),
    srcs=['main.cpp'])

Firmware(
    name='feather',
    board=FQBN('adafruit:avr:feather32u4'),
    srcs=['main.cpp'])
