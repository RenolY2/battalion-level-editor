# Python 3 necessary

import subprocess
from struct import unpack_from, pack

from .BCOnvert import (normalize_vector, create_vector, cross_product,
                        write_float, write_uint32, write_short)


def read_array(buffer, offset, length):
    return buffer[offset:offset+length]


def read_float(buffer, offset):
    return unpack_from(">f", buffer, offset)[0]


def read_int32(buffer, offset):
    return unpack_from(">i", buffer, offset)[0]


def read_uint32(buffer, offset):
    return unpack_from(">I", buffer, offset)[0]


def read_uint16(buffer, offset):
    return unpack_from(">H", buffer, offset)[0]


def read_uint8(buffer, offset):
    return unpack_from("B", buffer, offset)[0]


class RacetrackCollision(object):
    def __init__(self):
        self._data = None
        self.identifier = b"0003"
        self.grid_xsize = 0
        self.grid_zsize = 0
        self.coordinate1_x = 0
        self.coordinate1_z = 0
        self.coordinate2_x = 0
        self.coordinate2_z = 0
        self.entrycount = 0
        self.padding = 0

        self.gridtable_offset = 0
        self.triangles_indices_offset = 0
        self.trianglesoffset = 0
        self.verticesoffset = 0
        self.unknownoffset = 0

        self.grids = []
        self.triangles = []
        self.vertices = []

    def load_file(self, f):
        data = f.read()
        self._data = data
        if data[:0x4] != b"0003":
            raise RuntimeError("Expected header start 0003, but got {0}. "
                               "Likely not MKDD collision!".format(data[:0x4]))

        self.identifier = data[:0x4]


        self.grid_xsize = read_uint16(data, 0x4)
        self.grid_zsize = read_uint16(data, 0x6)

        self.coordinate1_x = read_int32(data, 0x8)
        self.coordinate1_z = read_int32(data, 0xC)
        self.gridcell_xsize = read_int32(data, 0x10)
        self.gridcell_zsize = read_int32(data, 0x14)

        self.entrycount = read_uint16(data, 0x18)
        self.padding = read_uint16(data, 0x1A)

        self.gridtable_offset = 0x2C
        self.triangles_indices_offset = read_uint32(data, 0x1C)
        self.trianglesoffset = read_uint32(data, 0x20)
        self.verticesoffset = read_uint32(data, 0x24)
        self.unknownoffset = read_uint32(data, 0x28)

        # Parse triangles
        trianglescount = (self.verticesoffset-self.trianglesoffset) // 0x24
        print((self.verticesoffset-self.trianglesoffset)%0x24)

        for i in range(trianglescount):
            v1 = read_int32(data, self.trianglesoffset+i*0x24 + 0x00)
            v2 = read_int32(data, self.trianglesoffset+i*0x24 + 0x04)
            v3 = read_int32(data, self.trianglesoffset+i*0x24 + 0x08)
            collision_type = read_uint16(data, self.trianglesoffset+i*0x24 + 0x16)
            rest = read_array(data, self.trianglesoffset+i*0x24 + 0x0C, length=0x24-0xC)
            self.triangles.append((v1,v2,v3, collision_type, rest))

        # Parse vertices
        vertcount = (self.unknownoffset-self.verticesoffset) // 0xC
        print((self.unknownoffset-self.verticesoffset) % 0xC)

        biggestx = biggestz = -99999999
        smallestx = smallestz = 99999999

        for i in range(vertcount):
            x = read_float(data, self.verticesoffset + i*0xC + 0x00)
            y = read_float(data, self.verticesoffset + i*0xC + 0x04)
            z = read_float(data, self.verticesoffset + i*0xC + 0x08)
            self.vertices.append((x,y,z))

            if x > biggestx:
                biggestx = x
            if x < smallestx:
                smallestx = x

            if z > biggestz:
                biggestz = z
            if z < smallestz:
                smallestz = z
            #print(x,y,z)
        print("smallest/smallest vertex coordinates:",smallestx, smallestz, biggestx, biggestz)
        f.seek(self.unknownoffset)
        self.matentries = []

        for i in range(self.entrycount):
            val1, val2, unk, int1, int2 = unpack_from(">BBHII", f.read(0xC), 0)
            self.matentries.append((val1, val2, unk, int1, int2))


def read_gridtable_entry(data, offset):
    unk1 = read_uint8(data, offset+0)
    unk2 = read_uint8(data, offset+1)
    gridtableindex = read_uint16(data, offset+2)
    triangleindices_index = read_int32(data, offset+4)

    return unk1, unk2, gridtableindex, triangleindices_index


def get_grid_entries(data, index, offset, limit, f, indent, gottem):
    unk1, unk2, nextindex, triangleindex_offset = read_gridtable_entry(data, offset)
    f.write("{0}index: {1}| {2} {3} {4} {5}\n".format(indent*4*" ", index, unk1, unk2, nextindex, triangleindex_offset))

    if nextindex != 0:
        for i in range(4):
            offset = 0x2C + (nextindex+i)*8
            print(nextindex, offset, limit)
            assert offset < limit
            gottem[nextindex+i] = True
            get_grid_entries(data, nextindex+i, offset, limit, f, indent+1, gottem)


if __name__ == "__main__":
    col = RacetrackCollision()
    bcofile = "D:\\Wii games\\MKDDModdedFolder\\P-GM4E\\files\\Course\\Daisy.arc_ext\\daisy\\daisy_course.bco"
    with open(bcofile, "rb") as f:
        col.load_file(f)
    for i in (col.triangles_indices_offset, col.trianglesoffset, col.verticesoffset, col.unknownoffset):
        print(hex(i), i)
    print(hex(len(col._data)))

    print("grid start:", col.coordinate1_x, col.coordinate1_z)
    print("cell size:", col.gridcell_xsize, col.gridcell_zsize)
    print("grid end:",
          col.coordinate1_x + col.grid_xsize*col.gridcell_xsize,
          col.coordinate1_z + col.grid_zsize*col.gridcell_zsize)
    #print(hex(col.grid_xsize), hex(col.grid_zsize))
    additional_verts = []
    additional_edges = []
    vertoff = len(col.vertices)

    print(col.gridtable_offset)

    maxsize = col.grid_xsize*col.grid_zsize
    total_gridentries = (col.triangles_indices_offset - 0x2C) / 8.0
    print(maxsize, "possible entries:", total_gridentries)

    gottem = {}
    for i in range(int(total_gridentries)):
        gottem[i] = False

    entries = 0

    with open("grid_data.txt", "w") as f:
        f.write("{0} {1} max index: {2}\n\n".format(col.grid_xsize, col.grid_zsize, col.grid_xsize*col.grid_zsize))


        for z in range(col.grid_zsize):
            for x in range(col.grid_xsize):
                index = col.grid_xsize * z + x
                baseindex = index
                gottem[index] = True
                #index = col.grid_xsize * z + x

                offset = 0x2C + index*8
                f.write("{0}:{1}\n".format(x,z))
                get_grid_entries(col._data, index, offset, col.triangles_indices_offset, f, 0, gottem)
                #unk1, unk2, nextindex, triangleindex_offset = read_gridtable_entry(col._data, offset)
                #followup = 1
                #f.write("{0}:{1} index: {2}| {3} {4} {5} {6}\n".format(x, z, index, unk1, unk2, nextindex, triangleindex_offset))

                #if nextindex != 0:
                #    for i in range(4):
                #        offset = 0x2C + (nextindex+i)*8
                #        assert offset < col.triangles_indices_offset

                """while nextindex != 0:
                    gottem[nextindex] = True
                    #print(nextindex, "hm")
                    index = nextindex
                    offset = 0x2C + (index)*8
                    assert offset < col.triangles_indices_offset

                    unk1, unk2, nextindex, triangleindex_offset = read_gridtable_entry(col._data, offset)
                    followup += 1
                    f.write("->{0}:{1} index: {2}| {3} {4} {5} {6}\n".format(x, z, index, unk1, unk2, nextindex, triangleindex_offset))

                entries += followup"""

                f.write("\n\n")

                assert offset < col.triangles_indices_offset
    print("")
    u = 0
    a = 0
    for i, v in gottem.items():
        if v is False:
            #print("didn't get", i)
            u += 1
            offset = 0x2C + i*8

            data = read_uint32(col._data, offset)
            data2 = read_uint32(col._data, offset+4)
            if read_uint8(col._data, offset+1) != 0:
                print("THIS IS RARE", offset)
            if data != 0 or data2 != 0:
                a += 1