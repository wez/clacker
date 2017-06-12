''' This is a tiny module that helps to set the directory
    that holds the current info.py file '''

import os

Dir = None
Root = None


def set(dir):
    global Dir
    global Root

    Dir = os.path.relpath(os.path.realpath(dir), Root)
