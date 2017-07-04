from __future__ import absolute_import
from __future__ import print_function

from . import component
from . import kicadpcb
import skidl
import collections
from tqdm import tqdm

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
        skidl.builtins.default_circuit.reset()

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
        net = skidl.Net(name)
        net.drive = drive
        self._nets[name] = net
        return net

    def part(self, device, value, footprint, cls=component.Component, ref=None):
        if device:
            part = skidl.Part(device, value, footprint=footprint)
        else:
            part = None
        module = self.pcb.parseFootprintModule(footprint)

        if not part and not ref:
            ref = 'X%d' % self._next_ref
            self._next_ref += 1

        component = cls(part, footprint, module, ref=ref)
        component.reserve_nets(self)
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

    def diode(self):
        return self.part('device',
                         'D',
                         'Diodes_THT:D_DO-41_SOD81_P7.62mm_Horizontal')

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
        for net in skidl.builtins.default_circuit._get_nets():
            if net == skidl.builtins.NC:
                continue
            self.pcb.net(net.name)

        self.pcb.save(filename + '.kicad_pcb')
        skidl.generate_netlist(filename + '.net')

    def finalize(self):
        self.assign_pins()
        skidl.ERC()
        tqdm.write('Removing redundant pads')
        for part in self._parts:
            part.add_to_pcb(self.pcb)
            part.remove_nc_pads()

    def computeNets(self):
        ''' Returns a list of Net instances corresponding to
            the nets in the circuit. '''

        nets = []
        for net in skidl.SubCircuit._get_nets():
            if net == skidl.builtins.NC:
                continue
            nets.append(Net(net))

        return nets
