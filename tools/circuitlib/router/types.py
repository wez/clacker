from __future__ import absolute_import
from __future__ import print_function

TRACK_RADIUS = 0.125
FRONT = 'F.Cu'
BACK = 'B.Cu'


class Connectable(object):
    ''' Common properties for nodes that can be connected '''
    shape = None
    movable = True

    def is_on_layer(self, layername):
        return False


class ThruHole(Connectable):
    ''' A pad that is present on both layers '''
    movable = False

    def __init__(self, pin):
        self.shape = pin.component.pad(pin.num)
        self.layers = [FRONT, BACK]

    def is_on_layer(self, layer):
        return True

    def __str__(self):
        return 'ThruHole at %r' % (
            tuple(self.shape.centroid.coords))


class SmdPad(Connectable):
    ''' A pad that is present on a single layer '''
    movable = False

    def __init__(self, pin, pad):
        self.shape = pin.component.pad(pin.num)
        self.layers = [FRONT if FRONT in pad.layers else BACK]

    def is_on_layer(self, layer):
        return self.layers[0] == layer

    def __str__(self):
        return 'SmdPad on %s at %r' % (
            self.layers[0],
            tuple(self.shape.centroid.coords))


class Branch(Connectable):
    ''' A point on a layer that connects to multiple points.
        There is no pad associated with it '''

    def __init__(self, shape, layer=None, proxy_for=None):
        self.shape = shape.centroid.buffer(TRACK_RADIUS)
        self.proxy_for = proxy_for
        if layer:
            self.layers = [layer]
        else:
            self.layers = [FRONT, BACK]

    def is_on_layer(self, layer):
        if len(self.layers) == 2:
            return True
        return self.layers[0] == layer

    def __str__(self):
        if self.proxy_for:
            return 'Branch, proxy for %s' % str(self.proxy_for)
        return 'Branch on %s at %r' % (
            self.layers,
            tuple(self.shape.centroid.coords))


class Via(Connectable):
    ''' A via hole that connects two layers.  Basically a tiny
        ThruHole Connectable '''

    def __init__(self):
        self.layers = [FRONT, BACK]

    def is_on_layer(self, layer):
        return True

    def __str__(self):
        return 'Via at %r' % (
            tuple(self.shape.centroid.coords))


class Segment(object):
    ''' A path segment that joins a pair of connectables '''

    def __init__(self, shape, a, b):
        self.shape = shape
        self.a = a
        self.b = b

    def __str__(self):
        return 'Segment from %s -> %s' % (
            self.a,
            self.b)


class TwoNet(object):
    ''' A TwoNet is a net consisting of a unique pair of Connectables.
        We use this as the basic routable unit '''

    def __init__(self, net, a, b):
        self.net = net
        self.a = a
        self.b = b


class Obstacle(object):
    ''' Something that prevents routing '''
    shape = None

    def __init__(self, layer, shape, value):
        self.layer = layer
        self.shape = shape
        self.value = value

    def is_on_layer(self, layer):
        return self.layer == layer
