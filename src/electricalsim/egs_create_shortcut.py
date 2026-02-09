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
    name = 'EGS'
    if sys.platform.startswith('win'):
        icon_path = os.path.join(root_path, 'icons', 'app_icon.ico')
    else:
        icon_path = os.path.join(root_path, 'icons', 'app_icon.png')

    sct = make_shortcut(executable_path, name=name,
                        description='Electrical Grid Simulator',
                        terminal=False, icon=icon_path,
                        desktop=True, startmenu=True)
    
    # In case of Wayland session:
    session_type = os.environ.get("XDG_SESSION_TYPE")
    if session_type and session_type.lower() == "wayland":
        python_root, _ = sct.full_script.split(sep='lib')
        python_executable = os.path.join(python_root, 'bin', 'python')
        script = python_executable + ' ' + sct.full_script

        content_desktop = f"""[Desktop Entry]
Name=EGS
Type=Application
Path={sct.working_dir}
Comment=Electrical Grid Simulator
Terminal=false
StartupNotify=false
StartupWMClass=ar.utnfrsf.egs
Icon={sct.icon}
Exec={script}"""
        
        os.remove(os.path.join(sct.startmenu_dir, 'EGS.desktop'))
        desktop_file_path = os.path.join(sct.startmenu_dir, 'ar.utnfrsf.egs.desktop')
        with open(desktop_file_path, 'w') as file:
            file.write(content_desktop)

if __name__=='__main__':
    create_shortcut()
