import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


from widgets.tree_view import LevelDataTreeView, ObjectGroup, NamedItem
from lib.searchquery import create_query


class SearchTreeView(LevelDataTreeView):
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

        self.queryinput = QtWidgets.QTextEdit(self)
        self.queryinput.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.queryinput.setContextMenuPolicy(Qt.CustomContextMenu)

        self.searchbutton = QtWidgets.QPushButton("Find", self)
        self.searchbutton.pressed.connect(self.do_search)

        self.vlayout.addWidget(self.queryinput)
        self.vlayout.addWidget(self.searchbutton)

        self.treeview = SearchTreeView(self)
        self.vlayout.addWidget(self.treeview)

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