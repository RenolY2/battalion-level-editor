from OpenGL.GL import *
from io import BytesIO
from array import array
from struct import Struct
from PyQt5.QtGui import QImage, QPainter
from math import ceil, floor
from timeit import default_timer

from .read_binary import *


def decode_rgb565(color_val):
    b = (color_val & 0b11111) * 8
    g = ((color_val >> 5) & 0b111111) * 4
    r = ((color_val >> 11) & 0b11111) * 8
    return r, g, b


def decode_rgb5a3(color_val):
    isrgb555 = color_val >> 15

    if isrgb555:
        b = (color_val & 0b11111) * 8
        g = ((color_val >> 5) & 0b11111) * 8
        r = ((color_val >> 10) & 0b11111) * 8
        a = 0xFF
    else:
        # RGB4A3
        b = (color_val & 0b1111) * 0x11
        g = ((color_val >> 4) & 0b1111) * 0x11
        r = ((color_val >> 8) & 0b1111) * 0x11
        a = ((color_val >> 12) & 0b111) * 0x20

    return r, g, b, a


def addrgba(col1, col2):
    return col1[0]+col2[0], col1[1]+col2[1], col1[2]+col2[2], col1[3]+col2[3]


def multrgba(col, c):
    return col[0] * c, col[1] * c, col[2] * c, col[3] * c


def divrgba(col, c):
    return col[0] // c, col[1] // c, col[2] // c, col[3] // c

colors_format = Struct(">HH")
pixelmask_format = Struct(">I")

tileformat = Struct(">HHI")
tileunpack = tileformat.unpack

colors_unpack = colors_format.unpack
pixelmask_unpack = pixelmask_format.unpack


DXT1 = b"\x00\x00\x00\x001TXD"
IA8 = b"\x00\x00\x00\x00\x008AI"
I8 = b"\x00\x00\x00\x00\x00\x008I"
P8 = b"\x00\x00\x00\x00\x00\x008P"
RGBA = b"8B8G8R8A"

DXT1BW1 = b'DXT1\x00\x00\x00\x00'#reversed(DXT1)
IA8BW1 = b'IA8\x00\x00\x00\x00\x00' #reversed(IA8)
I8BW1 = b'I8\x00\x00\x00\x00\x00\x00'
P8BW1 = b'P8\x00\x00\x00\x00\x00\x00'#reversed(P8)
RGBABW1 = b'A8R8G8B8'#reversed(RGBA)


class Texture(object):
    def __init__(self, name):
        self.name = name
        self._loaded = False

    def dump_to_file(self, filepath):
        img = QImage(self.size_x, self.size_y, QImage.Format_ARGB32)
        rgbadata = self.rgba
        for ix in range(self.size_x):
            for iy in range(self.size_y):
                baseindex = ix * 4 + iy * self.size_x * 4
                r = rgbadata[baseindex + 0]
                g = rgbadata[baseindex + 1]
                b = rgbadata[baseindex + 2]
                a = rgbadata[baseindex + 3]
                img.setPixel(ix, iy, (a << 24) | (r << 16) | (g << 8) | b)

        img.save(filepath, "PNG")

    def is_loaded(self):
        return self._loaded

    def generate_dummy(self, x, y):
        self.size_x = x
        self.size_y = y

        self.rgba = bytearray(self.size_x * self.size_y * 4*b"\x00")
        self.success = True
        self._loaded = True

    def from_file(self, f):
        start = default_timer()

        f.seek(0)
        name = f.read(0x20)

        self.size_x2 = read_uint32(f)
        self.size_y2 = read_uint32(f)
        self.unkint1 = read_uint32(f)
        self.unkint2 = read_uint32(f)
        self.format = f.read(0x10)
        self.unkint3 = read_uint32(f)
        self.unkint4 = read_uint32(f)
        self.unkint5 = read_uint32(f)
        self.unkint6 = read_uint32(f)
        self.unkints = f.read(0x10)
        self.mipcount = read_uint32(f)
        self.size_x = read_uint32(f)
        self.size_y = read_uint32(f)
        self.mipcount2 = read_uint32(f)
        print(self.name)
        #print(self.size_x, self.size_x2)
        #print(self.size_y, self.size_y2)
        assert self.size_x == self.size_x2
        assert self.size_y == self.size_y2
        assert self.mipcount == self.mipcount2
        self.success = True

        print(name, self.format)
        assert self.format[8:] == b"8B8G8R8A"
        if self.mipcount == 0:
            self.success = False
            return

        texformat = self.format[:8]
        self.rgba = bytearray(self.size_x * self.size_y * 4)

        x, y = 0, 0
        size_x = self.size_x
        size_y = self.size_y
        rgbadata = self.rgba
        #print("Initialization took", default_timer() - start, "s")
        start = default_timer()
        if texformat == DXT1:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #pic_data = f.read(pimsize)

            range_4 = range(0, 4)
            range_16 = range(0, 16)
            read = f.read

            #for ii in range(0, len(pic_data) // 8, 4):
            #    for ii2 in range_4:
            #        block = pic_data[(ii + ii2) * 8:(ii + ii2 + 1) * 8]
            for ii in range(0, pimsize // 8):

                #col0, col1 = colors_unpack(block[:4])
                #pixmask = pixelmask_unpack(block[4:])[0]

                col0, col1, pixmask = tileunpack(read(8))

                color0 = decode_rgb565(col0)
                color1 = decode_rgb565(col1)

                ii2 = ii % 4
                iix = (ii2 % 2) * 4
                iiy = (ii2 // 2) * 4

                if col0 > col1:
                    color2_r = (2 * color0[0] + color1[0]) // 3
                    color2_g = (2 * color0[1] + color1[1]) // 3
                    color2_b = (2 * color0[2] + color1[2]) // 3
                    #color2_a = 255

                    color3_r = (2 * color1[0] + color0[0]) // 3
                    color3_g = (2 * color1[1] + color0[1]) // 3
                    color3_b = (2 * color1[2] + color0[2]) // 3
                    color3_a = 255
                else:
                    color2_r = (color0[0] + color1[0]) // 2
                    color2_g = (color0[1] + color1[1]) // 2
                    color2_b = (color0[2] + color1[2]) // 2
                    #color2_a = 255
                    color3_r = 0
                    color3_g = 0
                    color3_b = 0
                    color3_a = 0

                #colortable = (color0, color1,
                #              (color2_r, color2_g, color2_b, color2_a),
                #              (color3_r, color3_g, color3_b, color3_a))
                for iii in range_16:
                    iy = iii // 4
                    ix = iii % 4
                    index = (pixmask >> ((15 - (iy*4 + ix)) * 2)) & 0b11

                    if index == 0:
                        r, g, b = color0
                        a = 255
                    elif index == 1:
                        r, g, b = color1
                        a = 255
                    elif index == 2:
                        #r, g, b, a = color2_r, color2_g, color2_b, color2_a
                        r = color2_r
                        g = color2_g
                        b = color2_b
                        a = 255 #color2_a
                    elif index == 3:
                        #r, g, b, a = color3_r, color3_g, color3_b, color3_a
                        r = color3_r
                        g = color3_g
                        b = color3_b
                        a = color3_a
                    else:
                        raise RuntimeError("This shouldn't happen: Invalid index {0}".format(index))

                    array_x = x + ix + iix
                    array_y = y + iy + iiy
                    if array_x < size_x and array_y < size_y:

                        rgbadata[array_x*4 + array_y*size_x*4 + 0] = r
                        rgbadata[array_x*4 + array_y * size_x*4 + 1] = g
                        rgbadata[array_x*4 + array_y * size_x*4 + 2] = b
                        rgbadata[array_x*4 + array_y * size_x*4 + 3] = a
                        #else:
                    #    print("tried to write outside of bounds:", size_x, size_y, x + ix + iix, y + iy + iiy)

                if ii2 == 3:
                    x += 8
                    if x >= size_x:
                        x = 0
                        y += 8

        elif texformat == I8:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #pic_data = f.read(pimsize)

            blocks_horizontal = int(ceil(size_x / 4.0))
            blocks_vertical = int(ceil(size_y / 4.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(4*4*1)

                    for y in range(4):
                        for x in range(4):
                            alphaintensity = block[(x + y * 4)]

                            imgx = ix * 4 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = alphaintensity

        elif texformat == IA8:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #pic_data = f.read(pimsize)

            blocks_horizontal = int(ceil(size_x / 4.0))
            blocks_vertical = int(ceil(size_y / 4.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(4*4*2)

                    for y in range(4):
                        for x in range(4):
                            intensity = block[(x + y*4)*2 + 1]
                            alpha = block[(x + y * 4) * 2 + 0]

                            imgx = ix * 4 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = alpha

        elif texformat == P8:
            assert f.read(4) == b" LAP"
            pimsize = read_uint32_le(f)
            assert pimsize == 512

            palette = []
            for i in range(256):
                palette.append(decode_rgb5a3(read_uint16(f)))
                #palette.append(decode_rgb565(read_uint16(f)))

            assert f.read(4) == b" PIM"
            datalen = read_uint32_le(f)

            blocks_vertical = int(ceil(size_y / 4.0))
            blocks_horizontal = int(ceil(size_x / 8.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(8*4*1)
                    if len(block) < 32:
                        break

                    for y in range(4):
                        for x in range(8):
                            imgx = ix * 8 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            #intensity = block[(x + y*4)*2 + 1]
                            #alpha = block[(x + y * 4) * 2 + 0]
                            index = block[x + y*8]
                            r, g, b, a = palette[index]# index, index, index, 255#palette[index]



                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = r
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = g
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = b
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = a

        elif texformat == RGBA:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #print("size")

            for i in range(pimsize//64):
                for iy in range(4):
                    for ix in range(4):
                        #ix = 3 - ix
                        #iy = 3 - iy
                        imgx = x + ix
                        imgy = y + iy

                        if imgx >= size_x or imgy >= size_y:
                            continue

                        a, r = read_uint8(f), read_uint8(f)
                        rgbadata[(imgx + imgy * size_x) * 4 + 0] = r
                        rgbadata[(imgx + imgy * size_x) * 4 + 3] = a

                for iy in range(4):
                    for ix in range(4):
                        #ix = 3 - ix
                        #iy = 3 - iy
                        imgx = x + ix
                        imgy = y + iy

                        if imgx >= size_x or imgy >= size_y:
                            continue

                        g, b = read_uint8(f), read_uint8(f)
                        rgbadata[(imgx + imgy * size_x) * 4 + 1] = g
                        rgbadata[(imgx + imgy * size_x) * 4 + 2] = b

                x += 4
                if x >= size_x:
                    x = 0
                    y += 4


        else:
            #print("unknown format", texformat)
            self.success = False
            return


        #print(self.size_x, self.size_y)
        #print("conversion took", default_timer()-start)
        start = default_timer()
        self.rgba = bytes(self.rgba)
        self._loaded = True
        self.success = True
        #print("final steps took", default_timer()-start)

    # Aragorn's Quest
    def from_file_aragorn(self, f):
        start = default_timer()

        f.seek(0)
        name = f.read(0x20)

        self.size_x2 = read_uint32(f)
        self.size_y2 = read_uint32(f)
        self.unkint1 = read_uint32(f)
        self.unkint2 = read_uint32(f)
        self.format = f.read(0x10)
        self.unkint3 = read_uint32(f)
        self.unkint4 = read_uint32(f)
        self.unkint5 = read_uint32(f)
        self.unkint6 = read_uint32(f)
        self.unkints = f.read(0x10)
        self.unkint7 = read_uint32(f)
        self.size_x = read_uint32(f)
        self.size_y = read_uint32(f)
        self.mipcount = read_uint32(f)
        #print(self.size_x, self.size_x2)
        #print(self.size_y, self.size_y2)
        assert self.size_x == self.size_x2
        assert self.size_y == self.size_y2
        assert self.mipcount > 0
        self.success = True

        print(name, self.format)
        assert self.format[8:] == b"8B8G8R8A"
        if self.mipcount == 0:
            self.success = False
            return

        texformat = self.format[:8]
        self.rgba = bytearray(self.size_x * self.size_y * 4)

        x, y = 0, 0
        size_x = self.size_x
        size_y = self.size_y
        rgbadata = self.rgba
        #print("Initialization took", default_timer() - start, "s")
        start = default_timer()
        if texformat == DXT1:
            assert f.read(4) == b"RPIM"
            pimsize = read_uint32_le(f)
            f.read(0x18)  # padding
            #pic_data = f.read(pimsize)

            range_4 = range(0, 4)
            range_16 = range(0, 16)
            read = f.read

            #for ii in range(0, len(pic_data) // 8, 4):
            #    for ii2 in range_4:
            #        block = pic_data[(ii + ii2) * 8:(ii + ii2 + 1) * 8]
            for ii in range(0, (pimsize-0x18) // 8):

                #col0, col1 = colors_unpack(block[:4])
                #pixmask = pixelmask_unpack(block[4:])[0]

                col0, col1, pixmask = tileunpack(read(8))

                color0 = decode_rgb565(col0)
                color1 = decode_rgb565(col1)

                ii2 = ii % 4
                iix = (ii2 % 2) * 4
                iiy = (ii2 // 2) * 4

                if col0 > col1:
                    color2_r = (2 * color0[0] + color1[0]) // 3
                    color2_g = (2 * color0[1] + color1[1]) // 3
                    color2_b = (2 * color0[2] + color1[2]) // 3
                    #color2_a = 255

                    color3_r = (2 * color1[0] + color0[0]) // 3
                    color3_g = (2 * color1[1] + color0[1]) // 3
                    color3_b = (2 * color1[2] + color0[2]) // 3
                    color3_a = 255
                else:
                    color2_r = (color0[0] + color1[0]) // 2
                    color2_g = (color0[1] + color1[1]) // 2
                    color2_b = (color0[2] + color1[2]) // 2
                    #color2_a = 255
                    color3_r = 0
                    color3_g = 0
                    color3_b = 0
                    color3_a = 0

                #colortable = (color0, color1,
                #              (color2_r, color2_g, color2_b, color2_a),
                #              (color3_r, color3_g, color3_b, color3_a))
                for iii in range_16:
                    iy = iii // 4
                    ix = iii % 4
                    index = (pixmask >> ((15 - (iy*4 + ix)) * 2)) & 0b11

                    if index == 0:
                        r, g, b = color0
                        a = 255
                    elif index == 1:
                        r, g, b = color1
                        a = 255
                    elif index == 2:
                        #r, g, b, a = color2_r, color2_g, color2_b, color2_a
                        r = color2_r
                        g = color2_g
                        b = color2_b
                        a = 255 #color2_a
                    elif index == 3:
                        #r, g, b, a = color3_r, color3_g, color3_b, color3_a
                        r = color3_r
                        g = color3_g
                        b = color3_b
                        a = color3_a
                    else:
                        raise RuntimeError("This shouldn't happen: Invalid index {0}".format(index))

                    array_x = x + ix + iix
                    array_y = y + iy + iiy
                    if array_x < size_x and array_y < size_y:

                        rgbadata[array_x*4 + array_y*size_x*4 + 0] = r
                        rgbadata[array_x*4 + array_y * size_x*4 + 1] = g
                        rgbadata[array_x*4 + array_y * size_x*4 + 2] = b
                        rgbadata[array_x*4 + array_y * size_x*4 + 3] = a
                        #else:
                    #    print("tried to write outside of bounds:", size_x, size_y, x + ix + iix, y + iy + iiy)

                if ii2 == 3:
                    x += 8
                    if x >= size_x:
                        x = 0
                        y += 8

        elif texformat == I8:
            assert f.read(4) == b"RPIM"
            pimsize = read_uint32_le(f)
            f.read(0x18)  # padding
            #pic_data = f.read(pimsize)

            blocks_horizontal = int(ceil(size_x / 4.0))
            blocks_vertical = int(ceil(size_y / 4.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(4*4*1)

                    for y in range(4):
                        for x in range(4):
                            alphaintensity = block[(x + y * 4)]

                            imgx = ix * 4 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = alphaintensity

        elif texformat == IA8:
            assert f.read(4) == b"RPIM"
            pimsize = read_uint32_le(f) - 0x18
            f.read(0x18)  # padding
            #pic_data = f.read(pimsize)

            blocks_horizontal = int(ceil(size_x / 4.0))
            blocks_vertical = int(ceil(size_y / 4.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(4*4*2)

                    for y in range(4):
                        for x in range(4):
                            intensity = block[(x + y*4)*2 + 1]
                            alpha = block[(x + y * 4) * 2 + 0]

                            imgx = ix * 4 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = alpha

        elif texformat == P8:
            assert f.read(4) == b" LAP"
            pimsize = read_uint32_le(f)
            assert pimsize == 512

            palette = []
            for i in range(256):
                palette.append(decode_rgb5a3(read_uint16(f)))
                #palette.append(decode_rgb565(read_uint16(f)))

            assert f.read(4) == b"RPIM"

            datalen = read_uint32_le(f)
            f.read(0x18)  # padding

            blocks_vertical = int(ceil(size_y / 4.0))
            blocks_horizontal = int(ceil(size_x / 8.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(8*4*1)
                    if len(block) < 32:
                        break

                    for y in range(4):
                        for x in range(8):
                            imgx = ix * 8 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            #intensity = block[(x + y*4)*2 + 1]
                            #alpha = block[(x + y * 4) * 2 + 0]
                            index = block[x + y*8]
                            r, g, b, a = palette[index]# index, index, index, 255#palette[index]



                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = r
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = g
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = b
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = a

        elif texformat == RGBA:
            assert f.read(4) == b"RPIM"
            pimsize = read_uint32_le(f)
            f.read(0x18)  # padding
            #print("size")

            for i in range(pimsize//64):
                for iy in range(4):
                    for ix in range(4):
                        #ix = 3 - ix
                        #iy = 3 - iy
                        imgx = x + ix
                        imgy = y + iy

                        if imgx >= size_x or imgy >= size_y:
                            continue

                        a, r = read_uint8(f), read_uint8(f)
                        rgbadata[(imgx + imgy * size_x) * 4 + 0] = r
                        rgbadata[(imgx + imgy * size_x) * 4 + 3] = a

                for iy in range(4):
                    for ix in range(4):
                        #ix = 3 - ix
                        #iy = 3 - iy
                        imgx = x + ix
                        imgy = y + iy

                        if imgx >= size_x or imgy >= size_y:
                            continue

                        g, b = read_uint8(f), read_uint8(f)
                        rgbadata[(imgx + imgy * size_x) * 4 + 1] = g
                        rgbadata[(imgx + imgy * size_x) * 4 + 2] = b

                x += 4
                if x >= size_x:
                    x = 0
                    y += 4


        else:
            #print("unknown format", texformat)
            self.success = False
            return


        #print(self.size_x, self.size_y)
        #print("conversion took", default_timer()-start)
        start = default_timer()
        self.rgba = bytes(self.rgba)
        self._loaded = True
        self.success = True
        #print("final steps took", default_timer()-start)

    def from_file_bw1(self, f):
        start = default_timer()

        f.seek(0)
        #print(f.read(0x10)) # name
        name = f.read(0x10)
        self.size_x = read_uint32_le(f)
        self.size_y = read_uint32_le(f)

        #print(self.size_x, self.size_y)
        self.unkint1 = read_uint32(f)
        self.unkint2 = read_uint32(f)
        self.format = f.read(0x10)
        f.read(0x20) # unk values
        self.mipcount = read_uint32(f)
        #print(self.size_x, self.size_x2)
        #print(self.size_y, self.size_y2)
        #assert self.size_x == self.size_x2
        #assert self.size_y == self.size_y2
        #assert self.mipcount == self.mipcount2
        self.success = True

        print(name, self.format)
        print(self.size_x, self.size_y)
        assert self.format[8:] == b"A8R8G8B8"
        if self.mipcount == 0:
            self.success = False
            return

        texformat = self.format[:8]
        self.rgba = bytearray(self.size_x * self.size_y * 4)

        x, y = 0, 0
        size_x = self.size_x
        size_y = self.size_y
        rgbadata = self.rgba
        #print("Initialization took", default_timer() - start, "s")
        start = default_timer()
        if texformat == DXT1BW1:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #pic_data = f.read(pimsize)

            range_4 = range(0, 4)
            range_16 = range(0, 16)
            read = f.read

            #for ii in range(0, len(pic_data) // 8, 4):
            #    for ii2 in range_4:
            #        block = pic_data[(ii + ii2) * 8:(ii + ii2 + 1) * 8]
            for ii in range(0, pimsize // 8):

                #col0, col1 = colors_unpack(block[:4])
                #pixmask = pixelmask_unpack(block[4:])[0]

                col0, col1, pixmask = tileunpack(read(8))

                color0 = decode_rgb565(col0)
                color1 = decode_rgb565(col1)

                ii2 = ii % 4
                iix = (ii2 % 2) * 4
                iiy = (ii2 // 2) * 4

                if col0 > col1:
                    color2_r = (2 * color0[0] + color1[0]) // 3
                    color2_g = (2 * color0[1] + color1[1]) // 3
                    color2_b = (2 * color0[2] + color1[2]) // 3
                    #color2_a = 255

                    color3_r = (2 * color1[0] + color0[0]) // 3
                    color3_g = (2 * color1[1] + color0[1]) // 3
                    color3_b = (2 * color1[2] + color0[2]) // 3
                    color3_a = 255
                else:
                    color2_r = (color0[0] + color1[0]) // 2
                    color2_g = (color0[1] + color1[1]) // 2
                    color2_b = (color0[2] + color1[2]) // 2
                    #color2_a = 255
                    color3_r = 0
                    color3_g = 0
                    color3_b = 0
                    color3_a = 0

                #colortable = (color0, color1,
                #              (color2_r, color2_g, color2_b, color2_a),
                #              (color3_r, color3_g, color3_b, color3_a))
                for iii in range_16:
                    iy = iii // 4
                    ix = iii % 4
                    index = (pixmask >> ((15 - (iy*4 + ix)) * 2)) & 0b11

                    if index == 0:
                        r, g, b = color0
                        a = 255
                    elif index == 1:
                        r, g, b = color1
                        a = 255
                    elif index == 2:
                        #r, g, b, a = color2_r, color2_g, color2_b, color2_a
                        r = color2_r
                        g = color2_g
                        b = color2_b
                        a = 255 #color2_a
                    elif index == 3:
                        #r, g, b, a = color3_r, color3_g, color3_b, color3_a
                        r = color3_r
                        g = color3_g
                        b = color3_b
                        a = color3_a
                    else:
                        raise RuntimeError("This shouldn't happen: Invalid index {0}".format(index))

                    array_x = x + ix + iix
                    array_y = y + iy + iiy
                    if array_x < size_x and array_y < size_y:
                        rgbadata[array_x*4 + array_y*size_x*4 + 0] = r
                        rgbadata[array_x*4 + array_y * size_x*4 + 1] = g
                        rgbadata[array_x*4 + array_y * size_x*4 + 2] = b
                        rgbadata[array_x*4 + array_y * size_x*4 + 3] = a
                        #else:
                    #    print("tried to write outside of bounds:", size_x, size_y, x + ix + iix, y + iy + iiy)

                if ii2 == 3:
                    x += 8
                    if x >= size_x:
                        x = 0
                        y += 8

        elif texformat == I8BW1:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #pic_data = f.read(pimsize)

            blocks_horizontal = int(ceil(size_x / 4.0))
            blocks_vertical = int(ceil(size_y / 4.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(4*4*1)

                    for y in range(4):
                        for x in range(4):
                            alphaintensity = block[(x + y * 4)]

                            imgx = ix * 4 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = alphaintensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = alphaintensity
        elif texformat == IA8BW1:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #pic_data = f.read(pimsize)

            blocks_horizontal = int(ceil(size_x / 4.0))
            blocks_vertical = int(ceil(size_y / 4.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(4*4*2)

                    for y in range(4):
                        for x in range(4):
                            intensity = block[(x + y*4)*2 + 1]
                            alpha = block[(x + y * 4) * 2 + 0]

                            imgx = ix * 4 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = intensity
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = alpha

        elif texformat == P8BW1:
            assert f.read(4) == b" LAP"
            pimsize = read_uint32_le(f)
            assert pimsize == 512

            palette = []
            for i in range(256):
                palette.append(decode_rgb5a3(read_uint16(f)))
                #palette.append(decode_rgb565(read_uint16(f)))

            assert f.read(4) == b" PIM"
            datalen = read_uint32_le(f)

            blocks_vertical = int(ceil(size_y / 4.0))
            blocks_horizontal = int(ceil(size_x / 8.0))

            for iy in range(blocks_vertical):
                for ix in range(blocks_horizontal):
                    block = f.read(8*4*1)

                    for y in range(4):
                        for x in range(8):
                            #intensity = block[(x + y*4)*2 + 1]
                            #alpha = block[(x + y * 4) * 2 + 0]
                            index = block[x + y*8]
                            r, g, b, a = palette[index]# index, index, index, 255#palette[index]

                            imgx = ix * 8 + x
                            imgy = iy * 4 + y

                            if imgx >= size_x or imgy >= size_y:
                                continue

                            rgbadata[(imgx + imgy * size_x) * 4 + 0] = r
                            rgbadata[(imgx + imgy * size_x) * 4 + 1] = g
                            rgbadata[(imgx + imgy * size_x) * 4 + 2] = b
                            rgbadata[(imgx + imgy * size_x) * 4 + 3] = a

        elif texformat == RGBABW1:
            assert f.read(4) == b" PIM"
            pimsize = read_uint32_le(f)
            #print("size")

            for i in range(pimsize//64):
                for iy in range(4):
                    for ix in range(4):
                        #ix = 3 - ix
                        #iy = 3 - iy
                        imgx = x + ix
                        imgy = y + iy
                        if imgx >= size_x or imgy >= size_y:
                            continue
                        a, r = read_uint8(f), read_uint8(f)
                        rgbadata[(imgx + imgy * size_x) * 4 + 0] = r
                        rgbadata[(imgx + imgy * size_x) * 4 + 3] = a

                for iy in range(4):
                    for ix in range(4):
                        #ix = 3 - ix
                        #iy = 3 - iy
                        imgx = x + ix
                        imgy = y + iy
                        if imgx >= size_x or imgy >= size_y:
                            continue
                        g, b = read_uint8(f), read_uint8(f)
                        rgbadata[(imgx + imgy * size_x) * 4 + 1] = g
                        rgbadata[(imgx + imgy * size_x) * 4 + 2] = b

                x += 4
                if x >= size_x:
                    x = 0
                    y += 4


        else:
            #print("unknown format", texformat)
            self.success = False
            return


        #print(self.size_x, self.size_y)
        #print("conversion took", default_timer()-start)
        #start = default_timer()
        self.rgba = bytes(self.rgba)
        self._loaded = True
        self.success = True
        #print("final steps took", default_timer()-start)


class TextureArchive(object):
    def __init__(self, archive):
        self.game = archive.get_game()

        self.textures = {}
        for texture in archive.textures:
            name = bytes(texture.res_name).lower()
            self.textures[name] = texture

            name2 = name.strip(b"\x00").decode("ascii")
            self.textures[name2] = texture

        self._cached = {}
        self.tex = glGenTextures(1)

    def reset(self):
        for name, val in self._cached.items():
            del val

        self._cached = {}

    def initialize_texture(self, texname, mipmap=False):
        dummy = False

        if texname in self._cached:
            return self._cached[texname]

        if texname not in self.textures:
            print("Texture not found:", texname)

            # Sometimes level terrain uses a dummy texture
            if texname == "Dummy":
                dummy = True
            else:
                return None


        # f = self.textures[texname].fileobj
        tex = Texture(texname)
        #tex.from_file(f)
        ID = glGenTextures(1)
        self._cached[texname] = (tex, ID)
        self.load_texture(texname, dummy, mipmap)
        return self._cached[texname]

    def load_texture(self, texname, dummy=False, mipmap=False):
        if texname not in self._cached:
            return None

        tex: Texture
        ID: int
        tex, ID = self._cached[texname]

        if tex.is_loaded():
            return self._cached[texname]

        if dummy:
            print("Generating dummy texture")
            tex.generate_dummy(32, 32)
        else:
            f = self.textures[texname].fileobj

            if self.game == "BW1":
                tex.from_file_bw1(f)
            elif self.game == "BW2":
                tex.from_file(f)
            elif self.game == "AQ":
                tex.from_file_aragorn(f)

        if tex.success:
            #tex.dump_to_file(str(texname.strip(b"\x00"), encoding="ascii")+".png")
            glBindTexture(GL_TEXTURE_2D, ID)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

            if mipmap:
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            else:
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

            # glPixelStorei(GL_UNPACK_ROW_LENGTH, tex.size_x)
            #print("call info", tex.size_x, tex.size_y, tex.size_x * tex.size_y * 4, len(tex.rgba))
            #print(ID)
            glTexImage2D(GL_TEXTURE_2D, 0, 4, tex.size_x, tex.size_y, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex.rgba)# b"\x00"*tex.size_x*tex.size_y*4)#tex.rgba)
            if mipmap:
                glGenerateMipmap(GL_TEXTURE_2D)
            #glTexImage2D(GL_TEXTURE_2D, 0, 4, tex.size_x, tex.size_y, 0, GL_RGBA, GL_UNSIGNED_BYTE, b"\x7F"*tex.size_x*tex.size_y*4)
            #testsize = 32
            #glTexImage2D(GL_TEXTURE_2D, 0, 4, testsize, testsize, 0, GL_RGBA, GL_UNSIGNED_BYTE,
            #             b"\x7F" * testsize * testsize * 4)
            #print("error after call", glGetError())
            #self._cached[texname] = (tex, ID)

            return self._cached[texname]
        else:
            print("loading tex wasn't successful", texname)
            return None

    def get_texture(self, texname):
        if texname in self._cached:
            #tex, id = self._cached[texname]
            #if tex.success:
            #    tex.dump_to_file(str(texname.strip(b"\x00"), encoding="ascii")+".png")
            return self._cached[texname]
        else:
            self.initialize_texture(texname)
            return self.load_texture(texname)

