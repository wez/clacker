import itertools


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def bounds_of(shapes):
    ''' compute min/max bounds of an iterable of shapes '''
    bounds = [0, 0, 0, 0]
    for shape in shapes:
        b = shape.bounds
        bounds[0] = min(bounds[0], b[0])
        bounds[1] = min(bounds[1], b[1])
        bounds[2] = max(bounds[2], b[2])
        bounds[3] = max(bounds[3], b[3])

    return bounds
