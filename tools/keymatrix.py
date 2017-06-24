from __future__ import absolute_import
from __future__ import print_function

import math
import os

from . import kle
from . import library
from . import projectdir
from . import targets
from . import filesystem


class KeyLayout(object):
    ''' Wraps a keyboard-layout-editor.com layout definition
        This is so that we can defer parsing the layout until
        we need to build the associated board.
    '''

    def __init__(self, layout):
        self.layout_filename = os.path.join(projectdir.Dir, layout)
        self._layout = None

    @property
    def layout(self):
        if self._layout is None:
            self._layout = kle.Layout(self.layout_filename)
        return self._layout


class KeyMatrix(targets.Target):
    ''' Compute information about a keyboard matrix

        Given a keyboard-layout-editor.com json definition,
        compute some properties for use by the firmware:

        Logical matrix dimensions (rows x cols)
        Physical switch <-> logical matrix mapping

    '''

    def __init__(self, name, layout, rows=None, cols=None):
        super(KeyMatrix, self).__init__(name)
        assert(isinstance(layout, KeyLayout))
        self.layout = layout
        self.lib = None
        self.rows = rows
        self.cols = cols

    def _compute_lib(self):
        if self.lib:
            return self.lib

        layout = self.layout.layout

        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        filesystem.mkdir_p(outputs)

        rows = self.rows
        cols = self.cols

        if (rows is None) or (cols is None):
            # TODO: this is where we'd want to do something like optionally
            # computing the minimum matrix.  For the moment we just do a dumb
            # thing to get the matrix dimensions
            rows = 0
            cols = 0
            for key in layout.keys():
                rows = max(rows, int(math.ceil(key.y)))
                cols = max(cols, int(math.ceil(key.x)))

        hfile = os.path.join(outputs, '%s-matrix.h' % self.name)
        with open(hfile, 'w') as f:
            f.write('// %s - %s\n' % (self.name, layout.name()))
            f.write('''
#include "src/libs/keymatrix/KeyMatrix.h"
namespace clacker {{
using Matrix = KeyMatrix<{rows}, {cols}>;
}}
            '''.format(rows=rows, cols=cols))

        projectdir.set(outputs)
        return library.Library(name='matrix-lib')

    def get_deps(self):
        return [self._compute_lib()]
