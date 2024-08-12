import PyQt5.QtWidgets as QtWidgets
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import bw_editor


class Menu(QtWidgets.QMenu):
    def __init__(self, parent, name):
        super().__init__(parent)
        self.setTitle(name)
        self.actions = []

    def add_action(self, name, func=None, shortcut=None):
        action = QtWidgets.QAction(name, self)
        if func is not None:
            action.triggered.connect(func)
        if shortcut is not None:
            action.setShortcut(shortcut)

        self.actions.append(action)
        return action