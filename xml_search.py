from lib.BattalionXMLLib import BattalionLevelFile, BattalionObject


class Search(object):
    def __init__(self):
        pass

    def searchlevel(self, level_data: BattalionLevelFile, preload: BattalionLevelFile):
        for objid, obj in level_data.objects.items():
            pass

    def conclusion(self):
        pass


def decompose_flag(flag):
    flags = []
    for i in range(10):
        if flag&(2**i):
            flags.append(hex(2**i))
    return flags


class WaypointSearch(Search):
    def __init__(self):
        self.waypointflags = set()

    def searchlevel(self, level_data, preload):
        sayonce = False

        for objid, obj in level_data.objects.items():
            if obj.type == "cWaypoint":
                self.waypointflags.add(obj.Flags)
                if obj.Flags & 0x80:
                    assert obj.Flags&0x8 or obj.Flags&0x40, obj.Flags
                if obj.Flags & 0x40 and not sayonce:
                    print("Has 0x40 waypoint")
                    sayonce = True

    def conclusion(self):
        print(self.waypointflags)
        for val in self.waypointflags:
            print(val, decompose_flag(val))


if __name__ == "__main__":
    import gzip
    import os

    BW1path = r"D:\Wii games\BattWars\P-G8WP\files\Data\CompoundFiles"
    BW2path = r"D:\Wii games\BW2Folder\files\Data\CompoundFiles"

    types = set()
    alltypes = set()
    search = WaypointSearch()
    for fname in os.listdir(BW1path):

        path = os.path.join(BW1path, fname)
        if path.endswith("_Level.xml"):
            ids = []
            preload = path.replace("_Level.xml", "_Level_preload.xml")
            print(path)
            with open(path, "rb") as g:
                level_data = BattalionLevelFile(g)
                with open(preload, "rb") as h:
                    with open(path + ".info.txt", "w") as f:
                        preload_data = BattalionLevelFile(h)

                        search.searchlevel(level_data, preload_data)

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
                        search.searchlevel(level_data, preload_data)

    search.conclusion()
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

    if False:
        import gzip
        import os

        BW1path = r"D:\Wii games\BattWars\P-G8WP\files\Data\CompoundFiles"
        BW2path = r"D:\Wii games\BW2Folder\files\Data\CompoundFiles"

        import csv


        # with csv.open("table.csv", "w") as tbl:
        if True:
            types = set()
            alltypes = set()
            for fname in os.listdir(BW1path):

                path = os.path.join(BW1path, fname)
                if path.endswith("_Level.xml"):
                    ids = []
                    preload = path.replace("_Level.xml", "_Level_preload.xml")
                    print(path)
                    with open(path, "rb") as g:
                        level_data = BattalionLevelFile(g)
                        with open(preload, "rb") as h:
                            with open(path + ".info.txt", "w") as f:
                                preload_data = BattalionLevelFile(h)
                                objectcounts = {}
                                for objid, obj in level_data.objects.items():
                                    ids.append(int(objid))

                                for objid, obj in preload_data.objects.items():
                                    ids.append(int(objid))

                    trail = {}
                    for id in ids:
                        trailvalue = id%0x400
                        if trailvalue in trail:
                            trail[trailvalue].append(id)
                        else:
                            trail[trailvalue] = [id]

                    for i,v in trail.items():
                        if len(v) > 1:
                            print(i, v)
                            for value in v:
                                print(level_data.objects[str(value)].type)
                    break


    if False:
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
                                    if hasattr(obj, "spawnMatrix"):
                                        assert hasattr(obj, "Mat")
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
                                    if hasattr(obj, "spawnMatrix"):
                                        assert hasattr(obj, "Mat")
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