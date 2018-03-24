from __future__ import absolute_import
from __future__ import print_function

import os
from . import targets
from . import filesystem
from .circuitlib import shape
from . import svg
from . import matrix
from . import openscad

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
    def __init__(self, name, layout, shape_config=None):
        super(Case, self).__init__(name)
        self.layout = layout
        self.shape_config = shape_config

    def build(self):
        print('Gen case %s' % self.full_name)
        # Compute outputs dir
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        filesystem.mkdir_p(outputs)
        layout = self.layout.layout
        shapes = shape.make_shapes(layout, shape_config=self.shape_config)

        self.case_bottom(shapes, outputs)
        self.case_top(shapes, outputs)
        self.switch_plate(shapes, outputs)
        self.case_top_3d(shapes, outputs)

    def case_bottom(self, shapes, outputs):
        doc = svg.SVG()

        doc.add(shapes['bottom_plate'].symmetric_difference(shapes['corner_holes']),
                **PONOKO_LASER_CUT)
        doc.add(shapes['mounting_holes'], **PONOKO_LASER_CUT)
        if shapes['rj45']:
            doc.add(shapes['rj45'], **PONOKO_LASER_ENGRAVE)
        doc.add(shapes['mcu'], **PONOKO_LASER_ENGRAVE)

        # remove me!
        doc.add(shapes['cap_holes'], **PONOKO_LASER_ENGRAVE)
        doc.add(shapes['switch_holes'], **PONOKO_LASER_ENGRAVE)

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

    def case_top_3d(self, shapes, outputs):
        scad = openscad.Script()

        plate = shapes['bottom_plate'].symmetric_difference(
            shapes['switch_holes'])

        scad.add(openscad.Shape(plate).linearExtrude(2).union(openscad.Shape(
            shapes['top_plate_no_corner_holes']).linearExtrude(5).translate([0, 0, 2])))
        scad.save(os.path.join(outputs, 'switch-plate.scad'))
