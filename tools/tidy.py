from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import subprocess


def find_sources(dir):
    py = []
    cpp = []

    for d, dirs, files in os.walk(dir):
        for f in files:
            full = os.path.join(d, f)
            if '.git' in full:
                # Don't pull in external git repo code
                continue

            if 'src/testing/lest' in full:
                continue

            _, ext = os.path.splitext(f)

            if ext in ['.c', '.cpp', '.h', '.hpp', '.ino']:
                cpp.append(full)
            elif ext == '.py':
                py.append(full)

    return {
        'py': py,
        'cpp': cpp,
    }


def tidy_py(pys):
    # `pip install --user autopep8`
    os.environ['PATH'] += ':%s/%s' % (os.environ['HOME'],
                                      '/Library/Python/2.7/bin')
    print('autopep8', pys)
    subprocess.check_call(['autopep8', '--in-place'] + pys)


def tidy_cpp(cpp):
    print('clang-format', cpp)
    subprocess.check_call(['clang-format', '-i'] + cpp)


def tidy(dir):
    to_tidy = find_sources(dir)

    tidy_py(to_tidy['py'])
    tidy_cpp(to_tidy['cpp'])
