from struct import pack, unpack, unpack_from
from lib.vectors import Triangle, Vector3
from OpenGL import *


def read_uint32(f):
    return unpack("I", f.read(4))[0]


def is_end(f):
    curr = f.tell()
    result = False

    if f.read(1) == b"":
        result = True

    f.seek(curr)
    return result


class BWSectionedFile(object):
    def __init__(self, f):
        self.sections = {}

        while not is_end(f):
            section_name = f.read(4)
            size = read_uint32(f)
            data = f.read(size)

            self.sections[section_name] = data


class BWTerrain(BWSectionedFile):
    def __init__(self, f):
        super().__init__(f)

        width, height, unk1, unk2 = unpack("IIII", self.sections[b"RRET"])
        assert width == height == 64
        self.tiles = self.sections[b"KNHC"]
        self.map = self.sections[b"PAMC"]

        print(len(self.tiles), "a")
        self.triangles = []
        self.colors = []
        pointdata = {}
        self.pointdata = [[None for y in range(height*16+1)] for x in range(width*16+1)]
        pointdata = self.pointdata

        for x in range(width):
            for y in range(height):
                a, b, index = self.get_map_entry(x, y)
                tilegroupdata = self.tiles[180*16*index:180*16*(index+1)]
                if b == 1:

                    for ix in range(4):
                        for iy in range(4):
                            groupdindex = iy * 4 + ix
                            tiledata = tilegroupdata[180*groupdindex:180*(groupdindex+1)]

                            for iix in range(4):
                                for iiy in range(4):
                                    pointindex = iiy*4 + iix
                                    pheight,  = unpack(">H", tiledata[2*pointindex:2*(pointindex+1)])
                                    r, g, b, unused = unpack("BBBB", tiledata[32 + 4*pointindex:32 + 4*(pointindex+1)])
                                    pointdata[x*16 + ix*4 + iix][y*16 + iy*4 + iiy] = (pheight, r, g, b)

        for x in range(width):
            for y in range(height):
                a, b, index = self.get_map_entry(x, y)
                tilegroupdata = self.tiles[180 * 16 * index:180 * 16 * (index + 1)]

                if b == 1:
                    for ix in range(4):
                        for iy in range(4):
                            for iix in range(4):
                                for iiy in range(4):
                                    totalx = x*16 + ix*4 + iix
                                    totaly = y*16 + iy*4 + iiy

                                    if (pointdata[totalx+1][totaly] is None
                                        or pointdata[totalx+1][totaly+1] is None
                                        or pointdata[totalx][totaly+1] is None):

                                        continue

                                    fac = 0.25
                                    hfac = 32.0
                                    v1 = Vector3((totalx)/fac - 2048,    -((totaly)/fac - 2048), pointdata[totalx][totaly][0]/hfac)
                                    v2 = Vector3((totalx+1)/fac - 2048,  -((totaly)/fac - 2048), pointdata[totalx+1][totaly][0]/hfac)
                                    v3 = Vector3((totalx+1)/fac - 2048,  -((totaly+1)/fac - 2048), pointdata[totalx+1][totaly+1][0]/hfac)
                                    v4 = Vector3((totalx)/fac - 2048,    -((totaly+1)/fac - 2048), pointdata[totalx][totaly+1][0]/hfac)

                                    c1 = pointdata[totalx][totaly][1:]
                                    c2 = pointdata[totalx+1][totaly][1:]
                                    c3 = pointdata[totalx+1][totaly+1][1:]
                                    c4 = pointdata[totalx][totaly+1][1:]

                                    tri1 = Triangle(v1, v3, v2)
                                    tri2 = Triangle(v1, v3, v4)

                                    self.triangles.append(tri1)
                                    self.triangles.append(tri2)
                                    self.colors.append((c1, c3, c2))
                                    self.colors.append((c1, c3, c4))

    def get_map_entry(self, map_x, map_y):
        index = map_y * 64 + map_x
        a, b, tileindex = unpack_from(">BBH", self.map, index*4)
        return a, b, tileindex


if __name__ == "__main__":
    with open("MP4.out", "rb") as f:
        bwterrain = BWTerrain(f)

    print(len(bwterrain.triangles))