import glob
import os
import re
import shutil

from cx_Freeze import setup, Executable


# To avoid importing the module, simply parse the file to find the version variable in it.
with open('bw_editor.py', 'r', encoding='utf-8') as f:
    data = f.read()
for line in data.splitlines():
    if '__version__' in line:
        version = re.search(r"'(.+)'", line).group(1)
        break
else:
    raise RuntimeError('Unable to parse product version.')


# Dependencies are automatically detected, but it might need fine tuning.

include_files = [
    "objecthelp",
    "resources/",
    ("plugins", "lib/plugins"),
    ("lib/fieldnames.txt", "lib/fieldnames.txt"),
    ("lib/fieldnamesbw2.txt", "lib/fieldnamesbw2.txt"),
    ("lib/color_coding.json", "lib/color_coding.json"),
    ("lib/values.txt", "lib/values.txt"),
    ("lib/valuesbw2.txt", "lib/valuesbw2.txt"),
]

build_dirpath = 'build'
bundle_dirname = f'battalion-level-editor-{version}'
bundle_dirpath = os.path.join(build_dirpath, bundle_dirname)

build_exe_options = {
    "packages": ["PyQt6", "OpenGL", "numpy", "numpy.lib.format", "PIL", "tkinter"],
    "includes": ["widgets"],
    "excludes": ["PyQt6.QtWebEngine", "PyQt6.QtWebEngineCore"],
    "optimize": 0,
    "build_exe": bundle_dirpath,
    "include_files": include_files
}

# GUI applications require a different base on Windows (the default is for a
# console application).
consoleBase = None
guiBase = None  #"Win32GUI"
#if sys.platform == "win32":
#    base = "Win32GUI"

setup(name="Battalion Level Editor",
      version=version,
      description="Level Editor for BW/BW2",
      options={"build_exe": build_exe_options},
      executables=[Executable("bw_editor.py", base=guiBase, icon="resources/icon.ico")])

os.mkdir(os.path.join(bundle_dirpath, 'lib', 'temp'))
os.remove(os.path.join(bundle_dirpath, 'frozen_application_license.txt'))
"""
# Qt will be trimmed to reduce the size of the bundle.
relative_pyqt_dir = os.path.join('lib', 'PyQt6')
pyqt_dir = os.path.join(bundle_dirpath, relative_pyqt_dir)
unwelcome_files = [
    'examples'

]
"""   
# 'include',
#    'qml',
#    'resources',
#    'scripts',
#    'support',
#    'translations',
#    'typesystems',
"""

for plugin in os.listdir(os.path.join(pyqt_dir, 'Qt6', 'plugins')):
    if plugin not in ('platforms', 'imageformats'):
        unwelcome_files.append(os.path.join('Qt6', 'plugins', plugin))
for glob_pattern in (
        '*.exe',
        '*3D*',
        '*Bluetooth*',
        '*Body*',
        '*Bus*',
        '*Charts*',
        '*Compat*',
        '*compiler*',
        '*Concurrent*',
        '*Container*',
        '*Designer*',
        '*Help*',
        '*HttpServer*',
        '*JsonRpc*',
        '*Keyboard*',
        '*Labs*',
        '*Language*',
        '*Location*',
        '*Multimedia*',
        '*Network*',
        '*Nfc*',
        '*Pdf*',
        '*Positioning*',
        '*Print*',
        '*Qml*',
        '*Quick*',
        '*Remote*',
        '*Scxml*',
        '*Sensors*',
        '*Serial*',
        '*Shader*',
        '*SpatialAudio*',
        '*Sql*',
        '*StateMachine*',
        '*SvgWidgets*',
        '*Test*',
        '*TextToSpeech*',
        '*Tools*',
        '*Visualization*',
        '*Web*',
        '*Xml*',
        'plugins/imageformats/*Pdf*',
):
    for filename in glob.glob(glob_pattern, root_dir=pyqt_dir):
        unwelcome_files.append(filename)

for relative_path in sorted(tuple(set(unwelcome_files))):
    path = os.path.join(pyqt_dir, relative_path)

    print(f'Remove: "{path}"')
    if not os.path.exists(path) and "\\examples" in path:
        continue
    assert os.path.exists(path)
    if os.path.isfile(path):
        os.remove(path)
    else:
        shutil.rmtree(path)
"""


"""
# Create the ZIP archive.
current_dirpath = os.getcwd()
os.chdir(build_dirpath)
try:
    print('Creating ZIP archive...')
    shutil.make_archive(bundle_dirname, 'zip', '.', bundle_dirname)
finally:
    os.chdir(current_dirpath)"""
