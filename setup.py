import sys
import os 
from cx_Freeze import setup, Executable
version = "0.9.8"
# Dependencies are automatically detected, but it might need fine tuning.

def files_from_folder(folder):
    return [(folder, x) for x in os.listdir(folder)]

#include_files = files_from_folder("resources/")
#include_files.extend(files_from_folder("object_templates"))
include_files = ["resources/", "lib/mkddobjects.json", "lib/music_ids.json"]
build_exe_options = {
"packages": ["OpenGL", "numpy.core._methods", "numpy.lib.format"],
"includes": ["widgets"], 
"excludes": ["tkinter", "scipy", "PyQt5.QtWebEngine", "PyQt5.QtWebEngineCore"],
"optimize": 0,
"build_exe": "build/mkdd-track-editor-{}".format(version),
"include_files": include_files}

# GUI applications require a different base on Windows (the default is for a
# console application).
consoleBase = None
guiBase = None#"Win32GUI"
#if sys.platform == "win32":
#    base = "Win32GUI"

setup(  name = "MKDD Track Editor",
        version = version,
        description = "Track Editor for MKDD",
        options={"build_exe": build_exe_options},
        executables = [Executable("mkdd_editor.py", base=guiBase, icon="resources/icon.ico")])