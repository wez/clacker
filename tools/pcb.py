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
from .circuitlib.router import router

import pycircuit


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

        logical_matrix, physical_matrix = matrix.compute_matrix(
            layout, outputs)
        circuit = self.gen_schematic(layout, shapes, outputs, physical_matrix)
        #self.route(circuit, outputs)

        #self.gen_pycircuit(layout, shapes, outputs, physical_matrix)

    def gen_pycircuit(self, layout, shapes, outputs, matrix):
        from pycircuit.circuit import (circuit, Node, Net, Ref, Sub)
        from pycircuit.export import (
            pcb_to_kicad, export_circuit_to_graphviz, export_pcb_to_svg)
        from pycircuit.pcb import (Pcb)

        def define_devices():
            from pycircuit.device import (Device, Pin)
            from pycircuit.package import (Package, RectCrtyd, TwoPads, Pad)
            from pycircuit.footprint import (Footprint, Map)
            import pycircuit.library

            Device('SW', Pin('1'), Pin('2'))
            #Device('D', Pin('A'), Pin('C'))
            Package('CHERRYMX', RectCrtyd(14, 14), TwoPads(10))
            Footprint('CHERRYMX', 'SW', 'CHERRYMX',
                      Map(1, '1'),
                      Map(2, '2'))
            Footprint('D0805', 'D', '0805', Map(1, 'A'), Map(2, 'K'))

        @circuit('SWITCH')
        def switch():
            n = Node('SW', 'SW')
            n.set_footprint('CHERRYMX')
            d = Node('D', 'D')
            d.set_footprint('D0805')
            Net('COL') + Ref('SW')['1']
            Ref('D')['A'] + Ref('SW')['2']
            Net('ROW') + Ref('D')['K']

        define_devices()

        @circuit('MATRIX')
        def matrix_circuit():
            for y, x, k in tqdm(list(matrix.keys()), desc='key schematic', unit='keys'):
                sub = switch()
                sub.node_by_name('SW').place(*k.centroid())
                sub.node_by_name('D').place(*k.centroid())
                Sub(k.identifier, sub)
                Net('col%d' % x) + Ref(k.identifier)['COL']
                Net('row%d' % y) + Ref(k.identifier)['ROW']

        c = matrix_circuit()

        export_circuit_to_graphviz(c, os.path.join(outputs, 'alt'))

        pcb = Pcb(c)
        export_pcb_to_svg(pcb, os.path.join(outputs, 'alt'))

        if False:
            kpcb = pcb_to_kicad(pcb)
            with filesystem.WriteFileIfChanged(os.path.join(outputs, 'alt.kicad_pcb')) as f:
                f.write(str(kpcb))

    def route(self, circuit, outputs):
        data = circuit.computeRoutingData()
        # g = data['graph'] # router.route(data)
        g = router.route(data)

        doc = circuit.toSVG()

        colors = {
            'F.Cu': ['green', 'magenta'],
            'B.Cu': ['grey',  'red']
        }
        done = set()
        for a, b in g.edges():
            def draw(a):
                if a not in done:
                    doc.add(a.shape,
                            stroke='red',
                            stroke_width=0.2,
                            fill_opacity=0.4,
                            fill='red')
                    done.add(a)
            draw(a)
            draw(b)
            collision = g[a][b].get('collision', False)
            layer = g[a][b].get('layer') or 'B.Cu'
            color = colors[layer]
            color = color[1] if collision else color[0]

            doc.add(LineString([a.shape.centroid, b.shape.centroid]).buffer(0.125),
                    fill=color,
                    fill_opacity=0.4,
                    stroke=color,
                    stroke_width=0.1)

        for ent in data['smap']._entries:
            doc.add(ent.shape.buffer(2),
                    fill='skyblue',
                    fill_opacity=0.2)

        doc.save(os.path.join(outputs, 'circuit.svg'))

    def gen_schematic(self, layout, shapes, outputs, matrix):
        bounds = shapes['bottom_plate'].envelope

        def cxlate(shape):
            PCBNEW_SPACING = 25
            return translate(shape,
                             PCBNEW_SPACING - bounds.bounds[0],
                             PCBNEW_SPACING - bounds.bounds[1])

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
        circuit.circuit.NC += cmcu.available_pins()
        # circuit.circuit.NC += cteensy.available_pins()
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
