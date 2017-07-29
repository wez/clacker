from __future__ import absolute_import
from __future__ import print_function

from tqdm import tqdm

from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
import networkx

from . import spatialmap
from . import types
from . import router
from . import tri
import numpy


class Triangulation(object):
    def __init__(self, other=None):
        self._cdt = None
        if other:
            assert isinstance(other, Triangulation)
            self._ctx = other._ctx.copy()
            self._coord_to_node = dict(other._coord_to_node)
        else:
            self._ctx = tri.ToPointsAndSegments()
            self._coord_to_node = {}

    def copy(self):
        return Triangulation(self)

    def triangulate(self, node_maker=None):
        if node_maker is None:
            def node_maker(pt):
                return types.Branch(pt)

        with tqdm(desc='triangulating') as pbar:
            g = networkx.Graph()

            self._cdt = tri.triangulate(
                self._ctx.points, self._ctx.infos, self._ctx.segments)

            for t in tri.TriangleIterator(self._cdt, finite_only=True):
                pbar.update(1)
                for a, b in [(0, 1), (1, 2), (2, 0)]:

                    v1 = t.vertices[a]
                    v2 = t.vertices[b]

                    node_a = self._coord_to_node.get((v1.x, v1.y))
                    if not node_a:
                        node_a = node_maker(Point(v1.x, v1.y))
                    node_b = self._coord_to_node.get((v2.x, v2.y))
                    if not node_b:
                        node_b = node_maker(Point(v2.x, v2.y))

                    g.add_node(node_a)
                    g.add_node(node_b)

                    g.add_edge(node_a, node_b, weight=node_a.shape.centroid.distance(
                        node_b.shape.centroid))

        tqdm.write('Triangulated graph with %d nodes and %d edges' %
                   (len(g), g.size()))
        return g

    def add_2net(self, a, b):
        a_pos = (a.shape.centroid.x, a.shape.centroid.y)
        b_pos = (b.shape.centroid.x, b.shape.centroid.y)
        if a_pos == b_pos:
            raise ValueError('terminals have the same location')
        self._coord_to_node[a_pos] = a
        points = [a_pos, b_pos]
        self._ctx.add_polygon([points])

    def add_node(self, node):
        is_edge = isinstance(node, types.Obstacle) and isinstance(
            node.value, str) and node.value == 'Edge'

        if not is_edge:
            point = tuple(*node.shape.centroid.coords)
            self._coord_to_node[point] = node
            self._ctx.add_point(point)

        if isinstance(node, types.Obstacle):
            # We route around obstacles
            shape = node.shape.buffer(
                types.TRACK_RADIUS * 2).simplify(types.TRACK_RADIUS * 4)
        else:
            # But have to touch pads
            return
            shape = node.shape.simplify(types.TRACK_RADIUS)

        # features for the perimeter of the shape
        vertices = spatialmap.vertices(shape)
        poly = []
        for v in vertices:
            point = Point(v)
            if isinstance(node, types.Obstacle):
                bnode = types.Obstacle(
                    getattr(node, 'layer', None), point, 'Edge')
            else:
                bnode = types.Branch(point, net=node.net,
                                     layer=getattr(node, 'layer', None),
                                     proxy_for=node)
            point = (point.x, point.y)
            self._coord_to_node[point] = bnode
            poly.append(point)

        if poly[0] == poly[-1]:
            poly.pop()
        self._ctx.add_polygon([poly])
