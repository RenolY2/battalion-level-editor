import importlib
import os
import traceback
import typing
if typing.TYPE_CHECKING:
    from bw_editor import LevelEditor

from functools import partial

from collections import namedtuple
from PyQt6.QtCore import QTimer
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
from widgets.menu.menu import Menu

from builtin_plugins import add_object_window

from PyQt6.QtCore import Qt

PluginEntry = namedtuple("PluginEntry", ("module", "plugin"))

pluginfolder = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "plugins")


class PluginWidgetEntry(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.widget_layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.widget_layout)

    def add_widget(self, widget):
        self.widget_layout.addWidget(widget)
        return widget

    def add_text(self, text):
        textlabel = QtWidgets.QLabel(text, self)
        self.add_widget(textlabel)
        return textlabel


class PluginHandler(object):
    def __init__(self):
        self.plugins = {}
        self.plugin_folder_last_changed = os.stat(pluginfolder).st_mtime

        self.plugin_menu: PluginMenu = None
        self.plugin_sidewidget: PluginHolderWidget = None


        # widget event: setup_widget(editor, widget)
        self.events = {}
        self.add_event("plugin_init", "LevelEditor")
        self.add_event("select_update", "LevelEditor")
        self.add_event("before_save", "LevelEditor")
        self.add_event("before_load")
        self.add_event("after_load")
        self.add_event("render_post", "BolMapViewer")
        self.add_event("world_click", "LevelEditor", "X", "Y")
        self.add_event("topdown_click", "X", "Y")
        self.add_event("world_click", "worldX", "worldY")
        self.add_event("raycast_3d", "ray")
        self.add_event("terrain_click_3d", "BolMapViewer", "ray", "point")
        self.add_event("terrain_click_2d", "BolMapViewer", "point")
        self.add_event("key_release", "LevelEditor", "qtkey")
        self.add_event("key_press", "LevelEditor", "qtkey")
        self.add_event("cancel_mode", "LevelEditor")

        self.add_object_window: add_object_window.Plugin = self.load_builtin_plugin(add_object_window)

    def add_event(self, event_name, *args):
        self.events[event_name] = args

    def create_plugin_menu(self, parent):
        self.plugin_menu = PluginMenu(parent)
        return self.plugin_menu

    def create_plugin_sidewidget(self, parent):
        self.plugin_sidewidget = PluginHolderWidget(parent)
        return self.plugin_sidewidget

    def hot_reload(self, editor):
        if self.plugin_folder_changed() and self.plugin_menu is not None:
            changed_plugins = self.reload_changed_plugins()
            self.plugin_folder_update_time()

            self.plugin_menu.clear_menu_actions()
            self.plugin_menu.add_menu_actions(self.plugins, editor)

            for pluginname in changed_plugins:
                self.execute_event("plugin_init", editor)
                self.execute_plugin_widget_setup(pluginname, editor)

    def plugin_folder_update_time(self):
        self.plugin_folder_last_changed = os.stat(pluginfolder).st_mtime

    def plugin_folder_changed(self):
        return self.plugin_folder_last_changed != os.stat(pluginfolder).st_mtime

    def plugin_changed(self, pluginname):
        if not self.plugins[pluginname].module.__hotload:
            return False

        pluginpath = os.path.join(pluginfolder, pluginname+".py")
        return self.plugins[pluginname].module.__time != os.stat(pluginpath).st_mtime

    def plugin_update_time(self, pluginname):
        if self.plugins[pluginname].module.__hotload:
            pluginpath = os.path.join(pluginfolder, pluginname + ".py")
            self.plugins[pluginname].module.__time = os.stat(pluginpath).st_mtime

    def is_loaded(self, pluginname):
        return pluginname in self.plugins

    def load_builtin_plugin(self, module):
        pluginname = module.__name__
        assert pluginname not in self.plugins
        module.__hotload = False

        plugin = module.Plugin()
        module.__time = 0
        self.plugins[pluginname] = PluginEntry(module, plugin)

        return plugin

    def load_plugin(self, pluginname, reload=False):
        assert pluginname not in self.plugins
        importlib.invalidate_caches()
        try:
            module = importlib.import_module("plugins."+pluginname)
            module.__hotload = True
            plugin = module.Plugin()
        except:
            traceback.print_exc()
        else:
            module.__time = os.stat(pluginfolder).st_mtime
            self.plugins[pluginname] = PluginEntry(module, plugin)

    def reload_plugin(self, pluginname):
        self.plugins[pluginname].plugin.unload()  # Allow the plugin to do cleanup before reloading it

        try:
            module = importlib.reload(self.plugins[pluginname].module)
            module.__hotload = True
            plugin = module.Plugin()

            self.plugins[pluginname] = PluginEntry(module, plugin)
        except:
            traceback.print_exc()

    def reload_changed_plugins(self):
        self.load_plugins()  # Check for newly added plugins
        changed_plugins = []
        for pluginname in self.plugins:
            if self.plugin_changed(pluginname):
                self.reload_plugin(pluginname)
                changed_plugins.append(pluginname)

            self.plugin_update_time(pluginname)

        return changed_plugins

    def load_plugins(self):
        for pluginfile in os.listdir(pluginfolder):
            if pluginfile.startswith("plugin") and pluginfile.endswith(".py"):
                pluginname = pluginfile[:-3]
                if not self.is_loaded(pluginname):
                    self.load_plugin(pluginname)

    def execute_event(self, eventname, *args, **kwargs):
        if eventname not in self.events:
            raise RuntimeError("Unknown event {}".format(eventname))
        for pluginname, entry in self.plugins.items():
            if hasattr(entry.plugin, eventname):
                try:
                    func = getattr(entry.plugin, eventname)
                    func(*args, **kwargs)
                except:
                    traceback.print_exc()

    def add_plugin_widgets(self, editor):
        for pluginname in self.plugins:
            self.execute_event("plugin_init", editor)
            self.execute_plugin_widget_setup(pluginname, editor)

    def execute_plugin_widget_setup(self, pluginname, editor):
        entry = self.plugins[pluginname]
        if hasattr(entry.plugin, "setup_widget"):
            widget = PluginWidgetEntry(self.plugin_sidewidget)
            try:
                func = getattr(entry.plugin, "setup_widget")
                func(editor, widget)
            except:
                traceback.print_exc()
                widget.setParent(None)
                widget.deleteLater()
            else:
                self.plugin_sidewidget.add_plugin_widget(pluginname, widget)

    def add_menu_actions(self, editor):
        self.plugin_menu.add_menu_actions(self.plugins, editor)

    def clear_menu_actions(self):
        self.plugin_menu.clear_menu_actions()


class PluginHolderWidget(QtWidgets.QScrollArea):
    def __init__(self, parent):
        super().__init__(parent)
        self.setMinimumWidth(200)

        self.setWidgetResizable(True)
        #policy = self.scroll_area.sizePolicy()
        #policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        #self.scroll_area.setSizePolicy(policy)
        self.scroll_area_content = QtWidgets.QWidget(self)

        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_area_content)
        self.scroll_area_content.setLayout(self.scroll_layout)
        self.scroll_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.scroll_area_content)

        self.plugin_widgets = {}

    def is_empty(self):
        return len(self.plugin_widgets) == 0

    def remove_plugin_widget(self, pluginname):
        if pluginname in self.plugin_widgets:
            widget = self.plugin_widgets[pluginname]
            index = self.scroll_layout.indexOf(widget)
            widget.setParent(None)
            widget.deleteLater()
            del self.plugin_widgets[pluginname]

            return index

    def add_plugin_widget(self, pluginname, widget):
        if pluginname not in self.plugin_widgets:
            self.plugin_widgets[pluginname] = widget
            self.scroll_layout.addWidget(widget)
        else:
            i = self.remove_plugin_widget(pluginname)

            self.plugin_widgets[pluginname] = widget
            self.scroll_layout.insertWidget(i, widget)


class PluginMenu(Menu):
    def __init__(self, parent):
        super().__init__(parent, "Plugins")
        self.parent = parent
        self.menus = []

    def add_menu_actions(self, plugins, editor):
        for pluginname, pluginentry in plugins.items():
            if len(pluginentry.plugin.actions) == 0:
                continue

            menu = Menu(self, pluginentry.plugin.name)
            for action in pluginentry.plugin.actions:
                name, func = action[:2]
                if len(action) == 3:
                    shortcut = action[2]
                else:
                    shortcut = None 
                menu.add_action(name, func=partial(func, editor), shortcut=shortcut)
            self.menus.append(menu)

        for menu in self.menus:
            self.addMenu(menu)

    def clear_menu_actions(self):
        for menu in self.menus:
            menu.deleteLater()

        self.menus = []


if __name__ == "__main__":
    import time

    pluginmenu = PluginMenu(None)
    pluginmenu.load_plugins()

    while True:
        for pluginname in pluginmenu.plugins:
            for action, func in pluginmenu.plugins[pluginname].plugin.actions:
                print(action)
                func(None)

        if pluginmenu.plugin_folder_changed():
            pluginmenu.reload_changed_plugins()
            pluginmenu.plugin_folder_update_time()

        time.sleep(1)
    print("Hi")