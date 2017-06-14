from __future__ import absolute_import
from __future__ import print_function

from . import targets

from glob import glob
import os


class Library(targets.Target):
    ''' A compilable code module '''

    def __init__(self, name, srcs=None, deps=None, cppflags=None, no_dot_a=False):
        super(Library, self).__init__(name)
        self.srcs = self._normalize_srcs(srcs)
        self.deps = deps or []
        self.cppflags = cppflags or []
        self.no_dot_a = no_dot_a

    def get_deps(self):
        return self.deps

    def get_srcs(self, board):
        return self.srcs

    def get_cppflags(self, board):
        return self.cppflags

    def get_scoped_cppflags(self, board):
        return []

    def get_cppflags_for_compile(self, board):
        flags = self.get_scoped_cppflags(board) + self.get_cppflags(board)

        for d in self._expand_deps():
            flags += d.get_cppflags(board)

        return flags
