import traceback

from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect


class ObjectViewSelectionToggle(object):
    def __init__(self, name, menuparent, option3d_exists=False):
        self.name = name
        self.menuparent = menuparent

        self.option3d_exists = option3d_exists

        self.action_view_toggle = QAction("{0} visible".format(name), menuparent)
        self.action_select_toggle = QAction("{0} 3D visible".format(name), menuparent)
        self.action_view_toggle.setCheckable(True)
        self.action_view_toggle.setChecked(True)
        self.action_select_toggle.setCheckable(True)
        self.action_select_toggle.setChecked(True)

        self.action_view_toggle.triggered.connect(self.handle_view_toggle)
        #self.action_select_toggle.triggered.connect(self.handle_select_toggle)

        menuparent.addAction(self.action_view_toggle)
        if option3d_exists:
            menuparent.addAction(self.action_select_toggle)

        self.action_view_toggle.triggered.connect(self.menuparent.emit_update)
        self.action_select_toggle.triggered.connect(self.menuparent.emit_update)

    def add_3d(self):
        self.menuparent.addAction(self.action_select_toggle)

    def handle_view_toggle(self, val):
        if not val:
            self.action_select_toggle.setChecked(False)
        else:
            self.action_select_toggle.setChecked(True)

    def handle_select_toggle(self, val):
        if val:
            self.action_view_toggle.setChecked(True)

    def is_visible(self):
        return self.action_view_toggle.isChecked()

    def is_selectable(self):
        return self.action_select_toggle.isChecked()


a = {
  "cAirVehicle":                    [1.0, 1.0, 0.0, 1.0],
  "cGroundVehicle":                 [0.705, 0.196, 0.0, 1.0],
   "cTroop":                         [0.0, 0.0, 1.0, 1.0],
  "cWaterVehicle":                  [0.0, 0.58, 0.0, 1.0],

  "cAmbientAreaPointSoundBox":      [0.4, 0, 0.6, 1.0],
  "cAmbientAreaPointSoundSphere":   [0.4, 0, 0.6, 1.0],

  "cBuilding":                      [0.549, 1.0, 0.0, 1.0],
  "cCamera":                        [0.929, 0.576, 0.576, 1.0],
  "cCapturePoint":                  [0.243, 0.352, 0.588, 1.0],

  "cCoastZone":                     [1.0, 1.0, 1.0, 1.0],
  "cDamageZone":                    [0.4, 0.6, 0.6, 1.0],
  "cMapZone":                       [0.5, 0.5, 0.5, 1.0],
  "cNogoHintZone":                  [1.0, 0.0, 0.0, 1.0],

  "cDestroyableObject":             [0.0, 0.0, 0.0, 1.0],


  "cMorphingBuilding":              [0.635, 0.564, 0.839, 1.0],

  "cObjectiveMarker":               [1.0, 1.0, 1.0, 1.0],
  "cPickupReflected":               [0.671, 0.012, 0.012, 1.0],
  "cReflectedUnitGroup":            [0.0, 0.341, 0.216, 1.0],
  "cSceneryCluster":                [0.352, 0.156, 0.156, 1.0],

  "cWaypoint":                      [0.0, 1.0, 1.0, 1.0],
}


class FilterViewMenu(QMenu):
    filter_update = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTitle("Filter View")

        self.show_all = QAction("Show All", self)
        self.show_all.triggered.connect(self.handle_show_all)
        self.addAction(self.show_all)

        self.hide_all = QAction("Hide All", self)
        self.hide_all.triggered.connect(self.handle_hide_all)
        self.addAction(self.hide_all)
        self.addSeparator()
        self.groundtroops = ObjectViewSelectionToggle("Troops", self, True)
        self.groundvehicles = ObjectViewSelectionToggle("Ground Vehicles", self, True)
        self.airvehicles = ObjectViewSelectionToggle("Air Vehicles", self, True)
        self.watervehicles = ObjectViewSelectionToggle("Water Vehicles", self, True)
        self.buildings = ObjectViewSelectionToggle("Buildings", self, True)
        self.pickups = ObjectViewSelectionToggle("Pickups", self, True)
        self.destroyableobjects = ObjectViewSelectionToggle("Destroyable Objects", self, True)
        self.scenerycluster = ObjectViewSelectionToggle("Scenery Clusters", self, True)
        self.capturepoints = ObjectViewSelectionToggle("Capture Points", self, True)
        self.cameras = ObjectViewSelectionToggle("Cameras", self)

        self.zones = ObjectViewSelectionToggle("Zones", self)
        self.waypoints = ObjectViewSelectionToggle("Waypoints", self)
        self.ambientareapoints = ObjectViewSelectionToggle("Ambient Area Points", self)
        self.objectivemarkers = ObjectViewSelectionToggle("Objective Markers", self)
        self.unitgroups = ObjectViewSelectionToggle("Unit Groups", self)

        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.pickups, self.destroyableobjects, self.scenerycluster,
                       self.cameras, self.capturepoints, self.zones, self.waypoints, self.ambientareapoints,
                       self.objectivemarkers, self.unitgroups):

            action.action_view_toggle.triggered.connect(self.emit_update)
            action.action_select_toggle.triggered.connect(self.emit_update)

        self.addSeparator()

        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.capturepoints, self.pickups, self.destroyableobjects, self.scenerycluster):
            action.add_3d()

        self.toggles = {}
        self.toggles["cAirVehicle"] = self.airvehicles
        self.toggles["cGroundVehicle"] = self.groundvehicles
        self.toggles["cTroop"] = self.groundtroops
        self.toggles["cWaterVehicle"] = self.watervehicles
        self.toggles["cAmbientAreaPointSoundBox"] = self.toggles["cAmbientAreaPointSoundSphere"] = self.ambientareapoints
        self.toggles["cBuilding"] = self.toggles["cMorphingBuilding"] = self.buildings
        self.toggles["cCamera"] = self.cameras
        self.toggles["cCapturePoint"] = self.capturepoints
        self.toggles["cCoastZone"] = self.toggles["cDamageZone"] = self.toggles["cMapZone"] = self.toggles["cNogoHintZone"] = self.zones
        self.toggles["cDestroyableObject"] = self.destroyableobjects
        self.toggles["cObjectiveMarker"] = self.objectivemarkers
        self.toggles["cPickupReflected"] = self.pickups
        self.toggles["cReflectedUnitGroup"] = self.unitgroups
        self.toggles["cSceneryCluster"] = self.scenerycluster
        self.toggles["cWaypoint"] = self.waypoints

    def restore(self, cfg):
        for type, toggle in self.toggles.items():
            if "View Filter Toggles" in cfg:
                visible = cfg["View Filter Toggles"].getboolean(type, fallback=False)
                visible3d = cfg["View Filter Toggles"].getboolean(type+"_3D", fallback=False)
                toggle.action_view_toggle.setChecked(visible)
                if toggle.option3d_exists:
                    toggle.action_select_toggle.setChecked(visible3d)

    def save(self, cfg):
        if "View Filter Toggles" not in cfg:
            cfg["View Filter Toggles"] = {}
        for type, toggle in self.toggles.items():
            cfg["View Filter Toggles"][type] = str(toggle.is_visible())
            if toggle.option3d_exists:
                cfg["View Filter Toggles"][type+"_3D"] = str(toggle.is_selectable())

    def object_3d_visible(self, objtype):
        if objtype in self.toggles:
            return self.toggles[objtype].is_selectable()
        else:
            return True

    def object_visible(self, objtype):
        if objtype in self.toggles:
            return self.toggles[objtype].is_visible()
        else:
            return True

    def handle_show_all(self):
        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.pickups, self.destroyableobjects, self.scenerycluster,
                       self.cameras, self.capturepoints, self.zones, self.waypoints, self.ambientareapoints,
                       self.objectivemarkers, self.unitgroups):
            action.action_view_toggle.setChecked(True)
            action.action_select_toggle.setChecked(True)
        self.filter_update.emit()

    def handle_hide_all(self):
        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.pickups, self.destroyableobjects, self.scenerycluster,
                       self.cameras, self.capturepoints, self.zones, self.waypoints, self.ambientareapoints,
                       self.objectivemarkers, self.unitgroups):
            action.action_view_toggle.setChecked(False)
            action.action_select_toggle.setChecked(False)
        self.filter_update.emit()

    def emit_update(self, val):
        self.filter_update.emit()

    def mouseReleaseEvent(self, e):
        try:
            action = self.activeAction()
            if action and action.isEnabled():
                action.trigger()
            else:
                QMenu.mouseReleaseEvent(self, e)
        except:
            traceback.print_exc()
