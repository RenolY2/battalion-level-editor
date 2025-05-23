import typing
import os
import math
import json
from functools import partial
from lib.bw_types import BWMatrix, decompose, recompose
from timeit import default_timer
from widgets.editor_widgets import open_message_dialog
from builtin_plugins.add_object_window import load_icon
from itertools import chain

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
from lib.BattalionXMLLib import BattalionObject, BattalionLevelFile
from widgets.editor_widgets import SearchBar
from widgets.edit_window_enums import FLAG_TYPES, ENUMS, FLAGS

ICONS = {"COPY": None}


def get_field_name(object_type, fieldname):
    return FLAG_TYPES.get((object_type, fieldname))


def make_getter(obj, attr, index=None):
    def get():
        val = getattr(obj, attr)
        if isinstance(val, list):
            return val[index]
        else:
            return val

    return get


def make_setter(obj, attr, index=None):
    def changed(newval):
        val = getattr(obj, attr)
        if isinstance(val, list):
            val[index] = newval
        else:
            setattr(obj, attr, newval)

    return changed


def make_getter_index(obj, index):
    def get():
        return obj[index]

    return get


def make_setter_index(obj, index):
    def changed(newval):
        obj[index] = newval

    return changed


class PythonIntValidator(QtGui.QValidator):
    def __init__(self, min, max, parent):
        super().__init__(parent)
        self.min = min
        self.max = max

    def validate(self, p_str, p_int):
        if p_str == "" or p_str == "-":
            return QtGui.QValidator.State.Intermediate, p_str, p_int

        try:
            result = int(p_str)
        except:
            return QtGui.QValidator.State.Invalid, p_str, p_int

        if self.min <= result <= self.max:
            return QtGui.QValidator.State.Acceptable, p_str, p_int
        else:
            return QtGui.QValidator.State.Invalid, p_str, p_int

    def fixup(self, s):
        pass


class SelectableLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)


def make_labeled_widget(parent, text, widget: QtWidgets.QWidget):
    labelwidget = QtWidgets.QWidget(parent)
    layout = QtWidgets.QHBoxLayout(labelwidget)
    layout.setContentsMargins(0, 0, 0, 0)
    labelwidget.setLayout(layout)
    label = SelectableLabel(labelwidget)
    label.setText(text)
    label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(label)
    layout.addWidget(widget)

    return labelwidget


class DecimalInputNormal(QtWidgets.QLineEdit):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, get_value, set_value, min=-math.inf, max=math.inf):
        super().__init__(parent)
        self.get_value = get_value
        self.set_value = set_value

        self.min = None
        self.max = None

        self.setValidator(QtGui.QDoubleValidator(min, max, 6, self))
        self.textChanged.connect(self.changed_value)

    def get_searchable_values(self):
        return [self.text()]

    def update_value(self):
        val = self.get_value()
        self.blockSignals(True)
        self.setText(str(val))
        self.blockSignals(False)

    def changed_value(self, value):
        val = float(value)
        self.set_value(val)
        self.changed.emit()


class DecimalInput(QtWidgets.QLineEdit):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, get_value, set_value, min=-math.inf, max=math.inf):
        super().__init__(parent)
        self.get_value = get_value
        self.set_value = set_value

        self.min = None
        self.max = None

        self.setValidator(QtGui.QDoubleValidator(min, max, 6, self))
        self.textChanged.connect(self.changed_value)

        self.start_x = None
        self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
        self.scaling_factor = 1
        self.scale_down = False
        self.currvalue = None

    def get_searchable_values(self):
        return [self.text()]

    def keyPressEvent(self, a0: typing.Optional[QtGui.QKeyEvent]) -> None:
        super().keyPressEvent(a0)
        event: QtGui.QKeyEvent = a0

        if event.key() == QtCore.Qt.Key.Key_Shift:
            self.scale_down = True

    def keyReleaseEvent(self, a0: typing.Optional[QtGui.QKeyEvent]) -> None:
        super().keyReleaseEvent(a0)
        event: QtGui.QKeyEvent = a0

        if event.key() == QtCore.Qt.Key.Key_Shift:
            self.scale_down = False

    def mousePressEvent(self, a0: typing.Optional[QtGui.QMouseEvent]) -> None:
        super().mousePressEvent(a0)

        event: QtGui.QMouseEvent = a0
        self.currvalue = self.get_value()
        self.start_x = event.pos().x()

    def mouseMoveEvent(self, a0: typing.Optional[QtGui.QMouseEvent]) -> None:
        if self.start_x is not None:
            event: QtGui.QMouseEvent = a0
            diff = event.pos().x() - self.start_x

            if self.scale_down:
                value = round(self.currvalue + diff * self.scaling_factor * 0.01, 6)
            else:
                value = round(self.currvalue + diff * self.scaling_factor, 6)
            self.setText(str(value))

    def mouseReleaseEvent(self, a0: typing.Optional[QtGui.QMouseEvent]) -> None:
        self.start_x = None
        self.scale_down = False

    def update_value(self):
        val = self.get_value()
        self.blockSignals(True)
        self.setText(str(val))
        self.blockSignals(False)

    def changed_value(self, value):
        val = float(value)
        self.set_value(val)
        self.changed.emit()


class IntegerInput(QtWidgets.QLineEdit):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, type, get_value, set_value):
        super().__init__(parent)
        self.get_value = get_value
        self.set_value = set_value

        self.min = None
        self.max = None
        # print(type)
        if type == "sInt8":
            self.min, self.max = -128, 127
        elif type == "sInt16":
            self.min, self.max = -(2 ** 15), (2 ** 15) - 1
        elif type == "sInt32":
            self.min, self.max = -(2 ** 31), (2 ** 31) - 1
        elif type == "sUInt8":
            self.min, self.max = 0, 255
        elif type == "sUInt16":
            self.min, self.max = 0, (2 ** 16) - 1
        elif type == "sUInt32":
            self.min, self.max = 0, (2 ** 32) - 1

        self.setValidator(PythonIntValidator(self.min, self.max, self))
        self.textChanged.connect(self.changed_value)

    def get_searchable_values(self):
        return [self.text()]

    def update_value(self):
        value = int(self.get_value())
        if value < self.min:
            print(f"WARNING: Value out of range: {value} will be capped to {self.min}")
            value = self.min
        if value > self.max:
            print(f"WARNING: Value out of range: {value} will be capped to {self.max}")
            value = self.max

        self.blockSignals(True)
        self.setText(str(value))
        self.blockSignals(False)

    def changed_value(self, value):
        val = int(value)
        if self.min <= val <= self.max:
            self.set_value(val)
            self.changed.emit()


class StrongFocusComboBox(QtWidgets.QComboBox):
    def __init__(self, *args, editable=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("QComboBox {combobox-popup: 0;}")

        self.items_total = []
        self.optimize = False
        self.callback = lambda: True
        if editable:
            self.setEditable(True)

    def get_searchable_values(self):
        return [self.currentText()]

    def full_callback(self, func):
        self.callback = func

    def showPopup(self) -> None:
        if self.optimize:
            self.callback()

        super().showPopup()

    def optimize_large_sets(self):
        self.optimize = True
        self.setMinimumContentsLength(int(self.minimumContentsLength() * 1.2))
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)

    def wheelEvent(self, event) -> None:
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class EnumBox(StrongFocusComboBox):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, items, get_value, set_value):
        super().__init__(parent)
        self.items = []
        for item in items:
            self.addItem(item)
            self.items.append(item)

        self.get_value = get_value
        self.set_value = set_value
        self.currentTextChanged.connect(self.change)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def get_searchable_values(self):
        return [self.currentText()]

    def update_value(self):
        value = self.get_value()
        self.blockSignals(True)
        if value not in self.items:
            self.setCurrentIndex(0)
        else:
            self.setCurrentText(value)
        self.blockSignals(False)

    def change(self, value):
        assert value in self.items

        self.set_value(value)
        self.changed.emit()


class BooleanEnumBox(EnumBox):
    def __init__(self, parent, get_value, set_value):
        super().__init__(parent, ["False", "True"], get_value, set_value)

    def update_value(self):
        value = self.get_value()
        self.blockSignals(True)
        if value:
            self.setCurrentIndex(1)
        else:
            self.setCurrentIndex(0)
        self.blockSignals(False)

    def change(self, value):
        self.set_value(value == "True")
        self.changed.emit()


class DecimalVector4Edit(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, get_value):
        super().__init__(parent)
        self.vector_layout = QtWidgets.QHBoxLayout(self)
        self.vector_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.vector_layout)
        self.edits = []
        vector = get_value()
        for i in ("x", "y", "z", "w"):
            getter = make_getter(vector, i)
            setter = make_setter(vector, i)

            labeled_widget = QtWidgets.QWidget(self)
            label_layout = QtWidgets.QHBoxLayout(labeled_widget)
            labeled_widget.setLayout(label_layout)
            label_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

            label = SelectableLabel(i, self)
            decimal_edit = DecimalInput(self, getter, setter)
            label_layout.addWidget(label)
            label_layout.addWidget(decimal_edit)

            self.edits.append(decimal_edit)
            self.vector_layout.addWidget(labeled_widget)

            decimal_edit.changed.connect(lambda x: self.changed.emit())

    def get_searchable_values(self):
        return [x.text() for x in self.edits]

    def update_value(self) -> None:
        for edit in self.edits:
            edit.update_value()


class ColorView(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.color = QtGui.QColor(0, 0, 0, 255)
        self.setMinimumSize(32, 32)
        sizepolicy = self.sizePolicy()
        sizepolicy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
        sizepolicy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
        self.setSizePolicy(sizepolicy)

    def paintEvent(self, a0) -> None:
        painter = QtGui.QPainter(self)
        h = self.height()
        painter.fillRect(0, 0, h, h, self.color)

    def change_color(self, r, g, b, a):
        self.color = QtGui.QColor(r, g, b, a)


class Line(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.color = QtGui.QColor(0, 0, 0, 255)
        self.setMinimumHeight(10)
        #self.setMinimumSize(32, 32)
        #sizepolicy = self.sizePolicy()
        #sizepolicy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
        #sizepolicy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
        #self.setSizePolicy(sizepolicy)

    def paintEvent(self, a0) -> None:
        painter = QtGui.QPainter(self)
        painter.setPen(self.color)
        w = self.width()
        mid = self.height()//2
        #painter.fillRect(0, mid, w, mid, self.color)
        painter.drawLine(0, mid, w, mid)

    def change_color(self, r, g, b, a):
        self.color = QtGui.QColor(r, g, b, a)


class HighlightArrow(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.color = QtGui.QColor(0, 0, 0, 255)
        self.setMinimumSize(32, 32)
        sizepolicy = self.sizePolicy()
        sizepolicy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
        sizepolicy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
        self.setSizePolicy(sizepolicy)

    def paintEvent(self, a0) -> None:
        painter = QtGui.QPainter(self)
        h = self.height()
        w = self.width()

        painter.setPen(self.color)
        painter.setBrush(self.color)
        """upper = h//4
        lower = upper*3
        mid = h//2
        painter.drawPolygon([
            QtCore.QPoint(0, upper),
            QtCore.QPoint(0, lower),
            QtCore.QPoint(mid, lower),
            QtCore.QPoint(mid, h),
            QtCore.QPoint(h, mid),
            QtCore.QPoint(mid, 0),
            QtCore.QPoint(mid, upper)],
            QtCore.Qt.FillRule.WindingFill
            )"""
        painter.fillRect(0, 0, w, h, self.color)

    def change_color(self, r, g, b, a):
        self.color = QtGui.QColor(r, g, b, a)


class MatrixEdit(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, get_value):
        super().__init__(parent)
        self.grid_layout = QtWidgets.QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.get_value = get_value

        matrix: BWMatrix = self.get_value()
        self.edits = []
        self.decomposed = list(decompose(matrix))

        self.grid_layout.addWidget(SelectableLabel("Position", self), 0, 0)
        self.grid_layout.addWidget(SelectableLabel("Scale", self), 1, 0)
        self.grid_layout.addWidget(SelectableLabel("Angle", self), 2, 0)

        for iy in range(3):
            for ix in range(3):
                getter = make_getter_index(self.decomposed, iy * 3 + ix)
                setter = make_setter_index(self.decomposed, iy * 3 + ix)

                text = ["x", "y", "z"][ix]

                if iy == 1:
                    index_edit = DecimalInput(self, getter, setter, min=0.0001)
                else:
                    index_edit = DecimalInput(self, getter, setter)

                labeled = make_labeled_widget(self, text, index_edit)

                self.grid_layout.addWidget(labeled, iy, ix + 1)
                self.edits.append(index_edit)
                index_edit.textChanged.connect(self.recompose_matrix)

        """
        for ix in range(4):
            for iy in range(4):
                getter = make_getter_index(matrix.mtx, iy*4+ix)
                setter = make_setter_index(matrix.mtx, iy*4+ix)

                index_edit = DecimalInput(self, getter, setter)
                self.grid_layout.addWidget(index_edit, ix, iy)
                self.edits.append(index_edit)"""

    def get_searchable_values(self):
        return [x.text() for x in self.edits] + ["Position", "Scale", "Angle", "x", "y", "z"]

    def update_value(self):
        for edit in self.edits:
            edit.blockSignals(True)
            edit.update_value()
            edit.blockSignals(False)

    def recompose_matrix(self):
        matrix = self.get_value()
        recomposed = recompose(*self.decomposed)
        matrix.mtx[:15] = recomposed.mtx[:15]
        self.changed.emit()


class Vector4Edit(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, vtype, get_value):
        super().__init__(parent)
        assert vtype in ("sVector4", "sU8Color", "sVectorXZ", "cU8Color")
        self.vector_layout = QtWidgets.QHBoxLayout(self)
        self.vector_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.setLayout(self.vector_layout)
        self.edits = []

        self.get_value = get_value
        vector = get_value()

        components = ("x", "y", "z", "w")
        if vtype == "sVectorXZ":
            components = ("x", "z")

        for i in components:
            getter = make_getter(vector, i)
            setter = make_setter(vector, i)

            labeled_widget = QtWidgets.QWidget(self)
            label_layout = QtWidgets.QHBoxLayout(labeled_widget)
            labeled_widget.setLayout(label_layout)
            label_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

            if vtype == "sVector4" or vtype == "sVectorXZ":
                label = SelectableLabel(i, self)
                decimal_edit = DecimalInput(self, getter, setter)
            elif vtype == "sU8Color" or vtype == "cU8Color":
                comp = {"x": "Red", "y": "Green", "z": "Blue", "w": "Alpha"}[i]
                label = SelectableLabel(comp, self)
                decimal_edit = IntegerInput(self, "sUInt8", getter, setter)

            label_layout.addWidget(label)
            label_layout.addWidget(decimal_edit)
            decimal_edit.changed.connect(lambda: self.changed.emit())

            self.edits.append(decimal_edit)
            self.vector_layout.addWidget(labeled_widget)

        if vtype == "sU8Color" or vtype == "cU8Color":
            self.color = ColorView(self)
            self.vector_layout.addWidget(self.color)
            for edit in self.edits:
                edit: IntegerInput
                edit.textChanged.connect(self.update_color)
        else:
            self.color = None

    def get_searchable_values(self):
        return [x.text() for x in self.edits]

    def update_color(self):
        if self.color is not None:
            col = self.get_value()
            self.color.change_color(int(col.x), int(col.y), int(col.z), int(col.w))
            self.color.update()

    def update_value(self) -> None:
        for edit in self.edits:
            edit.update_value()
        self.update_color()


class FlagBox(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, items, get_value, set_value):
        super().__init__(parent)
        self.flag_layout = QtWidgets.QGridLayout(self)
        self.setLayout(self.flag_layout)

        self.flags = []

        self.get_value = get_value
        self.set_value = set_value

        self.value = SelectableLabel(self)
        self.flag_layout.addWidget(self.value)

        i = 0
        for flagname, value in items:
            checkbutton = QtWidgets.QCheckBox(self)
            checkbutton.setText(flagname)

            self.flags.append((checkbutton, value))

            row = i // 2 + 1
            column = i % 2
            self.flag_layout.addWidget(checkbutton, row, column)
            checkbutton.stateChanged.connect(self.change)
            i += 1

    def get_searchable_values(self):
        out = []
        for button, value in self.flags:
            out.append(button.text())

        return out

    def update_value(self):
        val = self.get_value()
        checked = 0
        for button, value in self.flags:
            print(button.text())
            button: QtWidgets.QRadioButton
            button.blockSignals(True)
            button.setChecked(val & value)
            button.blockSignals(False)
            checked += value

        self.value.setText(f"Combined flag value: {val}")

        if (val & ~checked) != 0:
            raise RuntimeError(f"WARNING: Bits unaccounted for with value {val} vs {checked}")

    def change(self):
        newval = 0
        for button, value in self.flags:
            if button.isChecked():
                newval |= value
        self.value.setText(f"Combined flag value: {newval}")
        self.set_value(newval)
        self.changed.emit()


SUBSETS = {
    "cUnit": ["cTroop", "cGroundVehicle", "cWaterVehicle", "cAirVehicle", "cBuilding"],
    "sWeaponBase": ["cAdvancedWeaponBase"],
    "cAnimationTriggeredEffectChainItemBase": [
        "cAnimationTriggeredEffectChainItemGroundImpact",
        "cAnimationTriggeredEffectChainItemSound",
        "cAnimationTriggeredEffectChainItemTequilaEffect"],
    "cTaggedEffectBase": [
        "cSimpleTequilaTaggedEffectBase",
        "cImpactTableTaggedEffectBase"
    ],
    "cEntity": ["cWaypoint", "cCamera", "cMapZone", "cAmbientAreaPointSoundSphere",
                "cDestroyableObject", "cSceneryCluster", "cTroop", "cGroundVehicle",
                "cAirVehicle", "cObjectiveMarker", "cReflectedUnitGroup", "cPickupReflected",
                "cAmbientAreaPointSoundBox", "cBuilding", "cCapturePoint", "cDamageZone",
                "cMorphingBuilding", "cCoastZone", "cWaterVehicle", "cNogoHintZone"],
    "cGUIMetaNumber": ["cGUINumberNumber", "cGUINumberFromFunction", "cGUINumberFromLabel"],
    "cGUIMetaVector": ["cGUIVectorVector", "cGUIVectorFromLabel", "cGUIVectorFromFunction"],
    "cGUIMetaColour": ["cGUIColourColour", "cGUIColourFromFunction", "cGUIColourFromLabel",
                       "cGUIColourNumber"],
    "cGUIMetaScale": ["cGUIScaleVector", "cGUIScaleFromFunction", "cGUIScaleFromLabel"],
    "cGUIMetaBool": ["cGUIBoolFromLabel", "cGUIBoolBool", "cGUIBoolFromFunction"],
    "cGUIMetaString": ["cGUIStringFromLabel", "cGUIStringString", "cGUIStringFromFunction"],
    "cGUIWidget": ["cGUIButtonWidget", "cGUISpriteWidget", "cGUITextureWidget", "cGUICustomWidget",
                   "cGUITextBoxWidget", "cGUIRectWidget", "cGUIVertexColouredRectWidget",
                   "cGUITequilaWidget", "cGUI3DObjectWidget", "cGUIListBoxWidget", "cGUISliderWidget"],
    "cGUISpriteWidget": ["cGUIButtonWidget"],
    "cGUIMetaMatrix": ["cGUIMatrixFromLabel"]

}

SUBSETS["cWorldObject"] = SUBSETS["cEntity"]


class ReferenceEdit(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent,
                 objects: BattalionLevelFile,
                 preload: BattalionLevelFile,
                 type,
                 get_value,
                 set_value):
        super().__init__(parent)
        self.objects = objects
        self.preload = preload
        self.get_value = get_value
        self.set_value = set_value
        self.type = type

        # line_1_holder = QtWidgets.QWidget(self)
        # line_2_holder = QtWidgets.QWidget(self)
        line_1 = QtWidgets.QHBoxLayout(self)
        # line_2 = QtWidgets.QHBoxLayout(self)
        # line_1_holder.setLayout(line_1)
        # line_2_holder.setLayout(line_2)

        line_1.setContentsMargins(0, 0, 0, 0)
        # line_1.setContentsMargins(0, 0, 0, 0)
        # line_2.setContentsMargins(0, 0, 0, 0)

        self.object_combo_box = StrongFocusComboBox(self, editable=True)
        self.object_combo_box.optimize_large_sets()
        self.object_combo_box.setMaxVisibleItems(20)
        self.edit_button = QtWidgets.QPushButton("Edit", self)
        self.set_to_selected_button = QtWidgets.QPushButton("Set To Selected", self)
        self.goto_button = QtWidgets.QPushButton("Goto/Select", self)
        self.object_combo_box.currentIndexChanged.connect(self.change_object)
        self.object_combo_box.lineEdit().editingFinished.connect(self.change_object_text)

        self.copy_button = QtWidgets.QPushButton(parent=self, icon=ICONS["COPY"])
        self.copy_button.setToolTip("Copy ID into Clipboard")
        self.copy_button.pressed.connect(self.copy_id_into_clipboard)

        self.object_combo_box.setMinimumWidth(200)
        line_1.addWidget(self.object_combo_box)
        line_1.addWidget(self.copy_button)
        line_1.addWidget(self.edit_button)
        line_1.addWidget(self.set_to_selected_button)
        line_1.addWidget(self.goto_button)

        # self.gridlayout.addWidget(line_1_holder, 0, 0)
        # self.gridlayout.addWidget(line_2_holder, 1, 0)
        self.setLayout(line_1)

    def get_searchable_values(self):
        obj = self.get_value()

        if obj is None:
            return []
        else:
            return [obj.id, obj.name]

    def install_filter(self, filt):
        self.installEventFilter(filt)
        self.object_combo_box.installEventFilter(filt)

    def change_object_text(self, *args, **kwargs):
        print("text changed", self.object_combo_box.currentText())
        curr = self.get_value()
        default = "None" if curr is None else curr.name

        id = self.object_combo_box.currentText()
        if id in self.objects.objects:
            obj = self.objects.objects[id]
        elif id in self.preload.objects:
            obj = self.preload.objects[id]
        else:
            obj = None

        if obj is not None:
            check_types = [self.type]
            if self.type in SUBSETS:
                check_types.extend(SUBSETS[self.type])

            if obj.type not in check_types:
                open_message_dialog(
                    f"Warning!\n"
                    f"Object {obj.name} cannot be used because it has incompatible type {obj.type})")
                self.object_combo_box.setCurrentText(default)
            else:
                self.set_value(obj)
                self.object_combo_box.setCurrentText(obj.name)
                self.changed.emit()
        elif id == "0":
            self.set_value(None)
            self.object_combo_box.setCurrentIndex(0)
            self.changed.emit()
        else:
            self.object_combo_box.setCurrentText(default)

    def copy_id_into_clipboard(self):
        obj = self.get_value()
        if obj is None:
            value = 0
        else:
            value = obj.id

        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(str(value))

    def update_value(self, item_cache=None, large_set_optimize=False):
        self.object_combo_box.blockSignals(True)
        self.object_combo_box.clear()

        currobj = self.get_value()

        if large_set_optimize:
            self.object_combo_box.addItem(currobj.name)
            self.object_combo_box.full_callback(partial(self.update_value, item_cache))
            self.object_combo_box.setCurrentIndex(0)
        else:

            """
            noitem = QtWidgets.QListWidgetItem()
            noitem.setText("None")
            noitem.obj = None
            curritem = noitem
            items = []
            for objtype, objlist in chain(self.objects.category.items(), self.preload.category.items()):
                if self.is_instance(objtype):
                    for objid, object in objlist.items():
                        item = QtWidgets.QListWidgetItem()
                        item.setText(object.name)
                        item.obj = object
                        items.append(item)
                        if object == currobj:
                            curritem = item

            if currobj is not None and curritem == noitem:
                self.object_combo_box.blockSignals(False)
                raise RuntimeError(f"Failed to assign object: {currobj.type}")

            items.sort(key=lambda x: x.text())
            items.insert(0, noitem)
            currindex = items.index(curritem)
            self.items = items
            for item in items:
                self.object_combo_box.addItem(item.text(), item.obj)"""
            noitem = ("None", None)
            curritem = noitem

            items = []
            wrong_object = None
            # for objtype, objlist in chain(self.objects.category.items(), self.preload.category.items()):
            #    if self.is_instance(objtype):
            check_types = [self.type]
            if self.type in SUBSETS:
                check_types.extend(SUBSETS[self.type])

            if item_cache is None or self.type not in item_cache:
                for category in [self.objects.category, self.preload.category]:
                    for objtype in check_types:
                        if objtype in category:
                            objlist = category[objtype]
                            for objid, object in objlist.items():
                                item = (object.name, object)

                                items.append(item)
                                if object == currobj:
                                    curritem = item

                if currobj is not None and curritem == noitem:
                    checkedtypes = ", ".join(check_types)
                    open_message_dialog(f"Warning!\n"
                                        f"Tried to fit object {currobj.name} with type {currobj.type} into field that expects "
                                        f"one of {checkedtypes}.")
                    wrong_object = currobj
                    # self.object_combo_box.blockSignals(False)
                    # raise RuntimeError(f"Failed to assign object: {currobj.type}")

                items.sort(key=lambda x: x[0])
                items.insert(0, noitem)

                self.items = items
                # for item in items:
                self.object_combo_box.addItems([x[0] for x in items])
                if wrong_object is not None:
                    currindex = len(items)
                    self.object_combo_box.addItem(wrong_object.name)
                    self.wrong_object = wrong_object
                else:
                    currindex = items.index(curritem)
                self.object_combo_box.setCurrentIndex(currindex)

                if item_cache is not None:
                    item_cache[self.type] = self.items

            elif item_cache is not None and self.type in item_cache:
                if currobj is not None:
                    curritem = (currobj.name, currobj)
                else:
                    curritem = None

                items = item_cache[self.type]
                self.object_combo_box.addItems([x[0] for x in items])
                self.items = items

                try:
                    currindex = items.index(curritem)
                except ValueError:
                    if curritem is not None:
                        currindex = len(items)
                        self.object_combo_box.addItem(currobj.name)
                        checkedtypes = ", ".join(check_types)
                        open_message_dialog(f"Warning!\n"
                                            f"Tried to fit object {currobj.name} with type {currobj.type} into field that expects "
                                            f"one of {checkedtypes}.")
                    else:
                        currindex = 0

                self.object_combo_box.setCurrentIndex(currindex)
        self.object_combo_box.blockSignals(False)

    def change_object(self):
        result = self.object_combo_box.currentIndex()
        if result != -1:
            if result < len(self.items):
                obj = self.items[result][1]
                self.set_value(obj)
                if obj is not None:
                    obj.updatemodelname()
                self.changed.emit()
            else:
                currobj = self.get_value()
                if currobj is not None:
                    try:
                        index = self.items.index((currobj.name, currobj))
                    except ValueError:
                        pass
                    else:
                        self.object_combo_box.setCurrentIndex(index)
                        open_message_dialog(f"Selected object type doesn't match, selection reverted."
                                            "")

    def is_instance(self, other_type):
        if self.type == other_type:
            return True
        elif self.type in SUBSETS:
            return other_type in SUBSETS[self.type]

        return False


class DocFile(object):
    def __init__(self, classname):
        self.classname = classname
        self.docs = {}

    @classmethod
    def from_file(cls, path):
        basename: str = os.path.basename(path)
        objname = basename.removesuffix(".doc")
        doc = cls(objname)

        with open(path, "r") as f:
            lines = f.readlines()

        i = 0
        end = len(lines)
        game = None
        field = None
        fielddoc = []

        state = 0

        for i in range(0, end):
            if lines[i][0] in (">", "-") and fielddoc:
                doc.add_doc(game, objname, field, fielddoc)

            if lines[i].startswith(">"):
                state = 1
                game = lines[i][1:].strip().removesuffix(":")

            elif lines[i].startswith("-"):
                field = lines[i][1:].strip().removesuffix(":")
                fielddoc = []
                state = 2
            elif state == 2:
                assert game is not None and field is not None, "Parsing failure when reading {}".format(path)
                line = lines[i]
                fielddoc.append(line)

                if i == end - 1:
                    doc.add_doc(game, objname, field, fielddoc)

        return doc

    def add_doc(self, game, objname, field, doc):
        while doc[-1] == "\n":
            doc.pop(-1)

        if game == "BOTH":
            self.docs[("BW1", objname, field)] = "".join(doc)
            self.docs[("BW2", objname, field)] = "".join(doc)
        else:
            self.docs[(game, objname, field)] = "".join(doc)


class FieldDocumentationHolder(object):
    def __init__(self, doc_folder):
        self.docs = {}
        self.doc_folder = doc_folder
        self.last_changed = {}

        doc_files = os.listdir(doc_folder)

        for fname in doc_files:
            if fname.endswith(".doc"):
                self.read_object_doc(os.path.join(doc_folder, fname))

    def doc_needs_update(self, classname):
        if classname not in self.last_changed:
            return True

        doc_file = os.path.join(self.doc_folder, classname+".doc")
        return os.stat(doc_file).st_mtime > self.last_changed[classname]

    def update(self, classname):
        print("Checking if", classname, "needs update")
        if self.doc_needs_update(classname):
            print("Updating...")
            try:
                self.read_object_doc(os.path.join(self.doc_folder, classname+".doc"))
            except FileNotFoundError:
                pass

    def read_object_doc(self, fpath):
        objdoc: DocFile = DocFile.from_file(fpath)
        self.last_changed[objdoc.classname] = os.stat(fpath).st_mtime
        for item, doc in objdoc.docs.items():
            self.docs[item] = doc

    def add_doc(self, game, classname, fieldtype, doc):
        self.docs[(game, classname, fieldtype)] = doc

    def get_doc(self, game, classname, fieldtype):
        return self.docs.get((game, classname, fieldtype), "")

BW_DOCUMENTATION = FieldDocumentationHolder("objecthelp/")


class FieldEdit(QtCore.QObject):
    edit_obj = QtCore.pyqtSignal(str, int)
    editor_refresh = QtCore.pyqtSignal()

    def __init__(self, parent, editor, object, tag, name, type, elements, item_cache=None):
        super().__init__()
        self.object = object
        #self.edit_layout = QtWidgets.QVBoxLayout(self)
        self.name = SelectableLabel(name, parent)
        tooltip = "Data Type: {}".format(type)
        doc = BW_DOCUMENTATION

        if doc is not None:
            doc.update(object.type)
            game = "BW2" if editor.level_file.bw2 else "BW1"
            tooltip_extra = doc.get_doc(game, object.type, name)

            if tooltip_extra:
                tooltip += "\n" + tooltip_extra

        self.name.setToolTip(tooltip)
        #self.edit_layout.addWidget(self.name)
        #self.setLayout(self.edit_layout)

        #self.edit_layout.setSpacing(0)
        #self.edit_layout.setContentsMargins(0, 0, 0, 0)
        self.lines = []
        self.contents = []
        for i in range(elements):
            print("Adding", name)
            line, content = self.add_field(editor, parent, name, tag, type, i, item_cache)
            assert content is not None
            self.contents.append(content)
            self.lines.append(line)

        self.edit_button = None

    def find_text(self, text, case_sensitive):
        target = text if case_sensitive else text.lower()

        if case_sensitive:
            if target in self.name.text():
                return True, self.name
        else:
            if target in self.name.text().lower():
                return True, self.name

        for line, content in zip(self.lines, self.contents):
            if hasattr(content, "get_searchable_values"):
                values = content.get_searchable_values()

                for val in values:
                    if case_sensitive:
                        if target in val:
                            return True, content
                    else:
                        if target in val.lower():
                            return True, content

        return False, None

    def add_field(self, editor: "bw_editor.LevelEditor", parent, name, tag, type, element, item_cache=None):
        line = QtWidgets.QWidget(parent)
        #line.setContentsMargins(0, 0, 0, 0)
        line_layout = QtWidgets.QHBoxLayout(line)
        line_layout.setContentsMargins(0, 0, 0, 0)
        #line_layout.setSpacing(0)
        line_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        line_layout.addSpacing(30)

        if tag == "Enum":
            pass

        val = getattr(self.object, name)
        if isinstance(val, list):
            val = val[element]

        if editor.level_file.bw2:
            game = "BW2"
        else:
            game = "BW1"

        if tag == "Enum":
            items = ENUMS[game][type]
            getter = make_getter(self.object, name, element)
            setter = make_setter(self.object, name, element)
            if type == "eBoolean":
                content = BooleanEnumBox(line, getter, setter)
            else:
                content = EnumBox(line, items, getter, setter)
            content.update_value()
            line_layout.addWidget(content)
        elif tag == "Attribute" and get_field_name(self.object.type, name) is not None:
            flagtype = get_field_name(self.object.type, name)
            items = FLAGS[game][flagtype]

            getter = make_getter(self.object, name, element)
            setter = make_setter(self.object, name, element)

            content = FlagBox(line, items, getter, setter)
            content.update_value()
            line_layout.addWidget(content)
        elif tag == "Attribute" and type in ("sInt8", "sInt16", "sInt32",
                                                         "sUInt8", "sUInt16", "sUInt32"):
            getter = make_getter(self.object, name, element)
            setter = make_setter(self.object, name, element)

            content = IntegerInput(line, type, getter, setter)
            content.update_value()
            line_layout.addWidget(content)
        elif tag == "Attribute" and type in ("sFloat", "sFloat32"):
            getter = make_getter(self.object, name, element)
            setter = make_setter(self.object, name, element)

            content = DecimalInput(line, getter, setter)
            content.update_value()
            line_layout.addWidget(content)
        elif tag == "Attribute" and type in ("sVector4", "sU8Color", "sVectorXZ", "cU8Color"):
            getter = make_getter(self.object, name, element)

            content = Vector4Edit(line, type, getter)
            content.update_value()
            line_layout.addWidget(content)
        elif tag == "Attribute" and type in ("sMatrix4x4", "cMatrix4x4"):
            getter = make_getter(self.object, name, element)

            content = MatrixEdit(line, getter)
            content.update_value()
            line_layout.addWidget(content)
        elif tag == "Attribute" and type in ("cFxString8", "cFxString16"):
            getter = make_getter(self.object, name, element)
            setter = make_setter(self.object, name, element)

            content = StringEdit(line, getter, setter)
            content.update_value()
            line_layout.addWidget(content)
        elif tag in ("Pointer", "Resource"):
            getter = make_getter(self.object, name, element)
            setter = make_setter(self.object, name, element)

            content = ReferenceEdit(line, editor.level_file, editor.preload_file, type, getter, setter)
            content.edit_button.pressed.connect(lambda: self.edit_obj.emit(name, element))

            def model_refresh():
                for obj in editor.level_file.objects.values():
                    obj.updatemodelname()

            content.changed.connect(model_refresh)

            def set_to_selected():
                selected_obj = editor.get_selected_obj()
                if selected_obj is not None and content.is_instance(selected_obj.type):
                    setter(selected_obj)
                content.update_value()
                model_refresh()
                self.trigger_editor_refresh()

            def select_goto():
                obj = getter()
                if obj is not None:
                    editor.level_view.selected = [obj]
                    editor.pik_control.goto_object(obj.id)
                    editor.level_view.select_update.emit()

            content.set_to_selected_button.pressed.connect(set_to_selected)
            content.goto_button.pressed.connect(select_goto)

            content.update_value(item_cache)
            line_layout.addWidget(content)
        else:
            raise RuntimeError("Unknown Type")

        content.changed.connect(self.trigger_editor_refresh)

        #self.lines.append(line)
        return line, content

    def update_value(self):
        for content in self.contents:
            content.update_value()

    def trigger_editor_refresh(self):
        self.editor_refresh.emit()


class StringEdit(QtWidgets.QLineEdit):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent, get_value, set_value):
        super().__init__(parent)

        self.get_value = get_value
        self.set_value = set_value
        self.textChanged.connect(self.change_value)
        self.editingFinished.connect(self.emit_change)

    def install_filter(self, filt):
        self.installEventFilter(filt)

    def get_searchable_values(self):
        return [self.text()]

    def update_value(self):
        val = self.get_value()
        if val is None:
            val = ""
        self.blockSignals(True)
        self.setText(str(val))
        self.blockSignals(False)

    def change_value(self, val):
        self.set_value(val)

    def emit_change(self):
        self.changed.emit()


class CustomNameEdit(QtWidgets.QLineEdit):
    def __init__(self, parent, get_value, set_value):
        super().__init__(parent)

        self.get_value = get_value
        self.set_value = set_value
        self.textChanged.connect(self.change_value)

    def find_text(self, value, case_sensitive):
        if case_sensitive:
            return value in self.text(), self
        else:
            return value.lower() in self.text().lower(), self

    def update_value(self):
        val = self.get_value()
        if val is None:
            val = ""
        self.blockSignals(True)
        self.setText(str(val))
        self.blockSignals(False)

    def change_value(self, val):
        val = val.strip()
        if not val:
            self.set_value(None)
        else:
            self.set_value(val)


class LuaNameEdit(QtWidgets.QWidget):
    def __init__(self, parent, get_value, set_value, name_usages, obj):
        super().__init__(parent)

        self.textinput = QtWidgets.QLineEdit(self)
        self.vbox = QtWidgets.QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.already_exists = SelectableLabel("Lua name already exists! Please use a different one.", self)
        self.vbox.addWidget(self.textinput)
        self.vbox.addWidget(self.already_exists)
        self.already_exists.setVisible(False)

        self.get_value = get_value
        self.set_value = set_value
        self.name_usages = name_usages
        self.textinput.textChanged.connect(self.change_value)
        self.object = obj
    
    def find_text(self, value, case_sensitive):
        if case_sensitive:
            return value in self.textinput.text(), self
        else:
            return value.lower() in self.textinput.text(), self

    def get_searchable_values(self):
        return [self.textinput.text()]

    def display_already_exists(self):
        self.already_exists.setVisible(True)

    def hide_already_exists(self):
        self.already_exists.setVisible(False)

    def update_value(self):
        val = self.get_value()
        if val is None:
            val = ""
        self.blockSignals(True)
        self.textinput.setText(str(val))
        self.blockSignals(False)

    def change_value(self, val):
        val = val.strip()
        if not val:
            self.hide_already_exists()
            self.set_value(None)
        else:
            usages = self.name_usages(val)
            if len(usages) > 1 or len(usages) == 1 and self.object.id not in usages:
                self.display_already_exists()
            else:
                self.hide_already_exists()
                self.set_value(val)


class MiscEdit(QtWidgets.QWidget):
    def __init__(self,
                 parent,
                 get_setters_custom,
                 get_setters_lua,
                 name_usages,
                 obj):
        super().__init__(parent)
        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.setContentsMargins(0, 0, 0, 0)
        self.custom_name = CustomNameEdit(self,
                                          get_setters_custom[0],
                                          get_setters_custom[1])
        self.lua_name = LuaNameEdit(self,
                                    get_setters_lua[0],
                                    get_setters_lua[1],
                                    name_usages,
                                    obj)
        self.object_id = SelectableLabel(f"Object ID: {obj.id}", self)
        self.hbox.addWidget(self.object_id)
        self.hbox.addWidget(make_labeled_widget(self, "Lua name", self.lua_name))
        self.hbox.addWidget(make_labeled_widget(self, "Custom name", self.custom_name))

    def find_text(self, value, case_sensitive):
        result, ref = self.lua_name.find_text(value, case_sensitive)
        if not result:
            result, ref = self.custom_name.find_text(value, case_sensitive)

        return result, ref

    def update_value(self):
        self.custom_name.update_value()
        self.lua_name.update_value()


class TooltippedLabel(QtWidgets.QLabel):
    def __init__(self, name, parent, tooltip):
        super().__init__(name, parent)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setToolTip(tooltip)


class HorizWidgetHolder(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.setContentsMargins(0, 0, 0, 0)

    def add_widget(self, widget: QtWidgets.QWidget):
        self.hbox.addWidget(widget)
        widget.setParent(self)

    def add_stretch(self, value):
        self.hbox.addStretch(value)


class NewEditWindow(QtWidgets.QMdiSubWindow):
    closing = QtCore.pyqtSignal()
    main_window_changed = QtCore.pyqtSignal(object)
    object_edited = QtCore.pyqtSignal(object)

    def __init__(self, parent, object: BattalionObject, editor: "bw_editor.LevelEditor", makewindow):
        super().__init__(parent)
        self.resize(900, 500)
        self.setMinimumSize(QtCore.QSize(300, 300))

        self.highlight = HighlightArrow(self)
        self.highlight.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.highlight.change_color(255, 255, 0, 50)
        self.highlight.hide()
        self.installEventFilter(self)
        if ICONS["COPY"] is None:
            ICONS["COPY"] = load_icon("resources/Copy-32x32.png")

        self.is_autoupdate = False
        self.editor = editor
        self.object = object
        self.makewindow = makewindow
        self.setWindowTitle(f"Edit Object: {object.name}")

        self.scroll_area = QtWidgets.QScrollArea(self)

        self.content_holder = QtWidgets.QWidget(self.scroll_area)

        self.scroll_area.setWidget(self.content_holder)

        self.area_layout = QtWidgets.QGridLayout(self.content_holder)
        self.area_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.content_holder.setLayout(self.area_layout)
        self.setWidget(self.scroll_area)
        self.scroll_area.setWidgetResizable(True)
        self.keep_window_on_top = False
        self.setup_rows(object)

        self.scheduled_scrollbar_pos = None
        self.scroll_area.verticalScrollBar().rangeChanged.connect(self.scroll_area_bar_update)

        self.object_edited.connect(self.update_water_level)
        self.object_edited.connect(self.reset_highlight)

        self.search_curr_row = 0

        self.find_shortcut = QtGui.QShortcut("Ctrl+F", self)
        self.find_shortcut.activated.connect(self.goto_find_box)

    def eventFilter(self, object, event) -> bool:
        result = super().eventFilter(object, event)
        if (event.type() == QtCore.QEvent.Type.MouseButtonPress):
            self.reset_highlight()
        return result

    def changeEvent(self, changeEvent: QtCore.QEvent) -> None:
        super().changeEvent(changeEvent)
        print(changeEvent.type())
        if changeEvent.type() == QtCore.QEvent.Type.ActivationChange:
            self.reset_highlight()

    def mousePressEvent(self, mouseEvent: typing.Optional[QtGui.QMouseEvent]) -> None:
        super().mousePressEvent(mouseEvent)
        self.highlight.hide()
        self.search_curr_row = 0

    def attach_highlight(self, widget):
        self.highlight.setParent(widget)
        self.highlight.setFixedSize(widget.width(), widget.height())
        self.highlight.show()

    def reset_highlight(self):
        self.highlight.hide()
        self.search_curr_row = 0

    def goto_find_box(self):
        self.search_bar.textinput.setFocus()
        self.scroll_area.ensureWidgetVisible(self.search_bar)

    def search(self, text):
        maxrows = len(self.fields)

        if self.search_curr_row >= maxrows:
            self.search_curr_row = 0

        for i in range(self.search_curr_row, maxrows):
            field = self.fields[i]

            found, widget = field.find_text(text, False)

            if found:
                self.attach_highlight(widget)
                self.scroll_area.ensureWidgetVisible(widget)
                self.search_curr_row = i+1
                break
        else:
            self.search_curr_row = 0

    def closeEvent(self, event):
        self.closing.emit()

    def change_object(self, object):
        remember_scrollbar = object.type == self.object.type
        pos = self.scroll_area.verticalScrollBar().value()

        start = default_timer()
        self.content_holder.hide()
        self.content_holder.deleteLater()
        self.content_holder.setParent(None)

        self.content_holder = QtWidgets.QWidget()
        self.scroll_area.setWidget(self.content_holder)

        self.area_layout = QtWidgets.QGridLayout(self.content_holder)
        self.area_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.content_holder.setLayout(self.area_layout)

        self._curr_row = 0
        self.search_curr_row = 0
        self.object = object
        self.setWindowTitle(f"Edit Object: {object.name}")
        print("Edit reset in", default_timer()-start, "s")
        self.setup_rows(object)

        if remember_scrollbar:
            self.scheduled_scrollbar_pos = pos
        else:
            self.scheduled_scrollbar_pos = None

    # Have to update the scrollbar position on range change, otherwise it takes no effect
    def scroll_area_bar_update(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        if scrollbar.maximum() > 0 and self.scheduled_scrollbar_pos is not None:
            scrollbar.setValue(self.scheduled_scrollbar_pos)
            self.scheduled_scrollbar_pos = None

    def change_window_on_top_state(self, state):
        self.keep_window_on_top = state

        if state == QtCore.Qt.CheckState.Checked:
            print("turning ontop on", state)
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        else:
            print("turning ontop off", state)
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowStaysOnTopHint)

        self.show()

    def store_autoupdate_status(self):
        self.is_autoupdate = self.autoupdate_checkbox.isChecked()

    def setup_rows(self, object: BattalionObject):
        start = default_timer()
        self.fields = []
        editor = self.editor
        parent = None

        self._curr_row = 0


        self.search_bar = SearchBar(self.content_holder)
        self.add_row(name=SelectableLabel("Search"),
                     widget=self.search_bar)
        self.search_bar.find.connect(self.search)

        getter = make_getter(object, "customname")
        setter = lambda x: object.set_custom_name(x)

        checkbox_holder = HorizWidgetHolder(self)
        self.add_row(TooltippedLabel("Window Settings",
                                     parent,
                                     "Keep Window On Top: If set, this window will stay on top of other windows no matter which one is in focus.\n"
                                     "Change Context to Selected Object: If set, selecting an object in the editor will change this edit window to show that object's data."),
                     checkbox_holder)


        checkbox_widget = QtWidgets.QCheckBox(self.content_holder)
        checkbox_widget.setText("Keep Window On Top")
        """self.add_row(TooltippedLabel("Keep Window On Top",
                                     parent,
                                     "If set, this window will stay on top of other windows no matter which one is in focus."),
                    checkbox_widget)"""

        checkbox_widget.setChecked(self.keep_window_on_top==QtCore.Qt.CheckState.Checked)
        checkbox_widget.checkStateChanged.connect(self.change_window_on_top_state)

        self.autoupdate_checkbox = QtWidgets.QCheckBox(self.content_holder)
        self.autoupdate_checkbox.setText("Change Context to Selected Object")
        """self.add_row(TooltippedLabel(
            "Change Context to Selected Object",
            parent,
            "If set, selecting an object in the editor will change this edit window to show that object's data."

        ), self.autoupdate_checkbox)"""
        self.autoupdate_checkbox.setChecked(self.is_autoupdate)
        self.autoupdate_checkbox.checkStateChanged.connect(self.store_autoupdate_status)
        self.autoupdate_checkbox.checkStateChanged.connect(lambda x: self.main_window_changed.emit(self))
        checkbox_holder.add_widget(checkbox_widget)
        checkbox_holder.add_widget(self.autoupdate_checkbox)
        checkbox_holder.add_stretch(1)


        # Add custom name field
        getter = make_getter(object, "customname")
        setter = lambda x: object.set_custom_name(x)
        custom_getsetters = (getter, setter)


        #customname_edit = CustomNameEdit(self.content_holder, getter, setter)
        #self.fields.append(customname_edit)
        #self.add_row(TooltippedLabel("Custom Name",
        #                              parent,
        #                              "A user-decided object name for reference in the editor."),
        #                             customname_edit)
        #customname_edit.update_value()
        #customname_edit.editingFinished.connect(self.refresh_editor)

        # Add Lua name field
        def getter():
            if editor.lua_workbench.entityinit is not None:
                return editor.lua_workbench.entityinit.get_name(object.id)
            return ""

        def setter(x):
            if x is None:
                editor.lua_workbench.entityinit.delete_name(object.id)
            else:
                editor.lua_workbench.entityinit.set_name(object.id, x)

        lua_getsetters = (getter, setter)
        item_cache = {}
        #luaname_edit = LuaNameEdit(self.content_holder, getter, setter, editor.lua_workbench.entityinit.name_usages, object)
        #luaname_edit.textinput.installEventFilter(self)

        misc_edit = MiscEdit(self.content_holder,
                             custom_getsetters,
                             lua_getsetters,
                             editor.lua_workbench.entityinit.name_usages,
                             object)
        misc_edit.custom_name.editingFinished.connect(self.refresh_editor)
        misc_edit.lua_name.textinput.installEventFilter(self)
        misc_edit.update_value()
        self.fields.append(misc_edit)
        self.add_row(
            TooltippedLabel("Misc",
                            parent,
                            (
                                "Lua name: Lua variable which references this object.\n"
                                "Custom name: A user-decided object name for reference in the editor."
                            )),
                            misc_edit
        )

        self.add_row(Line(self), Line(self))

        #self.fields.append(luaname_edit)
        #self.add_row(TooltippedLabel("Lua Name", parent, "Lua variable which references this object."), luaname_edit)
        #luaname_edit.update_value()
        for tag, name, type, elements in object.fields():
            field = FieldEdit(self.content_holder, editor, object, tag, name, type, elements, item_cache)
            field.editor_refresh.connect(self.object_was_updated)
            field.editor_refresh.connect(self.refresh_editor)
            field.edit_obj.connect(self.open_window)
            self.fields.append(field)

            name, firstitem = field.name, field.lines[0]
            self.add_row(name, firstitem)
            if len(field.lines) > 1:
                for i in range(1, len(field.lines)):
                    self.add_row(None, field.lines[i])
        print("Added widgets in", default_timer()-start, "s")

    def object_was_updated(self):
        self.object_edited.emit(self.object)

    def update_water_level(self, obj):
        if obj is not None and obj.type == "cRenderParams":
            self.editor.level_view.waterheight = obj.mWaterHeight

    def refresh_editor(self):
        self.editor.level_view.do_redraw(forcelightdirty=True)
        self.editor.leveldatatreeview.updatenames()
        self.editor.set_has_unsaved_changes(True)

    def add_row(self, name=None, widget=None):
        if name is not None:
            self.area_layout.addWidget(name, self._curr_row, 0)

        if widget is not None:
            self.area_layout.addWidget(widget, self._curr_row, 1)
        self._curr_row += 1

    def open_window(self, attr, i):
        val = getattr(self.object, attr)
        if isinstance(val, list):
            obj = val[i]
        else:
            obj = val

        self.makewindow(self.editor, obj)

    def activate(self):
        self.setWindowState(
            self.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
        self.activateWindow()
        self.show()