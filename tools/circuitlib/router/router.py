from __future__ import absolute_import
from __future__ import print_function

from tqdm import tqdm
from ...utils import pairwise
import networkx
from shapely.affinity import (translate, scale, rotate)
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
from shapely.ops import unary_union
from . import (types, spatialmap, layerassign)
from heapq import heappush, heappop
from itertools import count, combinations

import random

COLLISION_COST = 1000000
VIA_COST = 125


def track_shape(a, b):
    line = LineString([a.shape.centroid, b.shape.centroid]
                      ).buffer(types.TRACK_RADIUS)
    return line
    track = line.difference(a.shape).difference(
        b.shape)  # .simplify(types.TRACK_RADIUS)
    return track


def resolve_proxy(node):
    while hasattr(node, 'proxy_for') and node.proxy_for is not None:
        node = node.proxy_for
    return node


def is_same_entry(entry, node):
    if resolve_proxy(entry.value) == node:
        return True
    if entry.shape == node.shape:
        return True
    return False


class Solution(object):
    def __init__(self, phys_map, g, two_nets):
        self.phys_map = phys_map
        self.two_nets = two_nets
        self.g = networkx.Graph(g)
        self.paths = []
        self.cost = 0
        self.layer_smap = {types.FRONT: None, types.BACK: None}
        self.weight_cache = {}

    def add_edge(self, a, b, layer=None, **kwargs):
        self.layer_smap[layer] = None
        self.weight_cache = {}
        self.g.add_edge(a, b, layer=layer, **kwargs)

    def copy(self):
        ''' make a copy that we can mutate into another solution '''
        s = Solution(self.phys_map, self.g, self.two_nets)
        s.paths = list(self.paths)
        s.cost = self.cost
        return s

    def _shape_intersects_on_layer(self, a, b, shape, layer, phys_only=False):
        orig_a = a
        orig_b = b
        a = resolve_proxy(a)
        b = resolve_proxy(b)

        obstacles = set()
        for entry in self.phys_map.intersects(shape):
            value = resolve_proxy(entry.value)
            if value.is_on_layer(layer):
                continue
            if is_same_entry(entry, a) or is_same_entry(entry, b):
                #tqdm.write('entry %a is same as %s or %s' % (value, a, b))
                continue
            obstacles.add(value)

        if not phys_only:
            smap = self.layer_smap.get(layer)
            if smap is None:
                smap = spatialmap.SpatialMap()
                for i, j in self.g.edges_iter():
                    edgedata = self.g[i][j]
                    edge_track = edgedata.get('track')
                    if not edge_track:
                        continue
                    edge_layer = edgedata.get('layer')
                    if edge_layer != layer:
                        continue

                    smap.add(edge_track.shape, edge_track)
                self.layer_smap[layer] = smap

            for entry in smap.intersects(shape):
                if isinstance(entry.value, types.Segment):
                    tup = (entry.value.a, entry.value.b)
                    if (tup == (a, b)) or (tup == (b, a)):
                        continue
                    if (tup == (orig_a, orig_b)) or (tup == (orig_b, orig_a)):
                        continue
                obstacles.add(entry.value)
        return obstacles

    def obstacles_in_path(self, a, b, layer, phys_only=False):
        ''' returns a set of unique obstacles between a and b '''

        orig_a = a
        orig_b = b
        a = resolve_proxy(a)
        b = resolve_proxy(b)

        track = track_shape(a, b)
        obstacles = self._shape_intersects_on_layer(
            orig_a, orig_b, track, layer, phys_only=phys_only)

        # if phys_only and obstacles:
        #    tqdm.write('obstacles for %s -> %s: %s' % (resolve_proxy(a), resolve_proxy(b), obstacles))
        return obstacles

    def edge_weight(self, a, b):
        weight = self.weight_cache.get((a, b))
        if weight is not None:
            return weight
        weight = self.weight_cache.get((b, a))
        if weight is not None:
            self.weight_cache[(a, b)] = weight
            return weight

        weight = self.compute_edge_weight(a, b)
        self.weight_cache[(a, b)] = weight
        return weight

    def compute_edge_weight(self, a, b):
        a_resolved = resolve_proxy(a)
        b_resolved = resolve_proxy(a)
        if (hasattr(b, 'proxy_for') and b.proxy_for == a) or (hasattr(a, 'proxy_for') and a.proxy_for == b):
            # it costs nothing to transit a proxy edge
            return 0

        cost = a.shape.centroid.distance(b.shape.centroid)

        if self.g[a][b].get('via'):
            # Changing layer
            cost += VIA_COST
        else:
            layer = self.g[a][b].get('layer')
            if layer:
                # We prefer vertical lines on the front layer, horizontal on
                # the back layer.
                if True:
                    width = abs(a.shape.centroid.x - b.shape.centroid.x)
                    height = abs(a.shape.centroid.y - b.shape.centroid.y)

                    if layer == types.FRONT:
                        # penalize horizontal line
                        cost += width
                    elif layer == types.BACK:
                        # penalize vertical line
                        cost += height

                obstacles = self.obstacles_in_path(a, b, layer)
                if len(obstacles) > 0:
                    # for obs in obstacles:
                    cost += COLLISION_COST

        return cost

    def single_source_dijkstra(self, source, target):
        G = self.g
        if source == target:
            return (0, [source])

        with tqdm(desc='path finding') as pbar:
            push = heappush
            pop = heappop
            dist = {}  # dictionary of final distances
            paths = {source: [source]}  # dictionary of paths
            seen = {source: 0}
            c = count()
            fringe = []  # use heapq with (distance,label) tuples
            push(fringe, (0, next(c), source))
            while fringe:
                pbar.update(1)
                (d, _, v) = pop(fringe)
                if v in dist:
                    continue  # already searched this node.
                dist[v] = d
                if v == target:
                    break
                # for ignore,w,edgedata in G.edges_iter(v,data=True):
                # is about 30% slower than the following
                edata = iter(G[v].items())

                for w, edgedata in edata:
                    pbar.update(1)
                    vw_dist = dist[v] + self.edge_weight(v, w)
                    if w in dist:
                        if vw_dist < dist[w]:
                            raise ValueError('Contradictory paths found:',
                                             'negative weights?')
                    elif w not in seen or vw_dist < seen[w]:
                        seen[w] = vw_dist
                        push(fringe, (vw_dist, next(c), w))
                        paths[w] = paths[v] + [w]
            return (dist[source], paths[source])

    def bidirectional_dijkstra(self, source, target):
        if source == target:
            return (0, [source])

        with tqdm(desc='path finding') as pbar:

            G = self.g
            push = heappush
            pop = heappop
            # Init:   Forward             Backward
            dists = [{},                {}]  # dictionary of final distances
            # dictionary of paths
            paths = [{source: [source]}, {target: [target]}]
            # heap of (distance, node) tuples for
            fringe = [[],                []]
            # extracting next node to expand
            # dictionary of distances to
            seen = [{source: 0},        {target: 0}]
            # nodes seen
            c = count()
            # initialize fringe heap
            push(fringe[0], (0, next(c), source))
            push(fringe[1], (0, next(c), target))
            neighs = [G.neighbors_iter, G.neighbors_iter]
            # variables to hold shortest discovered path
            #finaldist = 1e30000
            finalpath = []
            dir = 1
            while fringe[0] and fringe[1]:
                pbar.update(1)
                # choose direction
                # dir == 0 is forward direction and dir == 1 is back
                dir = 1 - dir
                # extract closest to expand
                (dist, _, v) = pop(fringe[dir])
                if v in dists[dir]:
                    # Shortest path to v has already been found
                    continue
                # update distance
                dists[dir][v] = dist  # equal to seen[dir][v]
                if v in dists[1 - dir]:
                    # if we have scanned v in both directions we are done
                    # we have now discovered the shortest path
                    return (finaldist, finalpath)

                for w in neighs[dir](v):
                    pbar.update(1)
                    # if(dir == 0):  # forward
                    minweight = self.edge_weight(v, w)
                    vwLength = dists[dir][v] + \
                        minweight  # G[v][w].get(weight,1)
                    # else:  # back, must remember to change v,w->w,v
                    #    minweight = self.edge_weight(w, v)
                    #    vwLength = dists[dir][v] + minweight  # G[w][v].get(weight,1)

                    if w in dists[dir]:
                        if vwLength < dists[dir][w]:
                            raise ValueError(
                                "Contradictory paths found: negative weights?")
                    elif w not in seen[dir] or vwLength < seen[dir][w]:
                        # relaxing
                        seen[dir][w] = vwLength
                        push(fringe[dir], (vwLength, next(c), w))
                        paths[dir][w] = paths[dir][v] + [w]
                        if w in seen[0] and w in seen[1]:
                            # see if this path is better than than the already
                            # discovered shortest path
                            totaldist = seen[0][w] + seen[1][w]
                            if finalpath == [] or finaldist > totaldist:
                                finaldist = totaldist
                                revpath = paths[1][w][:]
                                revpath.reverse()
                                finalpath = paths[0][w] + revpath[1:]
            raise networkx.NetworkXNoPath(
                "No path between %s and %s." % (source, target))

    def route_single_2net(self, a, b):
        cost, path = self.bidirectional_dijkstra(a, b)
        #cost, path = self.single_source_dijkstra(a, b)
        return cost, path

    def solve(self):
        self.cost = 0
        self.paths = []
        for a, b in tqdm(self.two_nets, desc='compute solution'):
            cost, path = self.route_single_2net(a, b)
            self.paths.append((cost, path))
            self.cost += cost

        return self.cost

    def _avoid_shape(self, shape, scale=1):
        return shape.buffer(types.TRACK_RADIUS * 2 * scale, resolution=9,
                            cap_style=CAP_STYLE.square,
                            join_style=JOIN_STYLE.mitre).simplify(types.TRACK_RADIUS * 2)

    def split_for_obstacle(self, a, b, layer, obs):
        avoid = self._avoid_shape(obs.shape)
        for i in range(1, 5):
            obstacles = self._shape_intersects_on_layer(a, b, avoid, layer)
            if len(obstacles) == 0:
                break
            for o in obstacles:
                avoid = unary_union([avoid, o.shape])
            avoid = avoid.convex_hull.buffer(
                types.TRACK_RADIUS).simplify(types.TRACK_RADIUS)

        tqdm.write('split_for_obstacle %s -> %s with shape %s' %
                   (a, b, avoid.wkt))
        branches = []
        closest_a = None
        closest_b = None
        #tqdm.write('Split edge into %d pieces' % len(avoid.exterior.coords))
        for x, y in avoid.exterior.coords:
            br = types.Branch(Point(x, y), layer)
            branches.append(br)
            self.g.add_node(br)

            if not closest_a or (a.shape.distance(br.shape) < a.shape.distance(closest_a.shape)):
                closest_a = br
            if not closest_b or (b.shape.distance(br.shape) < b.shape.distance(closest_b.shape)):
                closest_b = br

            track = track_shape(a, br)
            segment = types.Segment(track, a, br)
            self.add_edge(a, br, layer=layer, track=segment)

            track = track_shape(br, b)
            segment = types.Segment(track, br, b)
            self.add_edge(br, b, layer=layer, track=segment)

        self.g.remove_edge(a, b)

        for i, j in pairwise(branches):
            track = track_shape(i, j)
            segment = types.Segment(track, i, j)
            self.add_edge(i, j, layer=layer, track=segment)

        # Close the loop
        i = branches[0]
        j = branches[-1]
        track = track_shape(i, j)
        segment = types.Segment(track, i, j)
        self.add_edge(i, j, layer=layer, track=segment)

        return closest_a, closest_b

    def split_edge(self, a, b, phys_only=False):
        layer = self.g[a][b].get('layer')
        if not layer:
            tqdm.write('no layer set for %s -> %s' % (a, b))
            return False
        if a.shape.centroid.distance(b.shape.centroid) == 0:
            return False

        obstacles = self.obstacles_in_path(a, b, layer, phys_only=phys_only)
        if not obstacles:
            return False

        # If we're intersecting with a Segment, rather than treating the whole
        # segment as the region to workaround, just try to outline a small
        # region around the intersection; we will likely choose a via path
        # to hop over it
        track = track_shape(a, b)

        def fixup_obs(obs):
            if isinstance(obs, types.Segment):
                overlap = obs.shape.intersection(
                    track).buffer(types.TRACK_RADIUS)
                return types.Segment(overlap, obs.a, obs.b)
            return obs
        obstacles = set(map(fixup_obs, obstacles))

        if not phys_only:
            for o in obstacles:
                tqdm.write('   %s' % o)

        overlaps = set()
        merged = True
        while merged:
            merged = False
            for i, j in combinations(obstacles, r=2):
                i_shape = self._avoid_shape(i.shape)
                j_shape = self._avoid_shape(j.shape)
                if i_shape.intersects(j_shape):
                    obstacles.remove(i)
                    obstacles.remove(j)
                    obs = types.Obstacle(
                        layer,
                        unary_union([i_shape, j_shape]).convex_hull.buffer(-types.TRACK_RADIUS * 2), (i, j))
                    obstacles.add(obs)
                    merged = True
                    #tqdm.write('merged 2 obstacles')
                    break

        # Order them by distance from a
        def dist_from_a(node):
            return a.shape.centroid.distance(node.shape.centroid)

        obstacles = sorted(list(obstacles), key=dist_from_a)

        for obs in obstacles:
            a_branch, b_branch = self.split_for_obstacle(a, b, layer, obs)
            #self.split_edge(a, a_branch, phys_only=phys_only)
            #self.split_edge(b_branch, b, phys_only=phys_only)
            # return True
            a = b_branch
            # break
            #self.split_edge(b_branch, b)
        return True

    def split_all_track_edges(self):
        for a, b in tqdm(self.g.edges(), desc='splitting for physical obstacles'):
            edgedata = self.g[a][b]
            track = edgedata.get('track')
            if track:
                self.split_edge(a, b)

    def improve_one_path(self):
        improved = False
        paths = [path for cost, path in self.paths]
        random.shuffle(paths)
        for path in paths:
            for a, b in pairwise(path):
                cost = self.edge_weight(a, b)
                if cost >= COLLISION_COST:
                    tqdm.write('improve path %s (%r) -> %s (%r) with cost %s' %
                               (a, a.shape.centroid.wkt, b, b.shape.centroid.wkt, cost))
                    if self.split_edge(a, b):
                        improved = True
            if improved:
                return True

        return improved

    def build_initial_graph(self):
        ''' Build up an initial path between each terminal each 2net:
              /- a_branch on F.Cu ---------------- b_branch on F.Cu \   
             a      |                                 |              b
              \- a_branch on B.Cu ---------------- b_branch on B.Cu /
            If a doesn't exist on both layers, we won't emit edges to
            a_branch on the missing layers, and similarly for b.
        '''
        for a, b in tqdm(self.two_nets, desc='initialize graph'):
            save_smap = self.layer_smap

            self.g.add_node(a)
            self.g.add_node(b)

            vert_a = []
            vert_b = []
            assert(len(a.layers) > 0)
            assert(len(b.layers) > 0)
            for layer in [types.FRONT, types.BACK]:
                a_branch = types.Branch(a.shape, layer, proxy_for=a)
                vert_a.append(a_branch)
                self.g.add_node(a_branch)

                b_branch = types.Branch(b.shape, layer, proxy_for=b)
                vert_b.append(b_branch)
                self.g.add_node(b_branch)

                track = track_shape(a_branch, b_branch)
                self.add_edge(a_branch, b_branch, layer=layer,
                              track=types.Segment(track, a_branch, b_branch))

                if a.is_on_layer(layer):
                    self.add_edge(a, a_branch, layer=layer)
                if b.is_on_layer(layer):
                    self.add_edge(b, b_branch, layer=layer)

                self.layer_smap = save_smap
                #self.split_edge(a_branch, b_branch, phys_only=True)

            self.add_edge(vert_a[0], vert_a[1], via=True)
            self.add_edge(vert_b[0], vert_b[1], via=True)
        tqdm.write('Graph has %d nodes and %d edges' %
                   (len(self.g), self.g.size()))

    def make_solution(self):
        return Solution(self.phys_map, self.g, self.two_nets)


def compute_initial_2net_order(two_nets):
    # lets order the two nets such that fixed layer requirements are
    # routed first when we attempt a solution below.  We use the layers
    # attribute to figure this out; if the node has a single layer then
    # we must consider it first, otherwise we assume that it is present on
    # all layers and has more flexibility in routing.
    return sorted(two_nets, key=lambda x: len(x.layers) if hasattr(x, 'layers') else 3)


def route(data):
    import cProfile
    import pstats

    pr = cProfile.Profile()
    cfg = layerassign.Configuration(data['2nets'])
    cfg = cfg.initial_assignment()

    pr.enable()
    cfg = cfg.improve()
    pr.disable()

    sortby = 'cumulative'
    ps = pstats.Stats(pr).sort_stats(sortby)
    ps.print_stats()

    routed_graph = networkx.Graph()
    for path in tqdm(cfg.paths, desc='distil route'):
        for i, j in pairwise(path):
            if isinstance(i, layerassign.SourceSinkNode):
                continue
            if isinstance(j, layerassign.SourceSinkNode):
                continue
            layer = None
            #tqdm.write('path segment layers: %r %r' % (i.layers, j.layers))
            if i.layers == j.layers:
                layer = i.layers[0]
            cost = cfg.edge_weight(i, j)
            routed_graph.add_node(i)
            routed_graph.add_node(j)
            distance = i.shape.centroid.distance(j.shape.centroid)
            cost = cfg.edge_weight(i, j)
            #tqdm.write('distance=%r cost=%r %s -> %s' % (distance, cost, i, j))
            routed_graph.add_edge(i, j,
                                  collision=cost > distance *
                                  (1 - layerassign.ALPHA),
                                  layer=layer)

    return routed_graph

    two_nets = compute_initial_2net_order(data['2nets'])
    solution = Solution(data['smap'], networkx.Graph(), two_nets)
    solution.build_initial_graph()
    solution.solve()
    best_solution = solution
    tqdm.write('Initial solution has cost %r' % best_solution.cost)

    improved = False
    while improved:
        attempts = 6
        improved = False
        solution = best_solution.copy()
        while attempts > 0:
            attempts -= 1
            solution.improve_one_path()
            cost = solution.solve()
            tqdm.write('Graph has %d nodes and %d edges' %
                       (len(solution.g), solution.g.size()))
            tqdm.write('Computed solution with cost %r, best %r' %
                       (cost, best_solution.cost))
            if cost < best_solution.cost:
                improved = True
                best_solution = solution
                break

    # return solution.g
    # Transform the solution to a graph so that caller can render it
    solution = best_solution
    routed_graph = networkx.Graph()
    for _cost, path in tqdm(solution.paths, desc='distil route'):
        for i, j in pairwise(path):
            layer = solution.g[i][j].get('layer')
            cost = solution.edge_weight(i, j)
            routed_graph.add_node(i)
            routed_graph.add_node(j)
            routed_graph.add_edge(i, j, collision=cost >= COLLISION_COST,
                                  layer=layer)

            if False and cost > 0:
                obs = solution.obstacles_in_path(i, j, layer)
                if obs:
                    tqdm.write('Path %s -> %s has obstacles:' % (i, j))
                    for o in obs:
                        tqdm.write('   %s' % o)

    return routed_graph
