#from lxml import etree
try:
    import xml.etree.cElementTree as etree
except: # cElementTree not available
    import xml.etree.ElementTree as etree
from copy import copy

TEXTURE = "cTextureResource"
SOUND = "sSampleResource"
MODEL = "cNodeHierarchyResource"
ANIMATION = "cAnimationResource"
SCRIPT = "cGameScriptResource"
EFFECT = "cTequilaEffectResource"


class BattWarsObject(object):
    def __init__(self, obj):
        self._attributes = {}

        self.type = obj.get("type")
        self.id = obj.get("id")
        self._xml_node = obj

        # We will create a name for this object by putting the type and ID together.
        self.name = "{0}[{1}]".format(self.type, self.id)

        for attr in obj:
            assert attr not in self._attributes
            self._attributes[attr.get("name")] = attr
    

    @property
    def attributes(self):
        return self._attributes

    def has_attr(self, name):
        return name in self._attributes

    def get_attr(self, name):
        return self._attributes[name]

    def get_attr_type(self, name):
        return self._attributes[name].get("type")

    def get_attr_elements(self, name):
        return [elem.text for elem in self._attributes[name]]

    def get_attr_tag(self, name):
        return self._attributes[name].tag

    # Use this for attributes that have only 1 element
    def get_attr_value(self, name, pos=0):
        return self._attributes[name][pos].text

    def set_attr_value(self, name, val, pos=0):
        self._attributes[name][pos].text = val




class BattWarsLevel(object):
    def __init__(self, fileobj):
        self._tree = etree.parse(fileobj)
        self._root = self._tree.getroot()

        self.obj_map = {}

        self.resources = {}
        self.objtypes = []
        self.objtypes_with_positions = []

        for obj in self._root:
            bw_object = BattWarsObject(obj)
            if bw_object.type == None:
                continue

            self.obj_map[bw_object.id] = bw_object

            if bw_object.type is not None and bw_object.type not in self.objtypes:
                self.objtypes.append(bw_object.type)
            if (bw_object.type is not None and bw_object.type not in self.objtypes_with_positions
                and (bw_object.has_attr("Mat") or bw_object.has_attr("mMatrix"))):
                self.objtypes_with_positions.append(bw_object.type)

            # All resourcees
            if bw_object.type is not None and bw_object.type.endswith("Resource"):
                res_type = bw_object.type
                assert bw_object.has_attr("mName") is True
                if res_type not in self.resources:
                    self.resources[res_type] = [bw_object]
                else:
                    self.resources[res_type].append(bw_object)


    # Todo: synchronize the resources dict
    def add_object(self, xml_node):
        bwobj = BattWarsObject(xml_node)
        assert bwobj.id not in self.obj_map
        self._root.append(xml_node)
        self.obj_map[bwobj.id] = bwobj

    def remove_object(self, objectid):
        pos = None
        obj = self.obj_map[objectid]
        self._root.remove(obj._xml_node)
        del self.obj_map[objectid]


    # The root of a BW level xml file contains the objects
    # used by that level.
    @property
    def objects(self):
        return self._root


    def get_resource(self, res_type, res_name):
        res_name = res_name.upper()

        if res_type not in self.resources:
            raise KeyError("No such resource type: {0}".format(res_type))
        else:
            for obj in self.resources[res_type]:
                assert obj.has_attr("mName")
                if obj.get_attr_value("mName").upper() == res_name:
                    return obj

            raise RuntimeError("Resource not found: {0}".format(res_name))


    def generate_unique_id(self, id_base):
        base_str = str(id_base)
        prefix = int(base_str[0:2])

        digits = len(base_str)-2
        rest = int(base_str[2:])

        newid = int(id_base)
        newid_str = None
        done = False

        # We keep the first two digits, but choose the remaining digits in such a way that
        # they are unique.
        for i in range(10**digits):
            newid = prefix * (10**digits) + ((rest + 7*i) % (10**digits))
            newid_str = str(newid)

            if newid_str not in self.obj_map:
                break # We made a new unique object id!

        #print("original id:",id_base)
        #print("new id:", newid_str)
        return newid_str



def create_object_hierarchy(id_map):
    hierarchy = {}
    never_referenced = {obj_id: True for obj_id in id_map.keys()}

    for obj_id, obj in id_map.items():
        if obj.has_attr("mBase"):
            # In the xml file mBase has the type pointer, but it's actually
            # the ID of a different object in the file.
            pointer = obj.get_attr_value("mBase")
            #assert pointer in id_map

            if obj.id not in hierarchy:
                del never_referenced[obj_id]
                hierarchy[obj.id] = pointer
            else:
                raise RuntimeError("one object shouldn't have more than 1 reference: %s" % obj.name)

    return hierarchy, never_referenced

def create_ref(ref, hierarchy, id_map):
    if ref.id not in hierarchy:
        return ref.name
    else:
        return ref.name + " => " + create_ref(id_map[hierarchy[ref.id]], hierarchy, id_map)

if __name__ == "__main__":
    infile = "bw2_sandbox/SP_5.3_Level.xml"
    with open(infile, "r") as f:
        bw_level = BattWarsLevel(f)

    types = {}
    id_map = {}

    for obj in bw_level.objects:
        bw_object = BattWarsObject(obj)
        if bw_object.type not in types:
            types[bw_object.type] = 1
        else:
            types[bw_object.type] += 1

        #assert bw_object.id not in id_map
        if bw_object.id in id_map:
            print(bw_object.name)
        id_map[bw_object.id] = bw_object

    # Never referenced actually doesn't mean that it isn't referenced at all,
    # but that it isn't referenced in a mBase attribute
    hierarchy, never_referenced = create_object_hierarchy(id_map)
    print(never_referenced)
    with open("hierarchy.txt", "w") as f:
        f.write("")

    with open("hierarchy.txt", "a") as f:
        for obj_id in sorted(id_map.keys()):
            obj = id_map[obj_id]
            if obj_id in hierarchy:
                f.write(create_ref(obj, hierarchy, id_map)+"\n")

    print("done")









