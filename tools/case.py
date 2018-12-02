from __future__ import absolute_import
from __future__ import print_function

import os
import subprocess
from shapely.affinity import (translate, scale, rotate)
from shapely.geometry import (Point, box)
from shapely.ops import unary_union
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


def height_of(shape):
    return abs(shape.bounds[3] - shape.bounds[1])


def width_of(shape):
    return abs(shape.bounds[2] - shape.bounds[0])


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

        print_bed_width = self.shape_config.get('3dprint_bed_width', 140)
        print_bed_height = self.shape_config.get('3dprint_bed_height', 140)
        want_touchpad = self.shape_config.get('want_touchpad', True)
        want_mcu = self.shape_config.get('want_mcu', True)
        naked_mcu = self.shape_config.get('naked_mcu', False)

        wall_width = 2.0
        pcb_height = 1.6
        # space to allow for clearance of keycaps
        switch_cap_buffer = 0.5

        mx_switch_height = 12 - pcb_height
        # with short header socket, uc requires this clearance
        #mx_switch_height = 17 - pcb_height

        # for a quicker test print
        #mx_switch_height = 3

        # lip to hold the bottom case piece.  This needs to be taller than
        # the head of the bolts/screws used to hold the top and bottom together,
        # otherwise the heads will protrude and make the bottom of the case 
        # awkward.
        bottom_lip_height = 3.5

        max_height = 1.2 * (
                mx_switch_height + (wall_width * 2) +
                pcb_height + bottom_lip_height)

        bottom_plate = shapes['bottom_plate']
        raw_cap_holes = shapes['raw_cap_holes']
        corner_holes = shapes['corner_holes']
        corner_hole_posts = shapes['corner_hole_posts']
        mcu = shapes['mcu']
        trrs = shapes['trrs']

        tp_center = shapes.get('cirque_coords', None)
        azoteq_aperture = shapes.get('azoteq_aperture', None)
        if want_touchpad and azoteq_aperture:
            touchpad = Shape(azoteq_aperture).linearExtrude(
                            max_height).down(1).color('purple')
            # we want the touchpad surface to be as flush to
            # the panel as possible, so lets eat into the top
            # panel a little
            az_pcb_height = 1.2
            az_foot = shapes['azoteq_footprint']
            touchpad_footprint = Shape(az_foot).linearExtrude(
                        mx_switch_height + az_pcb_height).up(
                            wall_width - az_pcb_height).color('magenta')

            touchpad_enclosure = Shape(az_foot.buffer(wall_width)
                    ).linearExtrude(
                        mx_switch_height + wall_width-1).up(
                            1).color('lime')

            stand_outline = unary_union([
                    az_foot.buffer(-0.25).symmetric_difference(
                        az_foot.buffer(-2 * wall_width)),
                    box(az_foot.bounds[2] - (22 + wall_width),
                                    az_foot.bounds[1] + 1,
                                    az_foot.bounds[2] - 22,
                                    az_foot.bounds[3] - 1)])

            # the portion in contact with the case panel
            stand_upper = Shape(stand_outline).linearExtrude(mx_switch_height)
            # cut out some edges to allow cabling and removing the
            # panels without de-soldering
            stand_cutout = Shape(box(az_foot.bounds[0],
                             az_foot.bounds[1] + height_of(az_foot)/4,
                             az_foot.bounds[2],
                             az_foot.bounds[3] - height_of(az_foot)/4)
                            ).linearExtrude(mx_switch_height/2).up(
                                    mx_switch_height/2)
            stand_hole = Shape(box(az_foot.bounds[0] + 2*width_of(az_foot)/3,
                             az_foot.bounds[1] + height_of(az_foot)/4,
                             az_foot.bounds[2],
                             az_foot.bounds[3] - height_of(az_foot)/4)
                            ).linearExtrude(mx_switch_height/2)
            touchpad_stand = (stand_upper - stand_cutout) - stand_hole

        elif want_touchpad and tp_center:
            touchpad = Shape(
                    shapes['cirque_aperture']).linearExtrude(
                            max_height).down(1).color('purple')
            touchpad_footprint = Shape(
                    shapes['cirque_footprint']).linearExtrude(
                        mx_switch_height).up(
                            wall_width).color('magenta')
            touchpad_enclosure = None # TODO
            touchpad_stand = None # TODO
        else:
            touchpad = None
            touchpad_enclosure = None
            touchpad_stand = None

        # coupled with tools/pcb.py
        trrs = translate(rotate(trrs, 90), -7.5, 0)

        # make an elongated version of the hardware so
        # that we can project it through the side of the
        # case.  We're assuming that the hardware is mounted
        # at the back/top of the board here.
        trrs_height = height_of(trrs)
        trrs = (Shape(trrs) + Shape(trrs).back(trrs_height/2))
        trrs = trrs.linearExtrude(max_height).up(wall_width)

        mcu_height = height_of(mcu)
        if naked_mcu:
            jst_bump = box(mcu.bounds[0], mcu.bounds[1] - 18,
                        mcu.bounds[2], mcu.bounds[3])
            jst_bump = Shape(jst_bump).linearExtrude(max_height).color('pink')

        mcu = Shape(mcu) + Shape(mcu).back(mcu_height / 2)
        mcu = mcu.linearExtrude(max_height).up(wall_width)

        outer_wall = Shape(
                bottom_plate.buffer(
                    wall_width).symmetric_difference(
                        bottom_plate).buffer(0))
        outer_wall = outer_wall.linearExtrude(
                    mx_switch_height + pcb_height +
                    wall_width + bottom_lip_height)

        # poke holes for the ports in the outer wall
        if want_mcu:
            outer_wall -= mcu
            if naked_mcu:
                outer_wall -= jst_bump

        outer_wall -= trrs

        cap_hole_exclusion = raw_cap_holes.buffer(switch_cap_buffer)
        inner_wall = Shape(
                raw_cap_holes.buffer(
                    wall_width).symmetric_difference(
                        cap_hole_exclusion).buffer(0))
        inner_wall = inner_wall.linearExtrude(
                    mx_switch_height + wall_width-1).up(1)
        cap_hole_exclusion = Shape(cap_hole_exclusion).linearExtrude(
                    mx_switch_height + wall_width-1).up(1)

        plate = bottom_plate.symmetric_difference(raw_cap_holes).buffer(0)

        posts = Shape(corner_hole_posts).linearExtrude(
                    mx_switch_height + 1).up(wall_width - 1)
        inner_lip = Shape(
                bottom_plate.symmetric_difference(
                    bottom_plate.buffer(-wall_width)
                    )).linearExtrude(mx_switch_height + 1).up(wall_width - 1)

        plate_extruded = Shape(plate).linearExtrude(wall_width)

        case_top = plate_extruded + \
                posts + \
                inner_lip + \
                inner_wall + \
                outer_wall

        screw_up_into_case = True
        if screw_up_into_case:
            # Make room for insert nuts.  The ones I have on order are M3 nuts
            # with an exterior diameter of 4.1mm and a length of 3mm.  We want
            # to allow room for at least a 6mm thread both because that is how
            # long my bolts are and because when heating and pressing these
            # in to the case, some plastic material can pool below.
            screw_thread_height = mx_switch_height #  8
            inset_nut_height = 3
            # TODO: 3mm bolt head height

            screw_thread_clearance = Shape(corner_holes).linearExtrude(
                        screw_thread_height + 2
                        ).up(wall_width + (mx_switch_height - screw_thread_height))

            inset_nut_clearance = Shape(
                    # the advice I've been given is to use a 3.5mm hole for these,
                    # so buffer the M3 size by 0.5mm diameter
                    corner_holes.buffer(0.25)
                    ).linearExtrude(inset_nut_height + 0.5).up(
                            wall_width + (mx_switch_height - inset_nut_height) - 0.5)

            case_top -= screw_thread_clearance
            case_top -= inset_nut_clearance
        else:
            post_lugs = Shape(corner_holes).linearExtrude(
                        pcb_height + 1 + bottom_lip_height
                        ).up(wall_width + mx_switch_height - 1)
            case_top += post_lugs

        bounds = bottom_plate.buffer(wall_width).envelope
        model_width = width_of(bounds)
        model_height = height_of(bounds)
        if model_width <= print_bed_width and \
                model_height <= print_bed_height:
            needs_cut = False
        else:
            needs_cut = True

        # For debug purposes
        # needs_cut = False

        if touchpad:
            if not needs_cut:
                case_top += touchpad.transparent()
            case_top -= touchpad
            if touchpad_enclosure:
                case_top += touchpad_enclosure
            # and ensure we have clearance for it
            case_top -= touchpad_footprint
        if want_mcu:
            if not needs_cut:
                case_top += mcu.color('skyblue').transparent()
            if naked_mcu:
                if not needs_cut:
                    case_top += jst_bump.transparent()
                case_top -= jst_bump

        if not needs_cut:
            case_top += trrs.color('red').transparent()

        case_top -= cap_hole_exclusion

        def maybe_flip(shape):
            ''' This logic appears to be inverted... that's because
                by default we're building the mirror image, so we
                want to flip by default to produce the correct
                parts.  If the config says they want to flip then
                we can skip the flip here. '''
            if self.shape_config.get('3dprint_flip', False):
                return shape
            return shape.mirror([1, 0, 0])

        bounds = bottom_plate.buffer(wall_width).envelope
        model_width = width_of(bounds)
        model_height = height_of(bounds)

        case_top = scad.add_module('case_top', case_top)

        stl_to_render = []

        if needs_cut:
            assert(model_width/2 <= print_bed_width)
            assert(model_height/2 <= print_bed_height)

            for (name, piece) in [
                                  ('sliced_case_top_left', 0),
                                  ('sliced_case_top_right', 1),
                                  ('sliced_case_bottom_left', 2),
                                  ('sliced_case_bottom_right', 3),
                                  ('sliced_case_top', None)
                                ]:
                sliced = scad.add_module(name, case_top.quarter(
                    x=model_width,
                    y=model_height,
                    z=mx_switch_height + wall_width + \
                            bottom_lip_height,
                    y_cut_delta=self.shape_config.get(
                        '3dprint_quarter_y_cut_delta', 0),
                    x_cut_delta=self.shape_config.get(
                        '3dprint_quarter_x_cut_delta', 0),
                    offset=[bounds.bounds[0],
                            bounds.bounds[1]],
                    piece=piece))

                # Emit a separate scad file per quadrant for easier export
                # of individual parts as STL files
                part = openscad.Script()
                part.use('%s.scad' % self.name)
                part.add(maybe_flip(sliced.translate([
                        -(bounds.bounds[0] + model_width/2),
                        -(bounds.bounds[1] + model_height/2)])))

                scad_name = os.path.join(outputs, '%s-%s.scad' % (self.name, name))
                stl_name = os.path.join(outputs, '%s-%s.stl' % (self.name, name))
                part.save(scad_name)
                if piece is not None:
                    stl_to_render.append((scad_name, stl_name))

        case_top = case_top.translate([
                -(bounds.bounds[0] + model_width/2),
                -(bounds.bounds[1] + model_height/2)])
        scad.add(case_top)

        top_module = openscad.Module('case_top', [maybe_flip(case_top)])

        if touchpad_stand:
            stand_script = openscad.Script()
            stand_script.use('%s.scad' % self.name)
            stand_script.add(maybe_flip(touchpad_stand.right(model_width/2).back(model_height/2)))
            stand_script.save(os.path.join(outputs, 'touchpad_stand-%s.scad' % name))

        scad_filename = os.path.join(outputs, '%s.scad' % self.name)
        stl_filename = os.path.join(outputs, '%s.stl' % self.name)
        stl_to_render.append((scad_filename, stl_name))
        scad.save(scad_filename)

        procs = []
        for (scad_name, stl_name) in stl_to_render:
            print('Rendering %s...' % stl_name)
            procs.append(subprocess.Popen(['openscad', '-o', stl_name, scad_name]))
        for proc in procs:
            proc.wait()

