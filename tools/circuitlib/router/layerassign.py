from __future__ import absolute_import
from __future__ import print_function
import networkx
from . import (types, tri)
from ...utils import pairwise
import itertools
from tqdm import tqdm
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
from shapely.ops import unary_union
from heapq import heappush, heappop


# Alpha is a parameter that shifts the balance between vias and
# overall line length.  It must be > 0 and < 1.
# A larger value favors longer paths, whereas a smaller value
# will bias towards more vias.
ALPHA = 0.1


def line_between(shape1, shape2):
    return LineString([shape1.centroid, shape2.centroid])


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
                    g.add_edge(last, vl, line=line_between(
                        last.shape, vl.shape))
                last = vl

            if bl:
                g.add_edge(last, bl, line=line_between(last.shape, bl.shape))

            # Generate the short circuit branches.  The purpose
            # of these is to avoid understimation of certain
            # paths through the graph.  Each consecutive sequence
            # of nodes is connected together
            for i in range(2, via_count + 2):
                if nodes_by_layer[layer][i] is None:
                    continue
                for seq_len in range(2, via_count):
                    if i + seq_len < len(nodes_by_layer):
                        t = nodes_by_layer[layer][i + seq_len]
                        if t is not None:
                            g.add_edge(nodes_by_layer[layer][i], t, line=line_between(
                                nodes_by_layer[layer][i].shape, t.shape))

        for i, node in enumerate(nodes_by_layer[types.FRONT]):
            # Can traverse up or down
            other = nodes_by_layer[types.BACK][i]
            if node and other:
                g.add_edge(node, other, via=True)
                g.add_edge(other, node, via=True)

        return g


class Component(object):
    ''' Represents a component formed out of connected paths
        on a layer of a board '''

    def __init__(self, a, b):
        a = a.centroid
        b = b.centroid
        self.terminals = set([(a.x, a.y), (b.x, b.y)])
        self.lines = [LineString([(a.x, a.y), (b.x, b.y)])]
        self.shape = self.lines[0]

    def update_with(self, comp):
        ''' Extends self with the component info from comp '''
        self.terminals.update(comp.terminals)
        self.lines += comp.lines
        self.shape = MultiLineString(self.lines)

    def _buffer(self, shape):
        return shape.buffer(0.0001, cap_style=CAP_STYLE.square, join_style=JOIN_STYLE.mitre)

    def __str__(self):
        return '%d terminals %d lines' % (len(self.terminals), len(self.lines))

    def detour_cost(self, line):
        ''' computes the detour cost for the line (A->B).
            Precondition is that line intersects with this component!
            The detour cost is the smallest path around the shape represented
            by this component.  In the simplest case this component is a line I->J
            that forms an X shape where it intersects with A->B.  The detour is
            to form a square path around the outside.  This generalizes to
            computing the convex hull of the combined component and line; the
            detour cost is then the smallest distance walking from A to B
            either clockwise or counter clockwise around the vertices of
            the hull '''
        joined = unary_union([self.shape, line])
        hull = joined.convex_hull
        if hasattr(hull, 'exterior'):
            hull = list(hull.exterior.coords)
            # the final coord loops back to the start; remove it
            hull.pop()
        else:
            hull = list(hull.coords)

        a, b = list(line.coords)

        # Since we buffered out the shapes, we need to make a pass to find
        # the closest points to our A and B points

        def closest(vert, exclude=None):
            best = None
            vert = Point(vert)
            for p in hull:
                if exclude and exclude == p:
                    continue
                d = vert.distance(Point(p))
                if not best or d < best[0]:
                    best = [d, p]
            return best[1]

        a_close = closest(a)
        b_close = closest(b, exclude=a_close)

        # Map those to indices
        for i in range(0, len(hull)):
            if hull[i] == a_close:
                a_pos = i
            if hull[i] == b_close:
                b_pos = i

        if a_pos == b_pos:
            print(line)
            print(hull)
            print('boom')
            from ... import svg
            doc = svg.SVG()
            doc.add(self.shape, stroke='red',
                    stroke_width=0.01, fill_opacity=0)
            doc.add(line, stroke='blue', stroke_width=0.01, fill_opacity=0)
            doc.add(joined.convex_hull, stroke='grey',
                    stroke_width=0.01, fill_opacity=0)
            doc.save('/tmp/gah.svg')
            assert a_pos != b_pos
            return 0

        # [A x y B] -> [A, x, y, B] and [B, A]
        # [x A y B] -> [A, y, B] and [B, x, A]
        # [B x A y] -> [A, y, B] and [B, x, A]

        a_path = hull[a_pos:] + hull[:-a_pos]
        a_cost = 0
        for i, j in pairwise(a_path):
            a_cost += LineString([i, j]).length
            if j == b:
                assert a_cost != 0
                break

        b_path = hull[b_pos:] + hull[:-b_pos]
        b_cost = 0
        for i, j in pairwise(b_path):
            b_cost += LineString([i, j]).length
            if j == a:
                assert b_cost != 0
                break

        base_detour = LineString([a, a_close]).length + \
            LineString([b, b_close]).length
        return min(a_cost, b_cost) + base_detour


class ComponentList(object):
    ''' A list of components on a layer '''

    def __init__(self):
        self.comps = set()

    def component_for_vertex(self, vert):
        for comp in self.comps:
            if vert in comp.terminals:
                return comp
        return None

    def add(self, comp):
        ''' Adds a component, merging it if appropriate '''

        # Find the set of components that share vertices
        to_merge = set()
        for vert in comp.terminals:
            m = self.component_for_vertex(vert)
            if m:
                to_merge.add(m)
                # Remove it from the set; it will be merged
                # into the component we're adding in this call
                self.comps.remove(m)

        # Now merge them together
        for m in to_merge:
            comp.update_with(m)

        self.comps.add(comp)

    def intersects(self, shape):
        vert_a, vert_b = list(shape.coords)
        for comp in self.comps:
            if vert_a in comp.terminals:
                continue
            if vert_b in comp.terminals:
                continue
            if shape.intersects(comp.shape):
                yield comp


class Configuration(object):
    def __init__(self, two_nets):
        self.cost = None
        self.paths = []
        self.cost_cache = {}
        self.assignment_order = []
        self.components_by_layer = {
            types.FRONT: ComponentList(),
            types.BACK: ComponentList(),
        }

        if isinstance(two_nets, Configuration):
            # We're making a copy
            src = two_nets
            self.two_nets = src.two_nets
            self.graphs = src.graphs
        else:
            # Creating a new instance from a list of two_nets
            self.graphs = {}
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

    def edge_weight(self, source, target, edgedata=None):
        key = (source, target)
        cost = self.cost_cache.get(key)
        if cost is None:
            detour_cost = 0
            is_via = edgedata.get('via') if edgedata else False

            if isinstance(source, SourceSinkNode) or isinstance(target, SourceSinkNode):
                # Source/sink node traversal.
                basic_cost = 0

                if not isinstance(source, SourceSinkNode):
                    # we can never have SourceSinkNode->SourceSinkNode, so we can
                    # safely swap the values here to make the code simpler
                    source, target = target, source

                # assert isinstance(source, SourceSinkNode)
                # assert not isinstance(target, SourceSinkNode)
                # assert len(target.layers) == 1

                layer = target.layers[0]
                if layer not in source.nla.available_layers:
                    basic_cost = float('inf')
                elif (len(source.nla.configured_layers) > 0) and (
                        layer not in source.nla.configured_layers):
                    basic_cost = float('inf')

            else:
                my_line = edgedata.get('line') if edgedata else None
                if not my_line:
                    my_line = LineString(
                        [source.shape.centroid, target.shape.centroid])
                basic_cost = my_line.length

                # assert len(source.layers) == 1
                # assert len(target.layers) == 1
                source_layer = source.layers[0]
                target_layer = target.layers[0]
                is_via = source_layer != target_layer
                if not is_via and basic_cost > 0:
                    layer = source_layer

                    # Compute the detour cost; this is minimum length of an alternate
                    # path that we'd need to take to avoid intersecting segments


                    for comp in self.components_by_layer[layer].intersects(my_line):
                        d1 = comp.detour_cost(my_line)
                        #tqdm.write('segment %s intersects with comp %s, cost %s' % (my_line, comp, d1))
                        if detour_cost == 0:
                            detour_cost = d1
                        else:
                            detour_cost = min(detour_cost, d1)

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
                    cost = self.edge_weight(v, u, e)
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
            cost = 0
            for p in paths[target]:
                cost += dist[p]
            return (cost, paths[target])

    def _invalidate_cache_for_path(self, path):
        ''' Invalidate cached cost information for segments that intersect
            those in the newly added path '''
        if False:
            self.cost_cache = {}
            return

        if not self.paths or not self.cost_cache:
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

        for key in list(self.cost_cache.keys()):
            a, b = key
            if (a in invalidated) or (b in invalidated):
                del self.cost_cache[key]

    def add_path(self, node, path):
        self._invalidate_cache_for_path(path)
        self.paths.append(path)
        self.cost = None
        self.assignment_order.append(node)

        # Track the layer assignments
        for a, b in pairwise(path):
            if isinstance(a, SourceSinkNode):
                source, node = a, b
            elif isinstance(b, SourceSinkNode):
                source, node = b, a
            else:
                if a.shape.distance(b.shape) > 0:
                    comp = Component(a.shape, b.shape)
                    self.components_by_layer[a.layers[0]].add(comp)
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
                #tqdm.write('best is cost=%r (overall %r)' % (cost, self.compute_cost()))

            return self

    def improve(self):
        improved = True
        best_cfg = self
        import time

        start = time.time()

        # Setting a deadline because there are a lot of combinations to
        # try and it is relatively expensive
        deadline = start + 30
        while improved and time.time() < deadline:
            improved = False

            best_order = [x for x in best_cfg.assignment_order]
            for i, node in enumerate(tqdm(best_order, desc='improving')):
                if time.time() >= deadline:
                    break

                order = [x for x in best_order]
                order.insert(0, order.pop(i))

                if order == best_order:
                    continue

                cfg = self.copy()
                cutoff = None
                for n in tqdm(order, desc='pass %d' % i):
                    cost, path = cfg.dijkstra(
                        n.g, n.source, n.sink, cutoff=cutoff)
                    cfg.add_path(n, path)
                    cutoff = best_cfg.compute_cost() - cfg.compute_cost()
                    if cutoff <= 0:
                        break

                if cfg.compute_cost() < best_cfg.compute_cost():
                    improved = True
                    tqdm.write('Improved cost from %r to %r' %
                               (best_cfg.compute_cost(), cfg.compute_cost()))
                    best_cfg = cfg

        return cfg
