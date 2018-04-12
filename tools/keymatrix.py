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
    'alt': 'HID_KEYBOARD_LEFT_ALT',
    'super': 'HID_KEYBOARD_LEFT_GUI',
    'gui': 'HID_KEYBOARD_LEFT_GUI',
    'windows': 'HID_KEYBOARD_LEFT_GUI',
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
    'hyper': 'KeyEntry::BasicKeyEntry(HID_KEYBOARD_NO_EVENT, Hyper)',
    'f1': 'HID_KEYBOARD_F1',
    'f2': 'HID_KEYBOARD_F2',
    'f3': 'HID_KEYBOARD_F3',
    'f4': 'HID_KEYBOARD_F4',
    'f5': 'HID_KEYBOARD_F5',
    'f6': 'HID_KEYBOARD_F6',
    'f7': 'HID_KEYBOARD_F7',
    'f8': 'HID_KEYBOARD_F8',
    'f9': 'HID_KEYBOARD_F9',
    'f10': 'HID_KEYBOARD_F10',
    'f11': 'HID_KEYBOARD_F11',
    'f12': 'HID_KEYBOARD_F12',
    'f13': 'HID_KEYBOARD_F13',
    'f14': 'HID_KEYBOARD_F14',
    'f15': 'HID_KEYBOARD_F15',
    'f16': 'HID_KEYBOARD_F16',
    'f17': 'HID_KEYBOARD_F17',
    'f18': 'HID_KEYBOARD_F18',
    'f19': 'HID_KEYBOARD_F19',
    'f20': 'HID_KEYBOARD_F20',
    'f21': 'HID_KEYBOARD_F21',
    'f22': 'HID_KEYBOARD_F22',
    'f23': 'HID_KEYBOARD_F23',
    'f24': 'HID_KEYBOARD_F24',
    'end': 'HID_KEYBOARD_END',
    'home': 'HID_KEYBOARD_HOME',
    'pgdn': 'HID_KEYBOARD_PAGE_DOWN',
    'pgup': 'HID_KEYBOARD_PAGE_UP',
    'vol-': 'HID_KEYBOARD_VOLUME_DOWN',
    'vol+': 'HID_KEYBOARD_VOLUME_UP',
    'up': 'HID_KEYBOARD_UP_ARROW',
    'down': 'HID_KEYBOARD_DOWN_ARROW',
    'left': 'HID_KEYBOARD_LEFT_ARROW',
    'right': 'HID_KEYBOARD_RIGHT_ARROW',
    '`': 'HID_KEYBOARD_GRAVE_ACCENT_AND_TILDE',
    'play': 'HID_CONSUMER_PLAY_SLASH_PAUSE',
    'track+': 'HID_CONSUMER_SCAN_NEXT_TRACK',
    'track-': 'HID_CONSUMER_SCAN_PREVIOUS_TRACK',
    'l1': 'KeyEntry::LayerKeyEntry(1)',
    'l2': 'KeyEntry::LayerKeyEntry(2)',
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

    def __init__(self, layout_filename=None, mirror_layout=None):
        self._mirror_layout = mirror_layout
        if layout_filename:
            self.layout_filename = os.path.join(projectdir.Dir, layout_filename)
        self._layout = None

    @property
    def layout(self):
        if self._layout is None:
            if self._mirror_layout:
                self._layout = self._mirror_layout.layout.mirror()
            else:
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

    def _parseLabel(self, label):
        llabel = label.lower()
        v = hid_labels.get(llabel)
        if v:
            if v.startswith('HID_KEYBOARD'):
                return 'KeyEntry::BasicKeyEntry(%s)' % v
            elif v.startswith('HID_CONSUMER'):
                return 'KeyEntry::ExtraKeyEntry(ConsumerKey, %s)' % v
            return v

        m = re.match('(.+)/(.+)$', label)
        if m:
            # Dual Role key
            k = hid_labels[m.group(1).lower()]
            mods = {
                'ctrl': 'LeftControl',
                'alt': 'LeftAlt',
                'shift': 'LeftShift',
                'gui': 'LeftGui',
                'hyper': 'Hyper'
            }
            return 'KeyEntry::DualRoleKeyEntry(%s, %s)' % (k, mods[m.group(2).lower()])

        m = re.match('M(\d+)$', label)
        if m:
            # Macro
            return 'KeyEntry::MacroKeyEntry(%s)' % m.group(1)

        print('No mapping for ', label)
        return None

    def _computeKeyMap(self, rows, cols):
        ''' Make a pass through the keys and generate the keymap.
            The middle legend is the key assignment on the base layer.
            The front-left legend is the L1 assignment
            The front-right legend is the L2 assignment. '''
        maxCode = rows * cols

        physkeys = self.layout.layout.keys()
        keys = self.keymap.layout.keys()

        # indices in the labels array for the layer positions
        L0 = 0  # center
        L1 = 4  # front left
        L2 = 5  # front right
        allowed_layers = [L0, L1, L2]
        byLayer = {}

        def getLayer(n):
            if n not in byLayer:
                byLayer[n] = [None] * maxCode
            return byLayer[n]

        # Iterate both maps at the same time; we don't yet know anything
        # about the physical or logical layouts, but we know that the two
        # layouts have to match.  Since the layout parser yields the keys
        # in a deterministic order, and the layout editor saves the data
        # file with a deterministic order, the same layout in the editor
        # will yield the same ordering for the keys when we zip them
        # together in this loop.  We use this property to associate the
        # kXX labels from the layer assignment data file.  The kXX labels
        # are a hint to this code about the row/col number of a given
        # key position in the scanned matrix.
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

                for layer, idx in enumerate(allowed_layers):
                    if idx >= len(mkey.labels):
                        continue
                    label = mkey.labels[idx]
                    if len(label) > 0:
                        # print(layer, r, c, label)
                        scancode = (r * cols) + c + 1
                        getLayer(layer)[scancode - 1] = self._parseLabel(label)

        return byLayer

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
                layers = self._computeKeyMap(rows, cols)

                f.write('''
const KeyEntry keyMapData[%d * %d]
#ifdef PROGMEM
        PROGMEM
#endif
        = {\n''' % (len(layers), maxCode))
                for layer in sorted(layers.keys()):
                    kmap = layers[layer]
                    f.write('  // Layer %d\n' % layer)
                    for entry in kmap:
                        f.write('  %s,\n' %
                                (entry or 'KeyEntry::BasicKeyEntry(0)'))
                f.write('};\n')
            f.write('\n}\n')

        projectdir.set(outputs)
        return library.Library(name='matrix-lib')

    def get_deps(self):
        return [self._compute_lib(), 'src/libs/keyprocessor:keyprocessor']
