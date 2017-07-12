from __future__ import absolute_import
from __future__ import print_function

# Some setup to adjust the logging defaults for skidl.  This needs to
# happen before we import skidl.
from tqdm import tqdm
import logging

from scipy.spatial import Delaunay
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)


class SuppressSkidlWarning(logging.Filter):
    ''' suppress this warning; we take care of this for ourselves
        after we've imported skidl '''

    def filter(self, record):
        return not record.getMessage().startswith(
            'KISYSMOD environment variable is missing')


def fixup_skidl_logging_pre():
    logging.getLogger().addFilter(SuppressSkidlWarning())


fixup_skidl_logging_pre()

from . import component
from . import kicadpcb
from .router import spatialmap
from .router import types
from .router import triangulation
from .router import msteinertree
from .. import svg

import skidl
import collections
import networkx
import itertools


def fixup_skidl_logging_post():
    ''' Remove the ERC logging handler, because it doubles up the
        output and that makes things harder to read.
        We have to monkey patch this into the ERC setup because
        skidl unconditionally adds handlers each time it is run. '''
    orig_setup = skidl.Circuit._erc_setup

    def replace_handlers(logger):
        for h in logger.handlers:
            logger.removeHandler(h)

    def monkey_patched_erc_setup(circuit):
        orig_setup(circuit)
        replace_handlers(logging.getLogger('ERC_Logger'))

    skidl.Circuit._erc_setup = monkey_patched_erc_setup


fixup_skidl_logging_post()

skidl.lib_search_paths[skidl.KICAD] += [
    'kicad/symbols',
    '/Library/Application Support/kicad/library',
]


class Circuit(object):
    ''' Represents a circuit, both the schematic and the physical
        PCB aspects of it.
        We want to be able to produce both the schematic and the
        PCB layout; we want to be able to allocate pins from the MCU
        based on their physical position, so we need to be able
        to load up the footprints and interrogate them.
    '''

    def __init__(self):

        self.pcb = kicadpcb.Pcb()
        self.circuit = skidl.Circuit()

        # The list of parts that comprise this circuit
        self._parts = []

        self._defer_pins = []

        self._next_ref = 1

        self._nets = collections.OrderedDict()
        self.net('GND', skidl.POWER)
        self.net('3V3', skidl.POWER)

    def net(self, name, drive=skidl.Pin.NO_DRIVE):
        ''' define or return a well-known net '''
        if name in self._nets:
            return self._nets[name]
        net = skidl.Net(name, circuit=self.circuit)
        net.drive = drive
        self._nets[name] = net
        return net

    def part(self, device, value, footprint, cls=component.Component, ref=None):
        if device:
            part = skidl.Part(device,
                              value,
                              footprint=footprint,
                              circuit=self.circuit)
        else:
            part = None
        module = self.pcb.parseFootprintModule(footprint)

        if not part and not ref:
            ref = 'X%d' % self._next_ref
            self._next_ref += 1

        component = cls(part, footprint, module, self, ref=ref)
        component.reserve_nets()
        self._parts.append(component)

        return component

    def defer_pin_assignment(self, net_or_pin, component):
        ''' arrange to compute a pin assignment later on.
            The specified net will be connected to an available pin
            at save time.  The assignment will consider the pins
            already connected to the net and take into account the
            physical distances for possible pin mappings '''
        self._defer_pins.append((net_or_pin, component))

    def assign_pins(self):
        ''' Evaluate pin assignments '''

        for net_or_pin, component in tqdm(self._defer_pins, desc='pin assignment', unit='pins'):
            # First, look at all of the pins associated with the net; we want
            # to locate the pin that is closest to the component and use that
            # to score possible connections
            def has_pad(pin):
                return hasattr(pin, 'component')

            def padshape(pin):
                return pin.component.pad(pin.num)

            def dist_from_comp(pin):
                return padshape(pin).distance(component.position)

            if isinstance(net_or_pin, skidl.Net):
                net = net_or_pin
                pins = filter(has_pad, sorted(net.pins,
                                              key=dist_from_comp,
                                              reverse=True))
                # this is our most representative pin from the net
                net_pin = list(pins)[0]
            else:
                net_pin = net_or_pin

            net_shape = padshape(net_pin).centroid

            def dist_from_net_pin(pin):
                return padshape(pin).centroid.distance(net_shape)

            pins = filter(has_pad, sorted(filter(has_pad,
                                                 component.available_pins()),
                                          key=dist_from_net_pin,
                                          reverse=False))

            if not pins:
                raise Exception("no more pins are available on %s" % component)

            # this is the best available pin on the component
            comp_pin = list(pins)[0]

            # Connect the net to the best available pin
            net_pin += comp_pin

        # and we're done; clear out the list so that we can potentially
        # do a second batch of these later
        self._defer_pins = []

    def diode(self, surface_mount=False):
        return self.part('device',
                         'D',
                         'clacker:D_axial' if not surface_mount else 'clacker:D_SOD123')

    def feather(self):
        return self.part('MiscellaneousDevices',
                         'ADAFRUIT_FEATHER',
                         'clacker:ADAFRUIT_FEATHER_NO_MOUNTING_HOLES',
                         cls=component.Feather)

    def keyswitch(self):
        return self.part('keyboard_parts',
                         '~KEYSW',
                         'clacker:Mx_Alps_100')

    def rj45(self):
        return self.part('conn',
                         'RJ45',
                         'Connectors:RJ45_8')

    def teensy(self):
        return self.part('teensy',
                         'Teensy-LC',
                         'clacker:Teensy_LC',
                         cls=component.Teensy)

    def hole_m3(self):
        ''' the hole is footprint only and doesn't have a part
            for the electrical model '''
        return self.part(None, None, 'Keyboard_Parts:HOLE_M3')

    def drawShape(self, layerName, shape):
        ''' Draw the specified shape on the specified layer '''
        self.pcb.drawShape(layerName, shape)

    def addArea(self, layerName, net, shape):
        ''' Create an filled area and attach it to the specified net '''
        self.pcb.addArea(layerName, net.name, shape)

    def save(self, filename):
        ''' called after all of the parts have been placed and
            all of the nets have been connected.
            This walks through the model and populates a fresh
            instance of the pcbnew board model '''
        for net in self.circuit._get_nets():
            if net == self.circuit.NC:
                continue
            self.pcb.net(net.name)

        self.pcb.save(filename + '.kicad_pcb')
        skidl.generate_netlist(filename + '.net')

    def finalize(self):
        self.assign_pins()
        self.circuit.ERC()
        # tqdm.write('Removing redundant pads')
        for part in self._parts:
            part.add_to_pcb(self.pcb)
            # part.remove_nc_pads()

    def computeRoutingData(self):
        to_route = networkx.Graph()
        tri = triangulation.Triangulation()

        # Turn each net into the set of TwoNets that we'll need to route.
        # We compute the minimum spanning tree of each net, then take
        # each pair of edges; those are the TwoNets
        two_nets = []
        pad_to_node = {}
        smap = spatialmap.SpatialMap()

        list_of_nets = []

        for net in self.circuit._get_nets():
            if net == self.circuit.NC:
                continue
            g = networkx.Graph()
            pins_in_net = []
            for pin in net._get_pins():
                pad = pin.component.find_pad(pin)
                if pad.type == 'thru_hole':
                    t = types.ThruHole(pin)
                else:
                    t = types.SmdPad(pin, pad)
                g.add_node(t)
                to_route.add_node(t)
                pad_to_node[t.shape.wkt] = t
                smap.add(t.shape, t)
                tri.add_node(t)
                pins_in_net.append(t)

            list_of_nets.append(pins_in_net)

            if False:
                for a, b in itertools.combinations(g.nodes(), r=2):
                    g.add_edge(a, b, weight=a.shape.centroid.distance(
                        b.shape.centroid))

                mst = networkx.minimum_spanning_tree(g)
                for a, b in mst.edges():
                    to_route.add_edge(a, b)
                    two_nets.append((a, b))
            else:
                # Prefer the steiner variant of the MST because it generates
                # a layout that is easier to route than the pure MST.
                mst = msteinertree.rectilinear_steiner_minimum_spanning_tree(
                    pins_in_net)
                two_nets += mst

        for part in self._parts:
            for pad, shape in part._pads_by_idx.values():
                if not part.find_pad_by_name(pad.name):
                    # Was elided
                    continue
                shape = part.transform(shape)
                node = pad_to_node.get(shape.wkt)
                if node:
                    smap.add(node.shape, node)
                else:
                    obs = types.Obstacle(pad.layer, shape, pad)
                    smap.add(shape, obs)
                    tri.add_node(obs)

        return {
            'graph': to_route,
            '2nets': two_nets,
            'smap': smap,
            'triangulation': tri,
            'list_of_nets': list_of_nets,
        }

    def toSVG(self):
        doc = svg.SVG()

        for comp in self._parts:
            for idx, pad in enumerate(comp.module.pads):
                if not comp.find_pad_by_name(pad.name):
                    # was elided
                    continue

                doc.add(comp.pad(idx),
                        stroke='orange' if pad.type == 'thru_hole' else 'green',
                        stroke_width=0.1,
                        fill='gold',
                        fill_opacity=0.2)
            for line in comp.module.lines:
                adjusted = map(comp.transform, map(
                    Point, [line.start, line.end]))
                doc.add(LineString(adjusted),
                        stroke='gray',
                        stroke_width=line.width)
            for circ in comp.module.circles:
                adjusted = comp.transform(Point(circ.center))
                doc.add(adjusted.buffer(circ.width / 2),
                        stroke='gray',
                        stroke_width=0.1,
                        fill_opacity=0)

        return doc
