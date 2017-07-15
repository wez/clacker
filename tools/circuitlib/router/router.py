from __future__ import absolute_import
from __future__ import print_function

from tqdm import tqdm
from ...utils import pairwise
import networkx
from shapely.affinity import (translate, scale, rotate)
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
from shapely.ops import unary_union
from . import (types, spatialmap, layerassign, triangulation)

import random


class Terminal(object):
    def __init__(self, node):
        assert isinstance(node, types.Connectable)
        self.node = node
        self.shape = node.shape


class RBSLayer(object):
    ''' Holds state for the rubber band sketch on a single layer '''

    def __init__(self, layer, tri):
        self.layer = layer
        self.tri = tri.copy()
        self.terminals = []
        self._node_to_terminal = {}

    def _terminal_for_node(self, a):
        while True:
            b = getattr(a, 'proxy_for', None)
            if not b:
                break
            a = b

        t = self._node_to_terminal.get(a)
        if not t:
            t = Terminal(a)
            self.terminals.append(t)
            self._node_to_terminal[a] = t

        return t

    def add_2net(self, a, b):
        if a.shape.centroid == b.shape.centroid:
            tqdm.write('skip: %s -> %s (same shape)' % (a, b))
            return

        a = self._terminal_for_node(a)
        b = self._terminal_for_node(b)

        self.tri.add_2net(a, b)

    def __str__(self):
        return 'RBSLayer %s with %d terminals' % (self.layer, len(self.terminals))


def route(data, profile=False):
    cfg = layerassign.Configuration(data['2nets'])
    cfg = cfg.initial_assignment()

    if profile:
        import cProfile
        import pstats

        pr = cProfile.Profile()
        pr.enable()

    cfg = cfg.improve()

    if profile:
        pr.disable()
        ps = pstats.Stats(pr).sort_stats('cumulative')
        ps.print_stats()

    # Transfer the paths for each layer
    tri = data['triangulation']
    #tri = triangulation.Triangulation()

    layers = {}
    for layer in [types.FRONT, types.BACK]:
        layers[layer] = RBSLayer(layer, tri)

    for path in tqdm(cfg.paths, desc='build rbs'):
        for i, j in pairwise(path.path):
            if isinstance(i, layerassign.SourceSinkNode):
                continue
            if isinstance(j, layerassign.SourceSinkNode):
                continue
            g = path.input_2net.g
            edge = g[i][j]
            line = edge.get('line')
            if not line:
                continue
            layer = i.layers[0]
            layers[layer].add_2net(i, j)

    for l in layers.values():
        tqdm.write('%s' % l)
        g = l.tri.triangulate()
        return g

    routed_graph = networkx.Graph()
    for path in tqdm(cfg.paths, desc='distil route'):
        for i, j in pairwise(path.path):
            if isinstance(i, layerassign.SourceSinkNode):
                continue
            if isinstance(j, layerassign.SourceSinkNode):
                continue
            g = path.input_2net.g
            layer = None
            #tqdm.write('path segment layers: %r %r' % (i.layers, j.layers))
            if i.layers == j.layers:
                layer = i.layers[0]
            cost = cfg.edge_weight(i, j, g[i][j])
            routed_graph.add_node(i)
            routed_graph.add_node(j)
            distance = i.shape.centroid.distance(j.shape.centroid)
            #tqdm.write('distance=%r cost=%r %s -> %s' % (distance, cost, i, j))
            routed_graph.add_edge(i, j,
                                  collision=cost > distance *
                                  (1 - layerassign.ALPHA),
                                  layer=layer,
                                  via=g[i][j].get('via'))

    return routed_graph
