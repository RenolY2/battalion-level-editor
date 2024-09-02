import sys
import os
from math import log2
from PIL import Image
from lib.bw.texlib.read_binary import *
from lib.bw.texlib.texture_utils import *

PALLETE = b"PAL "
MIP = b"MIP "

DXT1 = b"\x00\x00\x00\x001TXD"
IA8 = b"\x00\x00\x00\x00\x008AI"
IA4 = b"\x00\x00\x00\x00\x004AI"
I8 = b"\x00\x00\x00\x00\x00\x008I"
P8 = b"\x00\x00\x00\x00\x00\x008P"
I4 = b"\x00\x00\x00\x00\x00\x004I"
P4 = b"\x00\x00\x00\x00\x00\x004P"
RGBA = b"8B8G8R8A"

DXT1BW1 = b'DXT1\x00\x00\x00\x00'#reversed(DXT1)
IA8BW1 = b'IA8\x00\x00\x00\x00\x00' #reversed(IA8)
I8BW1 = b'I8\x00\x00\x00\x00\x00\x00'
P8BW1 = b'P8\x00\x00\x00\x00\x00\x00'#reversed(P8)
RGBABW1 = b'A8R8G8B8'#reversed(RGBA)

STRTOFORMAT = {
    "DXT1": DXT1,
    "IA8": IA8,
    "IA4": IA4,
    "P4": P4,
    "P8": P8,
    "I8": I8,
    "I4": I4,
    "RGBA": RGBA
}

FORMATTOSTR = {}
for k, v in STRTOFORMAT.items():
    FORMATTOSTR[v] = k


FORMAT = {
    "DXT1": ImageFormat.CMPR,
    "IA8": ImageFormat.IA8,
    "IA4": ImageFormat.IA4,
    "P4": ImageFormat.C4,
    "P8": ImageFormat.C8,
    "I8": ImageFormat.I8,
    "I4": ImageFormat.I4,
    "RGBA": ImageFormat.RGBA32
}


# The statistically most used header values for each format
FORMATDEFAULTSBW2 = {
    "DXT1": (4100, 255, 255, 1, 1024, 0),
    "P8": (4116, 0, 255, 8, 245, 0),
    "IA8": (4116, 0, 255, 1, 1024, 0),
    "IA4": (4116, 0, 255, 165, 676, 0),
    "P4": (4108, 0, 0, 1, 16, 0xFFFFFFFF),
    "RGBA": (4116, 0, 255, 17, 1024, 0xFFFFFFFF),
    "I4": (4116, 0, 255, 100, 100, 0),
    "I8": (4116, 0, 255, 187, 1024, 0)
}

FORMATDEFAULTSBW1 = {
    "DXT1": (4, 255, 255, 1, 1024, 0),
    "P8": (20, 0, 255, 8, 69, 0xFFFFFFFF),#(20, 255, 255, 1, 1024, 0xFFFFFFFF)
    "RGBA": (20, 0, 255, 17, 1024, 0xFFFFFFFF),
}

def valuerange_assertion(val, start, end):
    if not start <= val <= end:
        raise RuntimeError("Value needs to be in range of {0} to {1} but is {2}.")


class Texture(object):
    def __init__(self, name):
        self.name = name
        self.mipmaps = []

    @classmethod
    def create_dummy(cls, name, x=32, y=32):
        tex = cls(name)
        tex.generate_dummy(x, y)

        return tex

    def generate_dummy(self, x, y):
        img = Image.new("RGBA", (x, y), (255, 255, 255, 255))
        self.mipmaps = [img]

    @classmethod
    def from_png(cls, name, path):
        tex = cls(name)
        img = Image.open(path)
        tex.mipmaps = [img]

        return tex

    def dump_to_file(self, filepath):
        self.mipmaps[0].save(filepath, "PNG")

    @property
    def texture(self):
        if len(self.mipmaps) == 0:
            raise RuntimeError("Texture has no texture image")
        return self.mipmaps[0]


class BW2Texture(Texture):
    def __init__(self, name):
        super().__init__(name)
        
        self.unkint1 = 1 
        self.unkint2 = 4100 # 4100, 4108 or 4116
        self.fmt = "DXT1"
        self.unkint3 = 0 # <= 255
        self.unkint4 = 0 # <= 255
        self.unkint5 = 0 # <= 255
        self.unkint6 = 0 # <= 1024
        self.unkint7 = 0 # <= 25 or 0xFFFFFFFF
        
        #self.mipcount = 0
        #self.size_x = 0
        #self.size_y = 0
        
        self.mipmaps = []
        #self.mipmaps_decoded = []
    
    def header_to_string(self):
        unkint7 = self.unkint7 
        if unkint7 == 0xFFFFFFFF:
            unkint7 = -1
        if len(self.mipmaps) > 1:
            values = ["MipMap", self.unkint2, self.unkint3, self.unkint4, self.unkint5, self.unkint6, unkint7]
        else:
            values = [self.unkint2, self.unkint3, self.unkint4, self.unkint5, self.unkint6, unkint7]
        
        return ".".join(str(x) for x in values)
        
    def header_from_string(self, string):
        values = string.split(".")
        if len(values) == 0:
            return 
            
        if values[0].lower() == "mipmap":
            values.pop(0)
        
        if len(values) < 6:
            return 
        
        try:
            values = [int(x) for x in values[:6]]
        except:
            raise RuntimeError("Non-number header values encountered:", values)
        if values[0] in (4, 12, 20):
            valmap = {4: 4100, 12: 4108, 20: 4116}
            new = valmap[values[0]]
            print("BW1 values detected. Changing", values[0], "to", new)
            values[0] = new
            
        if values[0] not in (4100, 4108, 4116): raise RuntimeError("Unknown value for value 1: {0}. Needs to be 4, 12 or 20.".format(values[0]))
        valuerange_assertion(values[1], 0, 255)
        valuerange_assertion(values[2], 0, 255)
        valuerange_assertion(values[3], 0, 255)
        valuerange_assertion(values[4], 0, 1024)
        valuerange_assertion(values[5], -1, 25)
        
        self.unkint2 = values[0]
        self.unkint3 = values[1]
        self.unkint4 = values[2]
        self.unkint5 = values[3]
        self.unkint6 = values[4]
        self.unkint7 = values[5]
        if self.unkint7 == -1:
            self.unkint7 = 0xFFFFFFFF
            
    @classmethod
    def from_path(cls, path, name, fmt, unkint2=None, unkint3=None, unkint4=None, unkint5=None, unkint6=None, unkint7=None, mipmaps=1, autogenmipmaps=False, mipmappaths = []):
        if unkint2 is None: unkint2 = FORMATDEFAULTSBW2[fmt][0]
        if unkint3 is None: unkint3 = FORMATDEFAULTSBW2[fmt][1]
        if unkint4 is None: unkint4 = FORMATDEFAULTSBW2[fmt][2]
        if unkint5 is None: unkint5 = FORMATDEFAULTSBW2[fmt][3]
        if unkint6 is None: unkint6 = FORMATDEFAULTSBW2[fmt][4]
        if unkint7 is None: unkint7 = FORMATDEFAULTSBW2[fmt][5]
        
        assert not (autogenmipmaps and mipmappaths)
        
        tex = cls(name)
        tex.fmt = fmt
        tex.unkint2 = unkint2
        tex.unkint3 = unkint3
        tex.unkint4 = unkint4
        tex.unkint5 = unkint5
        tex.unkint6 = unkint6
        tex.unkint7 = unkint7
        img = Image.open(path)
        tex.mipmaps.append(img)
        
        if autogenmipmaps:
            if log2(img.width) % 1 != 0 or log2(img.height) % 1 != 0:
                print("Warning: Cannot generate mipmaps for non-power of 2 texture. Skipping mipmap generation.")
            else:
                mipmap_count = int(log2(min(img.width, img.height)))
                mipmap_width = img.width 
                mipmap_height = img.height 
                
                for i in range(mipmap_count):
                    if i != 0:
                        mipmap_width //= 2
                        mipmap_height //= 2
                        mipmap_image = img.resize((mipmap_width, mipmap_height), Image.NEAREST)
                        tex.mipmaps.append(mipmap_image)
        
        return tex
    
    def write(self, f):
        start = f.tell()
        assert len(self.name) <= 0x20-1
        f.write(self.name.encode("ascii"))
        f.write(b"\x00"*(0x20 - f.tell()))
        assert f.tell()-start == 0x20
        
        image = self.mipmaps[0]
        write_uint32(f, image.width)
        write_uint32(f, image.height)
        write_uint32(f, self.unkint1)
        write_uint32(f, self.unkint2)
        f.write(STRTOFORMAT[self.fmt])
        f.write(b"8B8G8R8A")
        write_uint32(f, self.unkint3)
        write_uint32(f, self.unkint4)
        write_uint32(f, self.unkint5)
        write_uint32(f, self.unkint6)
        write_uint32(f, self.unkint7)
        f.write(b"\x00"*12)
        
        mipcount = 1 # len(self.mipmaps)
        write_uint32(f, mipcount)
        write_uint32(f, image.width)
        write_uint32(f, image.height)
        write_uint32(f, mipcount)
        assert f.tell()-start == 0x70
        
        imgdata, palettedata, _ = encode_image(image, FORMAT[self.fmt], PaletteFormat.RGB5A3, mipmap_count=1)
        if self.fmt in ("P4", "P8"):
            write_id(f, PALLETE)
            write_uint32_le(f, 512)
            f.write(palettedata.getbuffer())
            f.write(b"\x00"*(512-len(palettedata.getbuffer())))
        
        write_id(f, MIP)
        write_uint32_le(f, len(imgdata.getbuffer()))
        f.write(imgdata.getbuffer())
        
        if len(self.mipmaps) > 1:
            for mipmap in self.mipmaps[1:]:
                imgdata, palettedata, _ = encode_image(mipmap, FORMAT[self.fmt], PaletteFormat.RGB5A3, mipmap_count=1)
                write_id(f, MIP)
                write_uint32_le(f, len(imgdata.getbuffer()))
                f.write(imgdata.getbuffer())
    
    @classmethod 
    def from_file(cls, f, ignoremips=False):
        #f.seek(0)
        start = f.tell()
        name = f.read(0x20).rstrip(b"\x00").decode("ascii")
        tex = cls(name)
        
        size_x2 = read_uint32(f)
        size_y2 = read_uint32(f)
        tex.unkint1 = read_uint32(f)
        assert tex.unkint1 == 1
        tex.unkint2 = read_uint32(f) 
        assert tex.unkint2 in (4100, 4108, 4116)
        
        fmt = f.read(0x8)
        assert fmt in (DXT1, IA8, IA4, I8, I4, P8, P4, RGBA)
        tex.fmt = FORMATTOSTR[fmt]
        color_format = f.read(0x8)
        assert color_format == b"8B8G8R8A"
        
        tex.unkint3 = read_uint32(f) 
        assert tex.unkint3 <= 255
        
        tex.unkint4 = read_uint32(f)
        assert tex.unkint4 <= 255
        
        
        tex.unkint5 = read_uint32(f)
        assert tex.unkint5 <= 255
        
        tex.unkint6 = read_uint32(f)
        assert tex.unkint6 <= 1024
        
        tex.unkint7 = read_uint32(f)
        assert 0 <= tex.unkint7 <= 25 or tex.unkint7 == 0xFFFFFFFF
        pad = f.read(12) # between 0 and 25, or 0xFFFFFFFF
        assert pad == b"\x00"*12
        #tex.unkints = f.read(0x10)
        
        mipcount = read_uint32(f)
        tex.size_x = read_uint32(f)
        tex.size_y = read_uint32(f)
        mipcount2 = read_uint32(f)
        
        assert tex.size_x == size_x2
        assert tex.size_y == size_y2
        assert mipcount == mipcount2
        assert mipcount >= 1
        
        section = read_id(f)
        #print(section)
        size = read_uint32_le(f)
        #print(name, tex.format)
        if tex.fmt in ("P4", "P8"):
            assert section == PALLETE
            palette = BytesIO(f.read(size))
            num_colors = len(palette.getbuffer())//2  # Max 16 for P4 and max 256 for P8
            section = read_id(f)
            size = read_uint32_le(f)
            assert section == MIP
        else:
            palette = None 
            num_colors = 0
            assert section == MIP
        
        #tex.mipmaps.append(f.read(size))

        imagedata = BytesIO(f.read(size)+b"\x00"*256*256)
        
        #assert size == len(imagedata.getbuffer())
        mip = decode_image(
                        imagedata, palette, FORMAT[tex.fmt], PaletteFormat.RGB5A3, num_colors, 
                        tex.size_x, tex.size_y
                        )
        
        tex.mipmaps.append(mip)
        
        if mipcount > 1:
            assert log2(tex.size_x) % 1 == 0 and log2(tex.size_y) % 1 == 0

        if not ignoremips:
            for i in range(mipcount-1):
                section = read_id(f)
                size = read_uint32_le(f)
                assert section == MIP
                imagedata = BytesIO(f.read(size)+b"\x00"*256*256)
                mip_tex_x = max(tex.size_x//(2**(i+1)), 1)
                mip_tex_y = max(tex.size_y//(2**(i+1)), 1)
                #print(tex.size_x, mip_tex_x, tex.size_y, mip_tex_y)
                mip = decode_image(
                            imagedata, palette, FORMAT[tex.fmt], PaletteFormat.RGB5A3, num_colors,
                            mip_tex_x, mip_tex_y
                            )
                tex.mipmaps.append(mip)
        return tex 
        
        
class BW1Texture(Texture):
    def __init__(self, name):
        super().__init__(name)
        
        self.unkint1 = 1 
        self.unkint2 = 0 # 4, 12, 20
        self.fmt = "DXT1" 
        self.unkint3 = 0 
        self.unkint4 = 0
        self.unkint5 = 0 
        self.unkint6 = 0
        self.unkint7 = 0
        
        #self.mipcount = 0
        #self.size_x = 0
        #self.size_y = 0
        
        self.mipmaps = []
        #self.mipmaps_decoded = []
    
    def header_to_string(self):
        unkint7 = self.unkint7 
        if unkint7 == 0xFFFFFFFF:
            unkint7 = -1
        if len(self.mipmaps) > 1:
            values = ["MipMap", self.unkint2, self.unkint3, self.unkint4, self.unkint5, self.unkint6, unkint7]
        else:
            values = [self.unkint2, self.unkint3, self.unkint4, self.unkint5, self.unkint6, unkint7]
        
        return ".".join(str(x) for x in values)
    
    def header_from_string(self, string):
        values = string.split(".")
        if len(values) == 0:
            return 
            
        if values[0].lower() == "mipmap":
            values.pop(0)
        
        if len(values) < 6:
            return 
        
        try:
            values = [int(x) for x in values[:6]]
        except:
            raise RuntimeError("Non-number header values encountered:", values)
            
        if values[0] in (4100, 4108, 4116):
            valmap = {4100: 4, 4108: 12, 4116: 20}
            new = valmap[values[0]]
            print("BW2 values detected. Changing", values[0], "to", new)
            values[0] = new
            
        if values[0] not in (4, 12, 20): raise RuntimeError("Unknown value for value 1: {0}. Needs to be 4, 12 or 20.".format(values[0]))
        valuerange_assertion(values[1], 0, 255)
        valuerange_assertion(values[2], 0, 255)
        valuerange_assertion(values[3], 0, 255)
        valuerange_assertion(values[4], 0, 1024)
        valuerange_assertion(values[5], -1, 25)
        
        self.unkint2 = values[0]
        self.unkint3 = values[1]
        self.unkint4 = values[2]
        self.unkint5 = values[3]
        self.unkint6 = values[4]
        self.unkint7 = values[5]
        if self.unkint7 == -1:
            self.unkint7 = 0xFFFFFFFF
       
            
    @classmethod
    def from_path(cls, path, name, fmt, unkint2=None, unkint3=None, unkint4=None, unkint5=None, unkint6=None, unkint7=None, mipmaps=1, autogenmipmaps=False, mipmappaths = []):
        if unkint2 is None: unkint2 = FORMATDEFAULTSBW1[fmt][0]
        if unkint3 is None: unkint3 = FORMATDEFAULTSBW1[fmt][1]
        if unkint4 is None: unkint4 = FORMATDEFAULTSBW1[fmt][2]
        if unkint5 is None: unkint5 = FORMATDEFAULTSBW1[fmt][3]
        if unkint6 is None: unkint6 = FORMATDEFAULTSBW1[fmt][4]
        if unkint7 is None: unkint7 = FORMATDEFAULTSBW1[fmt][5]
        
        assert not (autogenmipmaps and mipmappaths)
        
        tex = cls(name)
        tex.fmt = fmt
        tex.unkint2 = unkint2
        tex.unkint3 = unkint3
        tex.unkint4 = unkint4
        tex.unkint5 = unkint5
        tex.unkint6 = unkint6
        tex.unkint7 = unkint7
        img = Image.open(path)
        tex.mipmaps.append(img)
        
        if autogenmipmaps:
            if log2(img.width) % 1 != 0 or log2(img.height) % 1 != 0:
                print("Warning: Cannot generate mipmaps for non-power of 2 texture. Skipping mipmap generation.")
            else:
                mipmap_count = int(log2(min(img.width, img.height)))
                mipmap_width = img.width 
                mipmap_height = img.height 
                
                for i in range(mipmap_count):
                    if i != 0:
                        mipmap_width //= 2
                        mipmap_height //= 2
                        mipmap_image = img.resize((mipmap_width, mipmap_height), Image.NEAREST)
                        tex.mipmaps.append(mipmap_image)
        return tex
    
    def write(self, f):
        start = f.tell()
        assert len(self.name) <= 0x10
        f.write(self.name.encode("ascii"))
        f.write(b"\x00"*(0x10 - len(self.name)))
        assert f.tell()-start == 0x10
        
        image = self.mipmaps[0]
        write_uint32_le(f, image.width)
        write_uint32_le(f, image.height)
        write_uint32_le(f, 1)
        write_uint32_le(f, self.unkint2)
        f.write(bytes(reversed(STRTOFORMAT[self.fmt])))
        f.write(b"A8R8G8B8")
        
        write_uint32_le(f, self.unkint3)
        write_uint32_le(f, self.unkint4)
        write_uint32_le(f, self.unkint5)
        write_uint32_le(f, self.unkint6)
        write_uint32_le(f, self.unkint7)
        f.write(b"\x00"*12)
        
        mipcount = len(self.mipmaps)
        write_uint32_le(f, mipcount)
        assert f.tell()-start == 0x54
        
        imgdata, palettedata, _ = encode_image(image, FORMAT[self.fmt], PaletteFormat.RGB5A3, mipmap_count=1)
        if self.fmt in ("P4", "P8"):
            write_id(f, PALLETE)
            write_uint32_le(f, 512)
            f.write(palettedata.getbuffer())
            f.write(b"\x00"*(512-len(palettedata.getbuffer())))
        
        write_id(f, MIP)
        write_uint32_le(f, len(imgdata.getbuffer()))
        f.write(imgdata.getbuffer())
        
        if len(self.mipmaps) > 1:
            for mipmap in self.mipmaps[1:]:
                imgdata, palettedata, _ = encode_image(mipmap, FORMAT[self.fmt], PaletteFormat.RGB5A3, mipmap_count=1)
                write_id(f, MIP)
                write_uint32_le(f, len(imgdata.getbuffer()))
                f.write(imgdata.getbuffer())
                
    @classmethod 
    def from_file(cls, f, ignoremips=False):
        name = f.read(0x10).rstrip(b"\x00").decode("ascii")
        tex = cls(name)
        assert len(name) <= 0x10
        tex.size_x = read_uint32_le(f)
        tex.size_y = read_uint32_le(f)

        tex.unkint1 = read_uint32_le(f)
        assert tex.unkint1 == 1
        tex.unkint2 = read_uint32_le(f)
        assert tex.unkint2 in (4, 12, 20)
        
        fmt = bytes(reversed(f.read(0x8)))
        assert fmt in FORMATTOSTR
        tex.fmt = FORMATTOSTR[fmt]
        
        outputformat = f.read(0x8)
        assert outputformat == b"A8R8G8B8"
        tex.unkint3 = read_uint32_le(f)
        tex.unkint4 = read_uint32_le(f)
        tex.unkint5 = read_uint32_le(f)
        tex.unkint6 = read_uint32_le(f)
        tex.unkint7 = read_uint32_le(f)
        
        assert tex.unkint3 <= 255 
        assert tex.unkint4 <= 255
        assert tex.unkint5 <= 255
        assert tex.unkint6 <= 1024 
        assert tex.unkint7 == 0xFFFFFFFF or 0 <= tex.unkint7 <= 25  # Only values up to 11 have been seen, using BW2 as limit
        
        pad = f.read(0xC)
        assert pad == b"\x00"*0xC
        mipcount = read_uint32_le(f)
        print(mipcount,"mips")
        section = read_id(f)
        assert section in (MIP, PALLETE)
        #print(section)
        size = read_uint32_le(f)
        #print(name, tex.format)
        
        if tex.fmt in ("P4", "P8"):
            assert section == PALLETE
            palette = BytesIO(f.read(size))
            num_colors = len(palette.getbuffer())//2  # Max 16 for P4 and max 256 for P8
            section = read_id(f)
            size = read_uint32_le(f)
            assert section == MIP
        else:
            palette = None 
            num_colors = 0
            assert section == MIP
 
        #tex.mipmaps.append(f.read(size))
        imagedata = BytesIO(f.read(size)+b"\x00"*256*256)
        
        #assert size == len(imagedata.getbuffer())
        #print(FORMAT[tex.fmt], hex(size), tex.size_x, tex.size_y)
        mip = decode_image(
                        imagedata, palette, FORMAT[tex.fmt], PaletteFormat.RGB5A3, num_colors, 
                        tex.size_x, tex.size_y
                        )
        
        tex.mipmaps.append(mip)
        
        if mipcount > 1:
            assert log2(tex.size_x) % 1 == 0 and log2(tex.size_y) % 1 == 0

        if not ignoremips:
            for i in range(mipcount-1):
                section = read_id(f)
                size = read_uint32_le(f)
                assert section == MIP
                imagedata = BytesIO(f.read(size)+b"\x00"*256*256)
                mip_tex_x = max(tex.size_x//(2**(i+1)), 1)
                mip_tex_y = max(tex.size_y//(2**(i+1)), 1)
                #print(tex.size_x, mip_tex_x, tex.size_y, mip_tex_y)
                mip = decode_image(
                            imagedata, palette, FORMAT[tex.fmt], PaletteFormat.RGB5A3, num_colors,
                            mip_tex_x, mip_tex_y
                            )
                tex.mipmaps.append(mip)
        return tex