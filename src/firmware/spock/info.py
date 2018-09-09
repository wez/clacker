# Firmware(
#    name='nrf52',
#    board=FQBN('adafruit:nrf52:feather52:debug=l0'),
#    deps=['src/libs/tasks:tasks', 'src/libs/progmem:progmem'],
#    srcs=['main.cpp'])

left = KeyLayout('left-keymap.json')

shape_config = {
        'mcu': 'feather',
        'trrs': 'left+right',
        'header': True,
}

Pcb(name='left-pcb', layout=left, shape_config=shape_config)
Case(name='left-case', layout=left, shape_config=shape_config)

#right = KeyLayout(mirror_layout=left)
#Case(name='right-case', layout=right, shape_config=shape_config)
