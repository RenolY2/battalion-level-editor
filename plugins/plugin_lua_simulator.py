import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
from functools import partial
from collections import namedtuple
from typing import TYPE_CHECKING
from widgets.editor_widgets import open_error_dialog
import queue
import lib.lua.lua_simulator as lua_simulator
from importlib import reload

from plugins.strings_editor.strings import BWLanguageFile
from lib.bw.texture import TextureArchive

if TYPE_CHECKING:
    import bw_editor


class BWGuiHandler(object):
    def __init__(self, level, textures):
        self.level = level
        self.textures: TextureArchive = textures
        #self.bwgui = QtWidgets.QMainWindow()
        #self.bwgui.resize(640, 480)
        #self.bwgui.show()
        self.sprite_depths = {}

    def register_functions(self, lua_sim: lua_simulator.LuaSimulator):
        lua_sim.set_function("GetPersistentData", self.GetPersistentData)
        lua_sim.set_function("GetStoredMissionData", self.GetStoredMissionData)
        lua_sim.set_function("GetMissionData", self.GetMissionData)
        lua_sim.set_function("IsBonusDone", self.IsBonusDone)
        lua_sim.set_function("rint", self.rint)
        lua_sim.set_function("GetSprite", self.GetSprite)

    def GetPersistentData(self):
        return 0, 1, 1

    def GetStoredMissionData(self, i):
        return 0, 0, 0, 0

    def GetMissionData(self):
        return 0, 0, 0, 0

    def IsBonusDone(self, i):
        return True

    def rint(self, x):
        return round(x)

    def GetSprite(self, spriteid):
        sprite = self.level.objects[str(spriteid)]
        return spriteid

    def ZDepthSprite(self, sprite, depth):
        self.sprite_depths[sprite] = depth

    def OpenSprite(self, spritesetup):
        sprite = spritesetup[0]
        size = spritesetup[1]
        unk = spritesetup[2]
        rotfunc = spritesetup[3]
        colorfunc = spritesetup[4]

    def OpenFlat(self, flat):
        name = flat[0]
        coord1 = flat[1]
        size = flat[2]
        coord2 = flat[3]
        size2 = flat[4]
        colorfunc = flat[5]

    def QuadraticBezier(self, x1, y1, x2, y2, gap, unk, dest):
        dest[1] = 0
        dest[2] = 0


class BWHandler(object):
    def __init__(self, print):
        self.level = None
        self.resources = None
        self.strings: BWLanguageFile = None
        self.print = print
        self.guihandler = None

    def set_gui_handler(self, handler: BWGuiHandler):
        self.guihandler = handler

    def set_messages(self, path):
        with open(path, "rb") as f:
            self.strings = BWLanguageFile(f)

    def phone_message(self, msgid, unk_const, army, timeout, sprite):
        msg = self.strings.get_message(msgid)
        msg_content = msg.get_message()
        self.print(f"TRANSMISSION {msgid}: "+msg_content)

    def register_functions(self, lua_sim: lua_simulator.LuaSimulator):
        lua_sim.set_function("PhoneMessage", self.phone_message)

        if self.guihandler is not None:
            self.guihandler.register_functions(lua_sim)


class LuaSimulatorWorker(QtCore.QThread):
    finished = QtCore.pyqtSignal(dict)
    message_out = QtCore.pyqtSignal(str)

    def __init__(self, lua_sim):
        super(LuaSimulatorWorker, self).__init__()
        self.lua_simulator: lua_simulator.LuaSimulator = lua_sim

    def run(self):
        self.lua_simulator.output_hook = self.emit_message
        self.lua_simulator.coroutine_loop()
        self.finished.emit(self.lua_simulator.get_globals())

    def emit_message(self, msg):
        if not self.lua_simulator.stop:
            self.message_out.emit(msg)

    def stop(self):
        self.lua_simulator.stop = True

    def update_context(self, context):
        self.lua_simulator.set_context(context)


class ToggleableButton(QtWidgets.QPushButton):
    def __init__(self, name1, name2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name1 = name1
        self.name2 = name2
        self.setCheckable(True)
        self.choice = 0
        self.setText(self.name1)

    def nextCheckState(self) -> None:
        super().nextCheckState()

        if self.isChecked():
            self.setText(self.name2)
            self.choice = 1
        else:
            self.setText(self.name1)
            self.choice = 0


class LuaSimulatorWindow(QtWidgets.QMdiSubWindow):
    run_toggle = QtCore.pyqtSignal()
    text_changed = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.central_widget = QtWidgets.QWidget(self)
        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.central_layout = QtWidgets.QVBoxLayout(self.central_widget)

        self.lua_context = QtWidgets.QPlainTextEdit(self)
        font = QtGui.QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        metrics =  QtGui.QFontMetrics(font)
        self.lua_context.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
        self.lua_context.setFont(font)

        self.lua_run = ToggleableButton("Run", "Stop", self)
        self.lua_run_all = ToggleableButton("Selected Script", "All Scripts", self)
        self.lua_update_context = QtWidgets.QPushButton("Update Context", self)
        self.splitter.addWidget(self.lua_context)

        self.output = QtWidgets.QTextEdit(self)
        self.splitter.addWidget(self.output)
        self.output.setReadOnly(True)
        self.central_layout.addWidget(self.splitter)
        self.buttonlayout = QtWidgets.QHBoxLayout(self)
        self.buttonlayout_run = QtWidgets.QHBoxLayout(self)

        self.buttonlayout_run.addWidget(self.lua_run)
        self.buttonlayout_run.addWidget(self.lua_run_all)
        self.buttonlayout.addLayout(self.buttonlayout_run)
        self.buttonlayout.addWidget(self.lua_update_context)
        self.lua_run.setCheckable(True)
        self.central_layout.addLayout(self.buttonlayout)

        self.setWidget(self.central_widget)
        self.orig_flags = self.windowFlags()
        self.force_ontop()

        self.output.textChanged.connect(self.scroll_text)

        self.lines = 0
        self.is_running = False
        self.lua_context.textChanged.connect(self.emit_text_changed)

    def emit_text_changed(self):
        self.text_changed.emit()

    def run(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def force_ontop(self):
        self.setWindowFlags(self.orig_flags | QtCore.Qt.WindowType.WindowStaysOnTopHint)

    def disable_ontop(self):
        self.setWindowFlags(self.orig_flags | QtCore.Qt.WindowType.WindowStaysOnBottomHint)

    def only_selected(self):
        return not self.lua_run_all.isChecked()

    def scroll_text(self):
        self.output.ensureCursorVisible()

    def reset_button(self):
        self.lua_run.setChecked(False)

    def get_context(self):
        return self.lua_context.toPlainText()

    def print(self, text):
        self.output.insertPlainText(text)
        self.output.insertPlainText("\n")
        self.lines += 1

        if self.lines > 2500:
            cursor = self.output.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Down, QtGui.QTextCursor.MoveMode.KeepAnchor, n=500)
            #cursor.select(QtGui.QTextCursor.SelectionType.LineUnderCursor)
            cursor.deleteChar()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)

            self.output.setTextCursor(cursor)
            self.lines -= 500

    def clear(self):
        self.output.clear()
        self.lines = 0


class Plugin(object):
    def __init__(self):
        self.name = "Lua Simulator"
        self.actions = [("Open Simulator", self.testfunc)]
        print("I have been initialized")

        self.lua_sim_window: LuaSimulatorWindow = None
        self.lua_sim = None
        self.lua_sim_thread = None
        self.bw_handler = None
        self.guihandler = None

        self.orig_globals = None

    def on_finish(self, globals):
        self.lua_sim_window.print("\n=== Finished Execution! ===\n")
        self.lua_sim_window.print("Script Context After Execution:")
        for key, value in globals.items():
            if key == "result__":
                continue

            if key not in self.orig_globals:

                self.lua_sim_window.print(f"{key} = {str(value)}")

    def print_output(self, text):
        self.lua_sim_window.print(text)

    def update_context(self):
        context = self.lua_sim_window.get_context()
        self.lua_sim_thread.update_context(context)

    def save_lua_context(self, editor: "bw_editor.LevelEditor"):
        context = self.lua_sim_window.get_context()
        context_path = editor.lua_workbench.get_lua_script_path("__lua_context__")

        with open(context_path, "w") as f:
            f.write(context)

    def run_simulator(self, editor: "bw_editor.LevelEditor"):
        if self.lua_sim_thread is not None:
            print("stopping...")
            self.lua_sim_thread.stop()

            self.lua_sim_thread.quit()
            self.lua_sim_thread = None
        else:
            init_scripts = {}
            scripts = {}
            if self.lua_sim_window.only_selected():
                if len(editor.level_view.selected) > 0:
                    obj = editor.level_view.selected[0]
                    if obj.type in ("cGlobalScriptEntity", "cInitialisationScriptEntity"):
                        if obj.mpScript is not None:
                            scriptname = obj.mpScript.mName
                            scripts[scriptname] = [int(obj.id)]
                    elif obj.type == "cGameScriptResource":
                        scriptname = obj.mName
                        scripts[scriptname] = [int(obj.id)]
            else:
                for objid, obj in editor.level_file.objects.items():
                    if hasattr(obj, "mpScript"):
                        if obj.mpScript is not None:
                            if obj.type == "cInitialisationScriptEntity":
                                script_dict = init_scripts
                            else:
                                script_dict = scripts

                            if obj.mpScript.mName not in script_dict:
                                script_dict[obj.mpScript.mName] = []
                            script_dict[obj.mpScript.mName].append(int(obj.id))

            if scripts or init_scripts:

                self.bw_handler = BWHandler(None)
                self.guihandler = BWGuiHandler(editor.level_file, editor.level_view.bwmodelhandler.textures)
                self.bw_handler.set_gui_handler(self.guihandler)
                stringpath = editor.file_menu.get_strings_path("English")

                try:
                    self.bw_handler.set_messages(stringpath)
                except FileNotFoundError:
                    print("No string file found")

                is_bw1 = not editor.level_file.bw2
                lua_sim = lua_simulator.LuaSimulator(self.print_output, is_bw1)
                lua_sim.debug = True
                self.bw_handler.register_functions(lua_sim)
                lua_sim.prepend_routine_name_to_print = True
                entityinit = "EntityInitialise"
                entityinitpath = editor.lua_workbench.get_lua_script_path(entityinit)
                with open(entityinitpath, "r") as f:
                    entityinit_content = f.read()

                lua_sim.set_context(entityinit_content)
                lua_sim.update_context()
                for scriptname, owners in init_scripts.items():
                    scriptpath = editor.lua_workbench.get_lua_script_path(scriptname)
                    lua_sim.add_script(scriptname, scriptpath, owners)

                for scriptname, owners in scripts.items():
                    scriptpath = editor.lua_workbench.get_lua_script_path(scriptname)
                    lua_sim.add_script(scriptname, scriptpath, owners)

                lua_sim.set_context("")
                lua_sim.setup_coroutine()
                self.orig_globals = lua_sim.get_globals()
                #for k, v in self.orig_globals.items():
                #    print(k,v)
                lua_sim.set_context(self.lua_sim_window.get_context())
                lua_sim.update_context()
                lua_sim.update_context()

                self.lua_sim_window.clear()

                self.lua_sim_thread = LuaSimulatorWorker(lua_sim)
                self.lua_sim_thread.message_out.connect(self.lua_sim_window.print)
                self.bw_handler.print = self.lua_sim_thread.emit_message
                self.lua_sim_thread.finished.connect(self.on_finish)
                self.lua_sim_thread.start()
            else:
                self.lua_sim_window.disable_ontop()
                open_error_dialog("Please select a script object.", None)
                self.lua_sim_window.force_ontop()
                self.lua_sim_window.show()

    def error_happened(self, string):
        print("error")
        print(string)

    def testfunc(self, editor: "bw_editor.LevelEditor"):
        self.lua_sim_window = LuaSimulatorWindow()

        path = editor.lua_workbench.get_lua_script_path("__lua_context__")

        try:
            with open(path, "r") as f:
                context = f.read()
            self.lua_sim_window.lua_context.setPlainText(context)
        except FileNotFoundError:
            print("No existing lua context file found, skipping...")
            pass

        self.lua_sim_window.show()
        self.lua_sim_window.lua_run.pressed.connect(partial(self.run_simulator, editor))
        self.lua_sim_window.text_changed.connect(partial(self.save_lua_context, editor))
        self.lua_sim_window.lua_update_context.pressed.connect(self.update_context)

    def unload(self):
        print("I have been unloaded")
        reload(lua_simulator)
