import traceback
from copy import copy, deepcopy
from os import path
from timeit import default_timer

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore

"""
from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication
from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QListWidget,
                             QLineEdit, QTextEdit)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
"""

from plugins.strings_editor.strings import BWLanguageFile, Message


class HighlightDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_text = ""

    def set_search_text(self, text):
        self.search_text = text.lower()

    def paint(self, painter, option, index):
        painter.save()

        # Draw background (selected, hover, etc.)
        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget)

        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not text:
            painter.restore()
            return

        text_rect = style.subElementRect(QtWidgets.QStyle.SubElement.SE_ItemViewItemText, option, option.widget)
        painter.setFont(option.font)

        text_color = option.palette.color(
            QtGui.QPalette.ColorGroup.Normal,
            QtGui.QPalette.ColorRole.HighlightedText if option.state & QtWidgets.QStyle.StateFlag.State_Selected
            else QtGui.QPalette.ColorRole.Text
        )

        if not self.search_text or self.search_text not in text.lower():
            # No match, draw normally
            painter.setPen(text_color)
            painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignVCenter, text)
        else:
            # Draw text with highlighted match
            lower_text = text.lower()
            match_start = lower_text.find(self.search_text)
            match_end = match_start + len(self.search_text)

            fm = QtGui.QFontMetrics(option.font)
            x = text_rect.x()
            y = text_rect.y()
            h = text_rect.height()

            before = text[:match_start]
            match = text[match_start:match_end]
            after = text[match_end:]

            before_w = fm.horizontalAdvance(before)
            match_w = fm.horizontalAdvance(match)

            # Draw text before match
            painter.setPen(text_color)
            painter.drawText(QtCore.QRect(x, y, before_w, h), QtCore.Qt.AlignmentFlag.AlignVCenter, before)

            # Draw yellow highlight behind matched text
            highlight_rect = QtCore.QRect(x + before_w, y + 2, match_w, h - 4)
            painter.fillRect(highlight_rect, QtGui.QColor(255, 200, 0, 180))

            # Draw matched text in black so it's readable on yellow
            painter.setPen(QtGui.QColor(0, 0, 0))
            painter.drawText(QtCore.QRect(x + before_w, y, match_w, h), QtCore.Qt.AlignmentFlag.AlignVCenter, match)

            # Draw text after match
            painter.setPen(text_color)
            painter.drawText(QtCore.QRect(x + before_w + match_w, y, text_rect.width(), h), QtCore.Qt.AlignmentFlag.AlignVCenter, after)

        painter.restore()


class BWEntityEntry(QtWidgets.QListWidgetItem):
    def __init__(self, xml_ref, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.xml_ref = xml_ref


def trim_message(msg, limit=50):
    if len(msg) > limit:
        return msg[:50]+"..."
    else:
        return msg


def set_default_path(path):
    print("WRITING", path)
    try:
        with open("default_path2.cfg", "wb") as f:
            f.write(bytes(path, encoding="utf-8"))
    except Exception as error:
        print("couldn't write path")
        traceback.print_exc()
        pass


def get_default_path():
    print("READING")
    try:
        with open("default_path2.cfg", "rb") as f:
            path = str(f.read(), encoding="utf-8")
        return path
    except:
        return None


class StringsEditorMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

        self.stringfile = None
        self.reset_in_process = False

        path = get_default_path()
        if path is None:
            self.default_path = ""
        else:
            self.default_path = path

        self.curr_path = None

        self.strings_list.currentItemChanged.connect(self.action_listwidget_change_item)
        self.button_set_message.pressed.connect(self.action_button_set_message)
        self.button_add_message.pressed.connect(self.action_button_add_message)
        self.button_remove_message.pressed.connect(self.action_button_delete_message)
        self.search_bar.textChanged.connect(self.action_search)

    def reset(self):
        self.reset_in_process = True
        self.stringfile = None
        self.strings_list.clearSelection()
        self.strings_list.clear()
        self.textedit_content.clear()
        self.lineedit_path.clear()
        self.lineedit_playtime.clear()
        self.lineedit_audioname.clear()
        self.search_bar.clear()
        self.search_count_label.setText("")

        self.curr_path = None
        self.reset_in_process = False

    def action_search(self, text):
        self.highlight_delegate.set_search_text(text)
        self.strings_list.viewport().update()

        text_lower = text.lower()
        match_count = 0

        for i in range(self.strings_list.count()):
            item = self.strings_list.item(i)
            if self.stringfile is not None:
                msg = self.stringfile.messages[item.xml_ref]
                match = (
                    text_lower in msg.get_message().lower() or
                    text_lower in msg.get_path().lower() or
                    text_lower in msg.get_name().lower()
                )
                item.setHidden(not match)
                if match:
                    match_count += 1
            else:
                item.setHidden(False)

        if text_lower:
            self.search_count_label.setText("{0} result{1}".format(match_count, "s" if match_count != 1 else ""))
        else:
            self.search_count_label.setText("")

    def action_button_add_message(self):
        if self.stringfile is not None:
            newmessage = Message(strings=[b"", b"", b"", b""], audioplaytime=0.0)
            self.stringfile.messages.append(newmessage)
            i = len(self.stringfile.messages) - 1
            entry = BWEntityEntry(i, "({0}): '{1}'-'{2}'".format(i,
                                                                 newmessage.get_path(),
                                                                 newmessage.get_message()))
            self.strings_list.addItem(entry)
            self.strings_list.setCurrentRow(i)

    def action_button_set_message(self):
        print("I was pressed")
        current = self.strings_list.currentItem()
        if current is not None and self.strings_list is not None:
            try:
                msg = self.stringfile.messages[current.xml_ref]
                print(current)
                msg.set_path(self.lineedit_path.text())
                msg.set_name(self.lineedit_audioname.text())
                msg.playtime = float(self.lineedit_playtime.text())
                msg.set_message(self.textedit_content.toPlainText())

                current.setText("({0}): '{1}'-'{2}'".format(current.xml_ref,
                                                            msg.get_path(),
                                                            msg.get_message()))
            except:
                traceback.print_exc()

    def action_button_delete_message(self):
        if self.stringfile is not None:
            lastindex = len(self.stringfile.messages) - 1
            lastmessage = self.stringfile.messages.pop()
            item = self.strings_list.takeItem(lastindex)

            self.strings_list.removeItemWidget(item)
            self.strings_list.setCurrentRow(lastindex-1)

            self.statusbar.showMessage("DELETED: ({0}) {1}".format(lastindex,
                                                                   trim_message(lastmessage.get_message())))

    def action_listwidget_change_item(self, current, previous):
        if current is not None:
            print(current.xml_ref)
            msg = self.stringfile.messages[current.xml_ref]
            self.lineedit_audioname.setText(msg.get_name())
            self.lineedit_path.setText(msg.get_path())
            self.lineedit_playtime.setText(str(msg.playtime))
            self.textedit_content.setText(msg.get_message())

    def button_load_strings(self):
        try:
            print("ok", self.default_path)
            self.xmlPath = ""
            filepath, choosentype = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open File",
                self.default_path,
                "BW string files (*.str);;All files (*)")
            print("doooone")
            if filepath:
                print("resetting")
                self.reset()
                print("done")

                with open(filepath, "rb") as f:
                    try:
                        self.stringfile = BWLanguageFile(f)
                        for i, msg in enumerate(self.stringfile.messages):
                            entry = BWEntityEntry(i, "({0}): '{1}'-'{2}'".format(i,
                                                                             msg.get_path(),
                                                                             msg.get_message()))
                            self.strings_list.addItem(entry)

                        pass
                        self.default_path = filepath
                        self.curr_path = filepath
                    except Exception as error:
                        print("error", error)
                        traceback.print_exc()
        except Exception as er:
            print("errrorrr", error)
            traceback.print_exc()
        print("loaded")

    def load_path(self, path):
        self.reset()
        print("done")

        with open(path, "rb") as f:
            try:
                self.stringfile = BWLanguageFile(f)
                for i, msg in enumerate(self.stringfile.messages):
                    entry = BWEntityEntry(i, "({0}): '{1}'-'{2}'".format(i,
                                                                         msg.get_path(),
                                                                         msg.get_message()))
                    self.strings_list.addItem(entry)

                pass
                self.default_path = path
                self.curr_path = path
            except Exception as error:
                print("error", error)
                traceback.print_exc()

    def button_save_as_strings(self):
        if self.stringfile is not None:
            filepath, choosentype = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save File",
                self.default_path,
                "BW level files (*.str);;All files (*)")
            print(filepath, "saved")
            if filepath:
                with open(filepath, "wb") as f:
                    self.stringfile.write(f)

                self.default_path = filepath
                set_default_path(filepath)
        else:
            pass # no level loaded, do nothing

    def button_save_strings(self):
        if self.stringfile is not None:
            if self.curr_path is not None:
                filepath = self.curr_path
                print(filepath, "saved")
                if filepath:
                    with open(filepath, "wb") as f:
                        self.stringfile.write(f)

                    self.default_path = filepath
                    set_default_path(filepath)
            else:
                self.button_save_as_strings()
        else:
            pass # no level loaded, do nothing

    def setup_ui(self):
        self.setObjectName("MainWindow")
        self.resize(820, 760)
        self.setMinimumSize(QtCore.QSize(720, 560))
        self.setWindowTitle("BW-StringsEdit")

        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.setCentralWidget(self.centralwidget)

        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")

        # Left side: search bar + list
        self.left_widget = QtWidgets.QWidget(self.centralwidget)
        self.left_layout = QtWidgets.QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(0, 0, 0, 0)

        # Search row: search bar + result count label
        self.search_row = QtWidgets.QHBoxLayout()
        self.search_bar = QtWidgets.QLineEdit(self.left_widget)
        self.search_bar.setPlaceholderText("Search messages, paths, filenames...")
        self.search_count_label = QtWidgets.QLabel("")
        self.search_count_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight)
        self.search_row.addWidget(self.search_bar)
        self.search_row.addWidget(self.search_count_label)
        self.left_layout.addLayout(self.search_row)

        self.strings_list = QtWidgets.QListWidget(self.left_widget)
        self.highlight_delegate = HighlightDelegate(self.strings_list)
        self.strings_list.setItemDelegate(self.highlight_delegate)
        self.left_layout.addWidget(self.strings_list)

        self.horizontalLayout.addWidget(self.left_widget)

        self.vertLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.vertLayoutWidget)
        self.button_add_message = QtWidgets.QPushButton(self.centralwidget)
        self.button_remove_message = QtWidgets.QPushButton(self.centralwidget)
        self.button_set_message = QtWidgets.QPushButton(self.centralwidget)

        self.button_add_message.setText("Add Message")
        self.button_remove_message.setText("Delete Last Message")
        self.button_set_message.setText("Set Message Content")

        self.lineedit_path = QtWidgets.QLineEdit(self.centralwidget)
        self.lineedit_audioname = QtWidgets.QLineEdit(self.centralwidget)
        self.lineedit_playtime = QtWidgets.QLineEdit(self.centralwidget)
        self.textedit_content = QtWidgets.QTextEdit(self.centralwidget)

        for widget in (self.button_remove_message, self.button_add_message, self.button_set_message,
                       self.lineedit_path, self.lineedit_audioname, self.lineedit_playtime, self.textedit_content):
            self.verticalLayout.addWidget(widget)

        self.horizontalLayout.addWidget(self.vertLayoutWidget)

        self.menubar = self.menuBar()
        self.file_menu = self.menubar.addMenu("File")
        self.file_menu.setObjectName("menuLoad")

        self.file_load_action = QtGui.QAction("Load", self)
        self.file_load_action.triggered.connect(self.button_load_strings)
        self.file_menu.addAction(self.file_load_action)
        self.file_save_action = QtGui.QAction("Save", self)
        self.file_save_action.setShortcut("Ctrl+S")
        self.file_save_action.triggered.connect(self.button_save_strings)
        self.file_save_as_action = QtGui.QAction("Save As", self)
        self.file_save_as_action.triggered.connect(self.button_save_as_strings)
        self.file_menu.addAction(self.file_save_action)
        self.file_menu.addAction(self.file_save_as_action)

        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        print("done")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    bw_gui = StringsEditorMainWindow()

    bw_gui.show()
    err_code = app.exec()
    #traceback.print_exc()
    sys.exit(err_code)