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
        'version_coords': (33, 158),
        'expander_coords': (173.08, 55.93, 90),
        'header_coords': (111, 33, 268),
        'reserve_pins': {
            # keep an analog pin for future hacking
            'mcu': ['A0'],
        },
        'cirque_coords': (114, 137),
        'azoteq_coords': (112.75, 137),
        '3dprint_quarter_y_cut_delta': -3,
}

Pcb(name='left-pcb', layout=left, shape_config=shape_config)

def extend(d, base):
    return dict(d, **base)

Case(name='left-case', layout=left, shape_config=extend({
        'want_touchpad': False,
        'want_mcu': False
    }, shape_config))

Case(name='right-case', layout=left, shape_config=extend({
        '3dprint_flip': True,
        'want_touchpad': True,
        'want_mcu': True,
        # expose the mcu because we used headers to mount it,
        # or because we want access to the jst or SWD header
        'naked_mcu': False,
    }, shape_config))

#right = KeyLayout(mirror_layout=left)
#Case(name='right-case', layout=right, shape_config=shape_config)
