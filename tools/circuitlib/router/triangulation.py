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
    def __init__(self):
        self._ctx = tri.ToPointsAndSegments()
        self._coord_to_node = {}

    def triangulate(self):
        with tqdm(desc='triangulating') as pbar:
            g = networkx.Graph()

            cdt = tri.triangulate(
                self._ctx.points, self._ctx.infos, self._ctx.segments)

            for t in tri.TriangleIterator(cdt, finite_only=True):
                pbar.update(1)
                for a, b in [(0, 1), (1, 2), (2, 0)]:

                    v1 = t.vertices[a]
                    v2 = t.vertices[b]

                    node_a = self._coord_to_node[(v1.x, v1.y)]
                    node_b = self._coord_to_node[(v2.x, v2.y)]

                    g.add_node(node_a)
                    g.add_node(node_b)

                    d = node_a.shape.centroid.distance(node_b.shape.centroid)
                    if isinstance(node_a, types.Obstacle) and isinstance(node_b, types.Obstacle):
                        d += router.COLLISION_COST
                    g.add_edge(node_a, node_b, weight=d,
                               collision=d > router.COLLISION_COST)

        tqdm.write('Triangulated graph with %d nodes and %d edges' %
                   (len(g), g.size()))
        return g

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
                bnode = types.Branch(point, getattr(
                    node, 'layer', None), proxy_for=node)
            point = (point.x, point.y)
            self._coord_to_node[point] = bnode
            poly.append(point)

        if poly[0] == poly[-1]:
            poly.pop()
        self._ctx.add_polygon([poly])
