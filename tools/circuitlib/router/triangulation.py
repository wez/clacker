from __future__ import absolute_import
from __future__ import print_function

from tqdm import tqdm

from scipy.spatial import Delaunay
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
import networkx

from . import spatialmap
from . import types
from . import router
import numpy


class Triangulation(object):
    def __init__(self):
        self._coords = []
        self._nodes = []

    def triangulate(self):
        with tqdm(desc='triangulating') as pbar:
            g = networkx.Graph()

            tri = Delaunay(numpy.array(self._coords))

            def find_neighbors(pindex):
                # Adapted from https://stackoverflow.com/questions/12374781/how-to-find-all-neighbors-of-a-given-point-in-a-delaunay-triangulation-using-sci
                start = tri.vertex_neighbor_vertices[0][pindex]
                stop = tri.vertex_neighbor_vertices[0][pindex + 1]
                return tri.vertex_neighbor_vertices[1][start:stop]

            for i, node_a in enumerate(self._nodes):
                pbar.update(1)
                for j in find_neighbors(i):
                    pbar.update(1)
                    node_b = self._nodes[j]
                    d = node_a.shape.centroid.distance(node_b.shape.centroid)
                    if isinstance(node_a, types.Obstacle) or isinstance(node_b, types.Obstacle):
                        d += router.COLLISION_COST
                    g.add_edge(node_a, node_b, weight=d,
                               collision=d > router.COLLISION_COST)

        tqdm.write('Triangulated graph with %d nodes and %d edges' %
                   (len(g), g.size()))
        return g

    def _add(self, node, coords):
        self._coords.append(coords)
        self._nodes.append(node)

    def add_node(self, node):
        is_edge = isinstance(node, types.Obstacle) and isinstance(
            node.value, str) and node.value == 'Edge'

        if not is_edge:
            self._add(node, list(*node.shape.centroid.coords))

        if isinstance(node, types.Obstacle):
            # We route around obstacles
            shape = node.shape.buffer(
                types.TRACK_RADIUS * 2).simplify(types.TRACK_RADIUS * 4)

            # Also add features for the perimeter of the shape
            for v in spatialmap.vertices(shape):
                bnode = types.Obstacle(node.layer, Point(v), 'Edge')
                self._add(bnode, list(v))
        else:
            # But have to touch pads
            shape = node.shape.simplify(types.TRACK_RADIUS)
