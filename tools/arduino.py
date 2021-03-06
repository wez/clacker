from __future__ import absolute_import
from __future__ import print_function

import glob
import re
import os
import subprocess


def find_arduino_exe():
    ''' Find the arduino executable '''

    candidates = [
        '/Applications/Arduino.app/Contents/MacOS/Arduino', 'arduino', 'self.exe']
    candidates += glob.glob(os.path.join(os.environ['HOME'], 'Downloads') + '/arduino*/arduino')
    path = os.environ['PATH'].split(os.pathsep)

    for c in candidates:
        if not os.path.isabs(c):
            for p in path:
                f = os.path.join(p, c)
                if os.path.isfile(f):
                    return f
        elif os.path.isfile(c):
            return c

    return None


class Arduino(object):
    ''' Locates the arduino tools and parses its prefs '''

    def __init__(self):
        self.arduino = find_arduino_exe()

        for pattern in ['Arduino', 'Library/Arduino*', '.arduino15']:
            for path in glob.glob(os.path.join(os.environ['HOME'], pattern)):
                if os.path.exists(path):
                    self.home_arduino = path
                    break

        if not self.home_arduino:
            raise Exception("did not find arduino!")
        self.prefs = self.load_prefs()

    def load_prefs(self):
        prefs = os.path.join('outputs', 'arduinoprefs.txt')
        if not os.path.isfile(prefs):
            if not os.path.isdir('outputs'):
                os.mkdir('outputs')

            with open(prefs, 'w') as f:
                subprocess.check_call([self.arduino, '--get-pref'], stdout=f)

        result = {}
        with open(prefs, 'r') as f:
            for line in f:
                cols = line.rstrip('\n').split("=", 1)
                if len(cols) == 2:
                    result[cols[0]] = cols[1]
        return result

    def board_prefs(self, fqbn):
        ''' Given a FQBN, load the builder prefs.  This provides information
            needed to figure out how to compile and flash a project to the
            device '''

        packages = os.path.join(self.home_arduino, 'packages')
        if not os.path.isdir(packages):
            packages = None

        cmd = [
            os.path.join(self.prefs['runtime.ide.path'], 'arduino-builder'),
            '-dump-prefs',
            '-hardware', os.path.join(
                self.prefs['runtime.ide.path'], 'hardware'),
        ]

        if packages:
            cmd += ['-hardware', packages]

        cmd += [
            '-tools', os.path.join(self.prefs['runtime.ide.path'],
                                   'tools-builder'),
            '-tools', os.path.join(self.prefs['runtime.ide.path'],
                                   'hardware', 'tools', 'avr'),
            ]

        if packages:
            cmd += ['-tools', packages]

        cmd += [
            '-fqbn', fqbn,
            '-built-in-libraries', os.path.join(
                self.prefs['runtime.ide.path'], 'libraries'),
            '-ide-version', self.prefs['runtime.ide.version'],
            '-warnings', 'all',
        ]

        for k, v in self.prefs.items():
            if k.startswith('runtime.tools.'):
                cmd.append('-prefs=%s=%s' % (k, v))

        out = subprocess.check_output(cmd)
        prefs = {}
        for line in out.splitlines():
            cols = line.decode('utf-8').split("=", 1)
            if len(cols) == 2:
                prefs[cols[0]] = cols[1]
        return prefs

    def resolve_pref(self, key, prefs=None):
        ''' Evaluate a pref value, expanding interpolated keys '''

        prefs = prefs or self.prefs
        value = prefs[key]
        r = re.compile('\\{([a-zA-Z0-9_._+-]+)\\}')

        path = []
        for ele in key.split('.'):
            if path:
                path.append('%s.%s' % (path[-1], ele))
            else:
                path.append(ele)

        while True:
            before = value

            m = r.search(value)
            if not m:
                return value

            key = m.group(1)
            if key not in prefs:
                # search configuration path
                key = None
                for ele in path:
                    k = '%s.%s' % (ele, m.group(1))
                    if k in prefs:
                        key = k
                        break
                if not key:
                    import pprint
                    pprint.pprint(prefs)
                    raise Exception(
                        'could not resolve prefs from %s (key %s)' % (value, m.group(1)))

            value = value.replace(m.group(0), prefs[key])

            if value == before:
                break
        return value


def clear_prefs():
    prefs = os.path.join('outputs', 'arduinoprefs.txt')
    try:
        os.unlink(prefs)
    except:
        pass


arduino = None


def get():
    global arduino
    if not arduino:
        arduino = Arduino()
    return arduino
