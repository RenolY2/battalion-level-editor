import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


from widgets.tree_view import LevelDataTreeView, ObjectGroup, NamedItem
from lib.searchquery import create_query, find_best_fit, autocompletefull


class AutocompleteDropDown(QtWidgets.QComboBox):
    def __init__(self, parent, items):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        for item in items:
            self.addItem(item)

        self.max = len(items)

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

    def set_objects(self, objects):
        self.reset()

        extra_categories = {}

        for object in objects:
            #object: BattalionObject
            objecttype = object.type
            if objecttype not in extra_categories:
                extra_categories[objecttype] = ObjectGroup(objecttype)
                print(objecttype)

            parent = extra_categories[objecttype]
            item = NamedItem(parent, object.name, object)

        for categoryname in sorted(extra_categories.keys()):
            category = extra_categories[categoryname]
            target = self.choose_category(categoryname)
            target.addChild(category)


def cursor_select(cursor, start, end):
    curr = cursor.position()

    cursor.setPosition(start)
    cursor.selectionStart()
    cursor.setPosition(end)
    cursor.selectionEnd()

    cursor.setPosition(end)
    pass


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
        prev = text.rfind(" ", 0, cursor.position())
        if prev == -1:
            prev = 0
        field = text[prev:cursor.position()]
        if field:
            rightmost_dot = field.rfind(".")
            field = field[rightmost_dot + 1:]
            if field:

                return text[rightmost_dot+1:cursor.position()]
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
        if self.autocomplete is not None and e.key() in (Qt.Key_Up, Qt.Key_Down):
            if e.key() == Qt.Key_Up:
                self.autocomplete.scroll_up()
            elif e.key() == Qt.Key_Down:
                self.autocomplete.scroll_down()
            field = self.get_last_field()
            cursor = self.textCursor()
            print(field)
            for i in range(len(field)):
                cursor.deletePreviousChar()
            cursor.insertText(self.autocomplete.currentText())

        elif self.autocomplete is not None:
            self.autocomplete.hide()
            self.autocomplete.deleteLater()
            del self.autocomplete
            self.autocomplete: AutocompleteDropDown = None

        if (e.key() == Qt.Key_Tab):
            text = self.toPlainText()
            cursor = self.textCursor()
            prev = text.rfind(" ",0, cursor.position())
            if prev == -1:
                prev = 0
            field = text[prev:cursor.position()]
            if field:
                rightmost_dot = field.rfind(".")
                field = field[rightmost_dot+1:]
                if field:
                    print(field)
                    bestmatch = find_best_fit(field, bw2=self.editor.level_file.bw2, max=15)
                    rect = self.cursorRect()

                    self.autocomplete = AutocompleteDropDown(self, [x[0] for x in bestmatch])
                    self.autocomplete.currentIndexChanged.connect(self.update_autocomplete)
                    self.autocomplete.move(rect.bottomRight().x(), rect.bottomRight().y()+5)

                    self.autocomplete.show()
                    self.setFocus()

                    if bestmatch:
                        cursor.clearSelection()
                        for i in range(len(field)):
                            cursor.deletePreviousChar()
                        cursor.insertText(bestmatch[0][0])
        else:
            super().keyPressEvent(e)


class SearchWidget(QtWidgets.QMdiSubWindow):
    closing = pyqtSignal()

    def __init__(self, editor):
        super().__init__()
        self.editor: bw_editor.LevelEditor = editor
        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))
        self.basewidget = QtWidgets.QWidget(self)

        self.setWidget(self.basewidget)

        self.vlayout = QtWidgets.QVBoxLayout(self)
        self.basewidget.setLayout(self.vlayout)

        self.queryinput = AutocompleteTextEdit(self, self.editor)


        self.searchbutton = QtWidgets.QPushButton("Find", self)
        self.searchbutton.pressed.connect(self.do_search)

        self.save_query = QtWidgets.QPushButton("Save Query")
        self.load_query = QtWidgets.QPushButton("Load Query")

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

    def tree_select(self):
        current = self.treeview.selectedItems()
        if len(current) == 1:
            self.editor.tree_select_object(current[0])

    def do_search(self):
        searchquery = self.queryinput.toPlainText().replace("\n", "")
        try:
            query = create_query(searchquery)
        except Exception as err:
            print(err)
            return

        objects = []
        for object in self.editor.level_file.objects.values():
            if query.evaluate(object):
                objects.append(object)

        self.treeview.set_objects(objects)
        self.treeview.expandAll()

    def closeEvent(self, closeEvent: QtGui.QCloseEvent):
        self.closing.emit()