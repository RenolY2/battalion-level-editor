import subprocess
import os
import io
import platform
import shutil
import sys
from io import BytesIO

import lib.lua.bwarchivelib as bwarchivelib
from widgets.editor_widgets import open_yesno_box
import gzip
import re
from hashlib import sha1

currpath = __file__
currdir = os.path.dirname(currpath)

JAVA_JRE_DIR = os.path.join(currdir, "jdk-21.0.5+11-jre")
LUAC_PATH = os.path.join(currdir, "luac5.0.2.exe")
LUADEC_PATH = os.path.join(currdir, "LuaDec.exe")
UNLUAC_PATH = os.path.join(currdir, "unluac.jar")
DECOMP_FIX_FOLDER = os.path.join(currdir, "lua_decomp_fixes")

# On Windows, try to use included java runtime
if platform.system() == "Windows":
    if os.path.exists(JAVA_JRE_DIR):
        JAVA = os.path.join(JAVA_JRE_DIR, "bin", "java.exe")
    else:
        JAVA = "java"
else:
    JAVA = "java"


def calc_script_hash(path):
    with open(path, "rb") as f:
        data = f.read()
        return sha1(data).digest()


DECOMP_FIXES = {}
script_fixes = os.listdir(DECOMP_FIX_FOLDER)
for filename in script_fixes:
    if "FIX_"+filename in script_fixes:
        orig_file = os.path.join(DECOMP_FIX_FOLDER, filename)
        fix_file = os.path.join(DECOMP_FIX_FOLDER, "FIX_"+filename)
        hash = calc_script_hash(os.path.join(DECOMP_FIX_FOLDER, filename))
        with open(fix_file, "rb") as f:
            DECOMP_FIXES[hash] = f.read()


def java_version():
    cmd = [JAVA, "-version"]
    print("Checking java version...")
    try:
        result = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        print("Java not found")
    else:
        print(
            str(result.stdout,
                encoding="ascii",
                errors="backslashreplace"))
        print(
            str(result.stderr,
                encoding="ascii",
                errors="backslashreplace"))


def decompile_luadec(path, out):
    with open(out, "wb") as f:
        result = subprocess.run([LUADEC_PATH, path], stdout=f)
    print(result)


def decompile_unluac(path, out):
    with open(out, "wb") as f:
        cmd = [JAVA, "-jar", UNLUAC_PATH, path]
        try:
            result = subprocess.run(cmd, stdout=f)
        except FileNotFoundError:
            raise RuntimeError("Couldn't execute command:\n {0}\nDo you have Java installed? (Recommended: Java 23/JDK 23, not Java 8!)".format(str(" ".join(cmd))))

    if result.returncode != 0:
        if result.stderr is not None:
            print(
                str(result.stderr,
                    encoding="ascii",
                    errors="backslashreplace"))
        raise RuntimeError("A decompiler error happened!\n{0}\nDo you have the correct version of Java installed? (Java 23/JDK 23, not Java 8!)".format(str(result)))


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

        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "RegisterReflectionId" in line:
                        match = reflect_regex.match(line)

                        name = match.group(1)
                        objectid = match.group(2)
                        self.reflection_ids[objectid] = name
        except FileNotFoundError:
            pass
    
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

    def name_usages(self, name):
        results = []
        for key, value in self.reflection_ids.items():
            if value == name:
                results.append(key)

        return results

    def set_name(self, id, name):
        self.reflection_ids[id] = name

    def delete_name(self, id):
        if id in self.reflection_ids:
            del self.reflection_ids[id]
        
        
class LuaWorkbench(object):
    def __init__(self, workdir):
        self.workdir = None
        self.tmp = None
        self.tmp_out = None
        self.entityinit = EntityInitialization()
        
        self.set_workdir(workdir)
        self.setup_workdir()
        
        self.last_file_change = {}

        java_version()

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

    def script_exists(self, script_name, withsuffix=False):
        # With suffix = name includes suffix
        if withsuffix:
            return os.path.exists(os.path.join(self.workdir, script_name))
        else:
            return os.path.exists(os.path.join(self.workdir, script_name+".lua"))

    def copy_script_into_workshop(self, scriptpath):
        base = os.path.basename(scriptpath)
        dest = os.path.join(self.workdir, base)

        try:
            shutil.copy(scriptpath, dest)
        except shutil.SameFileError:
            pass

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

        files_to_be_fixed = []

        for script in res.scripts():
            print("dumping", script.name)
            script.dump_to_directory(self.tmp)
            script_names.append(script.name)

        for script_name in script_names:
            print("decompiling", script_name)
            compiled_file = os.path.join(self.tmp, script_name + ".luap")
            decompiled_file = os.path.join(self.workdir, script_name + ".lua")
            decompile_unluac(compiled_file, decompiled_file)
            self.record_file_change(script_name)
            hash = calc_script_hash(decompiled_file)
            if hash in DECOMP_FIXES:
                files_to_be_fixed.append((decompiled_file, DECOMP_FIXES[hash]))

        if len(files_to_be_fixed) > 0:
            result = open_yesno_box("The following files are known to have been decompiled incorrectly:\n"
                                    +", ".join(os.path.basename(x[0]) for x in files_to_be_fixed),
                            "Do you want to replace them with fixed versions?", yes_default=True)

            if result:
                for fname, fix in files_to_be_fixed:
                    with open(fname, "wb") as f:
                        f.write(fix)

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
            self.record_file_change(script_name)

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
        self.record_file_change("EntityInitialise")

    def repack_scripts(self, res, scripts=[], delete_rest=True):
        script_sections = []
        for script_name in scripts+["EntityInitialise"]:
            print("compiling", script_name)
            compiled_file = os.path.join(self.tmp_out, script_name+".luap")
            decompiled_file = os.path.join(self.workdir, script_name+".lua")
            if not os.path.exists(compiled_file) or self.did_file_change(script_name):
                compile_lua(decompiled_file, compiled_file)
                self.record_file_change(script_name)
            else:
                print(script_name, "hasn't changed, compile skipped")
            
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

    def get_lua_script_path(self, script_name):
        return os.path.join(self.workdir, script_name+".lua")

    def get_lua_script_paths(self):
        result = []
        for fname in os.listdir(self.workdir):
            if fname.endswith(".lua") and fname.lower() != "__lua_context__.lua":
                lua_path = os.path.join(self.workdir, fname)
                result.append(lua_path)
        return result

    def current_scripts(self):
        result = []
        for fname in os.listdir(self.workdir):
            if fname.endswith(".lua") and fname.lower() != "__lua_context__.lua":
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