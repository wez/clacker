from __future__ import absolute_import
from __future__ import print_function
import os
import re
import subprocess

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
from .circuitlib.router import (router, types, msteinertree)

import pycircuit


class Pcb(targets.Target):
    def __init__(self, name, layout, surface_mount=False, shape_config=None):
        super(Pcb, self).__init__(name)
        self.layout = layout
        self.surface_mount = surface_mount
        self.shape_config = shape_config

    def build(self):
        commit_date = subprocess.check_output([
            'git','show','-s','--format=%ad', '--date=short']).decode('ascii').rstrip()
        commit_info = subprocess.check_output([
            'git', 'describe', '--always', '--dirty=-dirty']).decode('ascii').rstrip().rstrip()
        self.repo_state = '%s %s' % (commit_info, commit_date)

        print('Gen PCB %s %s' % (self.full_name, self.repo_state))
        # Compute outputs dir
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        filesystem.mkdir_p(outputs)
        layout = self.layout.layout
        shapes = shape.make_shapes(layout, shape_config=self.shape_config)

        logical_matrix, physical_matrix = matrix.compute_matrix(
            layout, outputs)
        circuit = self.gen_schematic(layout, shapes, outputs, physical_matrix)
        #self.route(circuit, shapes, outputs)

    def route(self, circuit, shapes, outputs):
        data = circuit.computeRoutingData()
        tri = data['triangulation']

        bounds = shapes['bottom_plate'].envelope

        def cxlate(shape):
            PCBNEW_SPACING = 25
            return translate(shape,
                             PCBNEW_SPACING - bounds.bounds[0],
                             PCBNEW_SPACING - bounds.bounds[1])

        tri.add_node(types.Obstacle(
            'Edge.Cuts', cxlate(shapes['bottom_plate']), 'Edge'))
        if False:
            # Add some grid-snapped points
            width = int(bounds.bounds[2])
            height = int(bounds.bounds[3])
            for x in range(0, width, 10):
                for y in range(0, height, 10):
                    p = Point(x, y)
                    if shapes['bottom_plate'].intersects(p):
                        tri.add_node(types.Branch(
                            cxlate(p), layer=types.FRONT))

        g = data['graph'] # router.route(data)
        #g = router.route(data)

        doc = circuit.toSVG()

        colors = {
            'F.Cu': ['green', 'magenta'],
            'B.Cu': ['blue',  'red']
        }
        done = set()

        def render_from_graph(g):
            for a, b in g.edges():
                def draw(a):
                    if a not in done:
                        if isinstance(a, types.Obstacle) and isinstance(a.value, str) and a.value == 'Edge':
                            doc.add(a.shape,
                                    stroke='green',
                                    fill_opacity=0,
                                    stroke_width=0.2)
                        else:
                            doc.add(a.shape,
                                    stroke='red',
                                    stroke_width=0.2,
                                    fill_opacity=0.4,
                                    fill='red')
                        done.add(a)
                draw(a)
                draw(b)

                if g[a][b].get('via'):
                    doc.add(a.shape.buffer(2),
                            fill='blue',
                            fill_opacity=0.4,
                            stroke='blue',
                            stroke_width=0.1)
                else:
                    collision = g[a][b].get('collision', False)
                    layer = g[a][b].get('layer') or 'B.Cu'
                    color = colors[layer]
                    color = color[1] if collision else color[0]

                    doc.add(LineString([a.shape.centroid, b.shape.centroid]).buffer(0.125),
                            fill=color,
                            fill_opacity=0.4,
                            stroke=color,
                            stroke_width=0.1)

        if False:
            tri_g = tri.triangulate()
            render_from_graph(tri_g)

        render_from_graph(g)

        if False:
            # Render physical objects with a blue halo
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
        mcu_type = self.shape_config.get('mcu', 'feather') if self.shape_config else 'feather'
        if mcu_type == 'feather':
            cmcu = circuit.feather()
            cmcu.set_value('FEATHER')
        elif mcu_type == 'teensy':
            cmcu = circuit.teensy()
        elif mcu_type == 'header':
            cmcu = circuit.header()
            header = cmcu
        else:
            raise Exception('handle mcu %s' % mcu_type)

        for pin in self.shape_config.get('reserve_pins', {}).get('mcu', []):
            cmcu.part[pin] += circuit.net(pin)

        if self.shape_config.get('header', False):
            header = circuit.header()
        else:
            header = None

        j1 = None
        j2 = None

        trrs_type = self.shape_config.get('trrs', None) if self.shape_config else None
        if trrs_type == 'basic':
            trrs = circuit.trrs(ref='J1')
            trrs.set_ident('J1')
            trrs.set_position(translate(cxlate(shapes['trrs']), 0, 5.5))
            trrs.set_rotation(90);
            trrs.reserve_i2c()
        elif trrs_type == 'left+right':
            trrs = circuit.trrs(ref='J1', dual=True)
            trrs.set_position(translate(cxlate(shapes['trrs']), 0, 5.5))
            trrs.set_rotation(90);
            trrs.reserve_i2c()
            j1 = circuit.jumper3(ref='JP1')
            j1.set_position(translate(cxlate(shapes['trrs']), 9, 3))
            j2 = circuit.jumper3(ref='JP2')
            j2.set_position(translate(cxlate(shapes['trrs']), 9, 9.5))
            j2.set_rotation(180)

            j1.part['1'] += circuit.net('3V3')
            j1.part['2'] += trrs.part['R2']
            j1.part['3'] += circuit.net('GND')

            j2.part['1'] += circuit.net('GND')
            j2.part['2'] += trrs.part['S']
            j2.part['3'] += circuit.net('3V3')
        else:
            trrs = None

        rj45_type = self.shape_config.get('rj45', None) if self.shape_config else None
        if rj45_type == 'basic':
            rj45 = circuit.rj45(ref='J1')
            rj45.set_position(translate(cxlate(shapes['rj45']), 0, 14))
            rj45.set_rotation(180);
            rj45.reserve_i2c()
            rj45_right = None
        elif rj45_type == 'left+right':
            rj45 = circuit.rj45(ref='J1')
            rj45.set_position(translate(cxlate(shapes['rj45']), 7.5, 14))
            rj45.set_rotation(0);
            rj45.flip()
            rj45_right = circuit.rj45(ref='J2')
            rj45_right.set_position(translate(cxlate(shapes['rj45']), 0, 14))
            rj45_right.set_rotation(180);
            rj45.reserve_i2c()
            rj45_right.reserve_i2c()
        elif rj45_type == 'magjack':
            rj45 = circuit.rj45_magjack()
            rj45.set_position(translate(cxlate(shapes['rj45']), 0, 0))
            rj45.reserve_i2c()
            rj45_right = None
        else:
            rj45 = None
            rj45_right = None

        cmcu.reserve_spi()
        cmcu.reserve_i2c()

        if mcu_type == 'feather':
            cmcu.set_position(translate(cxlate(shapes['mcu']), 12, 26))
            cmcu.set_rotation(90)
            cmcu.flip()
        elif mcu_type == 'teensy':
            cmcu.set_position(translate(cxlate(shapes['mcu']), 9, 18))
            cmcu.set_rotation(90)
            pass
        elif mcu_type == 'header':
            pass
        else:
            raise Exception('handle mcu %s' % mcu_type)

        if header:
            header_coords = self.shape_config.get('header_coords', (20, 120, 105))
            header.set_position(Point(header_coords[0], header_coords[1]))
            header.set_rotation(header_coords[2])
            header.reserve_i2c()
            header.reserve_spi()
            # keep an MCU pin for possible future SPI add-on
            circuit.defer_pin_assignment(circuit.net('CS'), cmcu)
            # bring out other supply levels
            for n in ['VBAT', 'VBUS']:
                circuit.defer_pin_assignment(circuit.net(n), header)
            for pin in self.shape_config.get('reserve_pins', {}).get('mcu', []):
                circuit.defer_pin_assignment(circuit.net(pin), header)

        cirque_coords = self.shape_config.get('cirque_coords', None)
        if cirque_coords:
            cirque = circuit.cirque()
            cirque.set_position(Point(*cirque_coords))
            cirque.reserve_spi()
        else:
            cirque = None

        expander = None
        if self.shape_config.get('expander', True):
            expander_coords = self.shape_config.get('expander_coords', (5, 90, 90))
            expander_rotation = expander_coords[2]
            expander = circuit.expander()
            expander.set_value('SparkFun SX1509')
            expander.set_ident('U2')
            expander.set_rotation(expander_rotation)
            expander.reserve_i2c()

            expander_pos = Point(expander_coords[0], expander_coords[1])
            if False:
                expander_pos = translate(expander_pos, 19, 0)
                expander.flip()

            expander.set_position(expander_pos)

        if rj45:
            rj45.part['5'] += circuit.net('~INT')
        if rj45_right:
            rj45_right.part['5'] += circuit.net('~INT')
        if header:
            circuit.defer_pin_assignment(circuit.net('~INT'), header)
        if rj45 or rj45_right or header:
            circuit.defer_pin_assignment(circuit.net('~INT'), cmcu)


        num_cols, num_rows = matrix.dimensions()
        col_nets = [circuit.net('col%d' % n) for n in range(0, num_cols)]
        row_nets = [circuit.net('row%d' % n) for n in range(0, num_rows)]

        for y, x, k in tqdm(list(matrix.keys()), desc='key schematic', unit='keys'):
            ident = '%d%d' % (y, x)  # k.identifier

            phys = k.centroid()
            phys = Point(phys[0], phys[1])

            csw = circuit.keyswitch()
            csw.set_position(cxlate(phys))
            csw.set_rotation(k.rotation_angle)
            csw.set_ident('SW%s' % ident)
            csw.set_value('SW%s' % ident)

            # pin 1 attaches to the column wiring
            csw.part['1'] += col_nets[x]
            csw.part['1a'] += col_nets[x]

            # anti-ghosting diode attaches to pin 2 and joins the row wiring

            diode_pos = translate(phys,
                                  yoff=-(SWITCH_SPACING / 2) + 1,
                                  xoff=(SWITCH_SPACING / 2) - 5
                                  )

            diode_pos = rotate(diode_pos, k.rotation_angle, phys)

            cdiode = circuit.diode(surface_mount=self.surface_mount)
            cdiode.set_ident('D' + ident)
            cdiode.set_position(cxlate(diode_pos))
            cdiode.set_rotation(180 + k.rotation_angle)
            csw.part['2'] += cdiode.part['A']  # anode
            csw.part['2a'] += cdiode.part['A']  # anode
            cdiode.part['K'] += row_nets[y]    # cathode -> row

        for y in range(0, num_rows):
            circuit.defer_pin_assignment(row_nets[y], cmcu)
            if header:
                circuit.defer_pin_assignment(row_nets[y], header)

        for x in range(0, num_cols):
            circuit.defer_pin_assignment(col_nets[x], cmcu)
            if header:
                circuit.defer_pin_assignment(col_nets[x], header)

        for n, pt in enumerate(shapes['corner_points']):
            hole = circuit.hole_m3()
            hole.set_position(cxlate(pt))
            hole.set_ident('CP%d' % n)

        # Ground plane.
        pour_area = shapes['bottom_plate'].buffer(0)
        circuit.addArea('B.Cu', circuit.net('GND'), cxlate(pour_area))
        circuit.addArea('F.Cu', circuit.net('GND'), cxlate(pour_area))

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

        if expander:
            for no, net in enumerate(row_nets):
                expander.part[str(no)] += net
            for no, net in enumerate(col_nets):
                expander.part[str(no + 8)] += net

        # make sure that those pins get mapped before we tie off all remaining
        # mcu pins to the NC net
        # circuit.assign_pins()

        # Any remaining pins on the mcu are intentionally left unconnected
        circuit.circuit.NC += cmcu.available_pins()

        logo_coords = Point(self.shape_config.get('logo_coords', (54, 157)))

        logo = circuit.spockl()
        logo.set_position(translate(logo_coords))

        version_coords = self.shape_config.get('version_coords', None)
        if version_coords:
            circuit.text(
                    '%s by %s' % (self.layout.layout.name(),
                                  self.layout.layout.author()),
                    version_coords,
                    #layer='F.SilkS',
                    #size=[1.0, 1.0],
                    justify='left',
                    #thickness=0.15
                    )
            circuit.text(
                    'https://github.com/wez/clacker %s %s' % (self.full_name, self.repo_state),
                    [version_coords[0], version_coords[1] + 2.5],
                    #layer='F.SilkS',
                    #size=[1.0, 1.0],
                    justify='left',
                    #thickness=0.15
                    )

        logor = circuit.spockr()
        logor.set_position(translate(logo_coords))

        # circuit.circuit.NC += cteensy.available_pins()
        circuit.finalize()

        # Render labels for the nets that are attached to the various
        # pins that we just emitted

        def oddeven(pin, remainder=0):
            ''' left or right justification depending on whether the
                pin number is odd or even.  This is for components
                where the pin numbers zig-zag '''

            try:
                pin_num = int(pin.num)
                return 'right' if pin_num % 2 == remainder else 'left'
            except ValueError:
                return 'right'

        def left_right(pin, cutoff):
            ''' left justify if the pin is < cutoff '''
            try:
                pin_num = int(pin.num)
                return 'right' if pin_num >= cutoff else 'left'
            except ValueError:
                return 'right'

        def right_left(pin, cutoff):
            ''' right justify if the pin is < cutoff '''
            try:
                pin_num = int(pin.num)
                return 'right' if pin_num < cutoff else 'left'
            except ValueError:
                return 'right'

        def list_get(list, idx, defval=None):
            ''' helper for safely accessing a list offset with a default '''
            return (list[idx:idx+1] or [defval])[0]

        def add_net_labels(component, layer='F.SilkS', mirror=False, rotate=0,
                           size=0.8, numbering=oddeven):
            ''' label each pad with the associated net '''
            for pin in component.part.pins:
                for net in pin.nets:
                    if net == net.circuit.NC or '$' in net.name:
                        continue
                    pad = component.find_pad(pin)

                    if pad.name == pin.name and pin.name == net.name:
                        # if the pin is already labelled, don't add another with
                        # the same text
                        continue

                    justify = numbering(pin)
                    if mirror:
                        justify=('left' if justify == 'right' else 'right', 'mirror')

                    label = '  %s  ' % net.name
                    at = [pad.at[0], pad.at[1], list_get(pad.at, 2, 0) + rotate]

                    text = circuitlib.kicadpcb.pykicad.module.Text(text=label,
                            at=at,
                            layer=layer,
                            size=[size, size],
                            justify=justify,
                            thickness=0.15)
                    component.module.texts.append(text)

        if header:
            add_net_labels(header, 'F.SilkS', rotate=30)
            add_net_labels(header, 'B.SilkS', rotate=30,
                           mirror=True,
                           numbering=lambda pin: oddeven(pin, remainder=0))
        add_net_labels(cmcu, 'F.SilkS', mirror=False, rotate=90,
                       numbering=lambda pin: left_right(pin, 17))
        add_net_labels(cmcu, 'B.SilkS', mirror=True, rotate=90,
                       numbering=lambda pin: left_right(pin, 17))
        if expander:
            add_net_labels(expander, 'B.SilkS', rotate=990, mirror=True,
                           numbering=lambda pin: left_right(pin, 8))
            add_net_labels(expander, 'F.SilkS', mirror=False, rotate=120,
                           numbering=lambda pin: left_right(pin, 8))
        if rj45:
            add_net_labels(rj45, 'B.SilkS', mirror=True, rotate=90)
        if rj45_right:
            add_net_labels(rj45_right, 'F.SilkS', rotate=90,
                           numbering=lambda pin: oddeven(pin, remainder=1))
        if trrs:
            add_net_labels(trrs, 'B.SilkS', mirror=True, rotate=180)
            add_net_labels(trrs, 'F.SilkS', rotate=180,
                           numbering=lambda pin: oddeven(pin, remainder=1))

        if j1:
            add_net_labels(j1, 'F.SilkS', rotate=90, size=0.6,
                           numbering=lambda pin: oddeven(pin, remainder=1))
        if j2:
            add_net_labels(j2, 'F.SilkS', rotate=90, size=0.6,
                           numbering=lambda pin: oddeven(pin, remainder=1))
        if cirque:
            add_net_labels(cirque, 'F.SilkS', rotate=30, size=0.6,
                           numbering=lambda pin: oddeven(pin, remainder=0))
            add_net_labels(cirque, 'B.SilkS', rotate=30, size=0.6,
                           mirror=True,
                           numbering=lambda pin: oddeven(pin, remainder=0))

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
