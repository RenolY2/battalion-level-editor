from functools import partial
from collections.abc import MutableSequence, Iterable
try:
    import xml.etree.cElementTree as etree
except: # cElementTree not available
    import xml.etree.ElementTree as etree

#import xml.etree.ElementTree.Element as Element
from lib.bw_types import convert_from, get_types, BWMatrix


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
                if hasattr(bwobject, "spawnMatrix") or hasattr(bwobject, "Mat"):
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


        """setattr = super().__setattr__
        if self.hasattr("spawnMatrix"):
            setattr("getposition", lambda: self.spawnMatrix)
        elif self.hasattr("Mat"):
            setattr("getposition", lambda: self.Mat)
        else:
            setattr("getposition", lambda: None)"""
    
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
    @property
    def modelname(self):
        return self._modelname

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
        if self.hasattr("mBase"):
            base = self.mBase
        else:
            base = self

        if base.hasattr("mpModel"):
            modelname = base.mpModel.mName
        elif base.hasattr("model"):
            modelname = base.model.mName
        elif base.hasattr("mBAN_Model"):
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

    def hasattr(self, attrname):
        return attrname in self._attributes
        
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

    with open("bw/MP2_Level_Preload.xml", "r") as f:
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
            print(obj.spawnMatrix.to_array())
    
    """alltypes = get_types()
    alltypes.sort()
    with open("types.txt", "w") as f:
        for t in alltypes:
            f.write(t)
            f.write("\n")"""
    with open("bw/C1_OnPatrol.xml", "r") as f:
        paths = BattalionFilePaths(f)
        print(paths.terrainpath)
        print(paths.stringpaths)
        print(paths.objectpath)
        print(paths.resourcepath)