from __future__ import absolute_import
from __future__ import print_function

import tempfile
from shapely.geometry import Point
from shapely.affinity import (translate, scale, rotate)
import urllib
import pprint
import pykicad.module
import pykicad.pcb
import shutil
from urllib.parse import urlparse
import urllib.request
import os

library_map = {
    'Keebs':    'kicad-deps/keebs.pretty',
    'clacker':    'kicad/clacker.pretty',
    'Diodes_THT': 'https://github.com/KiCad/Diodes_THT.pretty',
    'Pin_Headers': 'https://github.com/KiCad/Pin_Headers.pretty',
    'Connectors': 'https://github.com/KiCad/Connectors.pretty',
    'Jumper': 'https://github.com/KiCad/kicad-footprints/Jumper.pretty',
    'Connector_PinSocket_2.54mm': 'https://github.com/KiCad/kicad-footprints/Connector_PinSocket_2.54mm.pretty',
    'Keyboard_Parts': 'https://github.com/tmk/keyboard_parts.pretty',
    'imciner2_Modules': 'kicad-deps/imciner2-kicad/modules/Modules.pretty',
    'kicad_teensy': 'kicad-deps/kicad_teensy/Teensy.pretty',
}


def coords(shape):
    if shape.geom_type == 'point':
        return [shape.x, shape.y]
    return list(shape.bounds[0:2])


class Pcb(object):
    ''' a class for generating a PCB file and placing components '''

    _cache_dir = 'kicad-deps'

    def __init__(self):
        # These are the Seeed DRC parameters
        netclass = pykicad.pcb.NetClass('Default',
                    clearance=0.153,
                    trace_width=0.153,
                    via_dia=0.6,
                    via_drill=0.3)
        setup = pykicad.pcb.Setup(
                    zone_clearance=0.153,
                    trace_min=0.153,
                    segment_width=0.153,
                    via_size=0.6,
                    via_min_size=0.6,
                    via_min_drill=0.3)
        self.pcb = pykicad.pcb.Pcb(setup=setup,
                net_classes=[netclass],
                page_type='A3')
        self._nets = {}

    def net(self, name):
        if name in self._nets:
            return self._nets[name]

        n = pykicad.module.Net(name)
        self._nets[name] = n
        self.pcb.nets.append(n)
        return n

    def add_component(self, comp):
        self.pcb.modules.append(comp)
        return comp

    def save(self, filename):
        print('Saving %s' % filename)
        with open(filename, 'w') as f:
            f.write(str(self.pcb))

    def resolveFootprintPath(self, footprint):
        libname, compname = footprint.split(':')
        lib = library_map[libname]
        if lib.startswith('https://'):
            url = urlparse(lib)
            if url.netloc == 'github.com':
                comps = url.path.split('/')[1:]
                repo = comps[0] + '/' + comps[1]
                if len(comps) > 2:
                    extra = '/' + '/'.join(comps[2:])
                else:
                    extra = ''
                lib = 'https://raw.githubusercontent.com/' + repo + '/master' + extra
                url = urlparse(lib)
            dirname = os.path.join(self._cache_dir, url.path[1:])
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            localname = os.path.join(dirname, compname + '.kicad_mod')
            lib += '/' + os.path.basename(localname)
            if not os.path.isfile(localname):
                print('Fetching %s as %s' % (lib, localname))
                with open(localname, 'wb') as f:
                    f.write(urllib.request.urlopen(lib).read())
            lib = dirname
        return lib, compname

    def loadFootprint(self, footprint):
        libname, compname = self.resolveFootprintPath(footprint)
        return self.io.FootprintLoad(libname, compname)

    def parseFootprintModule(self, footprint):
        lib, compname = self.resolveFootprintPath(footprint)
        module = pykicad.module.Module.from_file(
            '%s/%s.kicad_mod' % (lib, compname))
        return module

    def addTrack(self, layerName, start, end, netName, width=0.25):
        segment = pykicad.pcb.Segment(start=coords(start),
                                      end=coords(end),
                                      width=width,
                                      net=self.net(netName).code,
                                      layer=layerName)
        self.pcb.segments.append(segment)
        return segment

    def addText(self, text, position, bold=False, italic=False, thickness=0.15, size=None, justify=None, layer=None):
        text = pykicad.pcb.GrText(text, position, bold=bold, italic=italic, thickness=thickness, size=size, justify=justify, layer=layer or 'F.SilkS')
        self.pcb.texts.append(text)
        return text

    def addVia(self, position, netName, size=0.6, drill=0.4, layers=['F.Cu', 'B.Cu']):
        via = pykicad.pcb.Via(at=coords(position),
                              size=size,
                              drill=pykicad.pcb.Drill(drill),
                              net=self.net(netName).code)
        self.pcb.vias.append(via)
        return via

    def drawSegment(self, layerName, start, end):
        segment = pykicad.pcb.GrLine(start=coords(start),
                                     end=coords(end),
                                     width=0.15,
                                     layer=layerName)
        self.pcb.lines.append(segment)
        return segment

    def drawShape(self, layerName, shape):
        if hasattr(shape, 'geoms'):
            for g in shape.geoms:
                self.drawShape(layerName, g)
            return
        if shape.geom_type == 'Polygon':
            last = None
            first = None
            # Note that while we could emit a fp_poly for this, kicad can't
            # process it in either the default canvas or the 3D preview, so
            # we just use a sequence of lines
            for coord in shape.exterior.coords:
                if not first:
                    first = coord
                if last:
                    self.drawSegment(layerName, Point(*last), Point(*coord))
                last = coord
            self.drawSegment(layerName, Point(*last), Point(*first))

        else:
            raise Exception('unhandled geometry ' + shape.wkt)

    def addArea(self, layerName, net, shape):
        if shape.geom_type == 'Polygon':
            coords = []
            for coord in shape.exterior.coords:
                coords.append(tuple(coord))
            self.pcb.zones.append(pykicad.pcb.Zone(
                net=self.net(net).code,
                net_name=net,
                layer=layerName,
                min_thickness=0.254,
                thermal_gap=0.508,
                thermal_bridge_width=0.508,
                arc_segments=16,
                clearance=0.508,
                hatch_type='edge',
                hatch_size=0.508,
                polygon=coords,
                # This fills the polygon, but it is not the same as having
                # kicad fill, respecting the rules specified above!
                # You'll need to run DRC when you open the board in kicad
                # to have it update correctly.
                filled_polygon=coords))

        else:
            raise Exception('unhandled geometry ' + shape.wkt)
