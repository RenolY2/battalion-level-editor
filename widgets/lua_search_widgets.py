import os
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
from widgets.editor_widgets import SearchBar
from lib.lua.luaworkshop import LuaWorkbench
from widgets.editor_widgets import open_message_dialog


class LuaSearchBar(SearchBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.case_sensitive = QtWidgets.QCheckBox(self)
        self.case_sensitive_text = QtWidgets.QLabel("Case Sensitive", self)
        self.l.addWidget(self.case_sensitive)
        self.l.addWidget(self.case_sensitive_text)

    def is_case_sensitive(self):
        return self.case_sensitive.isChecked()


class LuaSearchResultItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent, script, line, text):
        super().__init__(parent)
        self.script = script
        self.line = line
        self.textcontent = text
        self.setText(0, self.script)
        self.setText(1, self.line)
        self.setText(2, self.textcontent)


class LuaFindWindow(QtWidgets.QMdiSubWindow):
    def __init__(self, parent, luaworkbench: LuaWorkbench):
        super().__init__(parent)
        self.resize(900, 500)
        self.setWindowTitle("Lua Script Search")
        self.centralwidget = QtWidgets.QWidget(self)
        self.vbox = QtWidgets.QVBoxLayout(self)
        self.searchbar = LuaSearchBar(self)
        self.results = QtWidgets.QTreeWidget(self)
        self.results.setColumnCount(3)
        self.results.setHeaderLabels(["File", "Line", "Content"])

        self.vbox.addWidget(self.searchbar)
        self.vbox.addWidget(self.results)
        self.centralwidget.setLayout(self.vbox)
        self.luaworkbench = luaworkbench
        self.setWidget(self.centralwidget)
        self.searchbar.find.connect(self.search_line)

        self.results.itemDoubleClicked.connect(self.open_script)

    def open_script(self, item):
        lua_script_name = item.script.removesuffix(".lua")
        self.luaworkbench.open_script(lua_script_name)

    def search_line(self, text):
        root = self.results.invisibleRootItem()
        root.takeChildren()

        if text:
            if not self.searchbar.is_case_sensitive():
                text = text.lower()
                case_sensitive = False
            else:
                case_sensitive = True

            results = []
            for script_path in self.luaworkbench.get_lua_script_paths():
                with open(script_path, "r") as f:
                    for i, line in enumerate(f):
                        if case_sensitive:
                            if text in line:
                                results.append((os.path.basename(script_path), i+1, line))
                        else:
                            if text in line.lower():
                                results.append((os.path.basename(script_path), i + 1, line))

            for script, line, text in results:
                item = LuaSearchResultItem(self.results,
                                           script.strip(), str(line), text.strip())
                self.results.addTopLevelItem(item)

            if len(results) == 0:
                open_message_dialog("No results found.")
            else:
                self.results.resizeColumnToContents(0)
                self.results.resizeColumnToContents(1)