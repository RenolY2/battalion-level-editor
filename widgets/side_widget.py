from PyQt5.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence
from PyQt5.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu, QLineEdit,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit, QAction, QShortcut)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt
from widgets.data_editor import choose_data_editor

class PikminSideWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parent = args[0]

        self.parent = parent
        self.setMaximumSize(QSize(700, 1500))
        self.setMinimumWidth(300)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setAlignment(Qt.AlignTop)

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(9)

        self.verticalLayout.setObjectName("verticalLayout")

        self.button_add_object = QPushButton(parent)

        self.button_remove_object = QPushButton(parent)
        self.button_ground_object = QPushButton(parent)
        #self.button_move_object = QPushButton(parent)
        #self.button_edit_object = QPushButton(parent)

        #self.button_add_object.setDisabled(True)
        #self.button_remove_object.setDisabled(True)

        self.button_add_object.setText("Add Object")
        self.button_remove_object.setText("Remove Object(s)")
        self.button_ground_object.setText("Ground Object(s)")

        self.button_add_object.setToolTip("Hotkey: Ctrl+A")
        self.button_remove_object.setToolTip("Hotkey: Delete")
        self.button_ground_object.setToolTip("Hotkey: G")


        self.button_add_object.setCheckable(True)
        #self.button_move_object.setCheckable(True)

        #self.lineedit_coordinatex = QLineEdit(parent)
        #self.lineedit_coordinatey = QLineEdit(parent)
        #self.lineedit_coordinatez = QLineEdit(parent)
        #self.verticalLayout.addStretch(10)
        #self.lineedit_rotationx = QLineEdit(parent)
        #self.lineedit_rotationy = QLineEdit(parent)
        #self.lineedit_rotationz = QLineEdit(parent)
        self.verticalLayout.addWidget(self.button_add_object)
        self.verticalLayout.addWidget(self.button_remove_object)
        self.verticalLayout.addWidget(self.button_ground_object)
        #self.verticalLayout.addWidget(self.button_move_object)
        self.verticalLayout.addStretch(20)

        self.name_label = QLabel(parent)
        self.name_label.setFont(font)
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumSize(self.name_label.width(), 30)
        #self.identifier_label = QLabel(parent)
        #self.identifier_label.setFont(font)
        #self.identifier_label.setMinimumSize(self.name_label.width(), 50)
        #self.identifier_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.verticalLayout.addWidget(self.name_label)
        #self.verticalLayout.addWidget(self.identifier_label)

        """self.verticalLayout.addWidget(self.lineedit_coordinatex)
        self.verticalLayout.addWidget(self.lineedit_coordinatey)
        self.verticalLayout.addWidget(self.lineedit_coordinatez)

        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_coordinatex, "X:   "))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_coordinatey, "Y:   "))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_coordinatez, "Z:   "))
        self.verticalLayout.addStretch(10)
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_rotationx, "RotX:"))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_rotationy, "RotY:"))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_rotationz, "RotZ:"))"""
        #self.verticalLayout.addStretch(10)
        self.comment_label = QLabel(parent)
        self.comment_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.comment_label.setWordWrap(True)
        self.comment_label.setFont(font)
        self.verticalLayout.addWidget(self.comment_label)
        #self.verticalLayout.addStretch(500)

        self.objectlist = []

        self.object_data_edit = None

        self.reset_info()

    def _make_labeled_lineedit(self, lineedit, label):
        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        layout = QHBoxLayout()
        label = QLabel(label, self)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineedit)
        return layout

    def reset_info(self, info="None selected"):
        self.name_label.setText(info)
        #self.identifier_label.setText("")
        self.comment_label.setText("")

        if self.object_data_edit is not None:
            self.object_data_edit.deleteLater()
            del self.object_data_edit
            self.object_data_edit = None

        self.objectlist = []

    def update_info(self):
        if self.object_data_edit is not None:
            self.object_data_edit.update_data()

    def set_info(self, obj, update3d, usedby=[]):
        if usedby:
            self.name_label.setText("Selected: {}\nUsed by: {}".format(type(obj).__name__,
                                    ", ".join(usedby)))
        else:
            self.name_label.setText("Selected: {}".format(type(obj).__name__))
        #self.identifier_label.setText(obj.get_identifier())
        if self.object_data_edit is not None:
            #self.verticalLayout.removeWidget(self.object_data_edit)
            self.object_data_edit.deleteLater()
            del self.object_data_edit
            self.object_data_edit = None
            print("should be removed")

        editor = choose_data_editor(obj)
        if editor is not None:

            self.object_data_edit = editor(self, obj)
            self.verticalLayout.addWidget(self.object_data_edit)
            self.object_data_edit.emit_3d_update.connect(update3d)

        self.objectlist = []
        self.comment_label.setText("")

    def set_objectlist(self, objs):
        self.objectlist = []
        objectnames = []

        for obj in objs:
            if len(objectnames) < 25:
                objectnames.append(obj.name)
            self.objectlist.append(obj)

        objectnames.sort()
        if len(objs) > 0:
            text = "Selected objects:\n" + (", ".join(objectnames))
            diff = len(objs) - len(objectnames)
            if diff == 1:
                text += "\nAnd {0} more object".format(diff)
            elif diff > 1:
                text += "\nAnd {0} more objects".format(diff)

        else:
            text = ""

        self.comment_label.setText(text)


