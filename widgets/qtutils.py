import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets


class NonAutodismissibleMenu(QtWidgets.QMenu):
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        action = self.activeAction()
        if action is not None and (
                action.isEnabled() and action.isCheckable()
                or hasattr(action, "dismiss") and not action.dismiss
        ):
            action.trigger()
            event.accept()
            return

        super().mouseReleaseEvent(event)


class NonDismissableAction(QtGui.QAction):
    dismiss = False


class ActionFunction(QtGui.QAction):
    def __init__(self, name, parent, func):
        super().__init__(name, parent=parent)
        self.triggered.connect(func)
