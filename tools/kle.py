import copy
import json
import math
import shapely.geometry
import shapely.affinity

# Ref: https://github.com/ijprest/keyboard-layout-editor/wiki/Serialized-Data-Format

SWITCH_SPACING = 19.05


class Key(object):
    x = 0
    y = 0
    x2 = 0
    y2 = 0
    width = 1
    height = 1
    width2 = 1
    height2 = 1
    rotation_angle = 0
    rotation_x = 0
    rotation_y = 0
    sm = None  # switch mount
    sb = None  # switch brand
    st = None  # switch type
    _cluster = None
    c = None

    def __init__(self):
        self._cluster = [0, 0]

    def update_with(self, item):
        ''' Update the current item with the serialized data from
            the saved json file '''

        if 'rx' in item:
            val = item['rx']
            self._cluster[0] = val
            self.rotation_x = val
            self.x = val
            self.y = self._cluster[1]
        if 'ry' in item:
            val = item['ry']
            self._cluster[1] = val
            self.rotation_y = val
            self.y = val
            self.x = self._cluster[0]

        propmap = {
            'r': ['rotation_angle'],
            'w': ['width', 'width2'],
            'h': ['height', 'height2'],
            'w2': ['width2'],
            'h2': ['height2'],
        }
        for attr, val in item.items():
            if attr in ('rx', 'ry'):
                continue
            if attr in ('x', 'y'):
                setattr(self, attr, getattr(self, attr) + val)
                continue
            if attr in propmap:
                attr = propmap[attr]
            else:
                attr = [attr]
            for a in attr:
                setattr(self, a, val)

    def __str__(self):
        attrs = []
        for name in dir(self):
            if name.startswith('_'):
                continue
            if callable(getattr(self, name)):
                continue
            attrs.append(name)
        label = []
        for name in sorted(attrs):
            label.append('%s=%r' % (name, getattr(self, name)))
        return ' '.join(label)

    def shortLabel(self):
        for l in self.labels:
            if len(l) == 1:
                return l
            if len(l) == 0:
                continue
            if l[0] == '<':
                continue
            return l
        return '_'

    def polygon(self, unit=SWITCH_SPACING):
        ''' returns the bounding polygon for this key '''
        x = self.x * unit
        y = self.y * unit
        w = self.width * unit
        h = self.height * unit
        p = shapely.geometry.box(x, y, x + w, y + h)

        return self.rotated(p, unit)

    def centroid(self, unit=SWITCH_SPACING):
        c = tuple(self.polygon(unit).centroid.coords)[0]
        return c[0], c[1]

    def pin1(self, unit):
        ''' returns coords for pin1 of the keyswitch '''
        x = self.x * unit
        y = self.y * unit
        x += (self.width * unit) / 4.0
        y += (self.height * unit) / 4.0
        return self.rotated(shapely.geometry.Point(x, y), unit)

    def pin2(self, unit):
        ''' returns coords for pin2 of the keyswitch '''
        x = self.x * unit
        y = self.y * unit
        x += (self.width * unit) * 3.0 / 4.0
        y += (self.height * unit) / 4.0
        return self.rotated(shapely.geometry.Point(x, y), unit)

    def rotated(self, shape, unit):
        ''' helper for computing coords for the switch '''
        rx = self.rotation_x * unit
        ry = self.rotation_y * unit
        return shapely.affinity.rotate(shape, self.rotation_angle,
                                       origin=(rx, ry))


class Layout(object):

    def __init__(self, filename):
        with open(filename) as f:
            self._data = json.load(f)

        self._meta = self._data[0] if not isinstance(
            self._data[0], list) else {}
        self._keys = []

        current = Key()
        for rowdata in self._data:
            if not isinstance(rowdata, list):
                continue  # skip metadata item
            row = []
            for item in rowdata:
                if not isinstance(item, (unicode, str)):
                    current.update_with(item)
                    continue

                key = copy.deepcopy(current)
                key.width2 = current.width if key.width2 == 0 else current.width2
                key.height2 = current.height if key.height2 == 0 else current.height2
                key.labels = item.split('\n')

                self._keys.append(key)

                current.x += current.width
                current.width = 1
                current.height = 1
                current.x2 = 0
                current.y2 = 0
                current.width2 = 0
                current.height2 = 0

            current.y += 1
            current.x = current.rotation_x

    def name(self):
        return self._meta.get('name', 'anon')

    def keys(self):
        return self._keys

    def key_clusters(self):
        '''Returns a list of lists of keys.
           The lists are grouped by key clusters'''
        clusters = {}
        for k in self._keys:
            cluster = tuple(k._cluster)
            if cluster not in clusters:
                clusters[cluster] = []
            clusters[cluster].append(k)
        return clusters
