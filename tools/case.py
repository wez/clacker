from __future__ import absolute_import
from __future__ import print_function

import os
from shapely.affinity import (translate, scale, rotate)
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
        #if shapes['rj45']:
        #    doc.add(shapes['rj45'], **PONOKO_LASER_ENGRAVE)
        #doc.add(shapes['mcu'], **PONOKO_LASER_ENGRAVE)
        # remove me!
        #doc.add(shapes['cap_holes'], **PONOKO_LASER_ENGRAVE)
        #doc.add(shapes['switch_holes'], **PONOKO_LASER_ENGRAVE)

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
        Shape = openscad.Shape
        scad = openscad.Script()

        mx_switch_height = 11;
        # with short header socket, uc requires this clearance
        # mx_switch_height = 16.5;
        wall_width = 2.4
        pcb_height = 1.6

        # lip to hold the bottom case piece
        bottom_lip_height = 2

        bottom_plate = shapes['bottom_plate']
        raw_cap_holes = shapes['raw_cap_holes']
        corner_holes = shapes['corner_holes']
        corner_hole_posts = shapes['corner_hole_posts']
        mcu = shapes['mcu']
        trrs = shapes['trrs']

        # coupled with tools/pcb.py
        trrs = translate(rotate(trrs, 90), -8.5, 0)

        # make an elongated version of the hardware so
        # that we can project it through the side of the
        # case.  We're assuming that the hardware is mounted
        # at the back/top of the board here.
        def height_of(shape):
            return abs(shape.bounds[3] - shape.bounds[1])

        trrs_height = height_of(trrs)
        trrs = (Shape(trrs) + Shape(trrs).back(trrs_height/2))
        trrs = trrs.linearExtrude(mx_switch_height*2).up(wall_width)

        mcu_height = height_of(mcu)
        mcu = Shape(mcu) + Shape(mcu).back(mcu_height / 2)
        mcu = mcu.linearExtrude(mx_switch_height*2).up(wall_width)

        outer_wall = Shape(
                bottom_plate.buffer(
                    wall_width).symmetric_difference(
                        bottom_plate).buffer(0))
        outer_wall = outer_wall.linearExtrude(
                    mx_switch_height + pcb_height +
                    wall_width + bottom_lip_height)

        # poke holes for the ports in the outer wall
        outer_wall -= mcu
        outer_wall -= trrs

        inner_wall = Shape(
                raw_cap_holes.buffer(
                    wall_width).symmetric_difference(
                        raw_cap_holes).buffer(0))

        plate = bottom_plate.symmetric_difference(raw_cap_holes).buffer(0)

        posts = Shape(corner_hole_posts).linearExtrude(
                    mx_switch_height + 1).up(wall_width - 1)
        post_lugs = Shape(corner_holes).linearExtrude(
                    pcb_height + 1).up(wall_width + mx_switch_height - 1)

        plate_extruded = Shape(plate).linearExtrude(wall_width)

        scad.add(plate_extruded +
                posts +
                post_lugs +
                inner_wall.linearExtrude(
                    mx_switch_height + wall_width-1).up(1) +
                outer_wall
                )

        scad.add(mcu.color('skyblue').transparent())
        scad.add(trrs.color('red').transparent())
        scad.save(os.path.join(outputs, 'switch-plate.scad'))
