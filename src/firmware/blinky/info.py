Firmware(
    name='teensy',
    board=FQBN('teensy:avr:teensyLC:usb=serialhid,speed=48,opt=osstd,keys=en-us'),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])

Firmware(
    name='feather',
    board=FQBN('adafruit:avr:feather32u4'),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])

Firmware(
    name='feather-m0',
    board=FQBN('adafruit:samd:adafruit_feather_m0'),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])

Firmware(
    name='nrf52',
    board=FQBN('adafruit:nrf52:feather52:debug=l0'),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])

Firmware(
    name='host',
    board=HostCompiler(),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])

Firmware(
    name='ps2rgb',
    board=AVRBoard(mcu='atmega32a', clock=12000000),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])

Firmware(
    name='feather-noduino',
    board=AVRBoard(mcu='atmega32u4', clock=8000000),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])
