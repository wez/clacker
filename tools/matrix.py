from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from .kmeans import same_size_kmeans
import math
from .svg import SVG
import networkx as nx
from shapely.geometry import (Point, LineString)
from .kle import Key
from .tsp import greedy_tsp
import itertools
from .utils import pairwise
import os


class SparseList(list):
    def __setitem__(self, index, value):
        missing = index - len(self) + 1
        if missing > 0:
            self.extend([None] * missing)
        list.__setitem__(self, index, value)

    def __getitem__(self, index):
        try:
            return list.__getitem__(self, index)
        except IndexError:
            return None


class KeyboardMatrix(object):
    maxKeyCapLen = 0
    maxCols = 0

    def __init__(self):
        self.rows = SparseList()
        self.collisions = []

    def addKey(self, x, y, k):
        self.maxKeyCapLen = max(self.maxKeyCapLen, len(k.shortLabel()))

        grow = self._allowGrowing()
        limit_x, limit_y = self._getMaxBounds()
        if (not grow) and ((y >= limit_y) or (x >= limit_x)):
            self.collisions.append((x, y, k))
            return

        if self.rows[y] is None:
            self.rows[y] = SparseList()

        if self.rows[y][x] is None:
            self.rows[y][x] = k
            self.maxCols = max(x, self.maxCols)
            return

        self.collisions.append((x, y, k))
        #print(x, y, k.shortLabel(), ' collides with ', self.rows[y][x].shortLabel())

    def resolveCollisions(self):
        for x, y, k in self.collisions:
            self.placeCollision(x, y, k)

    def _getMaxBounds(self):
        ''' compute the max bounds for placement.
        '''
        return (self.maxCols, len(self.rows))

    def dimensions(self):
        ''' measures the occupied size of the matrix '''
        n_cols = 0
        for row in self.rows:
            n_cols = max(n_cols, len(row))
        return (n_cols, len(self.rows))

    def _allowGrowing(self):
        return True

    def placeCollision(self, x, y, k):
        ''' collision; find an alternate position.  We do this by
            walking the matrix and looking for the closest candidate
            position. '''
        best = None
        limit_x, limit_y = self._getMaxBounds()
        grow = self._allowGrowing()
        for x2 in range(0, limit_x + 1):
            for y2 in range(0, limit_y + 1):
                if (self.rows[y2] is None) or (self.rows[y2][x2] is None):
                    dy = y2 - y
                    if y2 == limit_y:
                        ''' make it more expensive to create a new row '''
                        if not grow:
                            continue
                        dy += math.copysign(10, y2)
                    dx = x2 - x
                    if x2 == limit_x:
                        ''' make it more expensive to create a new col '''
                        if not grow:
                            continue
                        dx += math.copysign(10, x2)
                    distance = (dx * dx) + (dy * dy)

                    #print('candidate ', x2, y2, ' has distance ', distance, dx, dy)

                    if (best is None) or (distance < best[0]):
                        best = (distance, x2, y2)
                        #print('best so far: ', x2, y2, distance, dx, dy)

        x2 = best[1]
        y2 = best[2]
        #print('resolved to ', x2, y2)

        if self.rows[y2] is None:
            self.rows[y2] = SparseList()

        self.rows[y2][x2] = k
        self.maxCols = max(x2, self.maxCols)

    def removeBlankRowsAndCols(self):
        # make a simple optimization pass; we're going to remove any
        # blank rows or columns.
        for y in range(len(self.rows) - 1, -1, -1):
            empty = True
            row = self.rows[y]
            if row is not None:
                for col in row:
                    if col is not None:
                        empty = False
                        break
            if empty:
                del self.rows[y]

        for col in range(self.maxCols, -1, -1):
            empty = True
            for row in self.rows:
                if row[col] is not None:
                    empty = False
                    break

            if empty:
                for row in self.rows:
                    del row[col]

    def positions(self):
        ''' generator that yields all matrix positions in row, column order '''
        limit_x, limit_y = self.dimensions()
        for y in range(0, limit_y):
            row = self.rows[y]
            if row is None:
                for x in range(0, limit_x + 1):
                    yield y, x, None
                continue
            for x in range(0, limit_x + 1):
                k = row[x]
                yield y, x, k

    def keys(self):
        ''' generator that yields the keys in row, column order '''
        limit_x, limit_y = self.dimensions()
        for y in range(0, limit_y):
            row = self.rows[y]
            if row is None:
                continue
            for x in range(0, limit_x + 1):
                k = row[x]
                if k is not None:
                    yield y, x, k

    def assignIdentifiers(self):
        ''' Make a pass over the final form of the matrix to assign
            identifiers for the switch positions.  This is simply
            a label of the form kYX, with the Y and X positions shown
            in hex.  For larger matrices, the Y and X will be separated
            by an underscore to disambiguate the legen.
            This label will be used in
            the KEYMAP macro definition and will be threaded through
            to renders of the physical key positions. '''

        fmt = 'k%x%x'
        if self.maxCols > 15 or len(self.rows) > 15:
            fmt = 'k%x_%x'

        for y, x, k in self.keys():
            k.identifier = fmt % (y, x)

    def key(self, x, y):
        if self.rows[y] is None:
            return None
        return self.rows[y][x]

    def render(self):
        limit_x, limit_y = self._getMaxBounds()
        for y in range(0, limit_y):
            row = self.rows[y]
            if row is None:
                continue
            disprow = []
            for x in range(0, limit_x + 1):
                k = row[x]
                label = ''
                if k is not None:
                    label = k.shortLabel()
                    if len(label) == 0:
                        label = '_'
                disprow.append(label.center(self.maxKeyCapLen))
            print(' | '.join(disprow))

    # Starting points for a walk
    NW = 0
    NE = 1
    SW = 2
    SE = 3

    UP = -1
    DOWN = 1

    def walk(self, start=NW):
        ''' iterate over the keys starting at one of the rectangular
            corners.  The walk progresses by moving vertically away
            from the corner until the opposite corner is hit.  The
            direction of the walk then flips and the walk continues
            the other way, moving inwards from the intersection
            with the edge, zig-zagging through the interior of the
            key matrix '''
        for x, y in self.zigzagpositions(start):
            row = self.rows[y]
            if not row:
                continue
            k = row[x]
            if not k:
                continue
            yield x, y, k

    def zigzagpositions(self, start=NW, limit_x=None, limit_y=None):
        ''' yield potential coordinates, zig-zagging through the matrix
            starting at the specified corner.
            Yields all possible coordinates, regardless of whether they
            are occupied by keys '''
        src_bound_x, src_bound_y = self.dimensions()
        limit_x = limit_x or src_bound_x + 1
        limit_y = limit_y or src_bound_y + 1

        if start == self.NW or start == self.NE:
            direction = self.DOWN
        else:
            direction = self.UP

        if start == self.NW or start == self.SW:
            xs = range(0, limit_x)
        else:
            xs = range(limit_x - 1, -1, -1)

        for x in xs:
            if direction == self.DOWN:
                ys = range(0, limit_y)
            else:
                ys = range(limit_y - 1, -1, -1)
            direction *= -1
            for y in ys:
                yield x, y


def min_matrix(layout, outputs):
    keys = list(layout.keys())
    k = int(math.ceil(math.sqrt(len(keys))))
    arr = []
    for key in keys:
        pt = key.polygon().centroid
        pt = (pt.x, pt.y)
        arr.append(list(pt))

    clusters = same_size_kmeans(keys, k)
    ''' now, we want to return the results in a well-defined order.
        For each cluster, we identify the key that is closest to the
        origin point.  This is used to order the clusters.
        Within the cluster, things are slightly more complex than
        it might seem at first.  We'd like there to be a line
        through the cluster that visits each node only once for
        the column wiring.  This is the Travelling Salesman Problem
        that we need to solve for each cluster. '''

    columns = []
    origin = Point(0, 0)

    class Pt(object):
        def __init__(self, shape):
            self.pt = Point(shape.bounds[0], shape.bounds[1])

        def __lt__(self, other):
            if self.pt.x < other.pt.x:
                return True
            return self.pt.y < other.pt.y

        def __eq__(self, other):
            return self.pt.x == other.pt.x and self.pt.y == other.pt.y

    for idx, cluster in enumerate(clusters):
        g = nx.DiGraph()

        cluster = sorted(cluster, key=lambda k: Pt(k.polygon()))
        for k1, k2 in itertools.permutations(cluster, 2):
            g.add_edge(k1, k2, weight=k1.polygon(
            ).centroid.distance(k2.polygon().centroid))

        cycle, weight = greedy_tsp(g, cluster[0])
        cycle.pop()  # break the cycle, so we just have the desired order
        # Now we want to rotate the cycle until our chosen first key is at the start
        while cycle[0] != cluster[0]:
            last = cycle.pop()
            cycle.insert(0, last)
        columns.append(cycle)

    columns = sorted(
        columns, key=lambda cluster: origin.distance(cluster[0].polygon()))

    if True:
        doc = SVG()

        def render_keys_and_path(keys, doc, color):
            for key in keys:
                doc.add(key.polygon(),
                        stroke=color,
                        stroke_width=0.2,
                        fill=color,
                        fill_opacity=0.4
                        )
            for k1, k2 in pairwise(keys):
                doc.add(LineString([k1.centroid(), k2.centroid()]),
                        stroke=color,
                        stroke_width=0.2
                        )

        colors = [
            'red',
            'blue',
            'green',
            'gray',
            'gold',
            'purple'
        ]

        for idx, keys in enumerate(columns):
            render_keys_and_path(keys, doc, colors[idx % len(colors)])

        doc.save(os.path.join(outputs, 'matrix.svg'))

    return columns


def compute_matrix(layout, outputs):
    ''' Compute the logical keyboard matrix.
        This corresponds to the KEYMAP that we'd emit for the QMK firmware code.
        This matrix is square; we ignore rotation and use the approximate x,y
        coords of the key in the keydata to decide on a preferred location for
        the key in the logical matrix.
        Collisions are resolved in a second pass; we prefer to stick those keys
        in existing empty space, but we can also expand the logical matrix if
        there is no nearby empty space.
    '''
    matrix = KeyboardMatrix()

    def labelLen(k):
        ''' Since the logical matrix is intended to make sense to humans, we
            prioritize placement of the alpha keys.  This is done fairly simply;
            we place the keys with the shorter legends first. '''
        return len(k.shortLabel())

    def logical_matrix_from_cluster(keys):
        matrix = KeyboardMatrix()
        for k in sorted(keys, key=labelLen):
            matrix.addKey(int(k.x), int(k.y), k)
        ''' Remove empty lines before attempting to place collisions, so that we
            can avoid creating a column holding a single key '''
        matrix.removeBlankRowsAndCols()
        matrix.resolveCollisions()

        return matrix

    matrix = logical_matrix_from_cluster(layout.keys())
    ''' The logical matrix defines the keyswitch identifiers '''
    matrix.assignIdentifiers()

    logical_cols, logical_rows = matrix.dimensions()
    print('Logical keyboard matrix: %d x %d\n' % (logical_cols, logical_rows))
    matrix.render()

    clusters = min_matrix(layout, outputs)
    phys = KeyboardMatrix()
    for x, keys in enumerate(clusters):
        for y, key in enumerate(keys):
            phys.addKey(x, y, key)

    cols, rows = phys.dimensions()
    print('Physical matrix %d x %d' % (cols, rows))
    phys.render()

    return matrix, phys
