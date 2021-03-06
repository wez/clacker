from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import subprocess


ignore_dirs = [
    '.git',
    'src/testing/lest',
    'pydeps',
    'outputs/',
    'pycircuit',
    'pykicad',
    'kicad-deps',
]


def is_ignored(path):
    for s in ignore_dirs:
        if s in path:
            return True
    return False


def categorize_sources(file_names):
    py = []
    cpp = []

    for full in file_names:
        _, ext = os.path.splitext(full)
        if ext in ['.c', '.cpp', '.h', '.hpp', '.ino']:
            cpp.append(full)
        elif ext == '.py':
            py.append(full)

    return {
        'py': py,
        'cpp': cpp,
    }


def find_sources(dir):
    file_names = []
    for d, dirs, files in os.walk(dir):
        for f in files:
            full = os.path.join(d, f)
            if is_ignored(full):
                continue

            file_names.append(full)

    return categorize_sources(file_names)


def changed_sources(dir):
    # Parse the output of git status and tidy only the changed files
    out = subprocess.check_output(['git', 'status', '--porcelain', '-z'],
                                  cwd=dir)
    file_names = []
    for line in out.decode('utf-8').split('\0'):
        fields = line.split(' ')
        name = fields[-1]
        file_names.append(name)

    return categorize_sources(file_names)


def tidy_py(pys):
    if pys:
        # `pip install --user autopep8`
        os.environ['PATH'] += ':%s/%s' % (os.environ['HOME'],
                                          '/Library/Python/2.7/bin')
        # print('autopep8', pys)
        subprocess.check_call(['autopep8', '--in-place'] + pys)
        print('Tidied %d python files' % len(pys))


def tidy_cpp(cpp):
    if cpp:
        # print('clang-format', cpp)
        subprocess.check_call(['clang-format', '-i'] + cpp)
        print('Tidied %d C/C++ files' % len(cpp))


def tidy(dir, all=False):
    if all:
        to_tidy = find_sources(dir)
    else:
        to_tidy = changed_sources(dir)

    tidy_py(to_tidy['py'])
    tidy_cpp(to_tidy['cpp'])
