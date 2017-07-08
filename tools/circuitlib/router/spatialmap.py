from __future__ import absolute_import
from __future__ import print_function
from scipy import spatial
from pprint import pprint

KDTree = spatial.cKDTree if hasattr(spatial, 'cKDTree') else spatial.KDTree


def vertices(shape):
    if shape.geom_type == 'Polygon':
        return [(x, y) for x, y in shape.exterior.coords]
    if shape.geom_type == 'LineString':
        return [(x, y) for x, y in shape.coords]
    if shape.geom_type == 'Point':
        if not shape.is_empty:
            return [(shape.bounds[0], shape.bounds[1])]
        return []
    if shape.geom_type in ('MultiPolygon', 'GeometryCollection'):
        v = []
        for geom in shape:
            v += vertices(geom)
        return v
    raise Exception('geom_type %s %r' % (shape.geom_type, shape.wkt))


class Entry(object):
    ''' proxy object for mapping vertices to the same value '''

    def __init__(self, shape, value):
        self.shape = shape
        self.value = value


class SpatialMap(object):
    ''' Provides means for mapping locations to objects '''
    USE_TREE = True

    def __init__(self):
        self._map = {}
        self._tree = None
        self._points = None
        self._entries = set()

    def _add(self, coord, entry):
        assert isinstance(coord, tuple)
        if coord not in self._map:
            self._map[coord] = []
        self._map[coord].append(entry)

    def add(self, shape, data):
        ''' record association from key points in shape to data '''

        # blow the cached tree, if any
        self._tree = None
        self._points = None

        entry = Entry(shape, data)
        self._entries.add(entry)

        for coord in vertices(shape):
            self._add(coord, entry)

        centroid = shape.centroid
        for coord in vertices(centroid):
            self._add(coord, entry)

    def at(self, coord):
        ''' yields Entry objects for things at the specified coord '''
        items = set()
        for entry in self._map.get(coord, []):
            items.add(entry)
        return items

    def _get_tree(self):
        ''' returns the cached tree, rebuilding it if it is not present '''
        if self._tree:
            return self._tree

        self._points = list(self._map.keys())
        if len(self._points) == 0:
            return None

        self._tree = KDTree(self._points)

        return self._tree

    def near(self, coord, radius):
        ''' yields Entry objects for things within radius of a point '''
        if SpatialMap.USE_TREE:
            items = set()
            tree = self._get_tree()
            if not tree:
                return items
            for hit in tree.query_ball_point(coord, radius):
                for entry in self._map[self._points[hit]]:
                    items.add(entry)
            return items

        return self._entries

    def _filter(self, shape, fn):
        if shape.is_empty:
            return
        bounds = shape.bounds
        centroid = shape.centroid
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        radius = max(width, height) / 2

        for entry in self.near(centroid, radius):
            if fn(entry.shape):
                yield entry

    def intersects(self, shape):
        ''' yields Entry objects for things that intersects() with shape '''

        return self._filter(shape, shape.intersects)

    def crosses(self, shape):
        ''' yields Entry objects for things that crosses() with shape '''

        return self._filter(shape, shape.crosses)
