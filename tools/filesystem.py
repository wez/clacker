from __future__ import absolute_import
from __future__ import print_function

import os
from io import StringIO


def mkdir_p(d):
    if not os.path.isdir(d):
        os.makedirs(d)


class WriteFileIfChanged(StringIO, object):
    ''' A helper for generating a source file.
        Usage is:
           with WriteFileIfChanged('filename') as f:
               f.write('blah')

        The specified filename is only updated if the contents
        are changed, which avoids rebuilding dependent code. '''

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __enter__(self):
        return self

    def close(self):
        towrite = self.getvalue()

        with open(self.filename, 'a+b') as f:
            f.seek(0)
            existing = f.read()

            if existing == towrite:
                return

            f.seek(0)
            f.truncate()
            f.write(towrite.encode('utf-8'))
            f.truncate()
