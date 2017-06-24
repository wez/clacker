Firmware(
    name='flutterby',
    board=FQBN('adafruit:avr:feather32u4'),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem', ':matrix',
          'src/libs/serial:avr'],
    srcs=['main.cpp'])

KeyMatrix(
    name='matrix',
    rows=4,
    cols=15,
    layout=KeyLayout('flutterby.json'))
