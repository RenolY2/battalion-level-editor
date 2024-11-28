import subprocess
import os
import io
import platform
import sys
from io import BytesIO

import lib.lua.bwarchivelib as bwarchivelib
import gzip
import re

currpath = __file__
currdir = os.path.dirname(currpath)


LUAC_PATH = os.path.join(currdir, "luac5.0.2.exe")
LUADEC_PATH = os.path.join(currdir, "LuaDec.exe")
UNLUAC_PATH = os.path.join(currdir, "unluac.jar")


def decompile_luadec(path, out):
    with open(out, "wb") as f:
        result = subprocess.run([LUADEC_PATH, path], stdout=f)
    print(result)



def decompile_unluac(path, out):
    with open(out, "wb") as f:
        cmd = ["java", "-jar", UNLUAC_PATH, path]
        try:
            result = subprocess.run(cmd, stdout=f)
        except FileNotFoundError:
            raise RuntimeError("Couldn't execute command:\n {0}\nDo you have Java installed?".format(str(" ".join(cmd))))
    
    if result.returncode != 0:
        raise RuntimeError("A decompiler error happened!\n{0}".format(str(result)))


def compile_lua(path, out):
    err = io.StringIO()
    result = subprocess.run([LUAC_PATH, "-o", out, path], capture_output=True)
    if result.returncode != 0:
        filename = os.path.basename(path)
        raise RuntimeError("A compiler error happened in script {0}:\n\n{1}".format(filename,
                                                                                    str(result.stderr,
                                                                                    encoding="ascii",
                                                                                    errors="backslashreplace")))


class EntityInitialization(object):
    def __init__(self):
        self.reflection_ids = {}
    
    def reset(self):
        self.reflection_ids = {}
    
    def read_initialization(self, path):
        self.reflection_ids = {}
        reflect_regex = re.compile(r"([0-9A-Za-z\._]+)\s*=\s*RegisterReflectionId\(\"(\d+)\"\)")
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if "RegisterReflectionId" in line:
                    match = reflect_regex.match(line)
                    
                    name = match.group(1)
                    objectid = match.group(2)
                    self.reflection_ids[objectid] = name
    
    def update_initialization(self, path, newpath):
        lines = []
        with open(path, "r") as f:
            for line in f:
                if "RegisterReflectionId" not in line:
                    lines.append(line)
                else:
                    break 
                    
        with open(newpath, "w") as f:
            for line in lines:
                f.write(line)
            
            for objectid, name in self.reflection_ids.items():
                f.write("{0} = RegisterReflectionId(\"{1}\")\n".format(name, objectid))
    
    def get_name(self, id):
        if id not in self.reflection_ids:
            return ""
        else:
            return self.reflection_ids[id]
    
    def set_name(self, id, name):
        self.reflection_ids[id] = name 
        
        
class LuaWorkbench(object):
    def __init__(self, workdir):
        self.workdir = None
        self.tmp = None
        self.tmp_out = None
        self.entityinit = EntityInitialization()
        
        self.set_workdir(workdir)
        self.setup_workdir()
        
        self.last_file_change = {}

    def reset(self):
        self.entityinit.reset()
        self.last_file_change = {}

    def setup_workdir(self):
        try:
            os.mkdir(self.workdir)
        except FileExistsError:
            pass 
            
        self.tmp = os.path.join(self.workdir, "tmp")
        
        try:
            os.mkdir(self.tmp)
        except FileExistsError:
            pass 
        
        self.tmp_out = os.path.join(self.workdir, "tmp_out")
        
        try:
            os.mkdir(self.tmp_out)
        except FileExistsError:
            pass 

    def script_exists(self, script_name):
        return os.path.exists(os.path.join(self.workdir, script_name+".lua"))

    def rename(self, old_name, new_name):
        oldpath = os.path.join(self.workdir, old_name+".lua")
        newpath = os.path.join(self.workdir, new_name+".lua")

        os.rename(oldpath, newpath)

    def create_empty_template(self, script_name):
        script_path = os.path.join(self.workdir, script_name+".lua")
        with open(script_path, "w") as f:
            f.write("function {0}(owner)\n".format(script_name))
            f.write("    \n")
            f.write("end")

    def create_empty_if_not_exist(self, script_name):
        if not self.script_exists(script_name):
            self.create_empty_template(script_name)

    def record_file_change(self, script_name):
        self.last_file_change[script_name] = os.stat(os.path.join(self.workdir, script_name+".lua")).st_mtime
    
    def did_file_change(self, script_name):
        curr = os.stat(os.path.join(self.workdir, script_name+".lua")).st_mtime
        if script_name not in self.last_file_change:
            return True 
        else:
            return self.last_file_change[script_name] != curr 
    
    def open_script(self, script_name):
        #subprocess.run(["start", os.path.join(self.workdir, script_name+".lua")])
        os.startfile(os.path.join(self.workdir, script_name+".lua"))
        
    def is_initialized(self):
        return os.path.exists(os.path.join(self.workdir, "EntityInitialise.lua"))

    def unpack_scripts_archive(self, res):
        script_names = []

        for script in res.scripts():
            print("dumping", script.name)
            script.dump_to_directory(self.tmp)
            script_names.append(script.name)

        for script_name in script_names:
            print("decompiling", script_name)
            compiled_file = os.path.join(self.tmp, script_name + ".luap")
            decompiled_file = os.path.join(self.workdir, script_name + ".lua")
            decompile_unluac(compiled_file, decompiled_file)

    def unpack_new_scripts(self, res):
        script_names = []

        for script in res.scripts():
            if not self.script_exists(script.name):
                print("dumping", script.name)
                script.dump_to_directory(self.tmp)
                script_names.append(script.name)

        for script_name in script_names:
            print("decompiling", script_name)
            compiled_file = os.path.join(self.tmp, script_name + ".luap")
            decompiled_file = os.path.join(self.workdir, script_name + ".lua")
            decompile_unluac(compiled_file, decompiled_file)

    def unpack_scripts(self, respath):
        if respath.endswith(".gz"):
            with gzip.open(respath, "rb") as f:
                res = bwarchivelib.BattalionArchive.from_file(f)
        else:
            with open(respath, "rb") as f:
                res = bwarchivelib.BattalionArchive.from_file(f)

        self.unpack_scripts_archive(res)
    
    def read_entity_initialization(self):
        self.entityinit.read_initialization(os.path.join(self.workdir, "EntityInitialise.lua"))
    
    def write_entity_initialization(self):
        self.entityinit.update_initialization(os.path.join(self.workdir, "EntityInitialise.lua"),
                                              os.path.join(self.workdir, "EntityInitialise.lua"))

    def repack_scripts(self, res, scripts=[], delete_rest=True):
        script_sections = []
        for script_name in scripts+["EntityInitialise"]:
            print("compiling", script_name)
            compiled_file = os.path.join(self.tmp_out, script_name+".luap")
            decompiled_file = os.path.join(self.workdir, script_name+".lua")
            compile_lua(decompiled_file, compiled_file)
            
            script_section = bwarchivelib.LuaScript.from_filepath(compiled_file)
            script_sections.append(script_section)
            
        if delete_rest:
            scripts = [x for x in res.scripts()]
            for script in scripts:
                print("deleting", script.name)
                res.delete_script(script.name)
            
        for script in script_sections:
            print("adding", script.name)
            res.add_script(script)

    def current_scripts(self):
        result = []
        for fname in os.listdir(self.workdir):
            if fname.endswith(".lua"):  
                result.append(fname.replace(".lua", ""))
        return result 

    def set_workdir(self, workdir):
        self.workdir = workdir


if __name__ == "__main__":  
    workbench = LuaWorkbench("TestLevel")
    print("Set up workbench")
    if not workbench.is_initialized():
        workbench.unpack_scripts("C1_Bonus_Level.res")
    print("unpacked scripts")
    workbench.repack_scripts("C1_Bonus_Level.res", "C1_Bonus_LevelNew.res", workbench.current_scripts())
    print("repacked scripts")
    
    print("are we init?", workbench.is_initialized())
    workbench.open_script("EntityInitialise")
    """bw1path = r"D:\Wii games\BattWars\BW1US\files\Data\CompoundFiles"
    bw2path = r"D:\Wii games\test\DATA\files\Data\CompoundFiles"
    
    for fname in os.listdir(bw1path):
        if fname.endswith(".res"):
            path = os.path.join(bw1path, fname)
            if os.path.isfile(path):
                print(path)
                workbench = LuaWorkbench(fname+"_lua")
                workbench.unpack_scripts(path)
    
    
    for fname in os.listdir(bw2path):
        if fname.endswith(".res") or  fname.endswith(".res.gz"):
            
            path = os.path.join(bw2path, fname)
            if os.path.isfile(path):
                print(path)
                workbench = LuaWorkbench(fname+"_lua")
                workbench.unpack_scripts(path)"""