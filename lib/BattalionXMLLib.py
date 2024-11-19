import json
import typing
import hashlib

from functools import partial
from collections.abc import MutableSequence, Iterable
try:
    import xml.etree.cElementTree as etree
except: # cElementTree not available
    import xml.etree.ElementTree as etree

from lib.searchquery import fieldnames

from numpy import array, float32
#import xml.etree.ElementTree.Element as Element
bwfieldnames = set()
for x in fieldnames.values():
    for y in x:
        bwfieldnames.add(y)
LOCALTESTING = False
if not LOCALTESTING:
    from lib.bw_types import convert_from, get_types, BWMatrix, convert_to
    from lib.vectors import Vector4

    with open("resources/BattalionWarsIcons.json", "r") as f:
        BWICONS = json.load(f)
else:
    from bw_types import convert_from, get_types, BWMatrix, convert_to
    from vectors import Vector4

    with open("../resources/BattalionWarsIcons.json", "r") as f:
        BWICONS = json.load(f)


TYPEORDER = [
    "cTequilaEffectResource",
    "cNodeHierarchyResource",
    "cGameScriptResource",
    "sSampleResource",
    "cTextureResource",
    "cSoundBase",
    "cGUINumberNumber",
    "cGUINumberFromFunction",
    "cGUINumberFromLabel",
    "cGUIScriptFunction",
    "cGUIVectorFromLabel",
    "cGUIVectorFromFunction",
    "cGUIScaleFromFunction",
    "cGUIColourFromLabel",
    "cGUIColourFromFunction",
    "cGUIBoolFromFunction",
    "cGUIBoolBool",
    "cGUIButtonSpriteSet",
    "cGUIColourColour",
    "cGUIColourNumber",
    "cGUIStringFromLabel",
    "cGUIStringFromFunction",
    "cCameraBase",
    "cGUIMatrixFromLabel",
    "cGUIStringString",
    "cGUIScaleVector",
    "cGUIBoolFromLabel",
    "cGUIVectorVector",
    "cGUIScaleFromLabel",
    "cSprite",
    "cGUIEvent",
    "cGUISpriteWidget",
    "sSpriteBasetype",
    "cWaypoint",
    "cScriptedSound",
    "cGUISoundWidget",
    "cGUIButtonWidget",
    "cGUISliderWidget",
    "cGUITextureWidget",
    "cGUITextBoxWidget",
    "cGUICustomWidget",
    "cGUIDialogBox3Widget",
    "cGUIDialogBox2Widget",
    "cGUIDialogBox1Widget",
    "cGUIDialogBox0Widget",
    "cGUI3DModelData",
    "cGUI3DObjectWidget",
    "cRenderParams",
    "cGlobalScriptEntity",
    "cInitialisationScriptEntity",
    "cGUIPage",
    "cGUIRectWidget",
    "cGUIVertexColouredRectWidget",
    "cGUIControllerBlip",
    "cScriptSprite",
    "cSKUSpecificData",
    "cGUITequilaData",
    "cGUIListBoxWidget",
    "cGUIEventHandler",
    "cGUITequilaWidget",
    "cScriptedEffectBase",
    "cCamera",
    "cAnimationResource",
    "cSimpleTequilaTaggedEffectBase",
    "cCoverPointBase",
    "sDestroyBase",
    "sSceneryClusterBase",
    "cAnimationTriggeredEffectChainItemGroundImpact",
    "cAdvancedWeaponBase",
    "cImpactTableTaggedEffectBase",
    "cProjectileSoundBase",
    "sProjectileBase",
    "sWeaponBase",
    "sAirVehicleBase",
    "cTroopAnimationSet",
    "cTroopVoiceManagerBase",
    "sTroopBase",
    "cReflectedPhysicsParams",
    "cGroundVehiclePhysicsBase",
    "cGroundVehicleSoundBase",
    "cSeatBase",
    "cGroundVehicleBase",
    "cAnimationTriggeredEffectManager",
    "cSoundCurve",
    "cAirVehicleEngineSoundBase",
    "cBuildingImpBase",
    "cWeaponSoundBase",
    "cArmyAllegiance",
    "cPanelSprites",
    "cObjectiveMarkerBase",
    "cAirVehicleSoundBase",
    "sExplodeBase",
    "cImpactBase",
    "cImpactTableBase",
    "cIncidentalBase",
    "cTerrainParticleGeneratorBase",
    "cCapturePointBase",
    "cAnimationTriggeredEffectChainItemSound",
    "cAnimationTriggeredEffectChainItemTequilaEffect",
    "cReticuleState",
    "cAnimationTriggeredEffect",
    "cTroopVoiceMessageBase",
    "cHUDSoundBlock",
    "sPickupBase",
    "cAirVehiclePhysicsBase",
    "cGroundVehicleEngineSoundBase",
    "cRevConScrollRegionBase",
    "cContextSensitiveIdle",
    "cContextSensitiveIdleList",
    "cPlayerSettings",
    "cHUDVariables",
    "cHUD",
    "cHUDTutorial",
    "cAttackSustainReleaseEnvelope",
    "cFlightData",
    "cMapZone",
    "cPhase",
    "cObjective",
    "cMorphingBuilding",
    "cStrategicInstallation",
    "cActionParameterData",
    "cMeleeHitReactionData",
    "cAmbientAreaPointSoundSphere",
    "cActionParameters",
    "cDestroyableObject",
    "cSceneryCluster",
    "cTroop",
    "cGroundVehicle",
    "cAirVehicle",
    "cBuilding",
    "cCapturePoint",
    "cObjectiveMarker",
    "cWaterVehiclePhysicsBase",
    "cWaterVehicleSoundBase",
    "cWaterVehicleBase",
    "cCoastZone",
    "cReflectedUnitGroup",
    "cWaterVehicle",
    "cPickupReflected",
    "cDamageZone",
    "cNogoHintZone"
]

TYPEORDER_VALUE = {}
for i, v in enumerate(TYPEORDER):
    TYPEORDER_VALUE[v] = i


def sort_key(key):
    if key in TYPEORDER_VALUE:
        return TYPEORDER_VALUE
    else:
        return 99999


class PointerPlaceholder(object):
    def __init__(self, pointer):
        self.pointer = pointer


class PointerAttribute(MutableSequence, Iterable):
    def __init__(self, tag, name, type, values, bwlevel):
        self.tag = tag
        self.name = name
        self.type = type
        self.elements = len(values)
        self.values = values 
        
        self._bwlevel = bwlevel

    def __getitem__(self, i):
        if self.values[i] == "0" or self.values[i] not in self._bwlevel.objects:
            return None 
        else:
            return self._bwlevel.objects[self.values[i]]
    
    def __setitem__(self, i, item):
        if item.id not in self._bwlevel.objects:
            raise RuntimeError("Object isn't in global object list: {0}".format(item.id))
        else:
            self.values[i] = item.id 
    
    def __delitem__(self, i):
        raise RuntimeError("Deletion not supported")
    
    def insert(self, i, item):
        raise RuntimeError("Insertion not supported")
    
    def __len__(self):
        return self.elements 

    def __iter__(self):
        return (self[i] for i in range(len(self)))
    
    def __str__(self):
        return str([x for x in self])
    
    @classmethod
    def from_node(cls, node: etree.Element, bwlevel):
        element_count = int(node.attrib["elements"])
        values = list(convert_from(
                                node.attrib["type"],
                                (node[i].text for i in range(element_count))))
        
        return cls(node.tag, node.attrib["name"], node.attrib["type"], values, bwlevel)
        

class Attribute(PointerAttribute):
    def __getitem__(self, i):
        return self.values[i]
    
    def __setitem__(self, i, item):
        self.values[i] = item
        

class ObjectIDAlreadyExists(Exception):
    pass
    

class AttributeNotAPointer(Exception):
    pass


class AttributeList(MutableSequence, Iterable):
    def __init__(self, node: etree.Element):
        self.node = node 
    
    def __getitem__(self, i):
        return self.node[i].text
    
    def __setitem__(self, i, item):
        self.node[i].text = item
    
    def __delitem__(self, i):
        raise RuntimeError("Deletion not supported")
        
    def insert(self, i, item):
        raise RuntimeError("Insertion not supported")
    
    def __len__(self):
        return int(self.node.attrib["elements"])
    
    def __iter__(self):
        return (self.node[i].text for i in range(len(self)))
    
    def __str__(self):
        return str([x for x in self])
    
        
class BattalionLevelFile(object):
    def __init__(self, fileobj=None, callback=None):
        if fileobj is None:
            root = etree.Element("Instances")
            self._tree = etree.ElementTree(root)
        else:
            self._tree = etree.parse(fileobj)
        self._root = self._tree.getroot()

        self.objects = {}
        self.objects_with_positions = {}

        self._categories: typing.Dict[str, typing.Dict[str, BattalionObject]] = {}
        for category, attr in [("cGameScriptResource", "scripts")]:
            self._categories[category] = {}
            setattr(self, attr, self._categories[category])
        self.scripts: typing.Dict[str, BattalionObject]

        self.bw2 = False

        for i, child in enumerate(self._root):
            if child.tag == "Object":
                bwobject = BattalionObject(self, child)

                if not self.bw2:
                    for node in bwobject._node:
                        if node.attrib["name"] not in bwfieldnames:
                            self.bw2 = True
                            #print("Detected XML as BW2")

                self.add_object(bwobject)
                if callback is not None: callback(len(self._root), i)

        if self.bw2:
            print("Detected XML as BW2")

    def delete_objects(self, objects):
        for obj in objects:
            assert not obj.deleted

        for k, v in self.objects.items():
            v.delete_references(objects)

        for obj in objects:
            if obj.id in self.objects:
                del self.objects[obj.id]
            if obj.id in self.objects_with_positions:
                del self.objects_with_positions[obj.id]
            if obj.type in self._categories and obj.id in self._categories[obj.type]:
                del self._categories[obj.type][obj.id]

        deleted_refs = set(obj.id for obj in objects)
        newroot = etree.Element("Instances")

        for node in self._root:
            if node.tag == "Object":
                if node.attrib["id"] not in deleted_refs:
                    newroot.append(node)
            else:
                newroot.append(node)

        self._tree._setroot(newroot)
        self._root = self._tree.getroot()

    def sort_nodes(self):
        nodes = []
        for node in self._root:
            nodes.append(node)

        nodes.sort(key=sort_key)

        newroot = etree.Element("Instances")
        for node in nodes:
            newroot.append(node)

        self._tree._setroot(newroot)
        self._root = self._tree.getroot()

    def resolve_pointers(self, other):
        for bwobject in self.objects.values():
            bwobject.resolve_pointers(self, other)

        for bwobject in self.objects.values():
            bwobject.updatemodelname()

    def add_object_new(self, bwobject):
        self.add_object(bwobject)
        self._root.append(bwobject._node)

    def add_object(self, bwobject):
        if bwobject in self.objects:
            raise ObjectIDAlreadyExists()

        self.objects[bwobject.id] = bwobject
        hasposition = hasattr(bwobject, "spawnMatrix") or hasattr(bwobject, "Mat") or hasattr(bwobject, "mMatrix")
        if hasposition:
            self.objects_with_positions[bwobject.id] = bwobject
            assert bwobject.getmatrix() is not None

        if bwobject.type in self._categories:
            self._categories[bwobject.type][bwobject.id] = bwobject

    def write(self, f):
        f.write(b"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
        self._tree.write(f, encoding="utf-8", short_empty_elements=False)


class BattalionFilePaths(object):
    def __init__(self, fileobj):
        self._tree = etree.parse(fileobj)
        self._root = self._tree.getroot()

        self.dirty = False

        self.terrainpath = None
        self.stringpaths = {}
        self.resourcepath = None
        self.objectpath = None
        self.preloadpath = None

        self.objectfilepadding = None
        self.preloadpadding = None
        if self._root.tag == "levelfiles":
            for child in self._tree.getroot():
                #print(child.tag)
                if child.tag == "terrain":
                    self.terrainpath = child[0].attrib["name"]
                elif child.tag == "level":
                    for child2 in child:
                        if child2.tag == "resourcefiles":
                            self.resourcepath = child2[0].attrib["name"]
                        elif child2.tag == "objectfiles":
                            self.objectpath = child2[0].attrib["name"]
                            if "padding" in child2[0].attrib:
                                self.objectfilepadding = int(child2[0].attrib["padding"])
                elif child.tag == "strings":
                    for lang in child:
                        self.stringpaths[lang.attrib["name"]] = lang.attrib["file"]
                elif child.tag == "preload":
                    self.preloadpath = child[0].attrib["name"]
                    if "padding" in child[0].attrib:
                        self.preloadpadding = int(child[0].attrib["padding"])

    def clear_object_padding(self):
        self.preloadpadding = None
        for child in self._tree.getroot():
            if child.tag == "level":
                for child2 in child:
                    if child2.tag == "objectfiles":
                        if "padding" in child2[0].attrib:
                            del child2[0].attrib["padding"]

    def set_object_padding(self, pad):
        self.objectfilepadding = pad
        for child in self._tree.getroot():
            if child.tag == "level":
                for child2 in child:
                    if child2.tag == "objectfiles":
                        child2[0].attrib["padding"] = str(pad)

    def clear_preload_padding(self):
        self.preloadpadding = None
        for child in self._tree.getroot():
            if child.tag == "preload":
                if "padding" in child[0].attrib:
                    del child[0].attrib["padding"]

    def set_preload_padding(self, pad):
        self.preloadpadding = pad
        for child in self._tree.getroot():
            if child.tag == "preload":
                child[0].attrib["padding"] = str(pad)

    def set_uncompressed(self):
        levelxml = self._tree.find("level/objectfiles")
        preload = self._tree.find("preload")
        terrain = self._tree.find("terrain")
        resource = self._tree.find("level/resourcefiles")

        self.objectpath = self.objectpath.removesuffix(".gz")
        self.preloadpath = self.preloadpath.removesuffix(".gz")
        self.terrainpath = self.terrainpath.removesuffix(".gz")
        self.resourcepath = self.resourcepath.removesuffix(".gz")

        levelxml[0].attrib["name"] = self.objectpath
        preload[0].attrib["name"] = self.preloadpath
        terrain[0].attrib["name"] = self.terrainpath
        resource[0].attrib["name"] = self.resourcepath

        self.dirty = True

    def set_compressed(self):
        levelxml = self._tree.find("level/objectfiles")
        preload = self._tree.find("preload")
        terrain = self._tree.find("terrain")
        resource = self._tree.find("level/resourcefiles")

        if not self.objectpath.endswith(".gz"):
            self.objectpath += ".gz"
        if not self.preloadpath.endswith(".gz"):
            self.preloadpath += ".gz"
        if not self.terrainpath.endswith(".gz"):
            self.terrainpath += ".gz"
        if not self.resourcepath.endswith(".gz"):
            self.resourcepath += ".gz"

        levelxml[0].attrib["name"] = self.objectpath
        preload[0].attrib["name"] = self.preloadpath
        terrain[0].attrib["name"] = self.terrainpath
        resource[0].attrib["name"] = self.resourcepath

        self.dirty = True

    def write(self, f):
        f.write(b"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
        self._tree.write(f, encoding="utf-8", short_empty_elements=False)
        self.dirty = False


class BattalionObject(object):
    def __init__(self, level: BattalionLevelFile, node: etree.Element):
        self._node = node
        self._level = level

        self._attributes = {}
        self._custom_name = ""
        self.lua_name = ""

        self._referenced_by = set()

        self.update_object_from_xml(self._node)

        self.height = None
        self.dirty = True
        self.deleted = False

        self.mtxoverride = None

    def choose_unique_id(self, level, preload):
        assert not self.deleted

        while self.id in level.objects or self.id in preload.objects:
            self._node.attrib["id"] = str(int(self.id)+7)

    def delete(self):
        self._custom_name = "DELETED"
        self.deleted = True

    def add_reference(self, obj):
        self._referenced_by.add(obj)

    def set_mtx_override(self, values):
        if values is None:
            self.mtxoverride = None
        else:
            self.mtxoverride = array(values, dtype=float32)

    def delete_references(self, references):
        for attr_node in self._node:
            if attr_node.tag in ("Pointer", "Resource"):
                fieldname = attr_node.attrib["name"]
                pointers = [subnode.text for subnode in attr_node]
                if len(pointers) == 1:
                    for ref in references:
                        if getattr(self, fieldname) == ref:
                            setattr(self, fieldname, None)
                            break
                elif len(pointers) > 1:
                    ptrlist = getattr(self, fieldname)
                    for i in range(len(pointers)):
                        obj = pointers[i]
                        for ref in references:
                            if obj == ref:
                                pointers[i] = None
        self.update_xml()

    def check_correctness(self, node, level, other):
        ownattrs = set(x.attrib["name"] for x in self._node)
        newattrs = set(x.attrib["name"] for x in node)
        for attr in ownattrs:
            if attr not in newattrs:
                raise RuntimeError("Missing attribute: {0}".format(attr))

        for attr in newattrs:
            if attr not in ownattrs:
                raise RuntimeError("New attr {0}".format(attr))

        for attr_node in node:
            if attr_node.tag in ("Pointer", "Resource"):
                pointers = [subnode.text for subnode in attr_node]
                for pointer in pointers:
                    if pointer != "0" and pointer not in level.objects and pointer not in other.objects:
                        raise RuntimeError("Field {0} has an invalid pointer: {1}".format(attr_node.attrib["name"],
                                                                                          pointer))
            else:
                try:
                    [convert_from(attr_node.attrib["type"], subnode.text) for subnode in attr_node]
                except Exception as err:
                    raise RuntimeError("Invalid value for type {0} in field {1}".format(attr_node.attrib["type"],
                                                                                        attr_node.attrib["name"]))

    def update_object_from_xml(self, node):
        for attr_node in node:
            if attr_node.tag in ("Pointer", "Resource"):
                elementcount = int(attr_node.attrib["elements"])
                if elementcount == 1:
                    setattr(self, attr_node.attrib["name"], PointerPlaceholder(attr_node[0].text))
                else:
                    setattr(self, attr_node.attrib["name"], [PointerPlaceholder(subnode.text for subnode in attr_node)])
            else:
                elementcount = int(attr_node.attrib["elements"])
                if elementcount == 1:
                    setattr(self,
                            attr_node.attrib["name"],
                            convert_from(attr_node.attrib["type"], attr_node[0].text))
                else:
                    setattr(self,
                            attr_node.attrib["name"],
                            [convert_from(attr_node.attrib["type"], subnode.text) for subnode in attr_node])
                #self._attributes[attr_node.attrib["name"]] = Attribute.from_node(attr_node, self._level)

        if hasattr(self, "Mat"):
            setattr(self, "getmatrix", lambda: self.Mat)
        elif hasattr(self, "mMatrix"):
            setattr(self, "getmatrix", lambda: self.mMatrix)
        else:
            setattr(self, "getmatrix", lambda: None)

    @property
    def references(self):
        result = []
        for attr_node in self._node:
            if attr_node.tag in ("Pointer", "Resource"):
                pointers = getattr(self, attr_node.attrib["name"])
                if isinstance(pointers, list):
                    for val in pointers:
                        if val is not None:
                            result.append(val)
                elif pointers is not None:
                    result.append(pointers)
        return result

    @property
    def enums(self):
        result = []
        for attr_node in self._node:
            if attr_node.tag == "Enum":
                enums = getattr(self, attr_node.attrib["name"])
                if isinstance(enums, list):
                    result.extend(enums)
                else:
                    result.append(enums)
        return result

    def resolve_pointers(self, level, other=None, othernode=None):
        if othernode is not None:
            node = othernode
        else:
            node = self._node

        for attr_node in node:
            if attr_node.tag in ("Pointer", "Resource"):
                elementcount = int(attr_node.attrib["elements"])
                result = []
                for subnode in attr_node:
                    if subnode.text == "0":
                        result.append(None)
                    else:
                        if subnode.text not in level.objects:
                            if other is None or subnode.text not in other.objects:
                                raise RuntimeError("ID {0} not found in level or preload".format(subnode.text))
                            else:
                                obj = other.objects[subnode.text]
                                obj.add_reference(self)
                        else:
                            obj = level.objects[subnode.text]
                            obj.add_reference(self)
                        result.append(obj)

                if elementcount == 1:
                    setattr(self, attr_node.attrib["name"], result[0])
                else:
                    setattr(self, attr_node.attrib["name"], result)

    def updatemodelname(self):
        self._modelname = None
        self._iconoffset = None
        if hasattr(self, "mBase") and self.mBase is not None:
            if hasattr(self.mBase, "mpModel"):
                model = self.mBase.mpModel
                self._modelname = model.mName
            elif hasattr(self.mBase, "model"):
                # modelname = object.mBase.model.mName
                model = self.mBase.model
                self._modelname = model.mName
            elif hasattr(self.mBase, "Model"):
                # modelname = object.mBase.model.mName
                model = self.mBase.Model
                self._modelname = model.mName
            elif hasattr(self.mBase, "mBAN_Model"):
                # modelname = object.mBase.mBAN_Model.mName
                model = self.mBase.mBAN_Model
                self._modelname = model.mName
            elif self.type == "cSceneryCluster":
                model = self.mBase.Element[0]
                if model is not None:
                    self._modelname = model.mName

            if self.type in ("cAirVehicle", "cGroundVehicle", "cTroop", "cWaterVehicle",
                             "cBuilding", "cCapturePoint", "cMorphingBuilding"):
                try:
                    icon = self.mBase.mUnitSprite.mBase.texture.mName
                except Exception as err:
                    print("{0}-{1} has no defined unit sprite".format(self.type, self.id))
                    x,y = 15, 15
                else:
                    x,y = BWICONS[icon.lower()]
                self._iconoffset = (x,y)
            elif self.type == "cPickupReflected":
                healthtype = self.mBase.mType
                if healthtype == "PICKUP_TYPE_TROOP_HEALTH":
                    self._iconoffset = BWICONS["icon_health"]
                elif healthtype == "PICKUP_TYPE_VEHICLE_HEALTH":
                    self._iconoffset = BWICONS["icon_fuel"]
            elif self.type == "cCamera":
                camtype = self.mCamType
                insflags = self.mInstanceFlags
                if camtype == "eCAMTYPE_CHASETARGET" and insflags == 20:
                    self._iconoffset = BWICONS["hud_p1"]
                elif camtype == "eCAMTYPE_CHASETARGET" and insflags == 24:
                    self._iconoffset = BWICONS["hud_p2"]
                elif camtype == "eCAMTYPE_CHASETARGET" and insflags == 21:
                    self._iconoffset = BWICONS["hud_p1"]
                elif camtype == "eCAMTYPE_CHASETARGET" and insflags == 25:
                    self._iconoffset = BWICONS["hud_p2"]
                else:
                    self._iconoffset = BWICONS["hud_cam"]
            elif self.type == "cObjectiveMarker":
                rcolor = self.mBase.mRadarColour
                if rcolor == Vector4(255,180,0,220):
                    self._iconoffset = BWICONS["PrimaryObj"]
                elif rcolor == Vector4(220,220,200,220):
                    self._iconoffset = BWICONS["SecondaryObj"]
        elif self.type == "cAmbientAreaPointSoundSphere":
            self._iconoffset = BWICONS["Volumeicon"]
        elif self.type == "cAmbientAreaPointSoundBox":
            self._iconoffset = BWICONS["Volumeicon"]
        elif self.type in ("cMapZone", "cDamageZone", "cCoastZone", "cNogoHintZone"):
            if self.mFlags == 1:
                self._iconoffset = BWICONS["zone3d"]
            else:
                self._iconoffset = BWICONS["zone"]
        elif self.type == "cMorphingBuilding":
            allegiancebuilding = {
                "eWesternFrontier": self.mBaseWF,
                "eXylvanian": self.mBaseXY,
                "eTundranTerritories": self.mBaseTT,
                "eSolarEmpire": self.mBaseSE,
                "eUnderWorld": self.mBaseUW,
                "eNeutral": self.mBaseNeutral,
                "eAngloIsles": self.mBaseAG,
            }
            if self.mAllegiance in allegiancebuilding:
                result = allegiancebuilding[self.mAllegiance]
            if result == None:
                for allegiance in (self.mBaseWF, self.mBaseXY, self.mBaseTT, self.mBaseSE,
                                   self.mBaseUW, self.mBaseNeutral, self.mBaseAG):
                    if allegiance is not None:
                        self._modelname = allegiance.mpModel.mName
                        break
            else:
                self._modelname = result.mpModel.mName

    def update_xml(self):
        for attr_node in self._node:
            if attr_node.tag in ("Pointer", "Resource"):
                elementcount = int(attr_node.attrib["elements"])
                if elementcount == 1:
                    obj = getattr(self, attr_node.attrib["name"])
                    if obj is None:
                        attr_node[0].text = "0"
                    else:
                        attr_node[0].text = str(obj.id)
                else:
                    objlist = getattr(self, attr_node.attrib["name"])
                    for obj, node in zip(objlist, attr_node):
                        if obj is None:
                            node.text = "0"
                        else:
                            node.text = str(obj.id)
            else:
                elementcount = int(attr_node.attrib["elements"])
                if elementcount == 1:
                    val = getattr(self, attr_node.attrib["name"])
                    attr_node[0].text = convert_to(attr_node.attrib["type"], val)
                else:
                    vallist = getattr(self, attr_node.attrib["name"])
                    for val, node in zip(vallist, attr_node):
                        node.text = convert_to(attr_node.attrib["type"], val)

    @classmethod
    def create_from_text(cls, xmltext, leveldata, preload, dontresolve=False):
        xmlnode = etree.fromstring(xmltext)
        obj = cls(leveldata, xmlnode)
        obj.resolve_pointers(leveldata, preload)
        obj.updatemodelname()
        if "customName" in xmlnode.attrib:
            obj._node.attrib["customName"] = xmlnode.attrib["customName"]
        elif "customName" in obj._node.attrib:
            del obj._node.attrib["customName"]
        return obj

    def update_object_from_text(self, xmltext, leveldata, preload):
        xmlnode = etree.fromstring(xmltext)
        self.check_correctness(xmlnode, leveldata, preload)
        self.update_object_from_xml(xmlnode)
        self.resolve_pointers(leveldata, preload, xmlnode)
        self.updatemodelname()
        if "customName" in xmlnode.attrib:
            self._node.attrib["customName"] = xmlnode.attrib["customName"]
        elif "customName" in self._node.attrib:
            del self._node.attrib["customName"]

    @property
    def modelname(self):
        return self._modelname

    @property
    def iconoffset(self):
        return self._iconoffset

    #@property
    #def position(self):
    #    return None

    @property
    def customname(self):
        if "customName" in self._node.attrib:
            return self._node.attrib["customName"]
        else:
            return None

    @property
    def id(self):
        if self.deleted:
            return "0"
        else:
            return self._node.attrib["id"]

    @property
    def type(self):
        return self._node.attrib["type"]

    @property
    def name(self):
        try:
            modelname = ""
            if hasattr(self, "mBase"):
                base = self.mBase
            else:
                base = self

            if hasattr(base, "mpModel"):
                modelname = base.mpModel.mName
            elif hasattr(base, "model"):
                modelname = base.model.mName
            elif hasattr(base, "mBAN_Model"):
                modelname = base.mBAN_Model.mName
            elif self.type in ("cGlobalScriptEntity", "cInitialisationScriptEntity") and self.mpScript is not None:
                return "{0}({1})".format(self.mpScript.mName, self.id)
            elif hasattr(base, "mName") and base.mName != "":
                return "{0}({1})".format(self.mName, self.id)
            #elif self.type ==

            if self._custom_name:
                if modelname:
                    return "{0}({2},{1})".format(self._custom_name, self.id, modelname)
                else:
                    return "{0}({1})".format(self._custom_name, self.id)
            else:
                if modelname:
                    return "{0}({2},{1})".format(self.type, self.id, modelname)
                else:
                    return "{0}({1})".format(self.type, self.id)
        except Exception as err:
            print("Error on", self.id, self.type, err)
            return "{0}({1})".format(self.type, self.id)

    def extra_detail_name(self):
        extradetail = ""
        if self.type == "cMapZone":
            extradetail = self.mZoneType
        elif self.type == "cCamera":
            flags = []
            for i, v in ((1, "First"),
                      (2, "Cutscene"),
                      (4, "P1 Screen"),
                      (8, "P2 Screen"),
                      (16, "Player"),
                      (32, "P3 Screen"),
                      (64, "P4 Screen"),
                      (128, "Force LOD")):
                if self.mInstanceFlags & i:
                    flags.append(v)
            extradetail = ",".join(flags)
        if self.customname is not None:
            return self.customname+","+extradetail
        else:
            return extradetail

    def calculate_height(self, bwterrain, waterheight):
        currbwmtx = self.getmatrix()
        if currbwmtx is None:
            return None


        currmtx = currbwmtx.mtx
        h = currmtx[13]

        if self.type in ("cMapZone", ):
            return h
        #elif self.type == "cObjectiveMarker":
        #    if self.

        originalh = h
        locktosurface = False
        sticktofloor = False

        if hasattr(self, "mStickToFloor"):
            if not self.mStickToFloor:
                return h
            else:
                sticktofloor = True

        if hasattr(self, "mLockToSurface"):
            if not self.mLockToSurface:
                return h
            else:
                currmtx = self.spawnMatrix.mtx
                locktosurface = True

        height = bwterrain.check_height(currmtx[12], currmtx[14])
        if height is None:
            if waterheight is not None:
                height = waterheight + 0.2  # Avoid z-fighting in some cases
            else:
                height = 0
        else:
            if waterheight is not None and height < waterheight:
                height = waterheight + 0.2  # Avoid z-fighting in some cases

        if locktosurface:
            return abs(currmtx[13]-height) + originalh
        elif sticktofloor:
            return originalh+height
        elif originalh < height:
            return height
        else:
            return originalh

    def is_preload(self):
        return self.type in ('cPhysicsMaterial', 'cPhysicsGlobalParams', 'cTerrainParticleAnimationBase', 'cWorldFreeListSizeLoader',
        'cPhysicsGlobalParamSet', 'cDamageArmourBonus', 'cBailOutData', 'cLevelSettings')

    def tostring(self):
        self.update_xml()
        return etree.tostring(self._node, encoding="unicode", short_empty_elements=False)

    def calc_hash(self):
        hash = hashlib.new("md5")
        result = []
        for attr_node in self._node:
            if attr_node.tag in ("Pointer", "Resource"):
                continue
            else:
                attribname = attr_node.attrib["name"]
                attribtype = attr_node.attrib["type"]
                val = getattr(self, attribname)
                if not isinstance(val, list):
                    val = [val]

                for value in val:
                    stringval = bytes(convert_to(attribtype, value), encoding="ascii")
                    hash.update(stringval)

        return hash.digest()

    def calc_hash_recursive(self, visited=None):
        if visited is None:
            visited = {}

        if self.id in visited:
            return self.calc_hash()
        basehash = hashlib.new("md5")
        basehash.update(self.calc_hash())

        for attr_node in self._node:
            if attr_node.tag in ("Pointer", "Resource"):
                attribname = attr_node.attrib["name"]
                attribtype = attr_node.attrib["type"]
                val = getattr(self, attribname)
                if not isinstance(val, list):
                    val = [val]

                for value in val:
                    if value is None:
                        basehash.update(b"\x00")
                    else:
                        visited[self.id] = True
                        basehash.update(value.calc_hash_recursive(visited))

        return basehash.digest()

    def iterate_fields_recursive(self, path=[], visited=None):
        if visited is None:
            visited = {}

        if self.id not in visited:
            nodes = [attr_node for attr_node in self._node]
            nodes.sort(key=lambda x: x.tag in ("Pointer", "Resource"))

            for attr_node in nodes:
                attribname = attr_node.attrib["name"]
                val = getattr(self, attribname)

                yield path + [attribname]

                if attr_node.tag in ("Pointer", "Resource"):
                    if isinstance(val, list):
                        for i in range(len(val)):
                            if val[i] is None:
                                yield path + [attribname, i]
                            else:
                                yield from val[i].iterate_fields_recursive(path+[attribname, i])
                    else:
                        if val is not None:
                            yield from val.iterate_fields_recursive(path+[attribname])

    def get_value(self, path):
        if len(path) == 0:
            return self

        assert len(path) > 0
        attrname = path[0]
        val = getattr(self, attrname)

        if len(path) == 1:
            return val
        else:
            if isinstance(val, list):
                assert isinstance(path[1], int)
                index = path[1]
                if val[index] is None:
                    return None
                else:
                    return val[index].get_value(path[2:])
            else:
                return val.get_value(path[1:])

    def get_dependencies(self, visited=None, skip=[]):
        if visited is None:
            visited = {}

        dependencies = []

        if self.id not in visited:
            visited[self.id] = True

            for attr_node in self._node:
                attribname = attr_node.attrib["name"]
                val = getattr(self, attribname)

                if attr_node.tag in ("Pointer", "Resource"):
                    if attribname not in skip:
                        if isinstance(val, list):
                            for i in range(len(val)):
                                if val[i] is None:
                                    pass
                                else:
                                    dependencies.append(val[i])
                                    dependencies.extend(val[i].get_dependencies(visited))
                        else:
                            if val is not None:
                                dependencies.append(val)
                                dependencies.extend(val.get_dependencies(visited))

        return dependencies

    def diff(self, otherobj):
        if self.type != otherobj.type:
            raise RuntimeError("Cannot compare objects of different types")

        diff = []

        for path in self.iterate_fields_recursive():
            val = self.get_value(path)
            try:
                otherval = otherobj.get_value(path)
            except:
                diff.append((path, val, None))
                continue

            if isinstance(val, BattalionObject) and isinstance(otherval, BattalionObject):
                continue

            if isinstance(val, list):
                if otherval is None:
                    diff.append((path, val, otherval))
                else:
                    for i in range(len(val)):
                        if isinstance(val[i], BattalionObject) and isinstance(otherval[i], BattalionObject):
                            continue
                        if val[i] != otherval[i]:
                            diff.append((path, val, otherval))
                            break
            else:
                if otherval is None or val != otherval:
                    diff.append((path, val, otherval))

        return diff

    def same(self, otherobj):
        if self.type != otherobj.type:
            raise RuntimeError("Cannot compare objects of different types")

        same = []

        for path in self.iterate_fields_recursive():
            val = self.get_value(path)
            try:
                otherval = otherobj.get_value(path)
            except:
                continue


            if isinstance(val, BattalionObject) and isinstance(otherval, BattalionObject):
                continue

            if isinstance(val, list):
                if otherval is None:
                    pass
                else:
                    for i in range(len(val)):
                        if isinstance(val[i], BattalionObject) and isinstance(otherval[i], BattalionObject):
                            continue
                        if val[i] == otherval[i]:
                            same.append((path, val, otherval))
                            break
            else:
                if val is None and otherval is None:
                    same.append((path, val, otherval))
                else:
                    if otherval is not None and val == otherval:
                        same.append((path, val, otherval))

        return same