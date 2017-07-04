from shapely.geometry import (Point, box)
from shapely.affinity import (translate, scale, rotate)
import skidl
from . import kicadpcb


class Component(object):

    def __init__(self, part, footprint, module, ref=None, hide_value=True):
        self.position = Point(0, 0)
        self.rotation = 0
        self._ref = ref

        self.part = part  # the skidl part
        self.footprint = footprint  # the footprint name
        self.module = module  # the pykicad footprint instance

        # Workaround https://github.com/dvc94ch/pykicad/issues/11
        self.module.model = None

        if ref:
            self.set_ident(ref)

        if hide_value:
            for t in self.module.texts:
                if t.type == 'value':
                    t.hide = True

        # Collect a map of pads from the footprint object; these are
        # the pins of the device, but with the physical coords
        self._pads = {}
        for padidx, pad in enumerate(self.module.pads):
            pos = pad.at
            size = pad.size
            shape = pad.shape
            if shape == 'rect':
                padshape = box(pos[0] - size[0] / 2,
                               pos[1] - size[0] / 2,
                               pos[0] + size[0] / 2,
                               pos[1] + size[0] / 2)
            elif shape in ('oval', 'circle'):
                padshape = scale(Point(*pos).buffer(1),
                                 size[0] / 2, size[1] / 2)
            else:
                raise Exception("unhandled pad shape " + str(shape))

            if len(pos) > 2:
                # apply its individual rotation
                padshape = rotate(padshape, 360 - pos[2], origin=pos[0:2])

            padname = str(padidx if pad.name in self._pads else pad.name)
            self._pads[padname] = padshape
            if self.part:
                # stitch the pad and the pin together
                try:
                    pin = self.part[padname]
                    # there are a number of HOLE pads that don't
                    # have corresponing pins, so skip those
                    if pin:
                        pin.component = self
                except KeyError:
                    pass

        if self.part:
            if ref:
                self.part.ref = ref

            for pin in self.part.pins:
                if not hasattr(pin, 'component'):
                    print('part', self.part.name,
                          'pin', pin.name,
                          'num', pin.num,
                          'has no matching pad')

    def transform(self, shape):
        ''' transforms a shape by the component position and rotation '''
        return rotate(translate(shape,
                                self.position.bounds[0],
                                self.position.bounds[1]),
                      self.rotation,
                      origin=(self.position.bounds[0], self.position.bounds[1]))

    def reserve_nets(self, circuit):
        ''' override me to associate pins with nets at creation time '''
        pass

    def pad(self, name):
        ''' Returns the coordinates of the named pad.
            The coordinates take into account the position and rotation
            of the part '''
        if name not in self._pads:
            name = self.module.pads[name].name
        return self.transform(self._pads[name])

    def set_ident(self, name):
        self._ref = name
        self.module.name = name
        if self.part:
            self.part.ref = name

        for t in self.module.texts:
            if t.type == 'reference':
                t.text = name

    def set_position(self, point):
        self.position = point
        self._apply_position()

    def _apply_position(self):
        self.module.at = kicadpcb.coords(self.position) + [-self.rotation]

    def set_rotation(self, angle):
        self.rotation = angle
        self._apply_position()

    def remove_nc_pads(self):
        ''' remove any pads that are not connected in the circuit.
            This can make room for routing connections '''
        if not self.part:
            return

        remove = []
        for pin in self.part.pins:
            pad = self.find_pad(pin)
            if not pad or pad.type == 'np_thru_hole':
                continue

            for n in pin.nets:
                if n == skidl.builtins.NC:
                    remove.append(pad)
                    break

        self.module.pads = [
            pad for pad in self.module.pads if pad not in remove]

    def find_pad_by_name(self, name):
        for pad in self.module.pads:
            if pad.name == name:
                return pad
        return None

    def find_pad(self, pin):
        for pad in self.module.pads:
            if pad.name == pin.num:
                return pad
        return None

    def add_to_pcb(self, pcb):
        ''' adds this component to pcb, an instance of kicadpcb.Pcb '''
        pcb.add_component(self.module)

        if self.part:
            for pin in self.part.pins:
                if len(pin.nets) > 1:
                    print('Multiple nets on %s\n%s' % (self.part, pin))
                    continue
                for n in pin.nets:
                    if n == skidl.builtins.NC:
                        continue
                    pad = self.find_pad(pin)
                    if not pad:
                        print('Module has no pad matching pin %r' % pin.num)
                    else:
                        pad.net = pcb.net(n.name)

    def available_pin(self):
        ''' looks at the pins that have no connections and returns
            the first one it finds '''
        avail = self.available_pins()
        if len(avail):
            return avail[0]
        return None

    def available_pins(self):
        ''' returns a list of all pins with no connections '''

        def is_pin_used(p):
            if not p.nets:
                return False
            if len(p.nets) == 0:
                return False
            return True

        return [p for p in self.part.pins if not is_pin_used(p)]


class Feather(Component):
    def reserve_nets(self, circuit):
        self.part['GND'] += circuit.net('GND')
        self.part['\+3V3'] += circuit.net('3V3')
        self.part[27] += circuit.net('SCL')
        self.part[28] += circuit.net('SDA')

        for p in ['VBAT', 'EN', 'RST', 'AREF', 'VBUS']:
            self.part[p] += skidl.builtins.NC


class Teensy(Component):
    def reserve_nets(self, circuit):
        #self.part['GND'] += circuit.net('GND')
        self.part['3.3V_max100m'] += circuit.net('3V3')
        self.part['18_A4_SDA0_Touch'] += circuit.net('SDA')
        self.part['19_A5_SCL0_Touch'] += circuit.net('SCL')

        for p in ['Program', 'GND', 'VUSB', 'Vin', 'AREF']:
            self.part[p] += skidl.builtins.NC