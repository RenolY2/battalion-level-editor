import json

from functools import partial
from collections.abc import MutableSequence, Iterable
try:
    import xml.etree.cElementTree as etree
except: # cElementTree not available
    import xml.etree.ElementTree as etree

from lib.searchquery import fieldnames

#import xml.etree.ElementTree.Element as Element
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
    def __init__(self, fileobj, callback=None):
        self._tree = etree.parse(fileobj)
        self._root = self._tree.getroot()
        self.objects = {}
        self.objects_with_positions = {}
        self.bw2 = False

        for i, child in enumerate(self._root):
            if child.tag == "Object":
                bwobject = BattalionObject(self, child)

                if not self.bw2:
                    for node in bwobject._node:
                        if node.attrib["name"] not in fieldnames:
                            self.bw2 = True
                            print("Detected XML as BW2")
                if hasattr(bwobject, "spawnMatrix") or hasattr(bwobject, "Mat") or hasattr(bwobject, "mMatrix"):
                    self.add_object(bwobject, position=True)
                else:
                    self.add_object(bwobject, position=False)
                if callback is not None: callback(len(self._root), i)

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

    def write(self, f):
        f.write(b"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
        self._tree.write(f, encoding="utf-8")


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

        self._referenced_by = set()

        self.update_object_from_xml(self._node)

        self.height = None
        self.dirty = True

    def add_reference(self, obj):
        self._referenced_by.add(obj)

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
        elif self.type == "cMorphingBuilding":
            for allegiance in (self.mBaseWF, self.mBaseXY, self.mBaseTT, self.mBaseSE,
                               self.mBaseUW, self.mBaseNeutral, self.mBaseAG):
                if allegiance is not None:
                    self._modelname = allegiance.mpModel.mName
                    break

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

    def update_object_from_text(self, xmltext, leveldata, preload):
        xmlnode = etree.fromstring(xmltext)
        self.check_correctness(xmlnode, leveldata, preload)
        self.update_object_from_xml(xmlnode)
        self.resolve_pointers(leveldata, preload)

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

    def tostring(self):
        self.update_xml()
        return etree.tostring(self._node, encoding="unicode")


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

    if True:
        import gzip
        import os

        BW1path = r"D:\Wii games\BattWars\P-G8WP\files\Data\CompoundFiles"
        BW2path = r"D:\Wii games\BW2Folder\files\Data\CompoundFiles"

        import csv

        fieldnames = set()
        fieldnames.add("id")
        fieldnames.add("modelname")
        fieldnames.add("type")
        fieldnames.add("name")

        fieldnamesbw2 = set()
        fieldnamesbw2.add("id")
        fieldnamesbw2.add("modelname")
        fieldnamesbw2.add("type")
        fieldnamesbw2.add("name")

        potentialvalues = set()
        potentialvalues.add("self")

        potentialvaluesbw2 = set()
        potentialvaluesbw2.add("self")

        preloadtypes = set()

        # with csv.open("table.csv", "w") as tbl:
        if True:
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
                            with open(path + ".info.txt", "w") as f:
                                preload_data = BattalionLevelFile(h)
                                objectcounts = {}
                                for objid, obj in level_data.objects.items():
                                    potentialvalues.add(obj.type)
                                    for node in obj._node:
                                        fieldnames.add(node.attrib["name"])
                                        potentialvalues.add(node.attrib["type"])
                                        if node.tag == "Enum" or node.attrib["type"] == "cFxString8":
                                            for subnode in node:
                                                potentialvalues.add(subnode.text)

                                        if "Matrix" in node.attrib["type"]:
                                            mtype = node.attrib["type"]
                                            # print(node.attrib["type"])
                                            types.add((obj.type, mtype, node.attrib["name"]))
                                            alltypes.add(obj.type)
                                    objectcounts[obj.type] = objectcounts.get(obj.type, 0) + 1
                                values = []

                                for objid, obj in preload_data.objects.items():
                                    preloadtypes.add(obj.type)
                                    potentialvalues.add(obj.type)
                                    for node in obj._node:
                                        fieldnames.add(node.attrib["name"])
                                        potentialvalues.add(node.attrib["type"])
                                        if node.tag == "Enum" or node.attrib["type"] == "cFxString8":
                                            for subnode in node:
                                                if subnode is not None:
                                                    potentialvalues.add(subnode.text)

                                    if obj.type == "cWorldFreeListSizeLoader":
                                        for var in (
                                                "numQuadtreeNodes", "numQuadtreeObjLists", "numNodeHierarchies",
                                                "numShadowVolumes",
                                                "numPolynodes", "numObjInstances", "numObjAnimInstances", "numJoints",
                                                "numJointAnims",
                                                "numBanJoints", "numAnimationBlends", "numMaxTerrainMaterials",
                                                "numMaxTroopVoiceMessageQueueItems"):
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

            # "mLuaScriptMemory", "mRenderToTextureMemory", "mbRenderToTextureUseMem1", "miMaxTerrainMemorySize",
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
                            with open(path + ".info.txt", "w") as f:
                                preload_data = BattalionLevelFile(h)
                                objectcounts = {}
                                for objid, obj in level_data.objects.items():
                                    potentialvaluesbw2.add(obj.type)
                                    for node in obj._node:
                                        fieldnamesbw2.add(node.attrib["name"])
                                        potentialvaluesbw2.add(node.attrib["type"])
                                        if node.tag == "Enum" or node.attrib["type"] == "cFxString8":
                                            for subnode in node:
                                                if subnode is not None:
                                                    potentialvaluesbw2.add(subnode.text)

                                    for node in obj._node:
                                        if "Matrix" in node.attrib["type"]:
                                            mtype = node.attrib["type"]
                                            # print(node.attrib["type"])
                                            types.add((obj.type, mtype, node.attrib["name"]))
                                            alltypes.add(obj.type)
                                    objectcounts[obj.type] = objectcounts.get(obj.type, 0) + 1
                                values = []

                                for objid, obj in preload_data.objects.items():
                                    preloadtypes.add(obj.type)
                                    potentialvaluesbw2.add(obj.type)
                                    for node in obj._node:
                                        fieldnamesbw2.add(node.attrib["name"])
                                        potentialvaluesbw2.add(node.attrib["type"])
                                        if node.tag == "Enum" or node.attrib["type"] == "cFxString8":
                                            for subnode in node:
                                                if subnode is not None:
                                                    potentialvaluesbw2.add(subnode.text)

                                    if obj.type == "cWorldFreeListSizeLoader":
                                        for var in (
                                                "numQuadtreeNodes", "numQuadtreeObjLists", "numNodeHierarchies",
                                                "numShadowVolumes",
                                                "numPolynodes", "numObjInstances", "numObjAnimInstances", "numJoints",
                                                "numJointAnims",
                                                "numBanJoints", "numAnimationBlends", "numMaxTerrainMaterials",
                                                "numMaxTroopVoiceMessageQueueItems"):
                                            val = getattr(obj, var)
                                            values.append((var, val))
                                    elif obj.type == "cLevelSettings":
                                        for var in (
                                                "mLuaScriptMemory", "mRenderToTextureMemory",
                                                "mbRenderToTextureUseMem1", "miMaxTerrainMemorySize",
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

            with open("fieldnames.txt", "w") as f:
                for fieldname in sorted(fieldnames):
                    f.write(fieldname)
                    f.write("\n")

            with open("fieldnamesbw2.txt", "w") as f:
                for fieldname in sorted(fieldnamesbw2):
                    f.write(fieldname)
                    f.write("\n")

            potentialvalues.remove(None)
            with open("values.txt", "w") as f:
                for fieldname in sorted(potentialvalues):
                    if " " in fieldname:
                        continue
                    f.write(fieldname)
                    f.write("\n")

            potentialvaluesbw2.remove(None)
            with open("valuesbw2.txt", "w") as f:
                for fieldname in sorted(potentialvaluesbw2):
                    if " " in fieldname:
                        continue
                    f.write(fieldname)
                    f.write("\n")

            print(preloadtypes)

    """from searchquery import create_query
    import gzip
    query = create_query("self.mDamageAmount >= 32")
    results = []
    with gzip.open(r"D:\Wii games\BW2Folder\files\Data\CompoundFiles\SP_5.2_Level.xml.gz", "rb") as f:
        level_data = BattalionLevelFile(f)
        for objid, obj in level_data.objects.items():
            try:
                obj.resolve_pointers(level_data)
            except:
                pass

        for objid, obj in level_data.objects.items():
            if query.evaluate(obj):
                results.append(obj)

    print(results)
    print([x.name for x in results])
    print(len(results))"""