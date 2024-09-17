import os
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
    def __init__(self, name, data):
        self.name = name
        self.data = data 
    
    @classmethod
    def from_file(cls, f):
        name = f.read(4)
        size = read_uint32(f)
        data = f.read(size)
        return cls(name, data)
    
    def write(self, f):
        f.write(self.name)
        write_uint32(f, len(self.data))
        f.write(self.data)
        

class LuaScript(Section):
    def __init__(self, name, script_name, data):
        super().__init__(name, data)
        self.script_name = script_name 
    
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
        return self.script_name+".luap"
    
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
        f.write(self.name)
        encoded_name = bytes(self.script_name, "ascii")
        write_uint32(f, len(self.data)+4+len(encoded_name))
        write_uint32(f, len(encoded_name))
        f.write(encoded_name)
        f.write(self.data)
        
    
ORDERLIST = [b"RXET", b"DNOS", b"LDOM", b"MINA", b"PRCS", b"FEQT"]
ORDER = {v: i for i,v in enumerate(ORDERLIST) }


class BattalionArchive(object):
    def __init__(self):
        self.sections = []
    
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
                else:
                    section = Section.from_file(f)
                arc.sections.append(section)
            else:
                break 
                
        return arc
    
    
    def write(self, f):
        for section in self.sections:
            section.write(f)

    def add_script(self, script: LuaScript):
        for sec in self.sections:
            if sec.name == b"PRCS" and sec.script_name == script.script_name:
                sec.data = script.data 
                break 
        else:
            self.sections.append(script)
            self.sections.sort(key=lambda x: ORDER[x.name])
    
    def delete_script(self, script_name):
        for i in range(len(self.sections)):
            sec = self.sections[i]
            if sec.name == b"PRCS" and sec.script_name == script_name:
                self.sections.pop(i)
                break
    
    def iter_sections(self, secname):
        for sec in self.sections:
            if sec.name == secname:
                yield sec 
    
    def scripts(self):
        yield from self.iter_sections(b"PRCS")
                
                
if __name__ == "__main__":
    with open("C1_Bonus_Level.res", "rb") as f:
        arc = BattalionArchive.from_file(f)
    with open("Test.res", "wb") as f:
        arc.write(f)
    for sec in arc.scripts():
        print(sec.name)
        if isinstance(sec, LuaScript):
            sec.dump_to_directory("test")
            fname = sec.create_file_name()
            newscript = LuaScript.from_filepath("test/"+fname)

        
    newscript = LuaScript.from_filepath("test/C1Bonus_BigBattle.luap")
    newscript.script_name = "DefinitelyNewScript"
    arc.add_script(newscript)
    arc.delete_script("C1Bonus_Encounter_WFgunships")
    with open("Test2.res", "wb") as f:
        arc.write(f)
    
    with open("Test2.res", "rb") as f:
        newarc = BattalionArchive.from_file(f)
    
    for sec in newarc.scripts():
        sec.dump_to_directory("test2")