import itertools
from heapq import heappush, heappop
from tqdm import tqdm


def dijkstra(G, source, target, cutoff=None, edge_weight=None):
    if edge_weight is None:
        def edge_weight(v, u, e):
            return e.get('weight', 1)

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
                cost = edge_weight(v, u, e)
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
