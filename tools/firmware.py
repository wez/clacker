from __future__ import absolute_import
from __future__ import print_function

import os
import re

from . import targets
from . import board
from . import library
from . import projectdir
from . import filesystem


class Linkable(targets.Target):
    ''' Base class for building an executable target '''

    def __init__(self, name, board=None, srcs=None, deps=None, cppflags=None,
                 pid=0x6000,
                 vid=0xfeed,
                 product=None,
                 manufacturer='Anon'):
        super(Linkable, self).__init__(name)
        self.board = board
        # We're going to add these cppflags to everything that we build
        self.cppflags = cppflags or []

        product = product or name

        self.cppflags += [
            '-DCLACKER_USB_PID=%s' % pid,
            '-DCLACKER_USB_VID=%s' % vid,
            "'-DCLACKER_USB_PRODUCT=\"%s\"'" % product,
            "'-DCLACKER_USB_PRODUCT_UNICODE=L\"%s\"'" % product,
            "'-DCLACKER_USB_MANUFACTURER=\"%s\"'" % manufacturer,
            "'-DCLACKER_USB_MANUFACTURER_UNICODE=L\"%s\"'" % manufacturer,
        ]

        self.lib = library.Library('%s-lib' % name,
                                   srcs=srcs,
                                   deps=deps,
                                   no_dot_a=True)

    def get_deps(self):
        return [self.lib]

    def _build_library(self, lib, outputs):
        # print('Build library %s' % lib.full_name)

        def check_depfile(objfile, depfile, srcfile, ext):
            ''' reads a makefile compatible dependency file.
                Returns True if the object needs to be compiled,
                False if it is up to date. '''
            try:
                obj_stat = os.lstat(objfile)
            except:
                # doesn't exist, so compile it
                # print('%s not present' % depfile)
                return True

            if not os.path.exists(depfile):
                # do a basic mtime check
                src_stat = os.lstat(srcfile)
                return src_stat.st_mtime > obj_stat.st_mtime

            with open(depfile, 'r') as f:
                blob = f.read()
                blob = blob.replace('\\', ' ')
                blob = re.sub(r'\s+', ' ', blob)
                lines = blob.strip().split(' ')
                # The first line is our own object, the rest are the deps
                for dep in lines[1:]:
                    try:
                        dep_stat = os.lstat(dep)
                        if dep_stat.st_mtime > obj_stat.st_mtime:
                            # It changed more recently, so recompile
                            # print('%s newer than %s' % (dep, objfile))
                            return True
                    except Exception as e:
                        # It doesn't exist, so recompile
                        # print('failed to stat %s: %s. depfile is %s' % (dep, str(e), depfile))
                        return True

            # Up to date!
            return False

        srcs = lib.get_srcs(self.board)
        objs = []

        libname = os.path.join(outputs, lib.full_name.replace(':', '/')) + '.a'
        filesystem.mkdir_p(os.path.dirname(libname))
        # print('Should make lib %s' % libname)

        for s in srcs:
            name, ext = os.path.splitext(s)
            if os.path.isabs(name):
                name = name[1:]

            ofile = os.path.join(outputs, '%s.o' % name)
            depfile = os.path.join(outputs, '%s.d' % name)

            filesystem.mkdir_p(os.path.dirname(ofile))

            if check_depfile(ofile, depfile, s, ext):
                print(' COMPILE %s from %s' % (os.path.relpath(ofile), s))

                cppflags = ' '.join(
                    self.cppflags + lib.get_cppflags_for_compile(self.board) + ['-I%s' % projectdir.Root])

                self.board.compile_src(s, ofile, depfile, cppflags)

            objs.append(ofile)

        if not objs or lib.no_dot_a:
            # Nothing to link; header only library
            return objs

        need_link = False
        try:
            lib_stat = os.lstat(libname)
            for o in objs:
                obj_stat = os.lstat(o)
                if obj_stat.st_mtime > lib_stat.st_mtime:
                    need_link = True
                    break

        except:
            need_link = True

        if need_link:
            self.board.link_lib(libname, objs)

        return [libname]

    def build(self):
        print('Build %s' % self.full_name)

        # Compute outputs dir
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        filesystem.mkdir_p(outputs)

        deps = self._expand_deps() + self.board.injected_deps()

        objs = []
        libs = []
        for d in deps:
            if not isinstance(d, library.Library):
                #  print('* Nothing to build for %s' % d.full_name)
                continue

            for obj in self._build_library(d, outputs):
                _, ext = os.path.splitext(obj)
                if ext == '.a':
                    libs.insert(0, obj)
                else:
                    objs.append(obj)

        exe = os.path.join(outputs, '%s.elf' % self.name)
        self.board.link_exe(exe, objs + libs)

        hex = os.path.join(outputs, '%s.hex' % self.name)
        self.board.exe_to_hex(exe, hex)


class Firmware(Linkable):
    ''' Compile code into a firmware image '''

    def upload(self, port=None):
        outputs = os.path.realpath(
            os.path.join(
                'outputs',
                self.full_name.replace(':', '/')))
        hex = os.path.join(outputs, '%s.hex' % self.name)
        self.board.upload(hex, port=port)
