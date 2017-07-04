from .kle import SWITCH_SPACING
from scipy.cluster.vq import kmeans2
from shapely.geometry import Point
from tqdm import tqdm
from .utils import bounds_of
from numpy import array
import itertools
import numpy
import warnings


def same_size_kmeans(keys, k, max_iter=1000):
    ''' Given a list of keys, group into k sets of
        spatially clustered items, with evenly balanced
        membership

        Inspired by https://elki-project.github.io/tutorial/same-size_k_means
        '''

    ''' use the kmeans algorithm to compute an initial set
        of cluster centroids.
        For a deterministic initialization, we pre-seed the kmeans call
        with a set of centroids where we expect each column to be;
        we divide up the bounding box by k and pick the center of
        each of those columns '''

    arr = []
    for key in keys:
        pt = key.polygon().centroid
        pt = (pt.x, pt.y)
        arr.append(list(pt))

    bounds = list(map(int, bounds_of([key.polygon() for key in keys])))
    kinit = []
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]

    if width > height:
        col_width = int(width / k)
        col_y = int(bounds[1] + (height / 2))
        for x in range(bounds[0], bounds[2], col_width):
            kinit.append([x - col_width, col_y])
    else:
        row_height = int(height / k)
        row_x = int(bounds[0] + (width / 2))
        for y in range(bounds[1], bounds[3], row_height):
            kinit.append([row_x, y - row_height])

    kinit = array(kinit)

    with warnings.catch_warnings():
        # kmeans2 may warn about one of the cluster columns being empty;
        # this is fine because basically this entire file has code to
        # iteratively improve the result.  Let's suppress the warning
        # to head off questions about that.
        warnings.simplefilter('ignore')
        centroid, _ = kmeans2(arr, kinit, minit='matrix',
                              check_finite=False, iter=max_iter)

    cluster_centroid = [Point(*x) for x in centroid]

    ''' the rest of this method is an algorithm to re-balance
        the distribution of clusters such that they are equal.
        The idea is that we rank the placement of individual
        keys based on how close they are to the centroids
        computed by the kmeans algorithm.
        This ranking is used to place the key in a cluster,
        but if a given cluster is too full, we recompute
        and move it to a second ary choice.
        The improvement phase of the algorithm tries to
        swap keys to improve the overall placement. '''

    INF = float("inf")
    max_size = int((len(keys) + k - 1) / k)
    min_size = int(len(keys) / k)

    ''' affects how harshly we penalize distance '''
    dist_pow = 3

    class Item(object):
        npt = None

        def __init__(self, key):
            self.key = key
            pt = key.polygon(SWITCH_SPACING).centroid
            self.npt = [pt.x, pt.y]
            self.pt = pt
            ''' our preferred cluster '''
            self.primary = 0
            ''' our least preferred cluster '''
            self.secondary = 0
            ''' dists holds the distancees to each of the k cluster
                centroids.  '''
            self.dists = list(itertools.repeat(INF, k))
            for i in range(0, k):
                dist = pt.distance(cluster_centroid[i]) ** dist_pow
                self.dists[i] = dist
                if i > 0:
                    if dist < self.dists[self.primary]:
                        self.primary = i
                    elif dist > self.dists[self.secondary]:
                        self.secondary = i

        def priority(self):
            ''' Priority / badness: difference between best and worst.
            (Assuming that "secondary" is the worst) '''
            return self.dists[self.secondary] - self.dists[self.primary]

        def gain(self, i):
            ''' Gain from switching to cluster i. '''
            return self.dists[self.primary] - self.dists[i]

        def compute_fallback(self, clusters):
            ''' Called when our primary is known to be full.
                We need to figure out an alternative primary. '''
            fix_idx = self.primary
            for i in range(0, k):
                if len(clusters[i]) >= max_size:
                    continue
                if self.primary == fix_idx or \
                        self.dists[i] < self.dists[self.primary]:
                    self.primary = i

        def update_distance(self, centroids):
            ''' recompute the cached distances to cluster centroids
                after we've re-balanced the centroids '''
            self.secondary = -1
            for i in range(0, k):
                dist = self.pt.distance(Point(centroids[i])) ** dist_pow
                self.dists[i] = dist
                if self.primary != i:
                    if self.secondary < 0 or \
                            self.dists[i] < self.dists[self.secondary]:
                        self.secondary = i

        def __str__(self):
            return '%s p=%d s=%d %f' % (self.key.shortLabel(),
                                        self.primary,
                                        self.secondary,
                                        self.priority())

        __repr__ = __str__

    ''' initialize by building up the item list '''
    items = []
    for idx, coord in enumerate(arr):
        items.append(Item(keys[idx]))

    clusters = []
    for i in range(k):
        clusters.append(set())

    ''' now populate clusters with preferred items until they are full '''
    while len(items) > 0:
        ''' (re)sort by priority.  Note that priority can change as
            clusters are filled up '''
        items = sorted(items, key=Item.priority, reverse=True)

        item = items.pop(0)
        c = clusters[item.primary]
        c.add(item)

        if len(c) == max_size:
            ''' now that cluster is full, adjust remaining items to use another '''
            full_idx = item.primary
            for item in items:
                if item.primary == full_idx:
                    item.compute_fallback(clusters)

    def compute_centroids(clusters):
        ''' computes the centroids of the cluster assignments '''
        result = []
        for cluster in clusters:
            pts = []
            for item in cluster:
                pts.append(item.npt)
            result.append(numpy.mean(pts, axis=0))
        return result

    ''' Now to iteratively improve things '''

    moved = 0

    for improvement_iters in tqdm(range(0, max_iter), desc='clustering'):
        centroids = compute_centroids(clusters)
        ''' update distances based on the new centroids '''
        items = []
        for cluster in clusters:
            for item in cluster:
                item.update_distance(centroids)
                items.append(item)

        items = sorted(items, key=Item.priority, reverse=False)

        transfers_by_cluster = []
        for _ in range(0, k):
            transfers_by_cluster.append(set())

        def centroid_distance(cluster_idx, item):
            return item.pt.distance(Point(centroids[cluster_idx]))

        for _ in range(0, 2):
            for item in items:
                ''' compute preferred destination clusters based on distance '''
                prefs = sorted(
                    range(0, k), key=lambda x: centroid_distance(x, item))

                for dest_cluster in prefs:
                    if item.primary == dest_cluster:
                        continue

                    ''' see if we can swap with an item in the transfer list '''
                    for other in transfers_by_cluster[dest_cluster]:
                        if item.gain(dest_cluster) + other.gain(item.primary) > 0:
                            ''' yep, it's worth it '''
                            assert dest_cluster == other.primary

                            old_cluster = item.primary

                            clusters[old_cluster].remove(item)
                            clusters[dest_cluster].remove(other)

                            clusters[old_cluster].add(other)
                            clusters[dest_cluster].add(item)

                            item.primary = dest_cluster
                            other.primary = old_cluster
                            transfers_by_cluster[dest_cluster].remove(other)
                            moved += 2
                            break

                    else:
                        if item.gain(dest_cluster) > 0 and \
                                len(clusters[dest_cluster]) < max_size and \
                                len(clusters[item.primary]) > min_size:
                            ''' there's room in the preferred cluster, so
                                we can just move this item in without having
                                to figure out a swap '''
                            assert item in clusters[item.primary]
                            clusters[item.primary].remove(item)
                            clusters[dest_cluster].add(item)
                            item.primary = dest_cluster
                            moved += 1
                            break

                ''' if we're not in our preferred slot, request a transfer '''
                if item.primary != prefs[0] and \
                        item.dists[item.primary] > item.dists[prefs[0]]:
                    assert item in clusters[item.primary]
                    transfers_by_cluster[item.primary].add(item)

        moved -= 1
        if moved < 0:
            ''' if we didn't think that anything should have moved,
                then no more improvements are needed '''
            break

    tqdm.write('done in %d steps!' % improvement_iters)

    result = []
    origin = Point(0, 0)
    for items in clusters:
        result.append([item.key for item in items])

    return result
