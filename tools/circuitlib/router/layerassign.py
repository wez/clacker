from __future__ import absolute_import
from __future__ import print_function
import networkx
from . import (types)
from ...utils import pairwise
import itertools
from tqdm import tqdm
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
from heapq import heappush, heappop


# Alpha is a parameter that shifts the balance between vias and
# overall line length.  It must be > 0 and < 1.
# A larger value favors longer paths, whereas a smaller value
# will bias towards more vias.
ALPHA = 0.1


class NodeLayerAssignment(object):
    ''' Represents the layer assignment for a connectable '''

    def __init__(self, node):
        self.node = node
        self.available_layers = set(node.layers)
        self.configured_layers = set()


class SourceSinkNode(object):
    ''' one of the endpoints of a two net assignment graph '''

    def __init__(self, nla):
        assert isinstance(nla, NodeLayerAssignment)
        self.nla = nla


class InputTwoNet(object):
    def __init__(self, a, b):
        self.source = SourceSinkNode(a)
        self.sink = SourceSinkNode(b)
        self.g = self.build_graph()

    def build_graph(self, via_count=2):
        ''' Build a layer assignment graph for the path a->b. '''
        g = networkx.DiGraph()

        a = self.source.nla.node
        b = self.sink.nla.node

        via_points = []
        left = a.shape.centroid
        right = b.shape.centroid
        distance = left.distance(right) / (via_count + 1)
        for i in range(0, via_count):
            line = LineString([left, right])
            vp = line.interpolate(distance)
            via_points.append(vp)
            left = vp

        g.add_node(self.source)
        g.add_node(self.sink)

        nodes_by_layer = {}

        for layer in [types.FRONT, types.BACK]:
            if a.is_on_layer(layer):
                al = types.Branch(a.shape, layer, proxy_for=a)
                g.add_node(al)
                g.add_edge(self.source, al)
            else:
                al = None

            if b.is_on_layer(layer):
                bl = types.Branch(b.shape, layer, proxy_for=b)
                g.add_node(bl)
                g.add_edge(bl, self.sink)
            else:
                bl = None

            nodes_by_layer[layer] = [al, bl]

            last = al
            for pt in via_points:
                vl = types.Branch(pt, layer)
                nodes_by_layer[layer].append(vl)
                if last:
                    g.add_edge(last, vl)
                last = vl

            if bl:
                g.add_edge(last, bl)

        for i, node in enumerate(nodes_by_layer[types.FRONT]):
            # Can traverse up or down
            other = nodes_by_layer[types.BACK][i]
            if node and other:
                g.add_edge(node, other)
                g.add_edge(other, node)

        return g


class Configuration(object):
    def __init__(self, two_nets):
        if isinstance(two_nets, Configuration):
            # We're making a copy
            src = two_nets
            self.paths = list(src.paths)
            self.cost_cache = dict(src.cost_cache)
            self.assignment_order = list(src.assignment_order)
            self.cost = src.cost
            # FIXME: need to copy InputTwoNet state!
            self.two_nets = src.two_nets
        else:
            # Creating a new instance from a list of two_nets
            self.cost = 0
            self.graphs = {}
            self.paths = []
            self.assignment_order = []
            self.cost_cache = {}
            self.two_nets = []

            nla_map = {}

            def nla_for_node(node):
                nla = nla_map.get(node)
                if not nla:
                    nla = NodeLayerAssignment(node)
                    nla_map[node] = nla
                return nla

            for net in two_nets:
                self.two_nets.append(InputTwoNet(nla_for_node(net[0]),
                                                 nla_for_node(net[1])))

    def copy(self):
        return Configuration(self)

    def clear(self):
        self.paths = []
        self.cost_cache = {}
        self.assignment_order = []
        self.cost = None

    def edge_weight(self, source, target):
        key = (source, target)
        cost = self.cost_cache.get(key)
        if cost is None:
            detour_cost = 0
            is_via = False

            if isinstance(source, SourceSinkNode) or isinstance(target, SourceSinkNode):
                # Source/sink node traversal.
                basic_cost = 0

                if not isinstance(source, SourceSinkNode):
                    # we can never have SourceSinkNode->SourceSinkNode, so we can
                    # safely swap the values here to make the code simpler
                    source, target = target, source

                assert isinstance(source, SourceSinkNode)
                assert not isinstance(target, SourceSinkNode)
                assert len(target.layers) == 1

                layer = target.layers[0]
                if layer not in source.nla.available_layers:
                    basic_cost = float('inf')
                elif (len(source.nla.configured_layers) > 0) and (
                        layer not in source.nla.configured_layers):
                    basic_cost = float('inf')

            else:
                basic_cost = source.shape.distance(target.shape)
                assert len(source.layers) == 1
                assert len(target.layers) == 1
                source_layer = source.layers[0]
                target_layer = target.layers[0]
                is_via = source_layer != target_layer
                if not is_via:
                    layer = source_layer

                    # Compute the detour cost; this is minimum length of an alternate
                    # path that we'd need to take to avoid intersecting segments

                    my_line = LineString(
                        [source.shape.centroid, target.shape.centroid])
                    for path in self.paths:
                        for i, j in pairwise(path):
                            if i == source or i == target or j == source or j == target:
                                # intersecting with myself
                                continue
                            if not (hasattr(i, 'shape') and hasattr(j, 'shape')):
                                continue
                            other_layer = i.layers[0]
                            if other_layer != layer:
                                # We can't intersect if we're on different layers!
                                continue

                            seg_line = LineString(
                                [i.shape.centroid, j.shape.centroid])
                            if seg_line.intersects(my_line):
                                # If A->B conflicts with I->J, we compute A->I->B and
                                # A->J->B as potential alternate paths, and take those
                                # lengths for our detour value
                                d1 = LineString([source.shape.centroid, i.shape.centroid]).length + \
                                    LineString(
                                        [i.shape.centroid, target.shape.centroid]).length
                                d2 = LineString([source.shape.centroid, j.shape.centroid]).length + \
                                    LineString(
                                        [j.shape.centroid, target.shape.centroid]).length

                                d = min(d1, d2)
                                if detour_cost == 0:
                                    detour_cost = d
                                else:
                                    detour_cost = min(detour_cost, d)

            cost = ((1 - ALPHA) * (basic_cost + detour_cost))
            if is_via:
                via_count = 1
                cost += ALPHA * via_count

            self.cost_cache[key] = cost
        return cost

    def dijkstra(self, G, source, target, cutoff=None):
        with tqdm(desc='path finding') as pbar:
            G_succ = G.succ if G.is_directed() else G.adj

            paths = {source: [source]}
            push = heappush
            pop = heappop
            dist = {}  # dictionary of final distances
            seen = {source: 0}
            c = itertools.count()
            fringe = []  # use heapq with (distance,label) tuples
            push(fringe, (0, next(c), source))
            while fringe:
                (d, _, v) = pop(fringe)
                if v in dist:
                    continue  # already searched this node.
                dist[v] = d
                if v == target:
                    break

                for u, e in G_succ[v].items():
                    cost = self.edge_weight(v, u)
                    if cost is None:
                        continue
                    vu_dist = dist[v] + cost
                    if cutoff is not None:
                        if vu_dist > cutoff:
                            continue
                    if u in dist:
                        if vu_dist < dist[u]:
                            raise ValueError('Contradictory paths found:',
                                             'negative weights?')
                    elif u not in seen or vu_dist < seen[u]:
                        seen[u] = vu_dist
                        push(fringe, (vu_dist, next(c), u))
                        paths[u] = paths[v] + [u]
            if target not in paths:
                return (None, None)
            return (dist[target], paths[target])

    def _invalidate_cache_for_path(self, path):
        ''' Invalidate cached cost information for segments that intersect
            those in the newly added path '''
        if False:
            tqdm.write('Blowing cost cache of size %d' %
                       (cost, len(self.cost_cache)))
            self.cost_cache = {}
            return

        invalidated = set()
        for source, target in pairwise(path):
            if isinstance(source, SourceSinkNode) or isinstance(target, SourceSinkNode):
                continue
            my_line = LineString(
                [source.shape.centroid, target.shape.centroid])
            for path in self.paths:
                for i, j in pairwise(path):
                    if not (hasattr(i, 'shape') and hasattr(j, 'shape')):
                        continue

                    seg_line = LineString([i.shape.centroid, j.shape.centroid])
                    if seg_line.intersects(my_line):
                        invalidated.add(i)
                        invalidated.add(j)

        n = 0
        for key in list(self.cost_cache.keys()):
            a, b = key
            if (a in invalidated) or (b in invalidated):
                del self.cost_cache[key]
                n += 1

        return n

    def add_path(self, node, path):
        self.paths.append(path)
        self._invalidate_cache_for_path(path)
        self.cost = None
        self.assignment_order.append(node)

        # Track the layer assignments
        for a, b in pairwise(path):
            if isinstance(a, SourceSinkNode):
                source, node = a, b
            elif isinstance(b, SourceSinkNode):
                source, node = b, a
            else:
                continue

            layer = node.layers[0]
            source.nla.configured_layers.add(layer)

    def compute_cost(self):
        if self.cost is None:
            self.cost = 0
            for path in tqdm(self.paths, desc='compute cost'):
                for a, b in pairwise(path):
                    self.cost += self.edge_weight(a, b)

        return self.cost

    def initial_assignment(self):
        ''' Assign 2net in ascending order of cost '''
        with tqdm(desc='initial 2net assignment', total=len(self.two_nets)) as pbar:
            free = set(self.two_nets)
            while len(free) > 0:
                pbar.update(1)
                best = None
                for n in free:
                    cost, path = self.dijkstra(n.g, n.source, n.sink,
                                               cutoff=best[0] if best is not None else None)

                    if cost is None:
                        # hit the cutoff
                        continue

                    if not best or cost < best[0]:
                        best = (cost, n, path)

                cost, n, path = best
                free.remove(n)
                self.add_path(n, path)
                tqdm.write('best is cost=%r (overall %r)' %
                           (cost, self.compute_cost()))

            return self

    def improve(self):
        improved = True
        best_cfg = self
        while improved:
            improved = False
            cfg = best_cfg.copy()

            for i, node in enumerate(tqdm(cfg.assignment_order, desc='improving')):
                cfg._invalidate_cache_for_path(cfg.paths[i])
                cfg.paths[i] = []

                cost, path = cfg.dijkstra(cfg.graphs[node], 'source', 'sink')
                cfg.paths[i] = path
                cfg._invalidate_cache_for_path(path)

            cfg.cost = None
            if cfg.compute_cost() < best_cfg.compute_cost():
                improved = True
                tqdm.write('Improved cost from %r to %r' %
                           (best_cfg.compute_cost(), cfg.compute_cost()))
                best_cfg = cfg
            else:
                tqdm.write('cost did not improve best=%r to attempt=%r' %
                           (best_cfg.compute_cost(), cfg.compute_cost()))

        return cfg
