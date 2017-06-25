Firmware(
    name='flutterby',
    manufacturer='Wez Furlong',
    board=AVRBoard(mcu='atmega32u4', clock=8000000),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem', ':matrix',
          'src/libs/lufa:lufa',
          ],
    srcs=['main.cpp'])

KeyMatrix(
    name='matrix',
    rows=4,
    cols=15,
    layout=KeyLayout('flutterby.json'))
