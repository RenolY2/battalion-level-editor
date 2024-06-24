import json

from functools import partial
from collections.abc import MutableSequence, Iterable
try:
    import xml.etree.cElementTree as etree
except: # cElementTree not available
    import xml.etree.ElementTree as etree

#import xml.etree.ElementTree.Element as Element
from lib.bw_types import convert_from, get_types, BWMatrix
from lib.vectors import Vector4

with open("resources/BattalionWarsIcons.json", "r") as f:
    BWICONS = json.load(f)

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
    def __init__(self, fileobj, preload=None):
        self._tree = etree.parse(fileobj)
        self._root = self._tree.getroot()
        self.objects = {}
        self.objects_with_positions = {}
        
        for child in self._root:
            if child.tag == "Object":
                bwobject = BattalionObject(self, child)
                if hasattr(bwobject, "spawnMatrix") or hasattr(bwobject, "Mat") or hasattr(bwobject, "mMatrix"):
                    self.add_object(bwobject, position=True)
                else:
                    self.add_object(bwobject, position=False)

    def resolve_pointers(self, other):
        for bwobject in self.objects.values():
            bwobject.resolve_pointers(self, other)

    def add_object(self, bwobject, position):
        if bwobject in self.objects:
            raise ObjectIDAlreadyExists()
            
        self.objects[bwobject.id] = bwobject
        if position:
            self.objects_with_positions[bwobject.id] = bwobject
            assert bwobject.getmatrix() is not None
                

class BattalionFilePaths(object):
    def __init__(self, fileobj):
        self._tree = etree.parse(fileobj)
        self._root = self._tree.getroot()

        self.terrainpath = None
        self.stringpaths = {}
        self.resourcepath = None
        self.objectpath = None
        self.preloadpath = None

        for child in self._tree.getroot():
            print(child.tag)
            if child.tag == "terrain":
                self.terrainpath = child[0].attrib["name"]
            elif child.tag == "level":
                for child2 in child:
                    if child2.tag == "resourcefiles":
                        self.resourcepath = child2[0].attrib["name"]
                    elif child2.tag == "objectfiles":
                        self.objectpath = child2[0].attrib["name"]
            elif child.tag == "strings":
                for lang in child:
                    self.stringpaths[lang.attrib["name"]] = lang.attrib["file"]
            elif child.tag == "preload":
                self.preloadpath = child[0].attrib["name"]


class BattalionObject(object):
    def __init__(self, level: BattalionLevelFile, node: etree.Element):
        self._node = node
        self._level = level

        self._attributes = {}
        self._custom_name = ""
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

        if hasattr(self, "spawnMatrix"):
            setattr(self, "getmatrix", lambda: self.spawnMatrix)
        elif hasattr(self, "Mat"):
            setattr(self, "getmatrix", lambda: self.Mat)
        elif hasattr(self, "mMatrix"):
            setattr(self, "getmatrix", lambda: self.mMatrix)
        else:
            setattr(self, "getmatrix", lambda: None)
    
    def resolve_pointers(self, level, other=None):
        for attr_node in self._node:
            if attr_node.tag in ("Pointer", "Resource"):
                elementcount = int(attr_node.attrib["elements"])
                print(elementcount)
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
                        else:
                            obj = level.objects[subnode.text]
                        result.append(obj)

                if elementcount == 1:
                    setattr(self, attr_node.attrib["name"], result[0])
                else:
                    setattr(self, attr_node.attrib["name"], result)

        self.updatemodelname()

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
                else:
                    self._iconoffset = BWICONS["hud_cam"]
            elif self.type == "cObjectiveMarker":
                rcolor = self.mBase.mRadarColour
                if rcolor == Vector4(255,180,0,220):
                    self._iconoffset = BWICONS["PrimaryObj"]
                elif rcolor == Vector4(220,220,200,220):
                    self._iconoffset = BWICONS["SecondaryObj"]
            elif self.type == "cAmbientAreaPointSoundSphere" or self.type == "cAmbientAreaPointSoundBox":
                self._iconoffset = BWICONS["Volumeicon"]
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
    def id(self):
        return self._node.attrib["id"]

    @property
    def type(self):
        return self._node.attrib["type"]

    @property
    def name(self):
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


if __name__ == "__main__":
    """with open("../credits_Level_Preload.xml", "r") as f:
        level = BattalionLevelFile(f)
    
    for objid, obj in level.objects.items():
        if obj.type == "cLevelSettings":
            print(obj.mNumPlayers)
            print(obj.mMipBias)
            print(obj.gameHUDs)
            obj.mMipBias = 1
            print(obj.mMipBias)
            print(obj.mCOHeadOneSad)"""

    """with open("bw/MP2_Level_Preload.xml", "r") as f:
        preload = BattalionLevelFile(f)

    with open("bw/MP2_Level.xml", "r") as f:
        level = BattalionLevelFile(f)
    level.resolve_pointers(preload)
    preload.resolve_pointers(level)

    for objid, obj in level.objects.items():
        if obj.type == "cMorphingBuilding":
            print(obj.mBaseTT.mpModel.mName)
            print(obj.spawnMatrix.to_array())
            new = BWMatrix(*obj.spawnMatrix.to_array())
            print(obj.spawnMatrix.to_array())"""
    
    """alltypes = get_types()
    alltypes.sort()
    with open("types.txt", "w") as f:
        for t in alltypes:
            f.write(t)
            f.write("\n")"""
    """with open("bw/C1_OnPatrol.xml", "r") as f:
        paths = BattalionFilePaths(f)
        print(paths.terrainpath)
        print(paths.stringpaths)
        print(paths.objectpath)
        print(paths.resourcepath)"""
    import gzip 
    import os
    BW1path = r"D:\Wii games\BattWars\P-G8WP\files\Data\CompoundFiles"
    BW2path = r"D:\Wii games\BW2Folder\files\Data\CompoundFiles"
    
    import csv 
    
    with csv.open("table.csv", "w") as tbl:
    
        types = set()
        alltypes = set()
        for fname in os.listdir(BW1path):
            path = os.path.join(BW1path, fname)
            if path.endswith("_Level.xml"):
                preload = path.replace("_Level.xml", "_Level_preload.xml")
                print(path)
                with open(path, "rb") as g:
                    level_data = BattalionLevelFile(g)
                    with open(preload, "rb") as h:
                        with open(path+".info.txt", "w") as f:
                            preload_data = BattalionLevelFile(h)
                            objectcounts = {}
                            for objid, obj in level_data.objects.items():
                                for node in obj._node:
                                    if "Matrix" in node.attrib["type"]:
                                        mtype = node.attrib["type"] 
                                        #print(node.attrib["type"])
                                        types.add((obj.type, mtype, node.attrib["name"]))
                                        alltypes.add(obj.type)
                                objectcounts[obj.type] = objectcounts.get(obj.type, 0) + 1
                            values = []
                            
                            for objid, obj in preload_data.objects.items():
                                if obj.type == "cWorldFreeListSizeLoader":
                                    for var in (
                                    "numQuadtreeNodes", "numQuadtreeObjLists", "numNodeHierarchies", "numShadowVolumes",
                                    "numPolynodes", "numObjInstances", "numObjAnimInstances", "numJoints", "numJointAnims",
                                    "numBanJoints", "numAnimationBlends", "numMaxTerrainMaterials", "numMaxTroopVoiceMessageQueueItems"):
                                        val = getattr(obj, var)
                                        values.append((var, val))
                                elif obj.type == "cLevelSettings":
                                    for var in (
                                    "mLuaScriptMemory",
                                    "mTequilaMemoryHeap"):
                                        val = getattr(obj, var)
                                        values.append((var, val))
                            f.write("=== Preload values ===\n")
                            for var, val in sorted(values, key=lambda x: x[0]):
                                f.write("{0} {1}\n".format(var, val))
                            f.write("\n=== Objects ===\n")
                            for objtype in sorted(objectcounts.keys()):
                                f.write("{0} {1}\n".format(objtype, objectcounts[objtype]))
                            
        #"mLuaScriptMemory", "mRenderToTextureMemory", "mbRenderToTextureUseMem1", "miMaxTerrainMemorySize",
        #                            "miPhysicsMemorySize", "miActionHeapMemorySize", "mTequilaMemoryHeap"):
        print("BW1")
        for result in sorted(types, key=lambda x: x[0]):
            print(result[0], result[1], result[2])
        types = set()
        for fname in os.listdir(BW2path):
            path = os.path.join(BW2path, fname)
            if path.endswith("_Level.xml.gz"):
                preload = path.replace("_Level.xml.gz", "_Level_preload.xml.gz")
                print(path)
                with gzip.open(path, "rb") as g:
                    level_data = BattalionLevelFile(g)
                    with gzip.open(preload, "rb") as h:
                        with open(path+".info.txt", "w") as f:
                            preload_data = BattalionLevelFile(h)
                            objectcounts = {}
                            for objid, obj in level_data.objects.items():
                                for node in obj._node:
                                    if "Matrix" in node.attrib["type"]:
                                        mtype = node.attrib["type"] 
                                        #print(node.attrib["type"])
                                        types.add((obj.type, mtype, node.attrib["name"]))
                                        alltypes.add(obj.type)
                                objectcounts[obj.type] = objectcounts.get(obj.type, 0) + 1
                            values = []
                            
                            for objid, obj in preload_data.objects.items():
                                if obj.type == "cWorldFreeListSizeLoader":
                                    for var in (
                                    "numQuadtreeNodes", "numQuadtreeObjLists", "numNodeHierarchies", "numShadowVolumes",
                                    "numPolynodes", "numObjInstances", "numObjAnimInstances", "numJoints", "numJointAnims",
                                    "numBanJoints", "numAnimationBlends", "numMaxTerrainMaterials", "numMaxTroopVoiceMessageQueueItems"):
                                        val = getattr(obj, var)
                                        values.append((var, val))
                                elif obj.type == "cLevelSettings":
                                    for var in (
                                    "mLuaScriptMemory", "mRenderToTextureMemory", "mbRenderToTextureUseMem1", "miMaxTerrainMemorySize",
                                    "miPhysicsMemorySize", "miActionHeapMemorySize", "mTequilaMemoryHeap"):
                                        val = getattr(obj, var)
                                        values.append((var, val))
                            f.write("n=== Preload values ===\n")
                            for var, val in sorted(values, key=lambda x: x[0]):
                                f.write("{0} {1}\n".format(var, val))
                            f.write("\n=== Objects ===\n")
                            for objtype in sorted(objectcounts.keys()):
                                f.write("{0} {1}\n".format(objtype, objectcounts[objtype]))
        print("BW2")
        for result in sorted(types, key=lambda x: x[0]):
            print(result[0], result[1], result[2])
        
        for result in sorted(alltypes):
            print(result)