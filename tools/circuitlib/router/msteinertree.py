from __future__ import absolute_import
from __future__ import print_function
from shapely.geometry import Point as sPoint

# Derived from https://github.com/Keydrain/Steiner-Tree-Visualization/blob/master/Steiner.py

from tqdm import tqdm
from . import types


class UnionFind:
    '''Union-find data structure.
    Each unionFind instance X maintains a family of disjoint sets of
    hashable objects, supporting the following two methods:
    - X[item] returns a name for the set containing the given item.
      Each set is named by an arbitrarily-chosen one of its members; as
      long as the set remains unchanged it will keep the same name. If
      the item is not yet part of a set in X, a new singleton set is
      created for it.
    - X.union(item1, item2, ...) merges the sets containing each item
      into a single larger set.  If any item is not yet part of a set
      in X, it is added to X as one of the members of the merged set.

    Based on Josiah Carlson's code,
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/215912
    with significant additional changes by D. Eppstein.
    '''

    def __init__(self):
        """Create a new empty union-find structure."""
        self.weights = {}
        self.parents = {}

    def __getitem__(self, obj):
        """Find and return the name of the set containing the object."""

        # check for previously unknown object
        if obj not in self.parents:
            self.parents[obj] = obj
            self.weights[obj] = 1
            return obj

        # find path of objects leading to the root
        path = [obj]
        root = self.parents[obj]
        while root != path[-1]:
            path.append(root)
            root = self.parents[root]

        # compress the path and return
        for ancestor in path:
            self.parents[ancestor] = root
        return root

    def __iter__(self):
        """Iterate through all items ever found or unioned by this structure."""
        return iter(self.parents)

    def union(self, *objects):
        """Find the sets containing the objects and merge them all."""
        roots = [self[x] for x in objects]
        heaviest = max([(self.weights[r], r) for r in roots])[1]
        for r in roots:
            if r != heaviest:
                self.weights[heaviest] += self.weights[r]
                self.parents[r] = heaviest


class Point(object):
    def __init__(self, x, y, node=None):
        self.x = x
        self.y = y
        self.reset()
        # node is the input node.  If none then this is a Steiner point
        self.node = node

    def reset(self):
        self.deg = 0
        self.edges = []
        self.MSTedges = []

    def update(self, edge):
        self.edges.append(edge)

    def MSTupdate(self, edge):
        self.deg += 1
        self.MSTedges.append(edge)

    def __str__(self):
        return 'x=%s, y=%s deg=%r edges=%d' % (self.x, self.y, self.deg, len(self.edges))


class Line:
    ''' Contains the two end points as well as the weight of the line. 
    Supports determining the first or last point as well as the other given one. '''

    def __init__(self, p1, p2, w):
        self.points = [p1, p2]
        self.w = w

    def getOther(self, pt):
        if pt == self.points[0]:
            return self.points[1]
        elif pt == self.points[1]:
            return self.points[0]
        else:
            raise Exception(
                "The line does not contain points that make sense.")

    def getFirst(self):
        return self.points[0]

    def getLast(self):
        return self.points[1]


def hanan_points(input_points):
    points = []
    for i in range(0, len(input_points)):
        for j in range(i, len(input_points)):
            if i != j:
                points.append(Point(input_points[i].x, input_points[j].y))
                points.append(Point(input_points[j].x, input_points[i].y))
    return points


def delta_mst(points, point):
    ''' Determines the difference in a MST's total weight after adding a point. '''
    MST = kruskal(points)
    cost1 = 0
    for p in MST:
        cost1 += p.w

    combo = points + [point]
    MST = kruskal(combo)
    cost2 = 0
    for p in MST:
        cost2 += p.w

    return cost1 - cost2


def kruskal(points):
    ''' Kruskal's Algorithm
    Sorts edges by weight, and adds them one at a time to the tree while avoiding cycles
    Takes any set of Point instances and converts to a dictionary via edge crawling 
    Takes the dictionary and iterates through each level to discover neighbors and weights
    Takes list of point index pairs and converts to list of Lines then returns
    '''

    for p in points:
        p.reset()

    for i in range(0, len(points)):
        for j in range(i, len(points)):
            if i != j:
                dist = (abs(points[i].x - points[j].x)
                        + abs(points[i].y - points[j].y))
                line = Line(points[i], points[j], dist)
                points[i].update(line)
                points[j].update(line)
            else:
                dist = 100000
                line = Line(points[i], points[j], dist)
                points[i].update(line)

    G = {}
    for i in range(0, len(points)):
        off = 0
        subset = {}
        for j in range(0, len(points[i].edges)):
            subset[j] = points[i].edges[j].w
        G[i] = subset

    subtrees = UnionFind()
    tree = []
    for W, u, v in sorted((G[u][v], u, v) for u in G for v in G[u]):
        if subtrees[u] != subtrees[v]:
            tree.append([u, v])
            subtrees.union(u, v)

    MST = []
    for i in range(0, len(tree)):
        point1 = points[tree[i][0]]
        point2 = points[tree[i][1]]
        for edge in point1.edges:
            if point2 == edge.getOther(point1):
                point1.MSTupdate(edge)
                point2.MSTupdate(edge)
                MST.append(edge)
    return MST


def rectilinear_steiner_minimum_spanning_tree(list_of_nodes):
    steiner_points = []

    points = [Point(n.shape.centroid.x, n.shape.centroid.y, n)
              for n in list_of_nodes]

    RSMT = []
    candidate_set = [0]  # Just to start the loop
    while candidate_set:
        max_point = None

        merged_points = points + steiner_points
        candidate_set = [x for x in hanan_points(
            merged_points) if delta_mst(merged_points, x) > 0]

        cost = 0
        for pt in candidate_set:
            delta_cost = delta_mst(merged_points, pt)
            if delta_cost > cost:
                max_point = pt
                cost = delta_cost

        # Remember the current set of steiner_points so that we can tell
        # when we need to terminate the loop; if we didn't mutate them
        # then there is no point continuing.
        before = [p for p in steiner_points]
        if max_point:
            steiner_points.append(max_point)

        steiner_points = [pt for pt in steiner_points if pt.deg > 2]

        RSMT = kruskal(points + steiner_points)

        if before == steiner_points:
            # The add/remove stuff above had no net effect, so terminate
            # the loop!
            break

    def point_to_node(pt):
        ''' converts a Steiner point (which by definition has node=None)
            into a Branch node.  Make sure we do this only once as we
            want to use that node in a graph later on.  This is as simple
            as just assigning the node property to the generated Branch '''
        if pt.node is None:
            pt.node = types.Branch(sPoint(pt.x, pt.y))
        return pt.node

    # unpack the internal representation into something our caller can use
    mst = []
    for line in RSMT:
        node_a = point_to_node(line.getFirst())
        node_b = point_to_node(line.getLast())
        mst.append((node_a, node_b))

    return mst
