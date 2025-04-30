import os
import gzip
from struct import unpack, pack


def read_uint32(fileobj):
    return unpack("I", fileobj.read(4))[0]


# read int as a big endian number
def read_uint32_BE(fileobj):
    return unpack(">I", fileobj.read(4))[0]


def unpack_uint32(data, offset):
    return unpack("I", data[offset:offset+4])[0]


def write_uint32(fileobj, val):
    fileobj.write(pack("I", val))
    
    
class Section(object):
    def __init__(self, secname, data):
        self.secname = secname
        self.data = data 
    
    @classmethod
    def from_file(cls, f):
        secname = f.read(4)
        size = read_uint32(f)
        data = f.read(size)
        return cls(secname, data)
    
    def write(self, f):
        f.write(self.secname)
        write_uint32(f, len(self.data))
        f.write(self.data)


class TextureArchive(Section):
    def __init__(self, name, level_name, textures, is_bw1):
        super().__init__(name, b"")
        self.level_name = level_name
        self.textures = textures
        self.is_bw1 = is_bw1

    @classmethod
    def from_file(cls, f):
        secname = f.read(4)
        size = read_uint32(f)
        name_length = read_uint32(f)
        level_name = f.read(name_length)

        subarchive_name = f.read(4)
        assert subarchive_name in (b"FTBG", b"FTBX")

        is_bw1 = subarchive_name == b"FTBX"

        subarchive_size = read_uint32(f)
        texcount = read_uint32(f)

        textures = []

        if is_bw1:
            for i in range(texcount):
                tex = TextureBW1.from_file(f)
                textures.append(tex)
        else:
            for i in range(texcount):
                tex = TextureBW2.from_file(f)
                textures.append(tex)

        return cls(secname, level_name, textures, is_bw1)

    def write(self, f):
        f.write(self.secname)
        archive_size = f.tell()
        write_uint32(f, 0xFFAABBCC)  # Placeholder
        write_uint32(f, len(self.level_name))
        f.write(self.level_name)

        if self.is_bw1:
            f.write(b"FTBX")
        else:
            f.write(b"FTBG")

        subarchive_size = f.tell()
        write_uint32(f, 0xFFAABBCC)
        write_uint32(f, len(self.textures))
        for tex in self.textures:
            tex.write(f)

        end = f.tell()
        f.seek(archive_size)
        write_uint32(f, end-(archive_size+4))
        f.seek(subarchive_size)
        write_uint32(f, end-(subarchive_size+4))
        f.seek(end)

    def get_texture(self, texname):
        for tex in self.textures:
            if tex.name.lower() == texname.lower():
                return tex
        return None


class TextureBW1(Section):
    def __init__(self, secname, texname, data):
        super().__init__(secname, b"")
        self.name = texname
        self.data = data

    @classmethod
    def from_file(cls, f):
        name = f.read(4)
        assert name == b"TXET"
        size = read_uint32(f)

        texname = str(f.read(0x10).strip(b"\x00"), encoding="ascii")
        data = f.read(size-0x10)

        return cls(name, texname, data)

    def dump_to_directory(self, dirpath):
        fname = self.name+".texture"
        encoded_name = bytes(self.name, "ascii").ljust(0x10, b"\x00")

        with open(os.path.join(dirpath, fname), "wb") as f:
            f.write(encoded_name)
            f.write(self.data)

    def dump_to_file(self, f):
        encoded_name = bytes(self.name, "ascii").ljust(0x10, b"\x00")
        f.write(encoded_name)
        f.write(self.data)

    @classmethod
    def from_filepath(cls, filepath):
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            f.read(0x10)
            data = f.read()

        return cls(b"TXET", fname.replace(".texture", ""), data)

    def write(self, f):
        f.write(self.secname)
        encoded_name = bytes(self.name, "ascii").ljust(0x10, b"\x00")
        assert len(encoded_name) <= 0x10
        write_uint32(f, 0x10+len(self.data))
        f.write(encoded_name)
        f.write(self.data)


class TextureBW2(Section):
    def __init__(self, secname, texname, data):
        super().__init__(secname, b"")
        self.name = texname
        self.data = data

    @classmethod
    def from_file(cls, f):
        name = f.read(4)
        assert name == b"DXTG"
        size = read_uint32(f)

        texname = str(f.read(0x20).strip(b"\x00"), encoding="ascii")
        data = f.read(size-0x20)

        return cls(name, texname, data)

    def dump_to_directory(self, dirpath):
        fname = self.name+".texture"
        encoded_name = bytes(self.name, "ascii").ljust(0x20, b"\x00")

        with open(os.path.join(dirpath, fname), "wb") as f:
            f.write(encoded_name)
            f.write(self.data)

    def dump_to_file(self, f):
        encoded_name = bytes(self.name, "ascii").ljust(0x20, b"\x00")
        f.write(encoded_name)
        f.write(self.data)

    @classmethod
    def from_filepath(cls, filepath):
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            f.read(0x20)
            data = f.read()

        return cls(b"DXTG", fname.replace(".texture", ""), data)

    def write(self, f):
        f.write(self.secname)
        encoded_name = bytes(self.name, "ascii").ljust(0x20, b"\x00")
        assert len(encoded_name) <= 0x20
        write_uint32(f, 0x20+len(self.data))
        f.write(encoded_name)
        f.write(self.data)


class SoundArchive(Section):
    def __init__(self, level_name, sounds):
        super().__init__(b"DNOS", b"")
        self.level_name = level_name
        self.sounds = sounds
        self._padding = 0

    @classmethod
    def from_file(cls, f):
        name = f.read(4)
        assert name == b"DNOS"
        totalsize = read_uint32(f)
        curr = f.tell()
        name_length = read_uint32(f)
        level_name = f.read(name_length)

        subarchive_name = f.read(4)
        assert subarchive_name == b"HFSB"
        size = read_uint32(f)
        assert size == 4
        soundcount = read_uint32(f)

        sounds = []

        for i in range(soundcount):
            sound = Sound.from_file(f)
            sounds.append(sound)

        # Skip padding
        f.seek(curr+totalsize)
        return cls(level_name, sounds)

    def write(self, f):
        f.write(b"DNOS")
        archive_size = f.tell()
        write_uint32(f, 0xFFAABBCC)  # Placeholder
        write_uint32(f, len(self.level_name))
        f.write(self.level_name)
        f.write(b"HFSB")
        write_uint32(f, 0x4)
        write_uint32(f, len(self.sounds))

        for sound in self.sounds:
            sound.write(f)

        if self._padding > 0:
            f.write(b"\x00"*self._padding)

        end = f.tell()
        f.seek(archive_size)
        write_uint32(f, end-(archive_size+4))
        f.seek(end)


class Sound(Section):
    def __init__(self, sound_name, data):
        super().__init__(b"HPSD", data)
        self.name = sound_name

    @classmethod
    def from_file(cls, f):
        secname = f.read(4)
        assert secname == b"HPSD"
        size = read_uint32(f)
        assert size == 0x20

        sound_name = str(f.read(size).strip(b"\x00"), encoding="ascii")

        secname = f.read(4)
        assert secname == b"DPSD"
        size = read_uint32(f)
        data = f.read(size)

        return cls(sound_name, data)

    def dump_to_directory(self, dirpath):
        fname = self.name+".adp"
        with open(os.path.join(dirpath, fname), "wb") as f:
            f.write(self.data)

    @classmethod
    def from_filepath(cls, filepath):
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            data = f.read()

        return cls(fname.replace(".adp", ""), data)

    def write(self, f):
        f.write(b"HPSD")
        write_uint32(f, 0x20)
        encoded_name = bytes(self.name, encoding="ascii").ljust(0x20, b"\x00")
        assert len(encoded_name) <= 0x20
        f.write(encoded_name)
        f.write(b"DPSD")
        write_uint32(f, len(self.data))
        f.write(self.data)


class Model(Section):
    def __init__(self, modelname, data):
        super().__init__(b"LDOM", b"")
        self.name = modelname
        self.data = data

    @classmethod
    def from_file(cls, f):
        name = f.read(4)
        assert name == b"LDOM"
        size = read_uint32(f)
        namelength = read_uint32(f)
        nm = f.read(namelength)
        modelname = str(nm, encoding="ascii")
        data = f.read(size-namelength-4)

        return cls(modelname, data)

    def dump_to_directory(self, dirpath):
        fname = self.name+".modl"
        with open(os.path.join(dirpath, fname), "wb") as f:
            f.write(self.data[8:])

    @classmethod
    def from_filepath(cls, filepath):
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            data = f.read()

        prefix = b"LDOM"+pack("I", len(data))

        return cls(fname.replace(".modl", ""), prefix+data)

    def write(self, f):
        f.write(b"LDOM")
        encoded_name = bytes(self.name, "ascii")
        write_uint32(f, 4+len(encoded_name)+len(self.data))
        write_uint32(f, len(encoded_name))
        f.write(encoded_name)
        f.write(self.data)


class Animation(Section):
    def __init__(self, animname, data):
        super().__init__(b"MINA", b"")
        self.name = animname
        self.data = data

    @classmethod
    def from_file(cls, f):
        secname = f.read(4)
        assert secname == b"MINA"
        size = read_uint32(f)
        namelenght = read_uint32(f)
        animname = str(f.read(namelenght), encoding="ascii")
        data = f.read(size-namelenght-4)

        return cls(animname, data)

    def dump_to_directory(self, dirpath):
        fname = self.name+".anim"
        with open(os.path.join(dirpath, fname), "wb") as f:
            f.write(self.data)

    @classmethod
    def from_filepath(cls, filepath):
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            data = f.read()

        return cls(fname.replace(".anim", ""), data)

    def write(self, f):
        f.write(b"MINA")
        encoded_name = bytes(self.name, "ascii")
        write_uint32(f, 4+len(encoded_name)+len(self.data))
        write_uint32(f, len(encoded_name))
        f.write(encoded_name)
        f.write(self.data)


class Effect(Section):
    def __init__(self, effect_name, data):
        super().__init__(b"FEQT", b"")
        self.name = effect_name
        self.data = data

    @classmethod
    def from_file(cls, f):
        name = f.read(4)
        assert name == b"FEQT"
        size = read_uint32(f)
        namelength = read_uint32(f)
        effect_name = str(f.read(namelength), encoding="ascii")
        data = f.read(size-namelength-4)

        return cls(effect_name, data)

    def dump_to_directory(self, dirpath):
        fname = self.name+".txt"
        with open(os.path.join(dirpath, fname), "wb") as f:
            f.write(self.data)

    @classmethod
    def from_filepath(cls, filepath):
        fname = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            data = f.read()

        return cls(fname.replace(".txt", ""), data)

    def write(self, f):
        f.write(b"FEQT")
        encoded_name = bytes(self.name, "ascii")
        write_uint32(f, 4+len(encoded_name)+len(self.data))
        write_uint32(f, len(encoded_name))
        f.write(encoded_name)
        f.write(self.data)


class LuaScript(Section):
    def __init__(self, name, script_name, data):
        super().__init__(name, data)
        self.name = script_name
    
    @classmethod
    def from_file(cls, f):
        name = f.read(4)
        assert name == b"PRCS"
        size = read_uint32(f)
        name_length = read_uint32(f)
        script_name = str(f.read(name_length), encoding="ascii")
        data = f.read(size-4-name_length)
        
        return cls(name, script_name, data)
    
    def create_file_name(self):
        return self.name+".luap"
    
    def dump_to_directory(self, dirpath):
        with open(os.path.join(dirpath, self.create_file_name()), "wb") as f:
            f.write(self.data)
    
    @classmethod
    def from_filepath(cls, path):
        assert path.endswith(".luap")
        basename = os.path.basename(path)
        script_name = basename.replace(".luap", "")
        with open(path, "rb") as f:
            data = f.read()
            
        return cls(b"PRCS", script_name, data)
    
    def write(self, f):
        f.write(self.secname)
        encoded_name = bytes(self.name, "ascii")
        write_uint32(f, len(self.data)+4+len(encoded_name))
        write_uint32(f, len(encoded_name))
        f.write(encoded_name)
        f.write(self.data)
        
    
ORDERLIST = [b"RXET", b"DNOS", b"LDOM", b"MINA", b"PRCS", b"FEQT"]
ORDER = {v: i for i,v in enumerate(ORDERLIST)}


class BattalionArchive(object):
    def __init__(self):
        self.sections = []
        self.textures = None
        self.sounds = None
    
    @classmethod
    def from_file(cls, f):
        arc = cls()
        while True:
            curr = f.tell()
            peek = f.read(4)
            if len(peek) == 4:
                f.seek(curr)
                if peek == b"PRCS":
                    section = LuaScript.from_file(f)
                elif peek == b"RXET":
                    section = TextureArchive.from_file(f)
                    arc.textures = section
                elif peek == b"DNOS":
                    section = SoundArchive.from_file(f)
                    arc.sounds = section
                elif peek == b"LDOM":
                    section = Model.from_file(f)
                elif peek == b"MINA":
                    section = Animation.from_file(f)
                elif peek == b"FEQT":
                    section = Effect.from_file(f)
                    if section.name == "__PADDING__":
                        continue
                else:
                    section = Section.from_file(f)
                arc.sections.append(section)
            else:
                break 
                
        return arc
    
    def write(self, f):
        self.sort_sections()
        for section in self.sections:
            section.write(f)

    def add_script(self, script: LuaScript):
        for sec in self.sections:
            if sec.secname == b"PRCS" and sec.name == script.name:
                sec.data = script.data 
                break 
        else:
            self.sections.append(script)
            self.sections.sort(key=lambda x: ORDER[x.secname])
    
    def delete_script(self, script_name):
        for i in range(len(self.sections)):
            sec = self.sections[i]
            if sec.secname == b"PRCS" and sec.name == script_name:
                self.sections.pop(i)
                break

    def get_script(self, script_name):
        for i in range(len(self.sections)):
            sec = self.sections[i]
            if sec.secname == b"PRCS" and sec.name == script_name:
                return self.sections[i]
        return None
    
    def iter_sections(self, secname):
        for sec in self.sections:
            if sec.secname == secname:
                yield sec 
    
    def scripts(self):
        yield from self.iter_sections(b"PRCS")

    def models(self):
        yield from self.iter_sections(b"LDOM")

    def animations(self):
        yield from self.iter_sections(b"MINA")

    def effects(self):
        yield from self.iter_sections(b"FEQT")

    def _get_resource_list(self, restype):
        resource_list = None
        if restype in (b"DXTG", b"TXET"):
            resource_list = self.textures.textures
        elif restype in (b"HFSB", b"HPSD"):
            resource_list = self.sounds.sounds
        elif restype == b"MINA":
            resource_list = self.animations()
        elif restype == b"LDOM":
            resource_list = self.models()
        elif restype == b"FEQT":
            resource_list = self.effects()

        return resource_list

    def resource_exists(self, restype, resname):
        resource_list = self._get_resource_list(restype)

        for res in resource_list:
            if res.secname == restype and res.name.lower() == resname.lower():
                return True
        return False

    def get_resource(self, restype, resname):
        resource_list = self._get_resource_list(restype)
        for res in resource_list:
            if res.secname == restype and res.name.lower() == resname.lower():
                return res

        return None

    def add_resource(self, resource):
        if isinstance(resource, TextureBW1):
            assert self.textures.is_bw1
            self.textures.textures.append(resource)
        elif isinstance(resource, TextureBW2):
            assert not self.textures.is_bw1
            self.textures.textures.append(resource)
        elif isinstance(resource, Sound):
            self.sounds.sounds.append(resource)
        elif isinstance(resource, (Model, Animation, Effect)):
            self.sections.append(resource)

    def delete_resource(self, resource):
        if isinstance(resource, TextureBW1):
            assert self.textures.is_bw1
            self.textures.textures.remove(resource)
        elif isinstance(resource, TextureBW2):
            assert not self.textures.is_bw1
            self.textures.textures.remove(resource)
        elif isinstance(resource, Sound):
            self.sounds.sounds.remove(resource)
        elif isinstance(resource, (Model, Animation, Effect)):
            self.sections.remove(resource)

    def sort_sections(self):
        self.sections.sort(key=lambda x: ORDER[x.secname])

    def set_additional_padding(self, padding):
        padding_res = self.get_resource(b"FEQT", "__PADDING__")

        if padding_res is not None and padding == 0:
            self.delete_resource(padding_res)
        elif padding > 0:
            if padding_res is not None:
                padding_res.data = b" "*padding
            else:
                padding_res = Effect("__PADDING__", b" "*padding)
                self.add_resource(padding_res)
                self.sort_sections()


if __name__ == "__main__":
    with open("C1_Bonus_Level.res", "rb") as f:
        arc = BattalionArchive.from_file(f)

    arc.set_additional_padding(10000)

    for x in arc.sounds.sounds:
        print(x.name)
        x.dump_to_directory("restest")
        newx = Sound.from_filepath("restest/"+x.name+".adp")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.textures.textures:
        print(x.name)
        x.dump_to_directory("restest")
        newx = TextureBW1.from_filepath("restest/" + x.name + ".texture")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.models():
        print(x.name)
        x.dump_to_directory("restest")

        newx = Model.from_filepath("restest/" + x.name + ".modl")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.animations():
        x.dump_to_directory("restest")
        print(x.name)
        newx = Animation.from_filepath("restest/" + x.name + ".anim")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.effects():
        x.dump_to_directory("restest")
        print(x.name)
        newx = Effect.from_filepath("restest/" + x.name + ".txt")
        assert x.name == newx.name
        assert x.data == newx.data

    with open("C1_Bonus_LevelNew.res", "wb") as f:
        arc.write(f)

    with open("C1_Bonus_LevelNew.res", "rb") as f:
        newarc = BattalionArchive.from_file(f)

    for sec in newarc.sections:
        print(sec.secname)

    with open("C1_Bonus_LevelNew2.res", "wb") as f:
        newarc.write(f)

    with gzip.open("MP4_Level.res.gz", "rb") as f:
        arc = BattalionArchive.from_file(f)

    for x in arc.sounds.sounds:
        print(x.name)
        x.dump_to_directory("restest")
        newx = Sound.from_filepath("restest/"+x.name+".adp")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.textures.textures:
        print(x.name)
        x.dump_to_directory("restest")
        newx = TextureBW2.from_filepath("restest/" + x.name + ".texture")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.models():
        print(x.name)
        x.dump_to_directory("restest")

        newx = Model.from_filepath("restest/" + x.name + ".modl")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.animations():
        x.dump_to_directory("restest")
        print(x.name)
        newx = Animation.from_filepath("restest/" + x.name + ".anim")
        assert x.name == newx.name
        assert x.data == newx.data

    for x in arc.effects():
        x.dump_to_directory("restest")
        print(x.name)
        newx = Effect.from_filepath("restest/" + x.name + ".txt")
        assert x.name == newx.name
        assert x.data == newx.data

    with open("MP4_LevelNew.res", "wb") as f:
        arc.write(f)

    with open("MP4_LevelNew.res", "rb") as f:
        newarc = BattalionArchive.from_file(f)

    """with open("Test.res", "wb") as f:
        arc.write(f)
    for sec in arc.scripts():
        print(sec.name)
        if isinstance(sec, LuaScript):
            sec.dump_to_directory("test")
            fname = sec.create_file_name()
            newscript = LuaScript.from_filepath("test/"+fname)

        
    newscript = LuaScript.from_filepath("test/C1Bonus_BigBattle.luap")
    newscript.name = "DefinitelyNewScript"
    arc.add_script(newscript)
    arc.delete_script("C1Bonus_Encounter_WFgunships")
    with open("Test2.res", "wb") as f:
        arc.write(f)
    
    with open("Test2.res", "rb") as f:
        newarc = BattalionArchive.from_file(f)
    
    for sec in newarc.scripts():
        sec.dump_to_directory("test2")"""