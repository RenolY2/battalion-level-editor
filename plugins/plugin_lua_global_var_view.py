import numpy
import time
import threading
import PyQt6.QtWidgets as QtWidgets
import lib.luastructs as luastructs
from plugins.plugin_pfd_edit import PFDPluginButton
from collections import namedtuple
from typing import TYPE_CHECKING
from lib.render.model_renderingv2 import QuadDrawing, LineDrawing
from OpenGL.GL import *
from math import cos, sin, radians
from widgets.edit_window import SelectableLabel
from lib.game_visualizer import MiniHook, LevelFileDummy, LuaTable, Item, BOOLEAN, NUMBER

if TYPE_CHECKING:
    import bw_editor
    import bw_widgets

"""
                if gameid == b"G8WE":  # US BW1
                    self.region = gameid
                elif gameid == b"G8WP":  # PAL BW1
                    self.region = gameid
                elif gameid == b"G8WJ":  # JP BW1
                    self.region = gameid
                elif gameid == b"RBWE":  # US BW2
                    self.region = gameid
                elif gameid == b"RBWP": # PAL BW2
                    self.region = gameid
                elif gameid == b"RBWJ":  # JP BW2
                    self.region = gameid"""

LUATABLEOFFSETS = {b"G8WP": 0x803C1708,
                   b"G8WE": 0x803BB318,
                   b"G8WJ": 0x803C0790,
                   b"RBWE": 0x805fe508,  # Reference: code at 0x800d114c
                   b"RBWJ": 0x806005D0,
                   b"RBWP": 0x80600088}

BW2OFFSET = (b"RBWE", b"RBWP", b"RBWJ")


class Plugin(object):
    def __init__(self):
        self.name = "Lua Global Var Viewer"
        self.actions = []
        self.guimode = False
        self.bwgame: MiniHook = None
        self.curr = 0
        self.table: QtWidgets.QTableWidget = None
        self.thread = None
        self.luatable = None
        self.luatable_filtered = []
        self.addr = None
        self.force_refresh = False

        self.scheduled_changes = {}
        self.table_lock = threading.RLock()
        self.dontupdate = False

    def testfunc(self, editor: "bw_editor.LevelEditor"):
        print("This is a test function")
        print("More")

    def plugin_init(self, editor):
        self.bwgame = MiniHook()

        pass
        """if hasattr(editor.file_menu, "level_data"):
            for obj in editor.file_menu.level_data.objects.values():
                if "cGUIPage" in obj.type:
                    self.guimode = True"""

    def after_load(self, editor: "bw_editor.LevelEditor"):
        self.guimode = False

        for obj in editor.file_menu.level_data.objects.values():
            if "cGUIPage" in obj.type:
                self.guimode = True

    def unload(self):
        pass

    def regular_refresh(self):
        while self.bwgame is not None and self.bwgame.running:
            time.sleep(0.05)
            self.table_refresh()

    def shutdown(self):
        self.bwgame.initialize(shutdown=True)
        self.bwgame.running = False
        self.thread = None
        if self.toggle_button.isChecked():
            #self.toggle_button.setChecked(False)
            self.toggle_button.setText("Activate Live Variable View")

    def tablechange(self, item: QtWidgets.QTableWidgetItem):
        data = item.text()
        if item.column() == 0: return
        key = self.table.item(item.row(), 0)

        if self.luatable is not None:
            print("lock acquired 2")
            with self.table_lock:
                byteskey = bytes(key.text(), "ascii")
                offset = self.luatable.voffsets[byteskey]
                vtype = self.luatable.type[byteskey]
                if vtype == NUMBER:
                    print("Written a double")
                    self.bwgame.dolphin.write_double(offset+8+16, float(data))
                elif vtype == BOOLEAN:
                    val = int(data)
                    if val != 0:
                        val = 1
                    print("Written a boolean")
                    self.bwgame.dolphin.write_uint32(offset+8+16, val)
            print("lock released 2")

    def table_refresh(self, newtable=False):
        print("gonna refresh")
        self.table_lock.acquire()
        print("acquired lock")
        try:
            offset = LUATABLEOFFSETS[self.bwgame.region]
            ptr = self.bwgame.deref(offset)

            if ptr <= 0x80000000:
                return

            try:
                if self.bwgame.region in BW2OFFSET:
                    luastate = self.bwgame.deref(ptr + 0x10)
                else:
                    luastate = self.bwgame.deref(ptr + 0xC)
            except:
                return

            if luastate <= 0x80000000:
                return

            if self.addr is not None and self.addr != luastate:
                newtable = True

            if self.luatable is None:
                newtable = True

            if newtable:
                self.addr = luastate

                obj = self.bwgame.readstruct(luastructs.TObject, luastate + 0x40, 0, typeunpack=True)
                try:
                    table = LuaTable(self.bwgame, obj.value)

                except:
                    self.luatable = None
                    return

                print(table.table)
                try:
                    self.luatable = LuaTable(self.bwgame, table.table[b"realtable"])
                except:
                    self.luatable = None
                    return
                self.luatable_filtered = []

                for k in self.luatable.table.keys():
                    if self.luatable.type[k] in (1, 3, 4):
                        self.luatable_filtered.append(k)
                self.luatable_filtered.sort()
            else:
                offset = LUATABLEOFFSETS[self.bwgame.region]
                try:
                    self.luatable.update_values()
                except:
                    self.luatable = None
                    return

            rowcount = len(self.luatable_filtered)
            self.table.setRowCount(rowcount)

            for i, k in enumerate(self.luatable_filtered):
                keyitem = self.table.item(i, 0)
                valueitem = self.table.item(i, 1)
                value = self.luatable.table[k]


                if keyitem is not None:
                    keyitem.setText(str(k, encoding="ascii"))
                else:
                    self.table.setItem(i, 0, Item(str(k, encoding="ascii")))

                print(k, value)
                self.table.blockSignals(True)
                if valueitem is not None:
                    valueitem.setText(str(value))
                else:
                    self.table.setItem(i, 1, Item(str(value)))
                self.table.blockSignals(False)
                self.dontupdate = False
        except Exception as err:
            self.table.blockSignals(False)
            self.table_lock.release()
            print("exception happen")
            raise
        else:
            if newtable:
                self.table.resizeColumnsToContents()

    def button_pressed(self):
        if self.toggle_button.isChecked():
            # Turn off viewer
            print("Shutting down")
            self.shutdown()
        else:
            print("Turning on")
            # Turn on viewer
            self.bwgame.initialize()
            if self.bwgame.region in LUATABLEOFFSETS:
                print("refreshed")
                self.table_refresh(True)
                self.thread = threading.Thread(target=self.regular_refresh)
                self.thread.daemon = True
                self.thread.start()
            else:
                print("Nopeeee")
                self.shutdown()

    def setup_widget(self, editor: "bw_editor.LevelEditor", widget: "plugin.PluginWidgetEntry"):
        widget.set_tab_name("Lua Var View")
        widget.add_text("Lua Global Variable Viewer")
        self.toggle_button: QtWidgets.QPushButton = widget.add_widget(QtWidgets.QPushButton(widget))
        self.toggle_button.setCheckable(True)
        self.toggle_button.pressed.connect(self.button_pressed)
        self.toggle_button.setText("Activate Live Variable View")

        testbutton = widget.add_widget(QtWidgets.QPushButton(widget))
        testbutton.pressed.connect(self.table_refresh)
        testbutton.setText("Refresh")


        self.table = widget.add_widget(QtWidgets.QTableWidget(widget))
        self.table: QtWidgets.QTableWidget
        self.table.itemChanged.connect(self.tablechange)

        self.table.setColumnCount(2)
        self.table.setRowCount(10)

        """
        self.section = widget.add_widget(QtWidgets.QLabel(widget, text="BW2 GUI Rendering:"))

        self.button_add_point = widget.add_widget(PFDPluginButton(
            widget, text="Toggle GUI branch", editor=editor, func=self.toggle_branch,
            checkable=False))

        self.roots = widget.add_widget(QtWidgets.QLabel(widget, text="GUI Parent Branches: 0"))
        self.currroots = widget.add_widget(QtWidgets.QLabel(widget, text="Current Branch: -"))
        self.root_text = widget.add_widget(QtWidgets.QLabel(widget, text="Current root:"))
        self.current_gui_root = widget.add_widget(SelectableLabel(widget, text=""))"""