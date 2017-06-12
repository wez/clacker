from __future__ import absolute_import
from __future__ import print_function

from . import targets

from glob import glob
import os


class Library(targets.Target):
    ''' A compilable code module '''

    def __init__(self, name, srcs=None, deps=None, cppflags=None):
        super(Library, self).__init__(name)
        self.srcs = self._normalize_srcs(srcs)
        self.deps = deps or []
        self.cppflags = cppflags

    def get_deps(self):
        return self.deps
