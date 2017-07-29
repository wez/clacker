from __future__ import absolute_import
from __future__ import print_function

from tqdm import tqdm
from ...utils import pairwise
import networkx
from shapely.affinity import (translate, scale, rotate)
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
from shapely.ops import unary_union
from . import (types, spatialmap, layerassign, triangulation, dijkstra)

import random


class TwoNet(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        assert a.net is not None
        self.net = a.net
        assert self.a.net == self.b.net
        self.path = None

    def __str__(self):
        return 'TwoNet (%s) -> (%s)' % (self.a, self.b)


class Terminal(object):
    ''' Represents a terminal in a rubber band sketch.

        A branch is incident to a terminal if the terminal is one of its
        end points.

        A branch that passes through this terminal with an angle > 0 is
        explicitly attached.

        A branch that passes through this terminal with an angle == 0
        is implicitly attached.

        A segment that passes through the e-neighborhood of this terminal
        (but whose endpoints are not in the e-neighborhood) is also
        implicitly attached.

        The e-neighborhood of the terminal is the radius around the terminal
        that holds the attachment arcs of the branches/segments as
        described above.

        The e-neighborhood of a branch is the union of the neighborhoods
        of the terminals and the tangents between them, forming a
        rounded rectangle.
    '''

    def __init__(self, node):
        assert isinstance(node, types.Connectable)
        self.node = node
        self._two_nets = []
        # incident nets are those that are connected to this terminal
        self._incident_nets = []
        # attached nets are those that are snapping around this terminal.
        # If the terminal has only implicit attachments then we maintain a
        # list for each side of the terminal, otherwise (if there is an
        # explicit attachment), we only populate one.  Each of these lists
        # are ordered with the inner-most attachments first.
        self._attached_nets = [[], []]

    def add_2net(self, net):
        self._two_nets.append(net)

    @property
    def shape(self):
        return self.node.shape

    def add_incident_twonet(self, two_net):
        ''' marks two_net as an incident two_net '''
        # TODO: compute angle and use that to sort the attachments
        self._incident_nets.append(two_net)

    def add_attached_twonet(self, two_net):
        # TODO: compute angle and figure out which "side' this
        # is attached to.
        self._attached_nets[0].append(two_net)


def _resolve_proxy(node):
    while True:
        b = getattr(node, 'proxy_for', None)
        if not b:
            return node
        node = b


class RBSLayer(object):
    ''' Holds state for the rubber band sketch on a single layer '''

    def __init__(self, layer, tri):
        self.layer = layer
        self.tri = tri.copy()
        self.terminals = []
        self._pos_to_terminal = {}
        self._two_nets = []

    def _terminal_for_node(self, node):
        vert = tuple(list(node.shape.centroid.coords))
        t = self._pos_to_terminal.get(vert)
        if not t:
            t = Terminal(node)
            self._pos_to_terminal[vert] = t
            self.terminals.append(t)

        if isinstance(node, (types.SmdPad, types.ThruHole)):
            # potentially upgrade the terminal to reference the
            # canonical terminal node for this position;
            # it's possible that we saw a coincidental branch
            # node at this location previously.
            t.node = node

        return t

    def add_2net(self, a, b):
        a = _resolve_proxy(a)
        b = _resolve_proxy(b)

        if a.shape.centroid == b.shape.centroid:
            tqdm.write('skip: %s -> %s (same shape)' % (a, b))
            return

        net = TwoNet(a, b)
        self._two_nets.append(net)
        t1 = self._terminal_for_node(a)
        t1.add_2net(net)
        t2 = self._terminal_for_node(b)
        t2.add_2net(net)

        self.tri.add_2net(t1, t2)

    def triangulate(self):
        def node_maker(pt):
            ''' this function is called when the triangulation has
                synthesized a point.  We need to generate a single
                Branch instance for this point and ensure that we
                have a single terminal for it.  '''
            vert = tuple(list(pt.centroid.coords))
            t = self._pos_to_terminal.get(vert)
            if t:
                return t

            node = types.Branch(pt, layer=self.layer)
            return self._terminal_for_node(node)

        self.g = self.tri.triangulate(node_maker=node_maker)
        return self.g

    def compute_assignment_order(self):
        ''' this is where we could perform a step to generate the best
            assignment order; the one that yields the shortest overall
            wiring length.  For the momement we're just doing the nets
            in the order that they were added. '''
        return self._two_nets

    def compute_paths(self):
        for two_net in tqdm(self.compute_assignment_order(), desc='topo routing'):
            t1 = self._terminal_for_node(two_net.a)
            t2 = self._terminal_for_node(two_net.b)
            cost, path = dijkstra.dijkstra(self.g, t1, t2)
            if cost is None:
                tqdm.write('not path from %s to %s' % (t1, t2))
                continue
            #tqdm.write('cost=%s path=%s' % (cost, path))
            # We've found a path through the terminals, now we need to figure
            # out whether the path is incident or just an attachment to each
            # terminal in the path.
            tqdm.write('%s' % path)
            for a, b in pairwise(path):
                # The path elements may be features/obstacles computed prior
                # to layer assignments.
                if not isinstance(a, Terminal):
                    a = self._terminal_for_node(a)
                if not isinstance(b, Terminal):
                    b = self._terminal_for_node(b)
                if a.node.net is None:
                    # This was a terminal for a point synthesized by the CDT
                    # and is not currently associated with a net; we get to
                    # claim it now
                    a.node.net = two_net.net

                if a.node.net == two_net.net:
                    a.add_incident_twonet(two_net)
                else:
                    a.add_attached_twonet(two_net)

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
        g = l.triangulate()
        l.compute_paths()
        tqdm.write('%s' % l)

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
