import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt
import PyQt5.QtCore as QtCore

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor

from widgets.editor_widgets import open_error_dialog
from widgets.tree_view import LevelDataTreeView, ObjectGroup, NamedItem
from widgets.menu.menubar import Menu
from lib.searchquery import create_query, find_best_fit, autocompletefull, QueryDepthTooDeepError
from lib.BattalionXMLLib import BattalionObject


class AutocompleteDropDown(QtWidgets.QComboBox):
    tabactivated = pyqtSignal()
    def __init__(self, parent, items):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        for item in items:
            self.addItem(item)

        self.max = len(items)

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == Qt.Key_Tab:
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


class SearchTreeView(LevelDataTreeView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMaximumWidth(9999)
        self.setColumnCount(2)
        self.setHeaderLabels(["XML Object", "Searched Values"])

    def set_objects(self, objects):
        self.reset()
        for category in self.get_top_categories():
            category.setText(1, "")
            category.objectcount = 0

        extra_categories = {}

        typecount = {}

        for object, values in objects:
            #object: BattalionObject
            objecttype = object.type
            if objecttype not in extra_categories:
                extra_categories[objecttype] = ObjectGroup(objecttype)
                print(objecttype)

            parent = extra_categories[objecttype]
            item = NamedItem(parent, object.name, object)
            writtenvalues = []
            for val in values:
                if isinstance(val, BattalionObject):
                    writtenvalues.append(val.name)
                else:
                    writtenvalues.append(str(val))
            max = 15
            if len(writtenvalues) > max:
                item.setText(1, ", ".join(writtenvalues[:max]) + " and {0} more".format(len(writtenvalues)-15))
            else:
                item.setText(1, ", ".join(writtenvalues))

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
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.editor: bw_editor.LevelEditor = editor
        self.autocomplete: AutocompleteDropDown = None

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

        if self.autocomplete is not None and e.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Tab):
            if e.key() == Qt.Key_Up:
                self.autocomplete.scroll_up()
            elif e.key() == Qt.Key_Down:
                self.autocomplete.scroll_down()

            if e.key() in (Qt.Key_Return, Qt.Key_Tab):
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
                if e.key() == Qt.Key_Return:
                    surpressenter = True

        elif self.autocomplete is not None:
            self.autocomplete.hide()
            self.autocomplete.deleteLater()
            del self.autocomplete
            self.autocomplete: AutocompleteDropDown = None

        if e.key() not in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right): #(e.key() == Qt.Key_Tab):
            if e.key() == Qt.Key_Return:
                pass
            elif e.key() != Qt.Key_Tab:
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

            if e.key() == Qt.Key_Return and surpressenter:
                surpressenter = False
            else:
                if self.autocomplete is not None and e.key() in (Qt.Key_Up, Qt.Key_Down):
                    pass
                else:
                    super().keyPressEvent(e)
                surpressenter = False


class HelpWindow(QtWidgets.QMdiSubWindow):
    closing = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(800, 400)

        self.helptext = QtWidgets.QTextEdit(self)
        self.helptext.setReadOnly(True)
        self.helptext.setText("""The "Find Objects" utility allows filtering the massive selection of objects in a Battalion Wars level based on your search query!

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

Possible comparison operations: = (equal), != (unequal), > (bigger than), >= (bigger than or equal), < (less than), <= (less than or equal).
Possible string content search operations: contains, excludes

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


class SearchWidget(QtWidgets.QMainWindow):
    closing = pyqtSignal()

    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor
        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))
        self.basewidget = QtWidgets.QWidget(self)

        self.setCentralWidget(self.basewidget)
        self.menubar = SearchMenubar(self)
        self.setMenuBar(self.menubar)

        self.vlayout = QtWidgets.QVBoxLayout(self)
        self.basewidget.setLayout(self.vlayout)


        self.queryinput = AutocompleteTextEdit(self, self.editor)


        self.searchbutton = QtWidgets.QPushButton("Find", self)
        self.searchbutton.pressed.connect(self.do_search)

        self.save_query = QtWidgets.QPushButton("Save Query")
        self.load_query = QtWidgets.QPushButton("Load Query")

        self.save_query.pressed.connect(self.action_save_query)
        self.load_query.pressed.connect(self.action_load_query)

        self.vlayout.addWidget(self.queryinput)

        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.hlayout.addWidget(self.searchbutton)
        self.vlayout.addLayout(self.hlayout)

        self.hlayout2 = QtWidgets.QHBoxLayout(self)
        self.hlayout2.addWidget(self.load_query)
        self.hlayout2.addWidget(self.save_query)

        self.hlayout.addLayout(self.hlayout2)


        self.treeview = SearchTreeView(self)
        self.vlayout.addWidget(self.treeview)
        self.treeview.itemDoubleClicked.connect(self.editor.do_goto_action)
        self.treeview.itemSelectionChanged.connect(self.tree_select)

        self.shortcut = QtWidgets.QShortcut("Ctrl+E", self)
        self.shortcut.activated.connect(self.editor.pik_control.action_open_edit_object)

        self.query_path = "searchqueries/"

    def open_help(self):
        pass

    def tree_select(self):
        current = self.treeview.selectedItems()
        if len(current) == 1:
            self.editor.tree_select_object(current[0])

    def do_search(self):
        searchquery = self.queryinput.toPlainText().replace("\n", "")
        try:
            query = create_query(searchquery)
        except Exception as err:
            open_error_dialog("Cannot save: Search query has syntax errors.", self)
            return

        try:
            objects = []
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