from __future__ import absolute_import
from __future__ import print_function

import os


def mkdir_p(d):
    if not os.path.isdir(d):
        os.makedirs(d)
