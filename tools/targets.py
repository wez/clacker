''' This is a module that maps fully qualified target names
    to their instances '''

from . import projectdir
import os
import sys

Targets = {}


class Target(object):
    def __init__(self, name):
        global Targets

        self.dir = projectdir.Dir
        self.name = name
        self.full_name = '%s:%s' % (self.dir, self.name)
        Targets[self.full_name] = self

    def _normalize_srcs(self, srcs):
        res = []
        if srcs is None:
            pats = ('*.cpp', '*.c', '*.s', '*.S')
            for pat in pats:
                res += glob(os.path.join(self.dir, pat))
        else:
            for src in srcs:
                if not os.path.isabs(src):
                    src = os.path.join(self.dir, src)
                res.append(src)
        return res

    def get_deps(self):
        return None

    def _expand_deps(self, uniq=None):
        ''' expand the dependencies of this target, and toposort them.
            Returns an ordered list of the target instances '''
        global Targets

        deps = []
        if uniq is None:
            uniq = set()

        for d in self.get_deps():
            if not isinstance(d, Target):
                if d[0] == ':':
                    # name is relative to dir
                    d = self.dir + d
                if d not in Targets:
                    raise Exception(
                        '%s depends on %s, but no such target exists\n' % (
                            self.full_name, d))
                d = Targets[d]

            if d in uniq:
                # Already covered
                continue

            uniq.add(d)
            # add its deps before our own
            deps += d._expand_deps(uniq)
            deps.append(d)

        return deps
