from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
import svgwrite
from shapely.affinity import translate
from . import utils

SVG_PADDING = 5  # mm


class SVG(object):
    ''' This class helps to construct and render an SVG document based
        on a collection of shapely geometries that were added.
        We defer computing the bounds of the document until we're ready
        to save, so that we can produce a document with no negative
        coordinates and that has reasonable automatic padding '''

    def __init__(self):
        self._shapes = []
        self._multi_poly = []

    def add(self, shape, **kwargs):
        if hasattr(shape, 'geoms'):
            # do something reasonable if shape is a multipolygon
            for g in shape.geoms:
                self.add(g, **kwargs)
            return
        self._shapes.append((shape, kwargs))
        self._multi_poly.append(shape)

    def save(self, filename, padding=SVG_PADDING):
        # The overall bounds of the shapes helps us figure out how to translate
        # the coords to ensure that all coords are positive and fit inside the
        # svg document.
        bounds = utils.bounds_of(self._multi_poly)
        # Give some extra space for padding
        bounds = [bounds[0] - padding,
                  bounds[1] - padding,
                  bounds[2] + padding,
                  bounds[3] + padding]

        tx = -bounds[0]
        ty = -bounds[1]
        w = bounds[2] + tx
        h = bounds[3] + ty
        svg = svgwrite.Drawing(filename=filename,
                               size=(w * svgwrite.mm,
                                     h * svgwrite.mm))
        g = svg.g()

        # Specifying the dimensions on the viewbox as well as the document
        # causes the document to adopt mm as its units
        svg.viewbox(width=w, height=h)

        for shape, kwargs in self._shapes:
            shape = translate(shape, xoff=tx, yoff=ty)

            if shape.geom_type == 'Polygon':
                if len(shape.interiors):
                    # if we have interiors we have to render the shape
                    # as a path.
                    def topath(coords):
                        p = []
                        first = coords[0]
                        coords = coords[1:]
                        p.append("M %s,%s" % (first[0], first[1]))
                        for c in coords:
                            p.append("%s,%s" % (c[0], c[1]))
                        p.append("z")
                        return ' '.join(p)

                    path = topath(shape.exterior.coords)
                    for interior in shape.interiors:
                        path += topath(interior.coords)
                    g.add(svg.path(d=path, **kwargs))
                else:
                    g.add(svg.polygon(shape.exterior.coords, **kwargs))

            elif shape.geom_type == 'LineString':
                g.add(
                    svg.line(start=shape.coords[0], end=shape.coords[1], **kwargs))
            else:
                raise Exception("Unhandled geometry " + shape.wkt)

        svg.add(g)
        svg.save()
