Firmware(
    name='flutterby',
    manufacturer='Wez Furlong',
    board=AVRBoard(mcu='atmega32u4', clock=8000000),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem', ':matrix',
          'src/libs/lufa:lufa',
          'src/libs/sx1509:sx1509',
          'src/libs/spi:spi',
          ],
    srcs=['main.cpp'])

KeyMatrix(
    name='matrix',
    rows=4,
    cols=16,
    layout=KeyLayout('flutterby.json'),
    keymap=KeyLayout('keymap.json'))
