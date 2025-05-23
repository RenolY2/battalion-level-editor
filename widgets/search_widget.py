import os
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt6.QtCore import Qt
import PyQt6.QtCore as QtCore

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor

from widgets.editor_widgets import open_error_dialog
from widgets.tree_view import LevelDataTreeView, ObjectGroup, NamedItem
from widgets.menu.menubar import Menu
from lib.searchquery import create_query, find_best_fit, autocompletefull, QueryDepthTooDeepError
from lib.BattalionXMLLib import BattalionObject
from widgets.lua_search_widgets import LuaSearchResultItem
import typing

class LabeledRadioBox(QtWidgets.QWidget):
    def __init__(self, text, parent):
        super().__init__(parent)
        self.l = QtWidgets.QHBoxLayout(self)
        self.radio = QtWidgets.QRadioButton(self)
        self.text = QtWidgets.QLabel(self)
        self.text.setText(text)
        self.l.addWidget(self.radio)
        self.l.addWidget(self.text)
        self.setMaximumWidth(100)

    def checked(self):
        return self.radio.isChecked()


class AutocompleteDropDown(QtWidgets.QComboBox):
    tabactivated = pyqtSignal()

    def __init__(self, parent, items):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        for item in items:
            self.addItem(item)

        self.max = len(items)

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Tab:
            self.tabactivated.emit()
        else:
            super().keyPressEvent(e)

    def scroll_up(self):
        if self.maxCount() == 0:
            return

        index = self.currentIndex()
        index -= 1
        if index < 0:
            index = self.max-1

        self.setCurrentIndex(index)

    def scroll_down(self):
        if self.maxCount() == 0:
            return

        index = self.currentIndex()
        index += 1
        if index >= self.max:
            index = 0

        self.setCurrentIndex(index)

        print(self.currentIndex(), self.currentText())


def to_clipboard(text):
    clipboard = QtWidgets.QApplication.clipboard()
    clipboard.setText(text)

OBJECTS = 0
LUA = 1


class SearchTreeView(LevelDataTreeView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMaximumWidth(9999)

        self.items = []

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.run_context_menu)

        self.mode = OBJECTS
        self.lua_scripts = None

    def set_objects_mode(self):
        if not self.mode == OBJECTS:
            self.setColumnCount(2)
            self.setHeaderLabels(["XML Object", "Searched Values"])
            self.invisibleRootItem().takeChildren()
            self.setup_groups()
        self.mode = OBJECTS

    def set_lua_mode(self):
        if not self.mode == LUA:
            self.setColumnCount(3)
            self.setHeaderLabels(["File", "Line", "Content"])
            self.invisibleRootItem().takeChildren()
            self.setup_lua_group()

        self.mode = LUA

    def setup_lua_group(self):
        self.lua_scripts = self._add_group("Lua Scripts")

    def run_context_menu(self, pos):
        if self.mode == LUA:
            return

        item = self.itemAt(pos)
        context_menu = QtWidgets.QMenu(self)

        if item.bound_to is not None:
            copy_id = QtGui.QAction("Copy ID")
            results = QtGui.QAction("Copy Values")

            def copy_id_to_clipboard():
                to_clipboard(item.bound_to.id)

            def copy_results_to_clipboard():
                to_clipboard(item.text(1))

            copy_id.triggered.connect(copy_id_to_clipboard)
            context_menu.addAction(copy_id)

            results.triggered.connect(copy_results_to_clipboard)
            context_menu.addAction(results)

            if hasattr(item, "results"):
                if len(item.results) > 1:
                    result_first = QtGui.QAction("Copy First Value")

                    def copy_first_result():
                        to_clipboard(item.results[0])

                    result_first.triggered.connect(copy_first_result)
                    context_menu.addAction(result_first)

                    result_second = QtGui.QAction("Copy Second Value")

                    def copy_second_result():
                        to_clipboard(item.results[1])

                    result_second.triggered.connect(copy_second_result)
                    context_menu.addAction(result_second)

        if context_menu.actions():
            context_menu.exec(self.mapToGlobal(pos))
            context_menu.destroy()
            del context_menu

    def set_lua_scripts(self, script_results):
        self.lua_scripts.remove_children()
        for name, line, content in script_results:
            item = LuaSearchResultItem(self.lua_scripts, name, str(line), content.strip())
            itemflag = QtCore.Qt.ItemFlag
            item.setFlags(itemflag.ItemIsEnabled | itemflag.ItemIsSelectable | itemflag.ItemIsEditable)

        if script_results:
            self.lua_scripts.setExpanded(True)
            self.resizeColumnToContents(0)
            self.resizeColumnToContents(1)

    def set_objects(self, objects):
        self.reset()
        for category in self.get_top_categories():
            category.setText(1, "")
            category.objectcount = 0

        extra_categories = {}
        self.items = []
        typecount = {}

        for object, values in objects:
            #object: BattalionObject
            objecttype = object.type
            if objecttype not in extra_categories:
                extra_categories[objecttype] = ObjectGroup(objecttype)
                print(objecttype)

            parent = extra_categories[objecttype]
            item = NamedItem(parent, object.name, object)
            itemflag = QtCore.Qt.ItemFlag
            item.setFlags(itemflag.ItemIsEnabled | itemflag.ItemIsSelectable | itemflag.ItemIsEditable)
            writtenvalues = []
            for val in values:
                if isinstance(val, BattalionObject):
                    writtenvalues.append(val.name)
                else:
                    writtenvalues.append(str(val))
            max = 15
            item.results = writtenvalues[:10]
            if len(writtenvalues) > max:
                item.setText(1, ", ".join(writtenvalues[:max]) + " and {0} more".format(len(writtenvalues)-15))
            else:
                item.setText(1, ", ".join(writtenvalues))
            self.items.append(item)
            typecount[objecttype] = typecount[objecttype] + 1 if objecttype in typecount else 1

        targetcounts = {}

        for categoryname in sorted(extra_categories.keys()):
            category = extra_categories[categoryname]

            target = self.choose_category(categoryname)
            target.addChild(category)

            if categoryname in typecount:
                if typecount[categoryname] == 1:
                    category.setText(1, "{0} result".format(typecount[categoryname]))
                elif typecount[categoryname] > 1:
                    category.setText(1, "{0} results".format(typecount[categoryname]))
                if target.text(0) not in targetcounts:
                    targetcounts[target.text(0)] = typecount[categoryname]
                else:
                    targetcounts[target.text(0)] += typecount[categoryname]

        for category in self.get_top_categories():
            name = category.text(0)
            if name in targetcounts:
                if targetcounts[name] == 1:
                    category.setText(1, "1 result")
                else:
                    category.setText(1, "{0} results".format(targetcounts[name]))
                category.objectcount = targetcounts[name]
            else:
                category.setText(1, "0 results")


def cursor_select(cursor, start, end):
    curr = cursor.position()

    cursor.setPosition(start)
    cursor.selectionStart()
    cursor.setPosition(end)
    cursor.selectionEnd()

    cursor.setPosition(end)
    pass


def find_rightmost(collection, text, start, end):
    rightmost = -1
    for symbol in collection:
        sympos = text.rfind(symbol, start, end)
        if sympos > rightmost:
            rightmost = sympos

    return rightmost


class AutocompleteTextEdit(QtWidgets.QTextEdit):
    trigger_search = pyqtSignal()

    def __init__(self, parent, editor):
        super().__init__(parent)
        self.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.editor: bw_editor.LevelEditor = editor
        self.autocomplete: AutocompleteDropDown = None
        self.enter_presses = 0

    def get_last_field(self):
        text = self.toPlainText()
        cursor = self.textCursor()
        prev = find_rightmost([" ", ">", "<", "=", "!"], text, 0, cursor.position())#text.rfind(" ", 0, cursor.position())
        if prev == -1:
            field = text[0:cursor.position()]
        else:
            field = text[prev+1:cursor.position()]

        if field:
            rightmost_dot = field.rfind(".")
            field = field[rightmost_dot + 1:]
            if field:

                return field#text[rightmost_dot+1:cursor.position()]
            else:
                return ""
        else:
            return ""

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if self.autocomplete is not None:
            self.autocomplete.hide()
            self.autocomplete.deleteLater()
            del self.autocomplete
            self.autocomplete: AutocompleteDropDown = None

        super().mousePressEvent(e)

    def update_autocomplete(self):
        field = self.get_last_field()
        cursor = self.textCursor()
        for i in range(len(field)):
            cursor.deletePreviousChar()
        cursor.insertText(self.autocomplete.currentText())

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        surpressenter = False

        if self.autocomplete is not None and e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Return, Qt.Key.Key_Tab):
            if e.key() == Qt.Key.Key_Up:
                self.autocomplete.scroll_up()
            elif e.key() == Qt.Key.Key_Down:
                self.autocomplete.scroll_down()

            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Tab):
                field = self.get_last_field()
                cursor = self.textCursor()
                print(field)
                for i in range(len(field)):
                    cursor.deletePreviousChar()
                cursor.insertText(self.autocomplete.currentText())

                self.autocomplete.hide()
                self.autocomplete.deleteLater()
                del self.autocomplete
                self.autocomplete: AutocompleteDropDown = None
                if e.key() == Qt.Key.Key_Return:
                    surpressenter = True

        elif self.autocomplete is not None:
            self.autocomplete.hide()
            self.autocomplete.deleteLater()
            del self.autocomplete
            self.autocomplete: AutocompleteDropDown = None

        if e.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right): #(e.key() == Qt.Key_Tab):
            if e.key() != Qt.Key.Key_Tab:
                super().keyPressEvent(e)

            text = self.toPlainText()
            cursor = self.textCursor()
            prev = find_rightmost([" ", ">", "<", "=", "!"], text, 0, cursor.position()) #text.rfind(" ",0, cursor.position())
            if prev == -1:
                field = text[0:cursor.position()]
            else:
                field = text[prev+1:cursor.position()]
            if field:
                rightmost_dot = field.rfind(".")
                field = field[rightmost_dot+1:]
                if rightmost_dot == -1:
                    field = field.lstrip(" ")
                if field:
                    bestmatch = find_best_fit(field, bw2=self.editor.level_file.bw2, values=rightmost_dot==-1, max=15)
                    if len(bestmatch) > 0:
                        rect = self.cursorRect()

                        self.autocomplete = AutocompleteDropDown(self, [x[0] for x in bestmatch])
                        #self.autocomplete.currentIndexChanged.connect(self.update_autocomplete)
                        self.autocomplete.textActivated.connect(self.update_autocomplete)
                        self.autocomplete.tabactivated.connect(self.update_autocomplete)
                        self.autocomplete.move(rect.bottomRight().x(), rect.bottomRight().y()+5)


                        self.autocomplete.show()
                        #self.autocomplete.showPopup()
                        self.setFocus()

                    """if bestmatch:
                        cursor.clearSelection()
                        for i in range(len(field)):
                            cursor.deletePreviousChar()
                        cursor.insertText(bestmatch[0][0])"""

        else:

            if e.key() == Qt.Key.Key_Return and surpressenter:
                surpressenter = False
            else:
                if self.autocomplete is not None and e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                    pass
                else:
                    super().keyPressEvent(e)
                surpressenter = False

            if self.enter_presses == 0 and e.key() == Qt.Key.Key_Return:
                self.enter_presses = 1
            elif self.enter_presses == 1:
                if e.key() == Qt.Key.Key_Return:
                    self.trigger_search.emit()
                else:
                    self.enter_presses = 0


class HelpWindow(QtWidgets.QMdiSubWindow):
    closing = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(800, 400)

        self.helptext = QtWidgets.QTextEdit(self)
        self.helptext.setReadOnly(True)
        self.helptext.setText("""The "Find Objects" utility allows filtering the massive selection of objects in a Battalion Wars level based on your search query!

If "Text Search" is enabled, it will perform a regular text search. Example: If you search for type="eInvisType", it will output all objects that have that particular text in their XML data.
If "Text Search" is disabled, it will perform a more complex search that can traverse BW's data structures, see below for examples.

Syntax example:
self.id = 50032934
This search term finds an object whose id is exactly 50032934.

self.type = cAirVehicle & self.State != AI_STATE_NORMAL
This search term finds an object whose type is a cAirVehicle but whose state is not AI_STATE_NORMAL.

self.type = cGroundVehicle & self.mBase.mArmy = eXylvanian & self.mBase.mMaximumCameraSpeed > 3
This search term finds a ground vehicle whose base object belongs to Xylvania and has a maximum camera speed bigger than 3.

self.mName contains lod | self.mName contains box
This search term finds objects whose name contains either the word "lod" or the word "box". The comparison is case insensitive and will also match e.g. "LOD".

self.type != cAirVehicle & (self.mLockToSurface = True | self.mStartWayPoint = 0)
This search term finds objects whose type isn't cAirVehicle and that either have lock to surface enabled or the start waypoint set to 0.

self.mPassenger.id = 50033037
This search finds objects with a passenger that has the id 50033037. With lists of references/values, the comparison is done for each reference/value in the list, e.g. each passenger, and is true if at least one comparison is true.

self.Seed & self.mBase.MaxSize != 18
This will record the seed of every object whose mBase has a MaxSize that is not equal to 18 in the "Searched Result" column, in addition to the MaxSize value.
This can be used to output additional info about objects whose data match your query into the search results.

Possible comparison operations: = (equal), != (unequal), > (bigger than), >= (bigger than or equal), < (less than), <= (less than or equal).
Possible string content search operations: contains, excludes
Additional fields of interest: 
modelname (name of 3D model of the object regardless of type)
references (example: self.references.id = 50032934 matches all objects that have any pointer pointing to object with id 50032934)
enums (example: self.enums = DAMAGE_NO_DAMAGE matches all objects that have DAMAGE_NO_DAMAGE as any of their enums)


Many fields can be searched for and it is possible to string together multiple fields with a dot that will follow the chain of references to retrieve a value.
You can save and load search queries using the Save Query/Load Query buttons. The Find button executes the search query.
Clicking on an object in the list will select it in the main window. Double click will teleport your view to that object. Ctrl + E will open up the edit window.
""")

        self.setWidget(self.helptext)

    def closeEvent(self, closeEvent: QtGui.QCloseEvent) -> None:
        self.closing.emit()


class SearchMenubar(QtWidgets.QMenuBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.help = self.addAction("Help")
        self.help.triggered.connect(self.show_help)
        self.helpwindow = None

    def show_help(self):
        self.helpwindow = HelpWindow()
        self.helpwindow.closing.connect(self.killhelp)
        self.helpwindow.show()

    def killhelp(self):
        self.helpwindow = None


class SplitterWithLayouts(QtWidgets.QSplitter):
    def add_layout(self, layout):
        layout_holder = QtWidgets.QWidget(self)
        layout_holder.setLayout(layout)
        self.addWidget(layout_holder)


class SearchWidget(QtWidgets.QMainWindow):
    closing = pyqtSignal()

    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor
        self.setWindowTitle("Object Search")
        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))
        #self.basewidget = QtWidgets.QWidget(self)

        #self.setCentralWidget(self.basewidget)
        self.menubar = SearchMenubar(self)
        self.setMenuBar(self.menubar)

        self.splitter = SplitterWithLayouts(self)
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.setCentralWidget(self.splitter)
        #self.vlayout = QtWidgets.QVBoxLayout(self)
        #self.basewidget.setLayout(self.vlayout)


        self.queryinput = AutocompleteTextEdit(self, self.editor)

        self.searchbutton = QtWidgets.QPushButton("Find", self)
        self.searchbutton.pressed.connect(self.do_search)
        self.queryinput.trigger_search.connect(self.do_search)

        self.textmodebutton = LabeledRadioBox("Text Search", self)
        self.luamodebutton = LabeledRadioBox("Lua Search", self)

        def toggle_textmode_off(x):
            if x:
                self.textmodebutton.radio.setChecked(False)

        def toggle_luamode_off(x):
            if x:
                self.luamodebutton.radio.setChecked(False)

        self.textmodebutton.radio.toggled.connect(toggle_luamode_off)
        self.luamodebutton.radio.toggled.connect(toggle_textmode_off)

        self.select_all = QtWidgets.QPushButton("Select All")
        self.save_query = QtWidgets.QPushButton("Save Query")
        self.load_query = QtWidgets.QPushButton("Load Query")

        self.select_all.pressed.connect(self.select_all_action)
        self.save_query.pressed.connect(self.action_save_query)
        self.load_query.pressed.connect(self.action_load_query)

        #self.vlayout.addWidget(self.queryinput)
        self.splitter.addWidget(self.queryinput)

        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout12 = QtWidgets.QHBoxLayout(self)

        self.hlayout12.addWidget(self.searchbutton)
        self.hlayout12.addWidget(self.textmodebutton)
        self.hlayout12.addWidget(self.luamodebutton)
        self.hlayout.addLayout(self.hlayout12)
        #self.vlayout.addLayout(self.hlayout)
        self.button_and_searchresults_layout = QtWidgets.QVBoxLayout(self)
        self.button_and_searchresults_layout.setContentsMargins(0, 0, 0, 0)
        self.button_and_searchresults_layout.addLayout(self.hlayout)
        #self.splitter.add_layout(self.hlayout)

        self.hlayout2 = QtWidgets.QHBoxLayout(self)
        self.hlayout2.addWidget(self.select_all)
        self.hlayout2.addWidget(self.load_query)
        self.hlayout2.addWidget(self.save_query)

        self.hlayout.addLayout(self.hlayout2)


        self.treeview = SearchTreeView(self)
        self.button_and_searchresults_layout.addWidget(self.treeview)
        #self.vlayout.addWidget(self.treeview)
        self.splitter.add_layout(self.button_and_searchresults_layout)
        self.treeview.itemDoubleClicked.connect(self.editor.do_goto_action)
        self.treeview.itemSelectionChanged.connect(self.tree_select)

        self.shortcut = QtGui.QShortcut("Ctrl+E", self)
        self.shortcut.activated.connect(self.editor.pik_control.action_open_edit_object)

        self.query_path = "searchqueries/"

    def select_all_action(self):
        self.editor.level_view.selected = []
        self.editor.level_view.selected_positions = []
        self.editor.level_view.selected_rotations = []
        self.treeview.selectAll()

        for item in self.treeview.items:
            self.editor.level_view.selected.append(item.bound_to)
            mtx = item.bound_to.getmatrix()
            if mtx is not None:
                self.editor.level_view.selected_positions.append(mtx)

        self.editor.update_3d()
        self.editor.level_view.do_redraw(forceselected=True)
        self.editor.level_view.select_update.emit()

    def open_help(self):
        pass

    def tree_select(self):
        current = self.treeview.selectedItems()
        if len(current) == 1:
            self.editor.tree_select_object(current[0])

    def do_search(self):
        searchtext = self.queryinput.toPlainText()
        if not searchtext:
            return

        if self.luamodebutton.checked():
            self.treeview.set_lua_mode()
            searchtext = self.queryinput.toPlainText()
            results = []

            for script_path in self.editor.lua_workbench.get_lua_script_paths():
                with open(script_path, "r") as f:
                    for i, line in enumerate(f):
                        if searchtext in line:
                            results.append((os.path.basename(script_path), i + 1, line))

            self.treeview.set_lua_scripts(results)
        else:
            self.treeview.set_objects_mode()
            objects = []
            if self.textmodebutton.checked():
                searchtext = self.queryinput.toPlainText()
                searchtextlower = searchtext.lower()
                if not searchtext:
                    return

                for object in self.editor.level_file.objects.values():
                    orig = object.tostring()
                    resultlower = orig.lower()
                    if searchtextlower in resultlower:
                        pos = resultlower.find(searchtextlower)
                        origtext = orig[pos:pos+len(searchtext)]
                        if len(origtext) > 100:
                            origtext = origtext[:100]+"..."
                        objects.append((object, [origtext]))
                print("searched all level file objects")
                for object in self.editor.preload_file.objects.values():
                    orig = object.tostring()
                    resultlower = orig.lower()
                    if searchtextlower in resultlower:
                        pos = resultlower.find(searchtextlower)
                        origtext = orig[pos:pos + len(searchtext)]
                        if len(origtext) > 100:
                            origtext = origtext[:100] + "..."
                        objects.append((object, [origtext]))
                print("searched all preload objects")
            else:
                searchquery = self.queryinput.toPlainText().replace("\n", "")
                try:
                    query = create_query(searchquery)
                except Exception as err:
                    open_error_dialog("Cannot save: Search query has syntax errors.", self)
                    return

                try:
                    for object in self.editor.level_file.objects.values():
                        if query.evaluate(object):
                            values = query.get_values(object)
                            objects.append((object, values))
                    print("searched all level file objects")
                    for object in self.editor.preload_file.objects.values():
                        if query.evaluate(object):
                            values = query.get_values(object)
                            objects.append((object, values))
                    print("searched all preload objects")
                except QueryDepthTooDeepError as err:
                    open_error_dialog(str(err), self)
                    return

            self.treeview.set_objects(objects)
            print("set objects")
            if len(objects) > 300:
                model = self.treeview.model()
                for i in range(model.rowCount(self.treeview.rootIndex())):
                    index = model.index(i, 0)
                    item = self.treeview.itemFromIndex(index)
                    if item.objectcount < 300:
                        self.treeview.expandRecursively(index)
                    QtWidgets.QApplication.processEvents()
            else:
                self.treeview.expandAll()
            print("expanded")
            self.treeview.resizeColumnToContents(0)
            print("resized")

    def action_load_query(self):
        filepath, choosentype = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open File",
            self.query_path,
            "Text (*.txt);;All files (*)")

        if filepath:
            with open(filepath, "r") as f:
                self.queryinput.setText(f.read())
            self.query_path = filepath

    def action_save_query(self):
        try:
            query = create_query(self.queryinput.toPlainText())
        except Exception as err:
            open_error_dialog("Cannot search: Search query has syntax errors.", self)
        else:
            filepath, choosentype = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save File",
                self.query_path,
                "Text (*.txt);;All files (*)")

            if filepath:
                with open(filepath, "w") as f:
                    f.write(self.queryinput.toPlainText())
                self.query_path = filepath

    def closeEvent(self, closeEvent: QtGui.QCloseEvent):
        self.closing.emit()