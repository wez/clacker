Firmware(
    name='flutterby',
    board=FQBN('adafruit:avr:feather32u4'),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
    srcs=['main.cpp'])
