import os
import time
import shutil
import random
from PIL import Image

from lib.BattalionXMLLib import BattalionFilePaths

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
from widgets.editor_widgets import open_error_dialog
from widgets.menu.file_menu import PF2
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


def open_yesno_box(mainmsg, sidemsg):
    msgbox = QtWidgets.QMessageBox()
    msgbox.setText(
        mainmsg)
    msgbox.setInformativeText(sidemsg)
    msgbox.setStandardButtons(
        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
    msgbox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
    msgbox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
    msgbox.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
    msgbox.setWindowTitle("Warning")
    result = msgbox.exec()
    return result == QtWidgets.QMessageBox.StandardButton.Yes


class Plugin(object):
    def __init__(self):
        self.name = "Misc"
        self.actions = [("ID Randomizer", self.randomize_ids),
                        ("Save State", self.save_state),
                        ("Load State", self.load_savestate),
                        ("Dump PF2 to PNG", self.pf2dump)]
        print("I have been initialized")

    def pf2dump(self, editor):
        filepath, chosentype = QtWidgets.QFileDialog.getOpenFileName(
            editor, "Open PF2 File",
            editor.pathsconfig["xml"],
            "PF2 files (*.pf2);;All files (*)")

        pf2 = PF2(filepath)

        missionboundary = Image.new("RGB", (512, 512))
        ford = Image.new("RGB", (512, 512))
        nogo = Image.new("RGB", (512, 512))

        for i in range(512*512):
            x = (i) % 512
            y = (i) // 512
            if x < 256:
                x *= 2
            else:
                x = x - 256
                x *= 2
                x += 1

            # NOGO
            val = pf2.data[x][y][0]
            nogo.putpixel((x,y), (val, val, val))

            # FORD
            val = pf2.data[x][y][1]
            ford.putpixel((x, y), (val, val, val))

            # MISSION BOUNDARY
            val = pf2.data[x][y][2]
            missionboundary.putpixel((x, y), (val, val, val))

        nogo.save(filepath+"_dump_nogo.png")
        ford.save(filepath+"_dump_ford.png")
        missionboundary.save(filepath+"_dump_missionboundary.png")
        print("Saved PNG dumps in same folder as", filepath)

    def randomize_ids(self, editor: "bw_editor.LevelEditor"):
        yes = open_yesno_box("You are about to randomize all IDs.", "Are you sure?")
        if yes:
            print("randomize...")
            newids = {}

            editor.lua_workbench.entityinit.reflection_ids = {}

            for id, obj in editor.level_file.objects.items():
                newid = random.randint(1, 800000)
                while newid in newids:
                    newid = random.randint(1, 800000)

                obj._node.attrib["id"] = str(newid)
                assert newid not in newids
                newids[newid] = True

                if obj.lua_name:
                    editor.lua_workbench.entityinit.reflection_ids[newid] = obj.lua_name

                editor.lua_workbench.write_entity_initialization()

            for id, obj in editor.level_file.objects.items():
                obj.update_xml()
            print("done")

    def save_state(self, editor: "bw_editor.LevelEditor"):
        try:
            os.mkdir("savestates")
        except FileExistsError:
            pass

        base = os.path.dirname(editor.file_menu.current_path)
        fname = os.path.basename(editor.file_menu.current_path)
        with open(editor.file_menu.current_path) as f:
            levelpaths = BattalionFilePaths(f)
        savestatename = "{0}_savestate_{1}".format(fname[:-4], int(time.time()))
        print(savestatename)
        savestatepath = os.path.join("savestates", savestatename)
        os.mkdir(savestatepath)
        pf2path = fname[:-4]+".pf2"
        editor.file_menu.button_save_level()

        for path in (levelpaths.terrainpath,
                     levelpaths.resourcepath,
                     levelpaths.objectpath,
                     levelpaths.preloadpath):
            shutil.copy(os.path.join(base, path),
                        os.path.join(savestatepath, path))

        try:
            shutil.copy(os.path.join(base, pf2path),
                        os.path.join(savestatepath,pf2path))
        except FileNotFoundError:
            pass

    def load_savestate(self, editor: "bw_editor.LevelEditor"):
        savestatepath = QtWidgets.QFileDialog.getExistingDirectory(
            editor, "Open Save State",
            "savestates/")

        savestatename = os.path.basename(savestatepath)
        if "_savestate_" in savestatename:
            levelname, time = savestatename.split("_savestate_")

            if levelname in editor.file_menu.current_path:
                base = os.path.dirname(editor.file_menu.current_path)
                fname = os.path.basename(editor.file_menu.current_path)
                with open(editor.file_menu.current_path) as f:
                    levelpaths = BattalionFilePaths(f)

                pf2path = fname[:-4] + ".pf2"

                for path in (levelpaths.terrainpath,
                             levelpaths.resourcepath,
                             levelpaths.objectpath,
                             levelpaths.preloadpath):
                    if not os.path.exists(os.path.join(
                        savestatepath, path
                        )):
                        open_error_dialog("Savestate was created with a different compression setting compared to current level!"
                                          "Cannot load.", editor)
                        return


                for path in (levelpaths.terrainpath,
                             levelpaths.resourcepath,
                             levelpaths.objectpath,
                             levelpaths.preloadpath):
                    shutil.copy(os.path.join(savestatepath, path),
                                os.path.join(base, path))

                try:
                    shutil.copy(os.path.join(savestatepath, pf2path),
                                os.path.join(base, pf2path))
                except FileNotFoundError:
                    pass
                editor.file_menu.button_load_level(fpathoverride=editor.file_menu.current_path)

                basepath = os.path.dirname(editor.current_gen_path)
                resname = editor.file_menu.level_paths.resourcepath

                editor.lua_workbench.unpack_scripts(os.path.join(basepath, resname))

            else:
                print("Level mismatch!")
        else:
            print("Not a savestate!")


    def unload(self):
        print("I have been unloaded")
