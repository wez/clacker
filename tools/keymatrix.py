from __future__ import absolute_import
from __future__ import print_function

import math
import re
import os

from . import kle
from . import library
from . import projectdir
from . import targets
from . import filesystem

hid_labels = {
    '1': 'HID_KEYBOARD_1_AND_EXCLAMATION_POINT',
    '2': 'HID_KEYBOARD_2_AND_AT',
    '3': 'HID_KEYBOARD_3_AND_POUND',
    '4': 'HID_KEYBOARD_4_AND_DOLLAR',
    '5': 'HID_KEYBOARD_5_AND_PERCENT',
    '6': 'HID_KEYBOARD_6_AND_CARAT',
    '7': 'HID_KEYBOARD_7_AND_AMPERSAND',
    '8': 'HID_KEYBOARD_8_AND_ASTERISK',
    '9': 'HID_KEYBOARD_9_AND_LEFT_PAREN',
    '0': 'HID_KEYBOARD_0_AND_RIGHT_PAREN',
    'enter': 'HID_KEYBOARD_ENTER',
    'escape': 'HID_KEYBOARD_ESCAPE',
    'esc': 'HID_KEYBOARD_ESCAPE',
    'tab': 'HID_KEYBOARD_TAB',
    'shift': 'HID_KEYBOARD_LEFT_SHIFT',
    'ctrl': 'HID_KEYBOARD_LEFT_CONTROL',
    'space': 'HID_KEYBOARD_SPACEBAR',
    '-': 'HID_KEYBOARD_MINUS_AND_UNDERSCORE',
    '_': 'HID_KEYBOARD_MINUS_AND_UNDERSCORE',
    '=': 'HID_KEYBOARD_EQUALS_AND_PLUS',
    '+': 'HID_KEYBOARD_EQUALS_AND_PLUS',
    '[': 'HID_KEYBOARD_LEFT_BRACKET_AND_LEFT_CURLY_BRACE',
    '{': 'HID_KEYBOARD_LEFT_BRACKET_AND_LEFT_CURLY_BRACE',
    ']': 'HID_KEYBOARD_RIGHT_BRACKET_AND_RIGHT_CURLY_BRACE',
    '}': 'HID_KEYBOARD_RIGHT_BRACKET_AND_RIGHT_CURLY_BRACE',
    'bksp': 'HID_KEYBOARD_DELETE',
    'backspace': 'HID_KEYBOARD_DELETE',
    'del': 'HID_KEYBOARD_DELETE_FORWARD',
    'meta': 'HID_KEYBOARD_LEFT_ALT',
    'super': 'HID_KEYBOARD_LEFT_GUI',
    '|': 'HID_KEYBOARD_BACKSLASH_AND_PIPE',
    '\\': 'HID_KEYBOARD_BACKSLASH_AND_PIPE',
    ':': 'HID_KEYBOARD_SEMICOLON_AND_COLON',
    ';': 'HID_KEYBOARD_SEMICOLON_AND_COLON',
    '"': 'HID_KEYBOARD_QUOTE_AND_DOUBLEQUOTE',
    '\'': 'HID_KEYBOARD_QUOTE_AND_DOUBLEQUOTE',
    ',': 'HID_KEYBOARD_COMMA_AND_LESS_THAN',
    '<': 'HID_KEYBOARD_COMMA_AND_LESS_THAN',
    '.': 'HID_KEYBOARD_PERIOD_AND_GREATER_THAN',
    '>': 'HID_KEYBOARD_PERIOD_AND_GREATER_THAN',
    '?': 'HID_KEYBOARD_SLASH_AND_QUESTION_MARK',
    '/': 'HID_KEYBOARD_SLASH_AND_QUESTION_MARK',
    'copy': 'HID_KEYBOARD_COPY',
    'paste': 'HID_KEYBOARD_PASTE',
}
for x in 'abcdefghijklmnopqrstuvwxyz':
    hid_labels[x] = 'HID_KEYBOARD_%s_AND_%s' % (x.upper(), x.upper())
for n, x in enumerate(')!@#$%^&*('):
    hid_labels[x] = hid_labels[str(n)]


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

    def __init__(self, name, layout, keymap=None, rows=None, cols=None):
        super(KeyMatrix, self).__init__(name)
        assert(isinstance(layout, KeyLayout))
        self.layout = layout
        if keymap:
            assert(isinstance(keymap, KeyLayout))
            self.keymap = keymap
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

        maxCode = rows * cols
        hfile = os.path.join(outputs, '%s-matrix.h' % self.name)
        with filesystem.WriteFileIfChanged(hfile) as f:
            f.write('// %s - %s\n' % (self.name, layout.name()))
            f.write('''
#include <stdint.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#endif
#include "src/libs/keymatrix/KeyMatrix.h"
#include "src/libs/keyprocessor/HIDTables.h"
#include "src/libs/keyprocessor/KeyProcessor.h"
namespace clacker {{
using Matrix = KeyMatrix<{rows}, {cols}>;
            '''.format(rows=rows, cols=cols, maxcode=maxCode))

            if self.keymap:
                physkeys = list(layout.keys())
                keys = list(self.keymap.layout.keys())
                kmap = {}
                for physk, mkey in zip(physkeys, keys):
                    # parse the physical key label into a matrix coordinate
                    m = re.match('k([0-9a-f]+)_?([0-9a-f]+)$',
                                 physk.shortLabel())

                    def parse_num(x):
                        try:
                            return int(x)
                        except ValueError:
                            return int(x, 16)

                    label = mkey.shortLabel().lower()
                    if m:
                        r = parse_num(m.group(1))
                        c = parse_num(m.group(2))
                        rhs = hid_labels.get(label, 'HID_KEYBOARD_NO_EVENT')
                        if rhs == 'HID_KEYBOARD_NO_EVENT':
                            print('need %s' % label)
                        scancode = (r * cols) + c + 1
                        kmap[scancode] = rhs
                    else:
                        print(physk.shortLabel(), ' no match', label)

                f.write('''
const KeyEntry keyMapData[%d]
#ifdef PROGMEM
        PROGMEM
#endif
        = {\n''' % maxCode)
                for scancode in range(1, 1 + maxCode):
                    v = kmap.get(scancode, 'HID_KEYBOARD_NO_EVENT')
                    if v.startswith('HID_KEYBOARD'):
                        v = 'KeyEntry::BasicKeyEntry(%s)' % v
                    elif v.startswith('HID_CONSUMER'):
                        v = 'KeyEntry::ExtraKeyEntry(ConsumerKey, %s)' % v
                    f.write('\t%s,\n' % v)
                f.write('};\n')
            f.write('\n}\n')

        projectdir.set(outputs)
        return library.Library(name='matrix-lib')

    def get_deps(self):
        return [self._compute_lib(), 'src/libs/keyprocessor:keyprocessor']
