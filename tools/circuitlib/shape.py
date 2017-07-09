from __future__ import absolute_import
from __future__ import print_function

from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
from shapely.ops import unary_union
from shapely.affinity import (translate, scale, rotate)
from shapely.validation import explain_validity
import shapely.wkt
import math


def add_geoms(geoms, shape):
    if hasattr(shape, 'geoms'):
        for g in shape.geoms:
            geoms.append(g)
        return
    geoms.append(shape)


def find_corners(shape):
    ''' return a list of the corner points from a shape
        We skip shallow corners; the idea is that we're locating candidates
        for screw holes '''
    coords = shape.exterior.coords
    l = len(coords)
    corners = []
    for i in range(0, l):
        A = Point(coords[i % l])
        B = Point(coords[(i + 1) % l])
        C = Point(coords[(i + 2) % l])
        c = A.distance(B)
        a = B.distance(C)
        b = C.distance(A)

        if a == 0 or c == 0:
            continue

        v = (a * a + c * c - b * b) / (2 * a * c)
        if v < -1:
            v = -1
        elif v > 1:
            v = 1
        r = math.acos(v)
        angle = math.degrees(r)

        if angle > 15 and angle < 165:
            corners.append(B)

    return corners


def make_shapes(layout, use_rj45=False):
    # First pass to compute some shapes
    cap_holes = []
    for _, cluster in layout.key_clusters().items():
        hull = []
        for k in cluster:
            key_poly = k.polygon()

            # Buffer the outline to increase the chances of having an
            # intersection for keys that are very close to each other
            hull.append(key_poly.buffer(0))

        # compute the outline of the keycaps; this is for the topmost plate
        hull = unary_union(MultiPolygon(hull))
        # add some spacing to allow the kepcaps room to move through the holes
        hull = hull.buffer(1,
                           cap_style=CAP_STYLE.square,
                           join_style=JOIN_STYLE.mitre)
        add_geoms(cap_holes, hull)

    # The buffer(0) here ensures that the geometry remains valid in the case
    # that the inflated key hole outlines intersect with each other.
    cap_holes = MultiPolygon(cap_holes).buffer(0)
    overall_hull = unary_union(cap_holes).convex_hull

    # Now, we want to find somewhere to place the microcontroller.
    # We can't place it under the keyswitches (unless we want a taller
    # keyboard; we could make this a configuration option), so we take
    # the available space from the convex hull and use that as the candidate
    # space for the components.   We expect things to not full fit in this space,
    # so we're trying to find the location with the largest overlap; once found,
    # we can include the components in the hull and continue with the rest of
    # the placement below.
    def find_space(hull, avoid, shape, padding=5):
        component_space = hull.symmetric_difference(avoid)
        bounds = component_space.envelope.bounds
        best = None
        for x in range(int(bounds[0]) - padding, int(bounds[2]) + padding):
            candidate = translate(shape, x, bounds[1])
            if avoid.intersects(candidate):
                continue
            overlap = component_space.intersection(candidate).area
            if (not best) or (overlap > best[0]):
                best = (overlap, candidate)

        if not best:
            raise Exception('could not place component')
        return best[1]

    mcu = translate(find_space(
        overall_hull, cap_holes, box(0, 0, 23, 51)), 0, 0)
    mcu = translate(mcu, 5, 0)  # make some space for easier routing
    # Adjust the hull to fit the mcu
    overall_hull = unary_union([overall_hull,
                                mcu.buffer(1,
                                           cap_style=CAP_STYLE.square,
                                           join_style=JOIN_STYLE.mitre)]).convex_hull

    if use_rj45:
        rj45 = find_space(overall_hull, unary_union(
            [cap_holes, mcu]), box(0, 0, 18, 18))
        overall_hull = unary_union([overall_hull,
                                    rj45.buffer(1,
                                                cap_style=CAP_STYLE.square,
                                                join_style=JOIN_STYLE.mitre)]).convex_hull
    else:
        rj45 = None

    # Locate screw holes at the corners.  We inflate the hull to allow room for
    # mounting material.  We do half of this now so we can locate the screw
    # hole centers, then the other half afterwards for the other side.
    CASE_HOLE_SIZE = 3.0  # M3 screws
    HOLE_PADDING = 2.0
    corner_holes = []
    overall_hull = overall_hull.buffer((CASE_HOLE_SIZE + HOLE_PADDING) / 2,
                                       cap_style=CAP_STYLE.square,
                                       join_style=JOIN_STYLE.mitre)
    corner_points = find_corners(overall_hull)
    for c in corner_points:
        corner_dot = c.buffer(CASE_HOLE_SIZE / 2)
        corner_holes.append(corner_dot)
    corner_holes = MultiPolygon(corner_holes)

    # and take us out the remaining padding, this time we'll round the corners
    overall_hull = overall_hull.buffer((CASE_HOLE_SIZE + HOLE_PADDING) / 2)
    bounds = overall_hull.envelope.bounds
    bounds = (bounds[2] - bounds[0], bounds[3] - bounds[1])

    # maximum footprint for the bottom of the case
    bottom_plate = overall_hull

    # Ensure that sockets are flush with the edge
    mcu = translate(mcu, 0, -(1 + CASE_HOLE_SIZE + HOLE_PADDING))
    if rj45:
        rj45 = translate(rj45, 0, -(1 + CASE_HOLE_SIZE + HOLE_PADDING))

    top_plate_no_corner_holes = bottom_plate.symmetric_difference(cap_holes)
    top_plate = top_plate_no_corner_holes.symmetric_difference(corner_holes)

    switch_holes = []
    for k in layout.keys():
        add_geoms(switch_holes, k.switch_hole())
    switch_holes = MultiPolygon(switch_holes).buffer(0)
    switch_plate = cap_holes.symmetric_difference(switch_holes)

    return {
        'bounds': bounds,
        'top_plate': top_plate,
        'top_plate_no_corner_holes': top_plate_no_corner_holes,
        'bottom_plate': bottom_plate,
        'corner_holes': corner_holes,
        'corner_points': corner_points,
        'switch_plate': switch_plate,
        'switch_holes': switch_holes,
        'mcu': mcu,
        'rj45': rj45,
    }
