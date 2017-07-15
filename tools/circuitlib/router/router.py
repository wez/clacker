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

import random


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
