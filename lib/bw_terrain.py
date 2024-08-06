from dataclasses import dataclass
from struct import pack, unpack, unpack_from, Struct
from lib.vectors import Triangle, Vector3
from OpenGL import *
from numpy import array


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


class ChunkModel(object):
    def __init__(self, points):
        self.vertices = []


def initiate_from_section(cls, section):
    assert len(section)%cls.size == 0.0
    return list(cls.from_array(section, i) for i in range(len(section)//cls.size))


@dataclass
class Color:
    r: float
    g: float
    b: float
    a: float
    size = 4

    @classmethod
    def from_array(cls, section, i):
        return cls(*(x/255.0 for x in unpack_from("BBBB", section, i*cls.size)))


@dataclass
class UVPoint:
    x: float  # ushort
    y: float  # ushort
    size = 4

    @classmethod
    def from_array(cls, section, i):
        x, y = unpack_from(">HH", section, i*cls.size)
        return cls(x/4096.0, y/4096.0)


@dataclass
class Vertex:
    pos: array
    color: Color
    uv1: UVPoint
    uv2: UVPoint


class TileModel(object):
    def __init__(self, tile, materials, offsetx, offsety):
        self.vertices = []
        self.quads = []
        self.material = materials[tile.material_index]

        tl = tile.surface_coordinates[0]
        tr = tile.surface_coordinates[1]
        bl = tile.surface_coordinates[2]
        br = tile.surface_coordinates[3]

        for y in range(4):
            for x in range(4):
                fx = x/3.0
                fy = y/3.0
                u = fy*(fx*tl.x + (1-fx)*tr.x) + (1-fy)*(fx*bl.x + (1-fx)*br.x)
                v = fy*(fx*tl.y + (1-fx)*tr.y) + (1-fy)*(fx*bl.y + (1-fx)*br.y)

                index = 4*y + x
                height = tile.heights[index]/16.0
                position = array([(x+offsetx)*4*(4/3)-2048, height, (y+offsety)*4*(4/3)-2048])
                uv1 = UVPoint(u, v)
                uv2 = tile.detail_coordinates[index]
                color = tile.vertex_colors[index]

                self.vertices.append(Vertex(position, color, uv1, uv2))

                if x < 3 and y < 3:
                    indexr = 4*y + x+1
                    indexb = 4*(y+1) + x
                    indexbr = 4*(y+1) + x+1

                    self.quads.append((index, indexr, indexbr, indexb))


@dataclass
class Tile:
    heights: list[int]                  # 16 ushorts
    vertex_colors: list[int]            # 16 vertex colors
    surface_coordinates: list[UVPoint]  # 4 UVs
    detail_coordinates: list[UVPoint]   # 16 UVs
    material_index: int
    size = 180


    @classmethod
    def from_array(cls, array, i):
        tiledata = array[i*cls.size:(i+1)*cls.size]
        offset = 0
        heights = list(unpack_from(">16H", tiledata, offset))
        offset += 16*2

        vertex_colors = initiate_from_section(Color, tiledata[offset:offset+16*4])
        offset += 16*4

        surface_coordinates = initiate_from_section(UVPoint, tiledata[offset:offset+16])
        offset += 4*4

        detail_coordinates = initiate_from_section(UVPoint, tiledata[offset:offset+16*4])
        offset += 16*4

        material_index = unpack_from(">I", tiledata, offset)[0]
        offset += 4

        assert offset == cls.size

        return cls(heights, vertex_colors, surface_coordinates, detail_coordinates, material_index)



@dataclass
class Chunk(object):
    tiles: list[Tile]
    size = Tile.size*16

    @classmethod
    def from_array(cls, array, i):
        chunkdata = array[i*cls.size:(i+1)*cls.size]
        tiles = initiate_from_section(Tile, chunkdata)
        return cls(tiles)



@dataclass
class TerrainData:
    chunks_x: int
    chunks_y: int
    unknown_count: int
    material_count: int

    @classmethod
    def from_section(cls, section):
        return cls(*unpack("IIII", section))


@dataclass
class MapMaterial:
    mat1: str
    mat2: str
    unk1: int
    unk2: int
    unk3: int
    unk4: int
    size = 48

    @classmethod
    def from_array(cls, array, i):
        mat1, mat2, unk1, unk2, unk3, unk4 = unpack_from("16s16sIIII", array, i*cls.size)
        mat1 = mat1.strip(b"\x00").decode("ascii")
        mat2 = mat2.strip(b"\x00").decode("ascii")

        return cls(mat1, mat2, unk1, unk2, unk3, unk4)


@dataclass
class MapChunkReference:
    a: int
    b: int
    chunkindex: int
    size = 4

    @classmethod
    def from_array(cls, array, i):
        return cls(*unpack_from(">BBH", array, i*4))


class BWTerrainV2(BWSectionedFile):
    def __init__(self, f):
        super().__init__(f)
        #width, height, unk1, unk2 = unpack("IIII", self.sections[b"RRET"])
        self.terrain_data = TerrainData.from_section(self.sections[b"RRET"])
        self.chunks = initiate_from_section(Chunk, self.sections[b"KNHC"])
        self.map = initiate_from_section(MapChunkReference, self.sections[b"PAMC"])
        self.materials = initiate_from_section(MapMaterial, self.sections[b"LTAM"])

        assert self.terrain_data.chunks_x == self.terrain_data.chunks_y == 64
        print(self.terrain_data.material_count)

        self.pointdata = [[None for y in range(self.terrain_data.chunks_y * 16 + 1)] for x in range(self.terrain_data.chunks_y * 16 + 1)]

        self.meshes: dict[TileModel] = {}
        for chunkx in range(64):
            for chunky in range(64):
                mapchunk = self.map[chunky*64 + chunkx]
                if mapchunk.b == 1:
                    print(mapchunk.chunkindex)
                    chunk = self.chunks[mapchunk.chunkindex]
                    for tilex in range(4):
                        for tiley in range(4):
                            tile = chunk.tiles[tiley*4+tilex]

                            if tile.material_index not in self.meshes:
                                self.meshes[tile.material_index] = []

                            for x in range(4):
                                for y in range(4):
                                    index = y*4 + x
                                    self.pointdata[chunkx*16 + tilex*4 + x][chunky*16+tiley*4+y] = tile.heights[index]/16.0

                            tilemodel = TileModel(tile, self.materials, chunkx*16 + tilex*4 - tilex -chunkx*4, chunky*16 + tiley*4 - tiley - chunky*4)
                            self.meshes[tile.material_index].append(tilemodel)

    def check_height(self, x, y):
        mapx = int((x + 2048)*0.25)
        mapy = int((y + 2048)*0.25)
        if 0 <= mapx < 4096 and 0 <= mapy < 4096:
            if self.pointdata[mapx][mapy] is None:
                return None
            return self.pointdata[mapx][mapy]
        else:
            return None






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
        bwterrain = BWTerrainV2(f)

    #print(bwterrain.chunks)
    #print(bwterrain.map)
    print(bwterrain.materials)

    for chunk in bwterrain.chunks:
        for tile in chunk.tiles:
            print(tile.surface_coordinates)