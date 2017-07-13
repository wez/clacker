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


class Configuration(object):
    def __init__(self, two_nets):
        self.cost = 0
        self.graphs = {}
        self.paths = []
        self.assignment_order = []
        self.cost_cache = {}
        if isinstance(two_nets, Configuration):
            # We're making a copy instead
            src = two_nets
            self.graphs = dict(src.graphs)
            self.paths = list(src.paths)
            self.cost_cache = dict(src.cost_cache)
            self.assignment_order = list(src.assignment_order)
            self.cost = src.cost
        else:
            self.two_nets = two_nets
            for net in self.two_nets:
                self.graphs[net] = self.build_layer_graph(net[0], net[1])

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

            if isinstance(source, str) or isinstance(target, str):
                # Source/sink node traversal.
                # TODO: take into account layer presence!
                basic_cost = 0
            else:
                basic_cost = source.shape.distance(target.shape)
                is_via = source.layers != target.layers
                if not is_via:
                    layer = source.layers[0]

                    # Compute the detour cost; this is minimum length of an alternate
                    # path that we'd need to take to avoid intersecting segments

                    my_line = LineString(
                        [source.shape.centroid, target.shape.centroid])
                    for path in self.paths:
                        for i, j in pairwise(path):
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
                via_count = (len(source.layers) + len(target.layers)) // 2
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

    def build_layer_graph(self, a, b, via_count=2):
        ''' Build a layer assignment graph for the path a->b. '''
        g = networkx.DiGraph()

        via_points = []
        left = a.shape.centroid
        right = b.shape.centroid
        distance = left.distance(right) / (via_count + 1)
        for i in range(0, via_count):
            line = LineString([left, right])
            vp = line.interpolate(distance)
            via_points.append(vp)
            left = vp

        g.add_node('source')
        g.add_node('sink')

        nodes_by_layer = {}

        for layer in [types.FRONT, types.BACK]:
            al = types.Branch(a.shape, layer, proxy_for=a)
            bl = types.Branch(b.shape, layer, proxy_for=b)

            nodes_by_layer[layer] = [al, bl]
            g.add_node(al)
            g.add_node(bl)

            last = al
            for pt in via_points:
                vl = types.Branch(pt, layer)
                nodes_by_layer[layer].append(vl)
                g.add_edge(last, vl)
                last = vl

            g.add_edge(last, bl)

            if a.is_on_layer(layer):
                g.add_edge('source', al)
            if b.is_on_layer(layer):
                g.add_edge(bl, 'sink')

        for i, node in enumerate(nodes_by_layer[types.FRONT]):
            # Can traverse up or down
            other = nodes_by_layer[types.BACK][i]
            g.add_edge(node, other)
            g.add_edge(other, node)

        return g

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
            if isinstance(source, str) or isinstance(target, str):
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
                    cost, path = self.dijkstra(self.graphs[n], 'source', 'sink',
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
