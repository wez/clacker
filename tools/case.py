from __future__ import absolute_import
from __future__ import print_function

import os
from . import targets
from . import filesystem
from .circuitlib import shape
from . import svg
from . import matrix

PONOKO_LASER_CUT = {
    'fill': 'none',
    'stroke_width': '0.01mm',
    'stroke': '#0000ff',
}

PONOKO_LASER_ENGRAVE = {
    'fill': 'none',
    'stroke_width': '0.01mm',
    'stroke': '#ff0000',
}

PONOKO_LASER_ENGRAVE_AREA = {
    'fill': '#000000',
    'stroke': 'none',
}


class Case(targets.Target):
    def __init__(self, name, layout):
        super(Case, self).__init__(name)
        self.layout = layout

    def build(self):
        print('Gen case %s' % self.full_name)
        # Compute outputs dir
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        filesystem.mkdir_p(outputs)
        layout = self.layout.layout
        shapes = shape.make_shapes(layout)

        self.case_bottom(shapes, outputs)
        self.case_top(shapes, outputs)
        self.switch_plate(shapes, outputs)

    def case_bottom(self, shapes, outputs):
        doc = svg.SVG()

        doc.add(shapes['bottom_plate'].symmetric_difference(shapes['corner_holes']),
                **PONOKO_LASER_CUT)

        doc.save(os.path.join(outputs, 'case-bottom.svg'))

    def case_top(self, shapes, outputs):
        doc = svg.SVG()

        doc.add(shapes['top_plate'],
                **PONOKO_LASER_CUT)

        doc.save(os.path.join(outputs, 'case-top.svg'))

    def switch_plate(self, shapes, outputs):
        doc = svg.SVG()

        doc.add(shapes['switch_plate'],
                **PONOKO_LASER_CUT)

        doc.save(os.path.join(outputs, 'switch-plate-minimal.svg'))

        doc = svg.SVG()

        doc.add(shapes['bottom_plate'].symmetric_difference(
            shapes['switch_holes']).symmetric_difference(
            shapes['corner_holes']),
            **PONOKO_LASER_CUT)

        doc.save(os.path.join(outputs, 'switch-plate-full.svg'))
