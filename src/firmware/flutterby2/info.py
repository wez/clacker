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
        'expander': True,
        'logo_coords': (44, 128),
        'expander_coords': (190.85, 55.93, 90),
        'header_coords': (111, 33, 268),
        'reserve_pins': {
            # keep an analog pin for future hacking
            'mcu': ['A0'],
        },
        'cirque_coords': (113, 137),
}

Pcb(name='left-pcb', layout=left, shape_config=shape_config)
Case(name='left-case', layout=left, shape_config=shape_config)

#right = KeyLayout(mirror_layout=left)
#Case(name='right-case', layout=right, shape_config=shape_config)
