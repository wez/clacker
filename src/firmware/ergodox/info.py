Firmware(
    name='ergodox',
    manufacturer='Wez Furlong',
    pid=0x1307,
    cppflags=['-DBOOTLOADER_SIZE=512'],
    board=AVRBoard(mcu='atmega32u4', clock=16000000),
    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem', ':matrix',
          'src/libs/twi:twi',
          'src/libs/lufa:lufa',
          ],
    srcs=['main.cpp'])

KeyMatrix(
    name='matrix',
    rows=14,
    cols=6,
    layout=KeyLayout('ergodox.json'),
    keymap=KeyLayout('keymap.json'))
