import importlib
import os
import traceback

from collections import namedtuple
from PyQt6.QtCore import QTimer
from widgets.menu.menu import Menu

PluginEntry = namedtuple("PluginEntry", ("module", "plugin"))

pluginfolder = "plugins"


class PluginMenu(Menu):
    def __init__(self, parent):
        super().__init__(parent, "Plugins")

        self.plugins = {}
        self.plugin_folder_last_changed = os.stat(pluginfolder).st_mtime

        self.menus = []

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.hot_reload)
        self.timer.start()

    def add_menu_actions(self):
        for pluginname, pluginentry in self.plugins.items():
            menu = Menu(self, pluginentry.plugin.name)
            for action in pluginentry.plugin.actions:
                name, func = action[:2]
                if len(action) == 3:
                    shortcut = action[2]
                else:
                    shortcut = None 
                menu.add_action(name, func=func, shortcut=shortcut)
            self.menus.append(menu)

        for menu in self.menus:
            self.addMenu(menu)

    def clear_menu_actions(self):
        for menu in self.menus:
            menu.deleteLater()

        self.menus = []

    def hot_reload(self):
        if self.plugin_folder_changed():
            self.reload_changed_plugins()
            self.plugin_folder_update_time()

            self.clear_menu_actions()
            self.add_menu_actions()

    def plugin_folder_update_time(self):
        self.plugin_folder_last_changed = os.stat(pluginfolder).st_mtime

    def plugin_folder_changed(self):
        return self.plugin_folder_last_changed != os.stat(pluginfolder).st_mtime

    def plugin_changed(self, pluginname):
        pluginpath = os.path.join(pluginfolder, pluginname+".py")
        return self.plugins[pluginname].module.__time != os.stat(pluginpath).st_mtime

    def plugin_update_time(self, pluginname):
        pluginpath = os.path.join(pluginfolder, pluginname + ".py")
        self.plugins[pluginname].module.__time = os.stat(pluginpath).st_mtime

    def is_loaded(self, pluginname):
        return pluginname in self.plugins

    def load_plugin(self, pluginname, reload=False):
        assert pluginname not in self.plugins
        module = importlib.import_module("plugins."+pluginname)
        plugin = module.Plugin()
        module.__time = os.stat(pluginfolder).st_mtime
        self.plugins[pluginname] = PluginEntry(module, plugin)

    def reload_plugin(self, pluginname):
        self.plugins[pluginname].plugin.unload()  # Allow the plugin to do cleanup before reloading it

        try:
        module = importlib.reload(self.plugins[pluginname].module)
        plugin = module.Plugin()

        self.plugins[pluginname] = PluginEntry(module, plugin)

    def reload_changed_plugins(self):
        self.load_plugins()  # Check for newly added plugins

        for pluginname in self.plugins:
            if self.plugin_changed(pluginname):
                self.reload_plugin(pluginname)

            self.plugin_update_time(pluginname)

    def load_plugins(self):
        for pluginfile in os.listdir("plugins/"):
            if pluginfile.startswith("plugin") and pluginfile.endswith(".py"):
                pluginname = pluginfile[:-3]
                if not self.is_loaded(pluginname):
                    self.load_plugin(pluginname)

    def execute_event(self, eventname, *args, **kwargs):
        for pluginname, entry in self.plugins.items():
            if hasattr(entry.plugin, eventname):
                try:
                    func = getattr(entry.plugin, eventname)
                    func(*args, **kwargs)
                except:
                    traceback.print_tb()


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