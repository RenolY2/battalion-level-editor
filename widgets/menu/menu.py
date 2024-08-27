import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class Menu(QtWidgets.QMenu):
    def __init__(self, parent, name):
        super().__init__(parent)
        self.setTitle(name)
        self.actions = []

    def add_action(self, name, func=None, shortcut=None):
        action = QtGui.QAction(name, self)
        if func is not None:
            action.triggered.connect(func)
        if shortcut is not None:
            action.setShortcut(shortcut)

        self.actions.append(action)
        self.addAction(action)
        return action