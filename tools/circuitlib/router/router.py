from __future__ import absolute_import
from __future__ import print_function

from tqdm import tqdm
from . import types
from ...utils import pairwise
import networkx
from shapely.affinity import (translate, scale, rotate)
from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)

COLLISION_COST = 1000000


def track_shape(a, b):
    return LineString([a.shape.centroid, b.shape.centroid]).buffer(types.TRACK_RADIUS)


def route(data):
    g = data['graph']
    two_nets = data['2nets']
    smap = data['smap']

    def avoid_obstacle(a, b, obstacle):
        avoid = obstacle.buffer(0.5, cap_style=CAP_STYLE.square,
                                join_style=JOIN_STYLE.mitre).simplify(types.TRACK_RADIUS)

        branches = []
        closest_a = None
        closest_b = None
        for x, y in avoid.exterior.coords:
            br = types.Branch(Point(x, y))
            branches.append(br)
            g.add_node(br)

            if not closest_a or (a.shape.distance(br.shape) < a.shape.distance(closest_a.shape)):
                closest_a = br
            if not closest_b or (b.shape.distance(br.shape) < b.shape.distance(closest_b.shape)):
                closest_b = br

        g.remove_edge(a, b)
        g.add_edge(a, closest_a)
        g.add_edge(closest_b, b)

        for i, j in pairwise(branches):
            g.add_edge(i, j)

        return closest_a, closest_b

    def avoid_obstacles(a, b):
        ''' find all the obstacles between a and b and compute a path around them '''
        obstacles = []
        track = track_shape(a, b)
        for entry in smap.intersects(track):
            if entry.shape == a.shape or entry.shape == b.shape:
                continue
            obstacles.append(entry.shape)

        if not obstacles:
            return

        # Order them by distance from a
        def dist_from_a(shape):
            return a.shape.centroid.distance(shape.centroid)

        obstacles = sorted(obstacles, key=dist_from_a)

        for obs in obstacles:
            a_branch, b_branch = avoid_obstacle(a, b, obs)
            # TODO: this new path from a->b may add or remove obstacles,
            # and we should really re-compute the obstacle set
            a = b_branch
            return avoid_obstacles(b_branch, b)

    # Make a first pass through the two nets to figure out how to route
    # around the fixed obstacles on the board
    for a, b in tqdm(two_nets, desc='avoid physical (easy)'):
        avoid_obstacles(a, b)

    def compute_weights():
        ''' Recompute the weights for each edge '''
        for a, b in g.edges():
            cost = a.shape.centroid.distance(b.shape.centroid)

            track = track_shape(a, b)
            for entry in smap.intersects(track):
                if entry.shape == a.shape or entry.shape == b.shape:
                    continue
                cost += COLLISION_COST
            g[a][b]['weight'] = cost

    def path_cost(path):
        cost = 0
        for a, b in pairwise(path):
            cost += g[a][b]['weight']
        return cost

    compute_weights()

    # Iteratively improve the paths
    mutated = True
    with tqdm(desc='avoid physical (improve)') as pbar:
        while mutated:
            pbar.update(1)
            mutated = False
            for a, b in two_nets:
                # We need to find a path from a -> b with an acceptable cost
                path = networkx.shortest_path(g, a, b, weight='weight')
                for i, j in pairwise(path):
                    cost = g[i][j]['weight']
                    if cost >= COLLISION_COST:
                        pbar.write(
                            '%s -> %s has cost %s, splitting path' % (i, j, cost))
                        avoid_obstacles(i, j)
                        compute_weights()
                        mutated = True

    routed_graph = networkx.Graph()
    for a, b in tqdm(two_nets, desc='distil route'):
        # We need to find a path from a -> b with an acceptable cost
        path = networkx.shortest_path(g, a, b, weight='weight')
        for i, j in pairwise(path):
            routed_graph.add_node(i)
            routed_graph.add_node(j)
            routed_graph.add_edge(i, j, weight=g[i][j]['weight'])

    return routed_graph
