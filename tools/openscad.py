from . import filesystem


class Action(object):
    def render(self):
        pass

    def __str__(self):
        return self.render()

    def disable(self):
        return Modifier('*', self)

    def showOnly(self):
        return Modifier('!', self)

    def debug(self):
        return Modifier('#', self)

    def transparent(self):
        return Modifier('%', self)

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

    def mirror(self, vector):
        return Operator('mirror', [self], v=vector)

    def scale(self, vector):
        return Operator('scale', [self], v=vector)

    def color(self, color):
        return Operator('color', [self], _=color)

    def up(self, amount):
        return self.translate([0, 0, amount])

    def down(self, amount):
        return self.translate([0, 0, -amount])

    def left(self, amount):
        return self.translate([-amount, 0, 0])

    def right(self, amount):
        return self.translate([amount, 0, 0])

    def forward(self, amount):
        return self.translate([0, amount, 0])

    def back(self, amount):
        return self.translate([0, -amount, 0])

    def __add__(self, other):
        return self.union(other)

    def __radd__(self, other):
        return self.union(other)

    def __sub__(self, other):
        return self.difference(other)

    def __mul__(self, other):
        return self.intersection(other)

    def quarter(self, x, y, z, offset, x_cut_delta=0, y_cut_delta=0):
        return Operator('quarter', [self],
                x=x,
                y=y,
                z=z,
                offset=offset,
                x_cut_delta=x_cut_delta,
                y_cut_delta=y_cut_delta)


def is_iterable(item):
    try:
        iter(item)
        return True
    except TypeError:
        return False


def scad_repr(val):
    if isinstance(val, str):
        return '"' + val + '"'
    return repr(val)


def pretty_pairs(pairs):
    ''' a poor-mans pretty printer for openscad '''
    pretty = []
    for item in pairs:
        if is_iterable(item) and len(item) > 3:
            pretty.append(pretty_pairs(item))
        else:
            pretty.append(scad_repr(item))
    return "[\n  " + ",\n  ".join(pretty) + "\n  ]"


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

        return 'polygon(%s, %s);\n' % (pretty_pairs(points), pretty_pairs(paths))


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


class Modifier(Action):
    def __init__(self, mod, child):
        self._mod = mod
        self._child = child

    def render(self):
        return self._mod + self._child.render()


class Operator(Action):
    def __init__(self, name, actions, **kwargs):
        self._name = name
        self._actions = actions
        self._kwargs = kwargs

    def render(self):
        params = []
        if self._kwargs:
            for k, v in self._kwargs.items():
                if k == '_':
                    params.append(scad_repr(v))
                else:
                    params.append('%s=%s' % (k, scad_repr(v)))
        params = ', '.join(params)
        lines = ['%s(%s) {' % (self._name, params)]
        for act in self._actions:
            if isinstance(act, Action):
                lines.append(act.render())
            else:
                raise Exception('%r is not an Action' % act)
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


helper_modules = """
module quarter(x, y, z, y_cut_delta=0, x_cut_delta=0, offset=[0,0,0]) {
    tongue_size = 2.8;
    displacement = 12;
    // tolerance on the groove side
    kerf = 0.25;

    y_cut = (y / 2) + y_cut_delta;
    x_cut = (x / 2) + x_cut_delta;
    total_z = z * 2;

    module cutout(kerf=0) {
        rotate([90, 0, 0])
        cylinder(h=kerf + max(y + abs(y_cut_delta),
                              x + abs(x_cut_delta))/2,
                 r=tongue_size, $fn=4);
    }

    module tongue() {
        cutout();
    }

    module groove() {
        cutout(kerf);
    }

    module top_left_quadrant() {
        cube([x_cut, y_cut, total_z]);
    }

    module offset_top_right() {
        translate([x_cut, 0, 0]) children();
    }

    module top_right_quadrant() {
        offset_top_right()
        cube([x - x_cut, y_cut, total_z]);
    }

    module offset_bottom_left() {
        translate([0, y_cut, 0]) children();
    }

    module bottom_left_quadrant() {
        offset_bottom_left()
        cube([x_cut, y - y_cut, total_z]);
    }

    module offset_bottom_right() {
        translate([x_cut, y_cut, 0]) children();
    }

    module bottom_right_quadrant() {
        offset_bottom_right()
        cube([x - x_cut, y - y_cut, total_z]);
    }

    module offset_top_left_lr() {
      offset_top_right()
      translate([0, y_cut, z/2])
      children();
    }

    module offset_bottom_left_lr() {
      offset_bottom_left()
      translate([x - x_cut, y - y_cut, z/2])
      children();
    }

    module offset_top_left_ud() {
      translate([0, y_cut, z/2])
      rotate([0, 0, 90])
      children();
    }

    module offset_top_right_ud() {
      offset_bottom_right()
      translate([0, 0, z/2])
      rotate([0, 0, 90])
      children();
    }

    // top left quadrant
    translate([-displacement, -displacement, 0]) {
      intersection() {
        translate(offset) {
          difference() {
            union() {
              top_left_quadrant();
              // RHS tongue
              intersection() {
                top_right_quadrant();
                offset_top_left_lr() tongue();
              }
            }
            // bottom groove
            offset_top_left_ud() groove();
          }
        }
        children(0);
      }
    }

    // top right quadrant
    translate([displacement, -displacement, 0]) {
      intersection() {
        translate(offset) {
          difference() {
            union() {
              top_right_quadrant();
              // bottom tongue
              intersection() {
                bottom_right_quadrant();
                offset_top_right_ud() tongue();
              }
            }
            // LHS groove
            offset_top_left_lr() groove();
          }
        }
        children(0);
      }
    }

    // bottom right quadrant
    translate([displacement, displacement, 0]) {
      intersection() {
        translate(offset) {
          difference() {
            union() {
              bottom_right_quadrant();
              // LHS tongue
              intersection() {
                bottom_left_quadrant();
                offset_bottom_left_lr() tongue();
              }
            }
            // top groove
            offset_top_right_ud() groove();
          }
        }
        children(0);
      }
    }

    // bottom left quadrant
    translate([-displacement, displacement, 0]) {
      intersection() {
        translate(offset) {
          difference() {
            union() {
              bottom_left_quadrant();
              // top tongue
              intersection() {
                top_left_quadrant();
                offset_top_left_ud() tongue();
              }
            }
            // RHS groove
            offset_bottom_left_lr() groove();
          }
        }
        children(0);
      }
    }
}

"""

class Script(object):
    def __init__(self):
        self._modules = []
        self._actions = []

    def save(self, filename):
        with filesystem.WriteFileIfChanged(filename) as f:
            f.write(helper_modules)

            for mod in self._modules:
                f.write(mod.render())

            # Our shapes have [0,0] as the top left, but openscad
            # has it as bottom left, so we need to adjust for that
            f.write('mirror([0, 1, 0]) {\n')
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
