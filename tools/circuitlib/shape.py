from __future__ import absolute_import
from __future__ import print_function

from shapely.geometry import (Point, Polygon, MultiPolygon, CAP_STYLE,
                              JOIN_STYLE, box, LineString, MultiLineString, MultiPoint)
from shapely.ops import unary_union
from shapely.affinity import (translate, scale, rotate)
from shapely.validation import explain_validity
import shapely.wkt
import math
from . import circuit as circuitlib


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
    coords = shape.simplify(1).exterior.coords
    # -1 because 0 == nth and we don't want to falsely assume that there
    # is no distance between those points in the a==0 case below
    l = len(coords) - 1
    corners = []
    for i in range(0, l):

        A = Point(coords[i % l])
        B = Point(coords[(i + 1) % l])
        C = Point(coords[(i + 2) % l])
        c = A.distance(B)
        a = B.distance(C)
        b = C.distance(A)

        if c > 110:
            # Add support points for long straight sections
            support = LineString([A, B]).interpolate(c/2)
            corners.append(support)

        if a == 0 or c == 0:
            continue

        v = (a * a + c * c - b * b) / (2 * a * c)
        if v < -1:
            v = -1
        elif v > 1:
            v = 1
        r = math.acos(v)
        angle = math.degrees(r)

        if angle > 15 and angle < 180:
            corners.append(B)

    return corners


def make_shapes(layout, shape_config=None):
    # First pass to compute some shapes
    cap_holes = []
    raw_cap_holes = []
    for _, cluster in layout.key_clusters().items():
        hull = []
        for k in cluster:
            key_poly = k.polygon()

            add_geoms(raw_cap_holes, key_poly)

            # Buffer the outline to increase the chances of having an
            # intersection for keys that are very close to each other.
            # Add a little extra room to minimize the chances that the
            # keycaps will touch the case/plate edging.
            hull.append(key_poly.buffer(2,
                                        cap_style=CAP_STYLE.square,
                                        join_style=JOIN_STYLE.mitre))

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
    raw_cap_holes = MultiPolygon(raw_cap_holes).buffer(0)
    overall_hull = unary_union(cap_holes).convex_hull

    switch_holes = []
    for k in layout.keys():
        add_geoms(switch_holes, k.switch_hole())
    switch_holes = MultiPolygon(switch_holes).buffer(0)

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

    mcu_type = shape_config.get('mcu', 'feather') if shape_config else 'feather'
    if mcu_type == 'feather':
        mcu_dims = (23, 51)
    elif mcu_type == 'teensy':
        mcu_dims = (18, 36)
    elif mcu_type == 'header':
        mcu_dims = (5, 25)
    else:
        raise Exception('handle mcu type %s' % mcu_type)

    mcu_coords = shape_config.get('mcu_coords', None)
    if mcu_coords is None:
        mcu = translate(find_space(
            overall_hull, cap_holes,
            box(0, 0, mcu_dims[0], mcu_dims[1])), 0, 0)
    else:
        mcu = box(mcu_coords[0], mcu_coords[1], mcu_dims[0], mcu_dims[1])

    #mcu = translate(mcu, 5, 0)  # make some space for easier routing
    # Adjust the hull to fit the mcu
    overall_hull = unary_union([overall_hull,
                                mcu.buffer(1,
                                           cap_style=CAP_STYLE.square,
                                           join_style=JOIN_STYLE.mitre)]).convex_hull

    trrs_type = shape_config.get('trrs', None) if shape_config else None
    if trrs_type == 'basic':
        trrs_box = box(0, 0, 10, 11)
    elif trrs_type == 'left+right':
        trrs_box = box(0, 0, 15, 12)
    elif trrs_type is None:
        trrs = None
    else:
        raise Exception('handle trrs type %s' % trrs_type)

    if trrs_type is not None:
        trrs = find_space(overall_hull,
                                    unary_union([switch_holes, mcu]),
                                    trrs_box, padding=0)
        trrs_hull = trrs
        overall_hull = unary_union([overall_hull,
                                    trrs_hull.buffer(1,
                                                cap_style=CAP_STYLE.square,
                                                join_style=JOIN_STYLE.mitre)]).convex_hull


    rj45_type = shape_config.get('rj45', None) if shape_config else None
    if rj45_type == 'magjack':
        rj45_box = box(0, 0, 33, 23)
    elif rj45_type == 'basic':
        rj45_box = box(0, 0, 18, 18)
    elif rj45_type == 'left+right':
        rj45_box = box(0, 0, 18, 18)
    elif rj45_type is None:
        rj45 = None
    else:
        raise Exception('handle rj45 type %s' % rj45_type)

    if rj45_type is not None:
        rj45 = find_space(overall_hull,
                                    unary_union([switch_holes, mcu]),
                                    rj45_box, padding=0)
        rj45_hull = rj45
        overall_hull = unary_union([overall_hull,
                                    rj45_hull.buffer(1,
                                                cap_style=CAP_STYLE.square,
                                                join_style=JOIN_STYLE.mitre)]).convex_hull

    # Locate screw holes at the corners.  We inflate the hull to allow room for
    # mounting material.  We do half of this now so we can locate the screw
    # hole centers, then the other half afterwards for the other side.
    CASE_HOLE_SIZE = 3.0  # M3 screws
    HOLE_PADDING = 2.0
    corner_holes = []
    corner_hole_posts = []
    overall_hull = overall_hull.buffer((CASE_HOLE_SIZE + HOLE_PADDING) / 2,
                                       cap_style=CAP_STYLE.square,
                                       join_style=JOIN_STYLE.mitre)

    # Ensure that sockets are flush with the edge
    mcu = translate(mcu, 0, -(1 + CASE_HOLE_SIZE + HOLE_PADDING))
    if rj45:
        rj45 = translate(rj45, 0, -(1 + CASE_HOLE_SIZE + HOLE_PADDING))
    if trrs:
        trrs = translate(trrs, 0, -(1 + CASE_HOLE_SIZE + HOLE_PADDING))

    corner_points = find_corners(overall_hull)
    points = []
    for c in corner_points:
        corner_dot = c.buffer(CASE_HOLE_SIZE)
        if corner_dot.intersects(mcu):
            continue
        if rj45 and rj45.intersects(corner_dot):
            continue
        if trrs and trrs.intersects(corner_dot):
            continue
        points.append(c)

    corner_points = points
    for c in corner_points:
        corner_dot = c.buffer(CASE_HOLE_SIZE / 2)
        corner_holes.append(corner_dot)
        corner_hole_posts.append(c.buffer((CASE_HOLE_SIZE + 3) / 2))

    corner_holes = MultiPolygon(corner_holes)
    corner_hole_posts = MultiPolygon(corner_hole_posts)

    # and take us out the remaining padding, this time we'll round the corners
    overall_hull = overall_hull.buffer((CASE_HOLE_SIZE + HOLE_PADDING) / 2)
    bounds = overall_hull.envelope.bounds
    bounds = (bounds[2] - bounds[0], bounds[3] - bounds[1])

    # maximum footprint for the bottom of the case
    bottom_plate = overall_hull


    mounting_holes = []
    circuit = circuitlib.Circuit()
    if mcu_type == 'feather':
        # mounting holes for the mcu
        feather = circuit.feather()
        # feather origin is at its center
        feather.set_position(translate(mcu, 11.5, 26))
        feather.set_rotation(90)
        for _, (pad, padshape, drillshape) in feather._pads_by_idx.items():
            if pad.name == "" and drillshape:
                mounting_holes.append(feather.transform(drillshape))

    # mounting holes for the rj45
    if rj45_type == 'magjack':
        jack = circuit.rj45_magjack()
        jack.set_position(rj45)
        for _, (pad, padshape, drillshape) in jack._pads_by_idx.items():
            if pad.name == "Hole" and drillshape:
                mounting_holes.append(jack.transform(drillshape))

    mounting_holes = MultiPolygon(mounting_holes)

    top_plate_no_corner_holes = bottom_plate.symmetric_difference(cap_holes)
    top_plate = top_plate_no_corner_holes.symmetric_difference(corner_holes)

    switch_plate = cap_holes.symmetric_difference(switch_holes)

    return {
        'bounds': bounds,
        'cap_holes': cap_holes,
        'raw_cap_holes': raw_cap_holes,
        'top_plate': top_plate,
        'top_plate_no_corner_holes': top_plate_no_corner_holes,
        'bottom_plate': bottom_plate,
        'corner_holes': corner_holes,
        'corner_hole_posts': corner_hole_posts,
        'corner_points': corner_points,
        'switch_plate': switch_plate,
        'switch_holes': switch_holes,
        'mounting_holes': mounting_holes,
        'mcu': mcu,
        'rj45': rj45,
        'trrs': trrs,
    }
