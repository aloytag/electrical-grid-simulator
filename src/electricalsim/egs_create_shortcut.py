#!/usr/bin/env python3
# -*- coding: utf-8 -*

import os
import sys

from pyshortcuts import make_shortcut
import electricalsim


def create_shortcut():
    """
    Creates a shortcut for the Electrical Grid Simulator
    on the desktop and startmanu.
    """
    root_path, _ = os.path.split(electricalsim.__file__)
    executable_path = os.path.join(root_path, 'egs_run.py')

    if sys.platform.startswith('win'):
        icon_path = os.path.join(root_path, 'icons', 'app_icon.ico')
    else:
        icon_path = os.path.join(root_path, 'icons', 'app_icon.png')

    make_shortcut(executable_path, name='EGS',
                description='Electrical Grid Simulator',
                terminal=False, icon=icon_path,
                desktop=True, startmenu=True)
    

if __name__=='__main__':
    create_shortcut()
