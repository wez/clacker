from . import filesystem


class Action(object):
    def render(self):
        pass

    def __str__(self):
        return self.render()

    def union(self, other):
        return Operator('union', [self, other])

    def intersection(self, other):
        return Operator('intersection', [self, other])

    def difference(self, other):
        return Operator('difference', [self, other])

    def linearExtrude(self, height):
        return Operator('linear_extrude', [self], height=height)

    def translate(self, vector):
        return Operator('translate', [self], v=vector)


class Polygon(Action):
    def __init__(self, shape):
        assert shape.geom_type == 'Polygon' or shape.geom_type == 'MultiPolygon'
        self._shape = shape

    def render(self):
        points = []
        paths = []

        def add_path(paths, points, coords):
            p = []
            idx = len(points)
            for pt in coords:
                points.append(list(pt))
                p.append(idx)
                idx += 1
            paths.append(p)

        add_path(paths, points, self._shape.exterior.coords)
        for interior in self._shape.interiors:
            add_path(paths, points, interior.coords)

        return 'polygon(%r, %r);\n' % (points, paths)


def Shape(shape):
    if hasattr(shape, 'geoms'):
        action = None
        for g in shape.geoms:
            s = Shape(g)
            if action:
                action = action.union(s)
            else:
                action = s

        return action

    if shape.geom_type == 'Polygon':
        return Polygon(shape)

    raise Exception("unhandled geom: %s" % shape.geom_type)


class Operator(Action):
    def __init__(self, name, actions, **kwargs):
        self._name = name
        self._actions = actions
        self._kwargs = kwargs

    def render(self):
        params = []
        if self._kwargs:
            for k, v in self._kwargs.items():
                params.append('%s=%r' % (k, v))
        params = ', '.join(params)
        lines = ['%s(%s) {' % (self._name, params)]
        for act in self._actions:
            lines.append(act.render())
        lines.append('}')
        return '\n'.join(lines)


class Module(Action):
    def __init__(self, name):
        self._name = name
        self._actions = []

    def add(self, action):
        assert isinstance(action, Action)
        self._actions.append(action)

    def render(self):
        lines = ['module %s() {']
        for act in self._actions:
            lines.append(act.render())
        lines.append('}')
        return '\n'.join(lines)


class Script(object):
    def __init__(self):
        self._modules = []
        self._actions = []

    def save(self, filename):
        with filesystem.WriteFileIfChanged(filename) as f:
            for mod in self._modules:
                f.write(mod.render())

            # Our shapes have [0,0] as the top left, but openscad
            # has it as bottom left, so we need to adjust for that
            f.write('mirror([0, 1, 0]) color("grey") {\n')
            for act in self._actions:
                f.write(act.render())
            f.write('}\n')

    def add(self, thing):
        if isinstance(thing, Module):
            self._modules.append(thing)
            return

        if isinstance(thing, Action):
            self._actions.append(thing)
            return

        raise Exception('unsupported type')
