import traceback
from functools import partial

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import QSize, pyqtSignal, QPoint, QRect
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
from lib.BattalionXMLLib import BattalionObject

from widgets.qtutils import NonDismissableAction, NonAutodismissibleMenu, ActionFunction

import typing
if typing.TYPE_CHECKING:
    from bw_editor import LevelEditor





class ShowHideAllCategory(object):
    def __init__(self, name, menuparent, content: None | list["ObjectViewSelectionToggle"] = None):
        self.name = name

        self.toggle_parent = menuparent

        self.action_show = NonDismissableAction("Show all {0}".format(name), self.toggle_parent)
        self.action_show_only = NonDismissableAction("Show only {0}".format(name), self.toggle_parent)
        self.action_hide = NonDismissableAction("Hide all {0}".format(name), self.toggle_parent)

        self.toggle_parent.addAction(self.action_show)
        self.toggle_parent.addAction(self.action_show_only)
        self.toggle_parent.addAction(self.action_hide)

        self.action_show.triggered.connect(self.show_all)
        self.action_hide.triggered.connect(self.hide_all)

        self.content = []
        if content is not None:
            self.content.extend(content)

    def show_all(self):
        for toggle in self.content:
            toggle.action_view_toggle.setChecked(True)
            toggle.action_select_toggle.setChecked(True)

    def hide_all(self):
        for toggle in self.content:
            toggle.action_view_toggle.setChecked(False)
            toggle.action_select_toggle.setChecked(False)


class SubGroup(NonAutodismissibleMenu):
    show_all = pyqtSignal(object)

    def __init__(self, name, menuparent):
        super().__init__(parent=menuparent, title=name)
        self.showhide = ShowHideAllCategory(name, self)
        self.showhide.action_show_only.triggered.connect(
            lambda: self.show_all.emit(self.showhide)
        )

    def add_content(self, content: "ObjectViewSelectionToggle"):
        self.showhide.content.append(content)


class ObjectViewSelectionToggle(object):
    def __init__(self, name, menuparent, option3d_exists=False, addlater=False, subgroup=None):
        self.name = name
        self.menuparent = menuparent
        self.toggle_parent = menuparent if subgroup is None else subgroup

        self.option3d_exists = option3d_exists

        self.action_view_toggle = QAction("{0} visible".format(name), self.toggle_parent)
        self.action_select_toggle = QAction("{0} 3D visible".format(name), self.toggle_parent)
        self.action_view_toggle.setCheckable(True)
        self.action_view_toggle.setChecked(True)
        self.action_select_toggle.setCheckable(True)
        self.action_select_toggle.setChecked(True)

        self.action_view_toggle.triggered.connect(self.handle_view_toggle)
        #self.action_select_toggle.triggered.connect(self.handle_select_toggle)
        self.toggle_parent: QMenu

        if not addlater:
            self.toggle_parent.addAction(self.action_view_toggle)

        if option3d_exists:
            self.toggle_parent.addAction(self.action_select_toggle)

        if subgroup is not None:
            subgroup.add_content(self)

        self.action_view_toggle.triggered.connect(self.menuparent.emit_update)
        self.action_select_toggle.triggered.connect(self.menuparent.emit_update)

    def add_3d(self):
        self.toggle_parent.addAction(self.action_select_toggle)

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


class FilterViewMenu(NonAutodismissibleMenu):
    filter_update = pyqtSignal()

    def __init__(self, editor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTitle("Filter View")
        self.visibility_override = False

        self.editor: LevelEditor = editor

        self.show_all = QAction("Show All", self)
        self.show_all.triggered.connect(self.handle_show_all)
        self.addAction(self.show_all)

        self.hide_all = QAction("Hide All", self)
        self.hide_all.triggered.connect(self.handle_hide_all)
        self.addAction(self.hide_all)
        self.addSeparator()

        self.show_full_scenery_action = QAction("Show Full Scenery", self)
        self.show_full_scenery_action.setCheckable(True)
        self.show_full_scenery_action.triggered.connect(self.show_full_scenery_changed)
        self.addAction(self.show_full_scenery_action)

        self.addSeparator()

        self.units_menu = SubGroup("Units", self)
        self.map_content = SubGroup("Map Objects", self)
        self.misc_content = SubGroup("Misc Objects", self)
        self.zones = SubGroup("Zones", self)

        self.units_menu.show_all.connect(self.show_only)
        self.map_content.show_all.connect(self.show_only)
        self.misc_content.show_all.connect(self.show_only)
        self.zones.show_all.connect(self.show_only)

        self.addMenu(self.units_menu)
        self.addMenu(self.map_content)
        self.addMenu(self.misc_content)
        self.addMenu(self.zones)

        self.groundtroops = ObjectViewSelectionToggle("Troops", self, True, subgroup=self.units_menu)
        self.groundvehicles = ObjectViewSelectionToggle("Ground Vehicles", self, True, subgroup=self.units_menu)
        self.airvehicles = ObjectViewSelectionToggle("Air Vehicles", self, True, subgroup=self.units_menu)
        self.watervehicles = ObjectViewSelectionToggle("Water Vehicles", self, True, subgroup=self.units_menu)

        self.buildings = ObjectViewSelectionToggle("Buildings", self, True, subgroup=self.map_content)
        self.pickups = ObjectViewSelectionToggle("Pickups", self, True, subgroup=self.map_content)
        self.destroyableobjects = ObjectViewSelectionToggle("Destroyable Objects", self, True, subgroup=self.map_content)
        self.scenerycluster = ObjectViewSelectionToggle("Scenery Clusters", self, True, subgroup=self.map_content)
        self.capturepoints = ObjectViewSelectionToggle("Capture Points", self, True, subgroup=self.map_content)
        self.cameras = ObjectViewSelectionToggle("Cameras", self, subgroup=self.misc_content)

        #self.mapzones = ObjectViewSelectionToggle("Map Zones", self)
        #self.damagezones = ObjectViewSelectionToggle("Damage Zones", self)
        #self.coastzones = ObjectViewSelectionToggle("Coast Zones", self)
        #self.nogohintzones = ObjectViewSelectionToggle("No-Go Hint Zones", self)

        self.zone_defaultzones = ObjectViewSelectionToggle("Default Zones", self, subgroup=self.zones)
        self.zone_worldboundary = ObjectViewSelectionToggle("World Boundary", self, subgroup=self.zones)
        self.zone_mission = ObjectViewSelectionToggle("Mission Boundary", self, subgroup=self.zones)
        self.zone_nogo = ObjectViewSelectionToggle("No-Go Areas", self, subgroup=self.zones)
        self.zone_ford = ObjectViewSelectionToggle("Fords", self, subgroup=self.zones)


        self.waypoints = ObjectViewSelectionToggle("Waypoints", self, subgroup=self.misc_content)
        self.ambientareapoints = ObjectViewSelectionToggle("Ambient Area Points", self, subgroup=self.misc_content)
        self.objectivemarkers = ObjectViewSelectionToggle("Objective Markers", self, subgroup=self.misc_content)
        self.unitgroups = ObjectViewSelectionToggle("Unit Groups", self, subgroup=self.misc_content)

        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.pickups, self.destroyableobjects, self.scenerycluster,
                       self.cameras, self.capturepoints, #self.mapzones, self.damagezones, self.coastzones, self.nogohintzones,
                       self.waypoints, self.ambientareapoints, self.objectivemarkers, self.unitgroups,
                       self.zone_defaultzones, self.zone_worldboundary, self.zone_mission, self.zone_nogo,self.zone_ford):

            action.action_view_toggle.triggered.connect(self.emit_update)
            action.action_select_toggle.triggered.connect(self.emit_update)

        self.addSeparator()

        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.capturepoints, self.pickups, self.destroyableobjects, self.scenerycluster):
            action.add_3d()

        """self.addSeparator()
        for action in (self.zone_defaultzones, self.zone_worldboundary, self.zone_mission, self.zone_nogo,self.zone_ford):
            self.addAction(action.action_view_toggle)"""
        #self.addAction(self.mapzones.action_view_toggle)
        #self.addAction(self.damagezones.action_view_toggle)
        #self.addAction(self.coastzones.action_view_toggle)
        #self.addAction(self.nogohintzones.action_view_toggle)

        self.toggles = {}
        self.toggles["cAirVehicle"] = self.airvehicles
        self.toggles["cGroundVehicle"] = self.groundvehicles
        self.toggles["cTroop"] = self.groundtroops
        self.toggles["cWaterVehicle"] = self.watervehicles
        self.toggles["cAmbientAreaPointSoundBox"] = self.toggles["cAmbientAreaPointSoundSphere"] = self.ambientareapoints
        self.toggles["cBuilding"] = self.toggles["cMorphingBuilding"] = self.buildings
        self.toggles["cCamera"] = self.cameras
        self.toggles["cCapturePoint"] = self.capturepoints
        #self.toggles["cCoastZone"] = self.coastzones
        #self.toggles["cDamageZone"] = self.damagezones
        #self.toggles["cMapZone"] = self.mapzones
        #self.toggles["cNogoHintZone"] = self.nogohintzones
        self.toggles["cDestroyableObject"] = self.destroyableobjects
        self.toggles["cObjectiveMarker"] = self.objectivemarkers
        self.toggles["cPickupReflected"] = self.pickups
        self.toggles["cReflectedUnitGroup"] = self.unitgroups
        self.toggles["cSceneryCluster"] = self.scenerycluster
        self.toggles["cWaypoint"] = self.waypoints

        self.toggles["ZONETYPE_DEFAULT"] = self.zone_defaultzones
        self.toggles["ZONETYPE_WORLDBOUNDARY"] = self.zone_worldboundary
        self.toggles["ZONETYPE_MISSIONBOUNDARY"] = self.zone_mission
        self.toggles["ZONETYPE_NOGOAREA"] = self.zone_nogo
        self.toggles["ZONETYPE_FORD"] = self.zone_ford

        self.addSeparator()
        self.object_specific_vis = set()

        self.action_limit_to_selection = ActionFunction("Filter to Selected",
                                                        self,
                                                        self.set_object_vis_to_selected)
        self.action_clear_filter = ActionFunction("Reset Filter",
                                                        self,
                                                        self.clear_object_visibility_filter)

        self.addAction(self.action_limit_to_selection)


        filter_menu = QMenu("Filter to Faction", self)
        filter_menu.addAction(ActionFunction("No Army", filter_menu,
                                             partial(self.faction_filter, "eNoArmy")))
        filter_menu.addAction(ActionFunction("Western Frontier", filter_menu,
                                             partial(self.faction_filter, "eWesternFrontier")))
        filter_menu.addAction(ActionFunction("Tundran Territories", filter_menu,
                                             partial(self.faction_filter, "eTundranTerritories")))
        filter_menu.addAction(ActionFunction("Xylvania", filter_menu,
                                             partial(self.faction_filter, "eXylvanian")))
        filter_menu.addAction(ActionFunction("Solar Empire", filter_menu,
                                             partial(self.faction_filter, "eSolarEmpire")))
        filter_menu.addAction(ActionFunction("Iron Legion", filter_menu,
                                             partial(self.faction_filter, "eUnderWorld")))
        filter_menu.addAction(ActionFunction("Neutral", filter_menu,
                                             partial(self.faction_filter, "eNeutral")))
        filter_menu.addAction(ActionFunction("Anglo Isles", filter_menu,
                                             partial(self.faction_filter, "eAngloIsles")))
        self.addMenu(filter_menu)
        self.addAction(self.action_clear_filter)

        self.filter_rule = None

    def show_full_scenery_changed(self):
        self.filter_update.emit()

    def show_full_scenery(self):
        return self.show_full_scenery_action.isChecked()

    def show_only(self, toggle_group):
        self.handle_hide_all()
        toggle_group.show_all()

    def set_filter_rule(self, filter_rule):
        self.filter_rule = filter_rule
        self.filter_update.emit()

    def faction_filter(self, faction):
        self.set_filter_rule(lambda x: x.faction == faction)

    def set_object_vis_to_selected(self):
        selected = set(self.editor.get_selected_objs())
        if selected:
            self.filter_rule = lambda x: x in selected
            self.filter_update.emit()

    def clear_object_visibility_filter(self):
        self.filter_rule = None
        self.filter_update.emit()

    def add_object_visibility(self, objects):
        for obj in objects:
            self.object_specific_vis.add(obj.id)

    def restore(self, cfg):
        for type, toggle in self.toggles.items():
            if "View Filter Toggles" in cfg:
                visible = cfg["View Filter Toggles"].getboolean(type, fallback=False)
                visible3d = cfg["View Filter Toggles"].getboolean(type+"_3D", fallback=False)
                toggle.action_view_toggle.setChecked(visible)
                if toggle.option3d_exists:
                    toggle.action_select_toggle.setChecked(visible3d)

        full_scenery = cfg["View Filter Toggles"].getboolean("full_scenery", fallback=False)
        self.show_full_scenery_action.setChecked(full_scenery)

    def save(self, cfg):
        if "View Filter Toggles" not in cfg:
            cfg["View Filter Toggles"] = {}
        for type, toggle in self.toggles.items():
            cfg["View Filter Toggles"][type] = str(toggle.is_visible())
            if toggle.option3d_exists:
                cfg["View Filter Toggles"][type+"_3D"] = str(toggle.is_selectable())

        cfg["View Filter Toggles"]["full_scenery"] = str(self.show_full_scenery_action.isChecked())

    def object_3d_visible(self, objtype):
        if self.visibility_override:
            return True

        if objtype in self.toggles:

            return self.toggles[objtype].is_selectable()
        else:
            return True

    def object_visible(self, objtype, obj):
        if self.visibility_override:
            return True

        if obj is not None and objtype in ("cMapZone", "cCoastZone", "cDamageZone", "cNogoHintZone"):
            if obj.mZoneType in self.toggles:
                if self.filter_rule is not None and obj is not None:
                    return self.toggles[obj.mZoneType].is_visible() and self.filter_rule(obj)
                else:
                    return self.toggles[obj.mZoneType].is_visible()
            else:
                return True

        if objtype in self.toggles:
            if self.filter_rule is not None and obj is not None:
                return self.toggles[objtype].is_visible() and self.filter_rule(obj)
            else:
                return self.toggles[objtype].is_visible()
        else:
            return True

    def handle_show_all(self):
        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.pickups, self.destroyableobjects, self.scenerycluster,
                       self.cameras, self.capturepoints, #.mapzones, self.damagezones, self.coastzones, self.nogohintzones,
                       self.waypoints, self.ambientareapoints,
                       self.objectivemarkers, self.unitgroups,
                       self.zone_defaultzones, self.zone_worldboundary, self.zone_mission, self.zone_nogo,self.zone_ford):
            action.action_view_toggle.setChecked(True)
            action.action_select_toggle.setChecked(True)
        self.filter_rule = None
        self.filter_update.emit()

    def handle_hide_all(self):
        for action in (self.groundtroops, self.groundvehicles, self.airvehicles, self.watervehicles,
                       self.buildings, self.pickups, self.destroyableobjects, self.scenerycluster,
                       self.cameras, self.capturepoints, #self.mapzones, self.damagezones, self.coastzones, self.nogohintzones,
                       self.waypoints, self.ambientareapoints,
                       self.objectivemarkers, self.unitgroups,
                       self.zone_defaultzones, self.zone_worldboundary, self.zone_mission, self.zone_nogo,self.zone_ford):
            action.action_view_toggle.setChecked(False)
            action.action_select_toggle.setChecked(False)
        self.filter_rule = None
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
