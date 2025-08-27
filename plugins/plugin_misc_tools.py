import os
import time
import shutil
import random
from PIL import Image, ImageOps

from lib.bw.vectors import Vector3
from lib.BattalionXMLLib import BattalionFilePaths

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
from widgets.editor_widgets import open_error_dialog, open_message_dialog
from widgets.menu.file_menu import PF2
from typing import TYPE_CHECKING
from configuration import read_config, make_default_config, save_cfg
from plugins.plugin_object_exportimport import LabeledWidget
from widgets.menu.file_menu import LoadingBar
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


class SaveStateNameDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Set Savestate Name")
        self.bundle_path = None
        self.layout = QtWidgets.QVBoxLayout(self)
        self.name_widget = LabeledWidget(self, "Name (optional)",
                                         QtWidgets.QLineEdit)

        self.layout.addWidget(self.name_widget)

        self.ok = QtWidgets.QPushButton(self, text="OK")
        self.cancel = QtWidgets.QPushButton(self, text="Cancel")

        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def get_name(self):
        return self.name_widget.widget.text()

    def confirm(self):
        self.name_widget.widget: QtWidgets.QLineEdit
        levelname = self.name_widget.widget.text()

        if "/" in levelname or "\\" in levelname:
            open_error_dialog("Invalid characters in level name!", self)
            return

        self.accept()

    def deny(self):
        self.reject()


class LuaUnpackDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unpack Lua")
        self.bundle_path = None
        self.layout = QtWidgets.QVBoxLayout(self)
        self.text_info = QtWidgets.QLabel(self,
                                          text=("Do you want to unpack the savestate's scripts?\n"
                                                "Your current scripts will be overwritten.\n"
                                                "You can always manually unpack lua scripts later with Lua->Reload Scripts from Resource."))
        self.remember_widget = QtWidgets.QCheckBox(self, text="Remember for future savestate loads")

        self.layout.addWidget(self.text_info)
        self.layout.addWidget(self.remember_widget)

        self.ok = QtWidgets.QPushButton(self, text="Yes")
        self.cancel = QtWidgets.QPushButton(self, text="No")
        self.cancel.setDefault(True)
        self.buttons = QtWidgets.QHBoxLayout(self)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)
        self.layout.addLayout(self.buttons)

        self.ok.pressed.connect(self.confirm)
        self.cancel.pressed.connect(self.deny)

    def remember(self):
        return self.remember_widget.isChecked()

    def confirm(self):
        self.accept()

    def deny(self):
        self.reject()


class LoadingBarOld(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        WIDTH = 200
        HEIGHT = 50
        self.setFixedWidth(WIDTH)
        self.setFixedHeight(HEIGHT)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000//60)
        self.timer.timeout.connect(self.update_loadingbar)
        self.timer.start()

        self.progress = 0
        self.starttime = time.time()

        self.vertical_distance = 10
        self.horizontal_distance = 10
        self.loadingbar_width = WIDTH-self.horizontal_distance*2
        self.loadingbar_height = HEIGHT-self.vertical_distance*2

        self.bar_highlight = -20
        self.last_time = None

    def closeEvent(self, closeevent):
        self.timer.stop()

    def update_loadingbar(self):
        self.update()

        timepassed = (time.time()-self.starttime)*3
        self.progress = timepassed/100.0
        self.progress = min(self.progress, 1.0)

        if self.last_time is None:
            self.last_time = time.time()
        else:
            curr = time.time()
            delta = curr-self.last_time
            self.last_time = curr
            self.bar_highlight += delta*50
            if self.bar_highlight > self.loadingbar_width * self.progress+100:
                self.bar_highlight = -20

    def paintEvent(self, paintevent:QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        bar_limit = int(self.loadingbar_width * self.progress)
        painter.fillRect(self.horizontal_distance,
                         self.vertical_distance,
                         bar_limit,
                         self.loadingbar_height,
                         0x00FF00)

        highlightcolor = Vector3(0xCF, 0xFF, 0xCF)
        barcolor = Vector3(0x00, 0xFF, 0x00)

        for x in range(0, self.loadingbar_width):
            distance = ((x-self.bar_highlight)**2)/1000.0 #abs(x - self.bar_highlight)/20.0
            if distance > 1:
                distance = 1

            color = highlightcolor*(1-distance) + barcolor*distance
            pencolor = int(color.x)<<16 | int(color.y)<<8 | int(color.z)
            painter.setPen(pencolor)
            if x < bar_limit:
                painter.drawLine(x+self.horizontal_distance,
                                 self.vertical_distance,
                                 x+self.horizontal_distance,
                                 self.vertical_distance+self.loadingbar_height)


class Plugin(object):
    def __init__(self):
        self.name = "Misc"
        self.actions = [#("ID Randomizer", self.randomize_ids),
                        ("Save State", self.save_state),
                        ("Load State", self.load_savestate),
                        ("Dump PF2 to PNG", self.pf2dump),
                        ("Update Texture Cache for Selection", self.update_texture_cache),
                        ("Clean Up Invalid Resources", self.clean_up)]
                        #("Open Dialog", self.open_dialog)]
                        #("Loading Bar Test", self.loading_bar)]
        print("I have been initialized")
        self.is_doing_manual_savestate = False
        self.remember_choice = None

    def open_dialog(self, editor):
        result = LuaUnpackDialog()
        a = result.exec()
        print(a, result.remember())

    def clean_up(self, editor: "bw_editor.LevelEditor"):
        res = editor.file_menu.resource_archive

        delete = []

        for objid, obj in editor.level_file.objects.items():
            if obj.type == "cAnimationResource":
                resource = res.get_resource(b"MINA", obj.mName)
            elif obj.type == "cTequilaEffectResource":
                resource = res.get_resource(b"FEQT", obj.mName)
            elif obj.type == "cNodeHierarchyResource":
                resource = res.get_resource(b"LDOM", obj.mName)
            elif obj.type == "cGameScriptResource":
                resource = res.get_script(obj.mName)
            elif obj.type == "sSampleResource":
                resource = res.get_resource(b"HPSD", obj.mName)
            elif obj.type == "cTextureResource":
                resource = res.get_resource(b"DXTG", obj.mName)
                if resource is None:
                    resource = res.get_resource(b"TXET", obj.mName)

            if resource is None:
                print("A resource has a XML entry but doesn't exist in the res!", obj.name)
                delete.append(obj)

        if len(delete) > 0:
            result = open_yesno_box(f"{len(delete)} XML entries for resources that no longer exist in resource archive found.\n"
                                    "They can interfere with the editor's Object Import functionality!",
                           "Do you want to delete them?")

            if result:
                print("deleting...")
                editor.delete_objects(delete)
                open_message_dialog("Done!", "")
        else:
            open_message_dialog("No XML entries for resources that don't exist in the resource archive found.",
                                "No clean-up necessary.")

    def update_texture_cache(self, editor: "bw_editor.LevelEditor"):
        selected = editor.level_view.selected

        texture_lookup = {}
        for objid, obj in editor.level_file.objects.items():
            if obj.type == "cTextureResource":
                texture_lookup[obj.mName.lower()] = obj

        texlist = []
        check = []

        for obj in selected:
            check.append(obj)
            for dep in obj.get_dependencies():
                if dep not in check:
                    check.append(dep)

        for obj in check:
            if obj.type == "cNodeHierarchyResource":
                modelname = obj.mName

                textures = editor.level_view.bwmodelhandler.models[modelname].all_textures
                for texname in textures:
                    if texname.lower() in texture_lookup:
                        texlist.append(texture_lookup[texname.lower()].mName)
            if obj.type == "cTextureResource":
                texlist.append(obj.mName)
        print("clearing...", texlist)
        editor.level_view.bwmodelhandler.textures.clear_cache(texlist)

    def loading_bar(self, editor):
        bar = LoadingBar(editor)
        bar.show()
        pass

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

        ImageOps.flip(nogo).save(filepath+"_dump_nogo.png")
        ImageOps.flip(ford).save(filepath+"_dump_ford.png")
        ImageOps.flip(missionboundary).save(filepath+"_dump_missionboundary.png")
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

    def before_save(self, editor):
        if not self.is_doing_manual_savestate:
            self.auto_save(editor)

    def get_autosaves(self):
        autosaves = []
        for entry in os.listdir("savestates"):
            path = os.path.join("savestates", entry)

            if entry.startswith("Autosave_"):
                assert os.path.isdir(path)

                autosaves.append(entry)

        return autosaves

    def auto_save(self, editor: "bw_editor.LevelEditor"):
        try:
            os.mkdir("savestates")
        except FileExistsError:
            pass

        AUTOSAVECOUNT = editor.configuration["editor"].getint("max_autosaves", fallback=None)
        if AUTOSAVECOUNT is None:
            editor.configuration["editor"]["max_autosaves"] = "5"
            AUTOSAVECOUNT = 5
            save_cfg(editor.configuration)

        base = os.path.dirname(editor.file_menu.current_path)
        fname = os.path.basename(editor.file_menu.current_path)
        savestatename = "Autosave_{0}_savestate_{1}".format(fname[:-4], int(time.time()))
        print(savestatename)
        savestatepath = os.path.join("savestates", savestatename)
        os.mkdir(savestatepath)
        with open(editor.file_menu.current_path) as f:
            levelpaths = BattalionFilePaths(f)

        for path in (levelpaths.terrainpath,
                     levelpaths.resourcepath,
                     levelpaths.objectpath,
                     levelpaths.preloadpath):
            shutil.copy(os.path.join(base, path),
                        os.path.join(savestatepath, path))

        pf2path = fname[:-4] + ".pf2"
        try:
            shutil.copy(os.path.join(base, pf2path),
                        os.path.join(savestatepath,pf2path))
        except FileNotFoundError:
            pass
        print("Saved autosave to", savestatepath)
        autosaves = self.get_autosaves()

        print("Autosave count:", AUTOSAVECOUNT)
        if len(autosaves) > AUTOSAVECOUNT:
            autosaves_date = []
            for save in autosaves:
                rest, date = save.rsplit("_", 1)

                autosaves_date.append((int(date), save))

            autosaves_date.sort(key=lambda x: x[0])
            oldest_date, autosave = autosaves_date[0]

            print("deleting oldest autosave", autosave)
            shutil.rmtree(os.path.join("savestates", autosave))

    def save_state(self, editor: "bw_editor.LevelEditor"):
        try:
            os.mkdir("savestates")
        except FileExistsError:
            pass

        base = os.path.dirname(editor.file_menu.current_path)
        fname = os.path.basename(editor.file_menu.current_path)
        with open(editor.file_menu.current_path) as f:
            levelpaths = BattalionFilePaths(f)

        dialog = SaveStateNameDialog()

        a = dialog.exec()
        if not a:
            return

        savestatename = "{0}_savestate_{1}".format(fname[:-4], int(time.time()))
        if dialog.get_name():
            savestatename += "_{0}".format(dialog.get_name())

        print(savestatename)
        savestatepath = os.path.join("savestates", savestatename)
        os.mkdir(savestatepath)
        pf2path = fname[:-4]+".pf2"

        # Avoid autosave when doing manual savestate
        self.is_doing_manual_savestate = True
        editor.file_menu.button_save_level()
        self.is_doing_manual_savestate = False

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

        try:
            pfd = editor.file_menu.get_pfd_path()
            shutil.copy(pfd,
                        os.path.join(savestatepath, os.path.basename(pfd)))
        except:
            pass


    def load_savestate(self, editor: "bw_editor.LevelEditor"):
        savestatepath = QtWidgets.QFileDialog.getExistingDirectory(
            editor, "Open Save State",
            "savestates/")

        savestatename = os.path.basename(savestatepath)
        if "_savestate_" in savestatename:
            if savestatename.startswith("Autosave_"):
                savestatename = savestatename.removeprefix("Autosave_")
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

                try:
                    pfd = editor.file_menu.get_pfd_path()

                    shutil.copy(os.path.join(savestatepath, os.path.basename(pfd)),
                                pfd)
                except:
                    pass

                if self.remember_choice is None:
                    dialog = LuaUnpackDialog()
                    do_unpack = dialog.exec()
                    if dialog.remember():
                        self.remember_choice = do_unpack
                else:
                    do_unpack = self.remember_choice

                editor.file_menu.button_load_level(fpathoverride=editor.file_menu.current_path)


                if do_unpack:
                    bar = LoadingBar(editor)

                    basepath = os.path.dirname(editor.current_gen_path)
                    resname = editor.file_menu.level_paths.resourcepath
                    bar.show()
                    def progress(i):
                        bar.update_progress(i)
                        QtWidgets.QApplication.processEvents()

                    try:
                        editor.lua_workbench.unpack_scripts(os.path.join(basepath, resname), progress)
                        open_message_dialog("Lua scripts unpacked!", "", editor)
                    except Exception as err:
                        bar.force_close()
                        raise
                    bar.force_close()

            else:
                open_message_dialog("Save state is from a different level!",
                                    f"{levelname} (save state) vs {os.path.basename(editor.file_menu.current_path)} (current)")
                print("Level mismatch!")
        else:
            open_message_dialog("Chosen folder does not seem to be a save state!")
            print("Not a savestate!")


    def unload(self):
        print("I have been unloaded")
