from __future__ import absolute_import
from __future__ import print_function

import os
import re

from . import targets
from . import board
from . import library
from . import projectdir
from . import filesystem
from .circuitlib import circuit as circuitlib
from .circuitlib import shape
from . import svg
from . import matrix

from shapely.affinity import (translate, scale, rotate)
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
import skidl
from tqdm import tqdm

from .kle import SWITCH_SPACING


class Pcb(targets.Target):
    def __init__(self, name, layout):
        super(Pcb, self).__init__(name)
        self.layout = layout

    def build(self):
        print('Gen PCB %s' % self.full_name)
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

        logical_matrix, physical_matrix = matrix.compute_matrix(
            layout, outputs)
        self.gen_schematic(layout, shapes, outputs, physical_matrix)

    def gen_schematic(self, layout, shapes, outputs, matrix):
        def cxlate(shape):
            PCBNEW_SPACING = 25
            return translate(shape,
                             PCBNEW_SPACING - bounds.bounds[0],
                             PCBNEW_SPACING - bounds.bounds[1])

        bounds = shapes['bottom_plate'].envelope
        circuit = circuitlib.Circuit()
        cmcu = circuit.feather()
        # cmcu.reserve_spi()
        # cmcu.reserve_i2c()
        cmcu.set_position(translate(cxlate(shapes['mcu']), 12, 26))
        cmcu.set_rotation(90)

        num_cols, num_rows = matrix.dimensions()
        col_nets = [circuit.net('col%d' % n) for n in range(0, num_cols)]
        row_nets = [circuit.net('row%d' % n) for n in range(0, num_rows)]

        surface_mount = True

        for y, x, k in tqdm(list(matrix.keys()), desc='key schematic', unit='keys'):
            ident = k.identifier

            phys = k.centroid()
            phys = Point(phys[0], phys[1])

            csw = circuit.keyswitch()
            csw.set_position(cxlate(phys))
            csw.set_rotation(k.rotation_angle)
            csw.set_ident(ident)

            # pin 1 attaches to the column wiring
            csw.part['1'] += col_nets[x]

            # anti-ghosting diode attaches to pin 2 and joins the row wiring

            diode_pos = translate(phys,
                                  yoff=-(SWITCH_SPACING / 2) + 1,
                                  xoff=(SWITCH_SPACING / 2) - 5
                                  )

            diode_pos = rotate(diode_pos, k.rotation_angle, phys)

            cdiode = circuit.diode(surface_mount=surface_mount)
            cdiode.set_ident('D' + ident)
            cdiode.set_position(cxlate(diode_pos))
            cdiode.set_rotation(180 + k.rotation_angle)
            csw.part['2'] += cdiode.part['2']  # anode
            cdiode.part['1'] += row_nets[y]    # cathode -> row

        for y in range(0, num_rows):
            circuit.defer_pin_assignment(row_nets[y], cmcu)

        for x in range(0, num_cols):
            circuit.defer_pin_assignment(col_nets[x], cmcu)

        for n, pt in enumerate(shapes['corner_points']):
            hole = circuit.hole_m3()
            hole.set_position(cxlate(pt))

        # Ground and supply planes.
        pour_area = shapes['bottom_plate'].buffer(0)
        circuit.addArea('F.Cu', circuit.net('GND'), cxlate(pour_area))
        circuit.addArea('B.Cu', circuit.net('3V3'), cxlate(pour_area))

        circuit.drawShape('Edge.Cuts', cxlate(shapes['bottom_plate']))

        # Figure out pin assignment for the feather
        circuit.assign_pins()

        # Now add in a teensy; the teensy can be used instead of a feather.
        # We place it inside the hull of the feather.  Let's find some reasonable
        # pins to attach the nets to.
        #cteensy = circuit.teensy()
        #cteensy.set_position(translate(cmcu.position, 0, -6.5))
        # cteensy.set_rotation(90)
        # for net in row_nets + col_nets:
        #    for pin in cmcu.part.pins:
        #        if net._is_attached(pin):
        #            circuit.defer_pin_assignment(pin, cteensy)
        # make sure that those pins get mapped before we tie off all remaining
        # mcu pins to the NC net
        # circuit.assign_pins()

        # Any remaining pins on the mcu are intentionally left unconnected
        skidl.builtins.NC += cmcu.available_pins()
        #skidl.builtins.NC += cteensy.available_pins()
        circuit.finalize()

        circuit.save(os.path.join(outputs, self.name))

        # We'd like to know what the matrix pin assignment was in the end,
        # because we need to generate a matrix scanner for it.
        # TODO: store this in a map.  Also need to augment the MCU component
        # type so that we can translate the pin names to the appropriate
        # code for the MCU.
        for net in row_nets + col_nets:
            for pin in net.pins:
                if pin.part == cmcu.part:
                    print('%s -> %s' % (net.name, pin.name))

        return circuit

    def case_bottom(self, shapes, outputs):
        doc = svg.SVG()

        doc.add(shapes['bottom_plate'].symmetric_difference(shapes['corner_holes']),
                stroke='blue',
                fill_opacity=0.1,
                fill='skyblue',
                stroke_width=0.1)

        doc.save(os.path.join(outputs, 'case-bottom.svg'))

    def case_top(self, shapes, outputs):
        doc = svg.SVG()

        doc.add(shapes['top_plate'],
                stroke='black',
                fill_opacity=0.1,
                fill='black',
                stroke_width=0.1)

        doc.save(os.path.join(outputs, 'case-top.svg'))

    def switch_plate(self, shapes, outputs):
        doc = svg.SVG()

        doc.add(shapes['switch_plate'],
                stroke='black',
                fill_opacity=0.1,
                fill='black',
                stroke_width=0.1)

        doc.save(os.path.join(outputs, 'switch-plate-minimal.svg'))

        doc = svg.SVG()

        doc.add(shapes['bottom_plate'].symmetric_difference(
            shapes['switch_holes']).symmetric_difference(
            shapes['corner_holes']),
            stroke='black',
            fill_opacity=0.1,
            fill='black',
            stroke_width=0.1)

        doc.save(os.path.join(outputs, 'switch-plate-full.svg'))
