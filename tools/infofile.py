from __future__ import absolute_import
from __future__ import print_function
import os
import string

from . import (
    board,
    firmware,
    keymatrix,
    library,
    pcb,
    projectdir,
    test
)


def load_info_files(dir):
    ''' evaluate the info files that exist under the specified dir '''
    for infodir, _, files in os.walk(dir):
        if 'info.py' in files:
            load_info_file(os.path.join(infodir, 'info.py'))


def load_info_file(filename):
    projectdir.set(os.path.dirname(filename))
    with open(filename, 'r') as f:
        code = compile(f.read(), filename, 'exec')
        g = {}

        def export(module, g):
            ''' Export globals into g '''
            for k in dir(module):
                if k[0] in string.ascii_uppercase:
                    g[k] = getattr(module, k)

        export(firmware, g)
        export(keymatrix, g)
        export(library, g)
        export(board, g)
        export(test, g)
        export(pcb, g)

        eval(code, g)
