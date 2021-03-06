from functools import partial
from collections.abc import MutableSequence, Iterable
try:
    import xml.etree.cElementTree as etree
except: # cElementTree not available
    import xml.etree.ElementTree as etree

#import xml.etree.ElementTree.Element as Element
from bw_types import convert_from, get_types




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
    def __init__(self, fileobj):
        self._tree = etree.parse(fileobj)
        self._root = self._tree.getroot()
        self.objects = {}
        
        for child in self._root:
            if child.tag == "Object":
                bwobject = BattalionObject(self, child)
                self.add_object(bwobject)
                
    def add_object(self, bwobject):
        if bwobject in self.objects:
            raise ObjectIDAlreadyExists()
            
        self.objects[bwobject.id] = bwobject
                
            
class BattalionObject(object):
    def __init__(self, level: BattalionLevelFile, node: etree.Element): 
        self._node = node
        self._level = level
        
        self._attributes = {}
        
        for attr_node in node:
            if attr_node.tag in ("Pointer", "Resource"):
                self._attributes[attr_node.attrib["name"]] = PointerAttribute.from_node(attr_node, self._level)
            else:
                self._attributes[attr_node.attrib["name"]] = Attribute.from_node(attr_node, self._level)
        
        """for attr, node in self._attributes.items():
            setattr(
                self, 
                attr, 
                property(
                    partial(self.access_value, attr), 
                    partial(self.set_value, attr)
                )
            )
            
            getattr(self, attr).__set_name__(self, attr)"""
            
    @property 
    def id(self):
        return self._node.attrib["id"]
        
    @property 
    def type(self):
        return self._node.attrib["type"]
    
    def __getattr__(self, attrname):
        attr = self._attributes[attrname]
        if attr.elements == 1:
            if attr.tag in ("Pointer", "Resource"):
                if attr.values[0] == "0":
                    return None 
                else:
                    return self._level.objects[attr.values[0]]
            else:
                return attr.values[0]
        elif attr.elements > 1:
            return attr.values
        else:
            return None 
    
    def __setattr__(self, attrname, value):
        if attrname.startswith("_"):
            super().__setattr__(attrname, value)
        else:
            attr = self._attributes[attrname]
            if attr.elements == 1:
                attr.values[0] = value
            elif attr_node.attrib["elements"] > 1:
                raise RuntimeError("Direct element assignment to attributes with multiple elements not supported")
    
    def resolve_pointer(self, attr):
        if attr.tag != "Pointer": 
            raise AttributeNotAPointer()
            
        #ptr = attr.self._level.objects[
        
        
if __name__ == "__main__":
    """with open("credits_Level_Preload.xml", "r") as f:
        level = BattalionLevelFile(f)
    
    for objid, obj in level.objects.items():
        if obj.type == "cLevelSettings":
            print(obj.mNumPlayers)
            print(obj.mMipBias)
            print(obj.gameHUDs)
            obj.mMipBias = 1
            print(obj.mMipBias)
            print(obj.mCOHeadOneSad)"""
            
    with open("MP2_Level.xml", "r") as f:
        level = BattalionLevelFile(f)
    
    for objid, obj in level.objects.items():
        if obj.type == "cMorphingBuilding":
            print(obj.mBaseTT.mpModel.mName)
            print(obj.spawnMatrix.position)
    
    """alltypes = get_types()
    alltypes.sort()
    with open("types.txt", "w") as f:
        for t in alltypes:
            f.write(t)
            f.write("\n")"""