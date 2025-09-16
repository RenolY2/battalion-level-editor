import os

import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets


def load_icon(imagepath: str) -> QtGui.QIcon | None:
    if not os.path.exists(imagepath):
        return None

    try:
        image = QtGui.QImage(imagepath)
    except Exception as err:
        icon = None
    else:
        pixmap = QtGui.QPixmap.fromImage(image)
        icon = QtGui.QIcon(pixmap)

    return icon


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


class LayoutedWidget(QtWidgets.QWidget):
    def __init__(self, layout_cls, parent, *widgets, margins=(0, 0, 0, 0)):
        super().__init__(parent)
        self.layout = layout_cls(self)
        self.setLayout(self.layout)
        self.layout.setContentsMargins(*margins)

        for widget in widgets:
            print(widget)
            self.layout.addWidget(widget)
            widget.setParent(self)


class HorizontalWidget(LayoutedWidget):
    def __init__(self, parent, *widgets, margins=(0, 0, 0, 0)):
        super().__init__(QtWidgets.QHBoxLayout, parent, *widgets, margins=margins)


class VerticalWidget(LayoutedWidget):
    def __init__(self, parent, *widgets, margins=(0, 0, 0, 0)):
        super().__init__(QtWidgets.QVBoxLayout, parent, *widgets, margins=margins)
