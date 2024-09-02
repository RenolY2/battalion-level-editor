
import io
import struct


from .helper import unpack_uint32
from .bw_archive_base import BWArchiveBase, BWSection, BWResource



class ArchiveHeader(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"RXET"
        strlength = unpack_uint32(memview, offset=0)
        offset = 4 + strlength

        super().__init__(name, size, memview, section_offset=offset)

        self.filename = self._header[4:4+strlength]

    def pack(self):
        # If the filename changed size, we have to resize the header
        if len(self.filename) != len(self._header) - 4:
            data = io.BytesIO()
            data.write(struct.pack("I", len(self.filename)))
            data.write(self.filename)
            self._header = data.getvalue()

            data.close()
        else:

            self._header[4:4+len(self.filename)] = self.filename

        return super().pack()


class TextureSection(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"FTBX"
        super().__init__(name, size, memview, section_offset=4)

    def pack(self):
        texture_count = len(self.entries)

        self._header[0:4] = struct.pack("I", texture_count)

        return super().pack()


class TextureSectionBW2(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"FTBG"
        super().__init__(name, size, memview, section_offset=4)

    def pack(self):
        texture_count = len(self.entries)

        self._header[0:4] = struct.pack("I", texture_count)

        return super().pack()


class TextureEntry(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"TXET"

        super().__init__(name, size, memview, section_offset=0x54)

        self.res_name = self._header[0x00:0x10]
        self.width = unpack_uint32(self._header, 0x10)
        self.height = unpack_uint32(self._header, 0x14)

        self.unknown1 = unpack_uint32(self._header, 0x18)
        self.unknown2 = unpack_uint32(self._header, 0x1C)

        self.tex_type = self._header[0x20:0x28]
        self.draw_type = self._header[0x28:0x30] # draw type is usually A8R8G8B8 in BW1

        self.unknowns = [unpack_uint32(self._header, 0x30+i*4) for i in range(8)]

    def pack(self):
        #print(bytes(self.res_name))
        self._header[0x00:0x10] = bytes(self.res_name).ljust(16, b"\x00")

        self._header[0x10:0x20] = struct.pack(
            "I"*4, self.width, self.height, self.unknown1, self.unknown2
        )

        self._header[0x20:0x28] = bytes(self.tex_type).ljust(8, b"\x00")
        self._header[0x28:0x30] = bytes(self.draw_type).ljust(8, b"\x00")

        self._header[0x30:0x50] = struct.pack("I"*8, *self.unknowns)
        #print(self.image_sections, len(self.entries), bytes(self.tex_type), bytes(self.draw_type))

        # P8 is a image format with a palette, so the amount of image entries is the amount of entries minus 1
        # due to one of the entries being the palette data (LAP), which doesn't count as an image.
        if self.tex_type == b"P8" + b"\x00"*6:
            image_sections = len(self.entries) - 1
        else:
            image_sections = len(self.entries)

        self._header[0x50:0x54] = struct.pack("I", image_sections)
        return super().pack()

    def get_format(self):
        return bytes(self.tex_type).rstrip(b"\x00")


class TextureEntryBW2(BWResource):
    def __init__(self, name, size, memview):
        assert name == b"DXTG"

        super().__init__(name, size, memview)#, section_offset=0x54)

        self.res_name = self.data[0:0x20]#self._header[0:0x16]

    """def pack(self):
        data = io.BytesIO()
        data.write(struct.pack("I", len(self.res_name)))
        data.write(self.res_name)
        data.write(self.image_data)
        self._header = data.getvalue()

        data.close()

        return super().pack()
"""

class SoundSection(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"DNOS"
        strlength = unpack_uint32(memview, offset=0)
        offset = 4 + strlength

        super().__init__(name, size, memview, section_offset=offset)

        self.filename = self._header[4:4+strlength]

    def pack(self):
        # If the filename changed size, we have to resize the header
        if len(self.filename) != len(self._header) - 4:
            data = io.BytesIO()
            data.write(struct.pack("I", len(self.filename)))
            data.write(self.filename)
            self._header = data.getvalue()

            data.close()
        else:

            self._header[4:4+len(self.filename)] = self.filename


        return super().pack()


class SoundCount(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"HFSB"
        super().__init__(name, size, memview, section_offset=4)

        self.count = unpack_uint32(self._header, 0x00)

    def pack(self):
        self._header[0x00:0x04] = struct.pack("I", self.count)

        return super().pack()


class SoundName(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"HPSD"
        super().__init__(name, size, memview, section_offset=0x20)

        self.res_name = self._header[0:0x20]

    def pack(self):
        self._header[0:0x20] = self.res_name

        return super().pack()


class ParticleEntry(BWResource):
    def __init__(self, name, size, memview):
        assert name == b"FEQT"
        super().__init__(name, size, memview)

        strlength = unpack_uint32(self._data, 0)
        self.res_name = self._data[4:4+strlength]
        self.particle_data = self._data[4+strlength:]

    def pack(self):
        self._fileobj = io.BytesIO()
        self._fileobj.write(struct.pack("I", len(self.res_name)))
        self._fileobj.write(self.res_name)
        self._fileobj.write(self.particle_data)

        self._data = self._fileobj.getbuffer()

        return super().pack()


class AnimationEntry(BWResource):
    def __init__(self, name, size, memview):
        assert name == b"MINA"
        super().__init__(name, size, memview)

        strlength = unpack_uint32(self._data, 0)
        self.res_name = self._data[4:4+strlength]
        self.animation_data = self._data[4+strlength:]

        #print(bytes(self.animation_name))

    def pack(self):
        self._fileobj = io.BytesIO()
        self._fileobj.write(struct.pack("I", len(self.res_name)))
        self._fileobj.write(self.res_name)
        self._fileobj.write(self.animation_data)

        self._data = self._fileobj.getbuffer()

        return super().pack()


class ModelSection(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"LDOM"
        strlength = unpack_uint32(memview, 0)
        super().__init__(name, size, memview, section_offset=4+strlength)

        assert self.entries[0].name == b"LDOM" and len(self.entries) == 1
        #self.entries[0] = self.modeldata = self.entries[0].as_section(cls=ModelSubsection)

        self.res_name = self._header[4:4+strlength]

    def pack(self):
        newheader = io.BytesIO()
        newheader.write(struct.pack("I", len(self.res_name)))
        newheader.write(self.res_name)

        self._header = newheader.getvalue()
        newheader.close()

        return super().pack()

"""
class ModelSubsection(BWSection):
    def __init__(self, name, size, memview):
        assert name == b"LDOM"
        super().__init__(name, size, memview, section_offset=0x18)
"""

class ScriptEntry(BWResource):
    def __init__(self, name, size, memview):
        super().__init__(name, size, memview)
        strlength = unpack_uint32(self._data, 0)
        self.res_name = self._data[4:4+strlength]
        self.script_data = self._data[4+strlength:]

    def pack(self):
        self._fileobj = io.BytesIO()
        self._fileobj.write(struct.pack("I", len(self.res_name)))
        self._fileobj.write(self.res_name)
        self._fileobj.write(self.script_data)

        self._data = self._fileobj.getbuffer()

        return super().pack()


class BWArchive(BWArchiveBase):
    def __init__(self, f):
        super().__init__(f)

        is_bw1 = True


        # Unpack RXET into an object containing other resources
        assert self.entries[0].name == b"RXET"
        self.entries[0] = self.rxet = self.entries[0].as_section(cls=ArchiveHeader)
        assert len(self.rxet.entries) == 1

        assert self.rxet.entries[0].name in (b"FTBX", b"FTBG")
        is_bw1 = (self.rxet.entries[0].name == b"FTBX")

        if is_bw1:
            self.rxet.entries[0] = self.ftb = self.rxet.entries[0].as_section(cls=TextureSection)
        else:
            self.rxet.entries[0] = self.ftb = self.rxet.entries[0].as_section(cls=TextureSectionBW2)

        for i in range(len(self.ftb.entries)):
            if is_bw1:
                self.ftb.entries[i] = self.ftb.entries[i].as_section(cls=TextureEntry)
            else:
                self.ftb.entries[i] = self.ftb.entries[i].as_section(cls=TextureEntryBW2)
            #else:
            #    raise RuntimeError("Unknown image entry name:", self.ftb.entries[i].name)

        assert self.entries[1].name == b"DNOS"
        self.entries[1] = self.dnos = self.entries[1].as_section(cls=SoundSection)

        assert self.dnos.entries[0].name == b"HFSB"
        self.dnos.entries[0] = self.hfsb = self.dnos.entries[0].as_section(cls=SoundCount)

        for i in range(1, len(self.dnos.entries)):
            assert self.dnos.entries[i].name in (b"HPSD", b"DPSD")

            if self.dnos.entries[i].name == b"HPSD":
                assert self.dnos.entries[i+1].name == b"DPSD"
                self.dnos.entries[i] = self.dnos.entries[i].as_section(cls=SoundName)

        for i, entry in enumerate(self.entries):
            if entry.name == b"FEQT":
                self.entries[i] = self.entries[i].as_section(cls=ParticleEntry)
            elif entry.name == b"MINA":
                self.entries[i] = self.entries[i].as_section(cls=AnimationEntry)
            elif entry.name == b"LDOM":
                self.entries[i] = self.entries[i].as_section(cls=ModelSection)
            elif entry.name == b"PRCS":
                self.entries[i] = self.entries[i].as_section(cls=ScriptEntry)

        self.sounds = [(self.dnos.entries[i], self.dnos.entries[i+1]) for i in range(1, len(self.dnos.entries), 2)]
        self.models = [x for x in filter(lambda k: k.name == b"LDOM", self.entries)]
        self.animations = [x for x in filter(lambda k: k.name == b"MINA", self.entries)]
        self.effects = [x for x in filter(lambda k: k.name == b"FEQT", self.entries)]
        self.scripts = [x for x in filter(lambda k: k.name == b"PRCS", self.entries)]
        self.textures = [x for x in self.ftb.entries]
        self.game = self.get_game()
        """for nameentry, dataentry in self.models:
            print(bytes(nameentry.modelname))
        print(self.dnos.entries[0].count)
        print((len(self.dnos.entries)-1)/2.0)"""

    """def add_model(self, model):
        found = False
        end = False
        for i, entry in enumerate(self.entries):
            if entry.name == b"LDOM" and found is False:
                #self.entries.insert(i, model)
                found = True
            elif entry.name != b"LDOM" and found is True:
                end = True
                self.entries.insert(i, model)
                break

        if end is False:
            raise RuntimeError("Malformed res archive?")
        #self.entries.append(model)"""

    # All resources have
    def get_resource(self, restype, name):
        name = name.upper()
        if restype == "sSampleResource":
            reslist = self.sounds

            for res, res_data in reslist:
                if bytes(res.res_name).strip(b"\x00").upper() == name:
                    return res, res_data
            return None

        elif restype == "cTequilaEffectResource":
            reslist = self.effects
        elif restype == "cNodeHierarchyResource":
            reslist = self.models
        elif restype == "cTextureResource":
            reslist = self.textures
        else:
            raise RuntimeError("Unknown resoure type: {0}".format(restype))

        for i, res in enumerate(reslist):
            #print(bytes(res.res_name).strip(b"\x00").upper(), name,bytes(res.res_name).strip(b"\x00").upper() == name)
            #if hasattr(res, "res_name"):
                #print("Comparing:", bytes(res.res_name).strip(b"\x00").upper(), name)
            if hasattr(res, "res_name") and bytes(res.res_name).strip(b"\x00").upper() == name:
                print("found", name, "at position", i)
                return res

        return None

    def pack(self):
        # Adjust the amount of models in case models were taken away or added.
        # Every model has a HPSD entry and a DPSD entry in the DNOS section.
        self.hfsb.count = (len(self.dnos.entries) - 1) // 2

        return super().pack()

    def get_game(self):
        result = None
        if self.ftb.entries[0].name != b"DXTG":
            result = "BW1"
        else:
            if b"RPIM" in bytes(self.textures[0].data):
                result = "AQ"
            else:
                result = "BW2"
        return result


    def is_bw2(self):
        return self.ftb.entries[0].name == b"DXTG"

    def is_bw(self):
        return not self.is_bw2()


class BW1Archive(BWArchive):
    def __init__(self, f):
        super().__init__(f)

        assert self.is_bw() is True


class BW2Archive(BWArchive):
    def __init__(self, f):
        super().__init__(f)

        assert self.is_bw() is True



def get_rxet_size(header):
    return 4 + unpack_uint32(header, 0)

def get_ftb_size(header):
    return 4