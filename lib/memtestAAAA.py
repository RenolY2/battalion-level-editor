import ctypes
import struct
from ctypes import wintypes, sizeof, addressof, POINTER, pointer
from ctypes.wintypes import DWORD, ULONG, LONG, WORD

# Various Windows structs/enums needed for operation
NULL = 0

TH32CS_SNAPHEAPLIST = 0x00000001
TH32CS_SNAPPROCESS  = 0x00000002
TH32CS_SNAPTHREAD   = 0x00000004
TH32CS_SNAPMODULE   = 0x00000008
TH32CS_SNAPALL      = TH32CS_SNAPHEAPLIST | TH32CS_SNAPPROCESS | TH32CS_SNAPTHREAD | TH32CS_SNAPMODULE
assert TH32CS_SNAPALL == 0xF


PROCESS_QUERY_INFORMATION   = 0x0400
PROCESS_VM_OPERATION        = 0x0008
PROCESS_VM_READ             = 0x0010
PROCESS_VM_WRITE            = 0x0020

MEM_MAPPED = 0x40000

ULONG_PTR = ctypes.c_ulonglong

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [ ( 'dwSize' , DWORD ) ,
                 ( 'cntUsage' , DWORD) ,
                 ( 'th32ProcessID' , DWORD) ,
                 ( 'th32DefaultHeapID' , ctypes.POINTER(ULONG)) ,
                 ( 'th32ModuleID' , DWORD) ,
                 ( 'cntThreads' , DWORD) ,
                 ( 'th32ParentProcessID' , DWORD) ,
                 ( 'pcPriClassBase' , LONG) ,
                 ( 'dwFlags' , DWORD) ,
                 ( 'szExeFile' , ctypes.c_char * 260 ) ]
                 
                 
class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [    ( 'BaseAddress' , ctypes.c_void_p),
                    ( 'AllocationBase' , ctypes.c_void_p),
                    ( 'AllocationProtect' , DWORD),
                    ( 'PartitionID' , WORD),
                    ( 'RegionSize' , ctypes.c_size_t),
                    ( 'State' , DWORD),
                    ( 'Protect' , DWORD),
                    ( 'Type' , DWORD)]
 
 
class PSAPI_WORKING_SET_EX_BLOCK(ctypes.Structure):
    _fields_ = [    ( 'Flags', ULONG_PTR),
                    ( 'Valid', ULONG_PTR),
                    ( 'ShareCount', ULONG_PTR),
                    ( 'Win32Protection', ULONG_PTR),
                    ( 'Shared', ULONG_PTR),
                    ( 'Node', ULONG_PTR),
                    ( 'Locked', ULONG_PTR),
                    ( 'LargePage', ULONG_PTR),
                    ( 'Reserved', ULONG_PTR),
                    ( 'Bad', ULONG_PTR),
                    ( 'ReservedUlong', ULONG_PTR)]
                    
                    
#class PSAPI_WORKING_SET_EX_INFORMATION(ctypes.Structure):
#    _fields_ = [    ( 'VirtualAddress' , ctypes.c_void_p),
#                    ( 'VirtualAttributes' , PSAPI_WORKING_SET_EX_BLOCK)]

class PSAPI_WORKING_SET_EX_INFORMATION(ctypes.Structure):
    _fields_ = [    ( 'VirtualAddress' , ctypes.c_void_p),
                    #( 'Flags', ULONG_PTR),
                    ( 'Valid', ULONG_PTR, 1)]
                    #( 'ShareCount', ULONG_PTR),
                    #( 'Win32Protection', ULONG_PTR),
                    #( 'Shared', ULONG_PTR),
                    #( 'Node', ULONG_PTR),
                    #( 'Locked', ULONG_PTR),
                    #( 'LargePage', ULONG_PTR),
                    #( 'Reserved', ULONG_PTR),
                    #( 'Bad', ULONG_PTR),
                    #( 'ReservedUlong', ULONG_PTR)]
                    
    #def print_values(self):
    #    for i,v in self._fields_:
    #        print(i, getattr(self, i))


# The following code is a port of aldelaro5's Dolphin memory access methods 
# for Windows into Python+ctypes.
# https://github.com/aldelaro5/Dolphin-memory-engine

"""
MIT License

Copyright (c) 2017 aldelaro5

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

class Dolphin(object):
    def __init__(self):
        self.pid = -1
        self.handle = -1
        
        self.address_start = 0
        self.mem1_start = 0
        self.mem2_start = 0
        self.mem2_exists = False

    def reset(self):
        self.pid = -1
        self.handle = -1

        self.address_start = 0
        self.mem1_start = 0
        self.mem2_start = 0
        self.mem2_exists = False

    def find_dolphin(self):
        entry = PROCESSENTRY32()
        
        entry.dwSize = sizeof(PROCESSENTRY32)
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, NULL)
        print(addressof(entry), hex(addressof(entry)))
        a = ULONG(addressof(entry))
        
        self.pid = -1
        self.handle = -1
        
        if ctypes.windll.kernel32.Process32First(snapshot, pointer(entry)):
            if entry.szExeFile in (b"Dolphin.exe", b"DolphinQt2.exe", b"DolphinWx.exe"):
                self.pid = entry.th32ProcessID 
            else:
                while ctypes.windll.kernel32.Process32Next(snapshot, pointer(entry)):
                    if entry.szExeFile in (b"Dolphin.exe", b"DolphinQt2.exe", b"DolphinWx.exe"):
                        self.pid = entry.th32ProcessID 
                
            
        ctypes.windll.kernel32.CloseHandle(snapshot)
        
        if self.pid == -1:
            return False 
        
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE,
            False, self.pid)
        
        return True
    
    def get_emu_info(self):
        info = MEMORY_BASIC_INFORMATION()
        MEM1_found = False
        
        p = NULL
        
        while ctypes.windll.kernel32.VirtualQueryEx(self.handle, ctypes.c_void_p(p), pointer(info), sizeof(info)) == sizeof(info):
            
            p += info.RegionSize 
            
            if info.RegionSize == 0x4000000:
                region_base_address = info.BaseAddress
                
                if MEM1_found and info.BaseAddress > self.address_start + 0x10000000:
                    break 
                
                page_info = PSAPI_WORKING_SET_EX_INFORMATION()
                page_info.VirtualAddress = info.BaseAddress
                
                if ctypes.windll.psapi.QueryWorkingSetEx(
                        self.handle,    
                        pointer(page_info), 
                        sizeof(PSAPI_WORKING_SET_EX_INFORMATION)
                ):
                    if (page_info.Valid):
                        self.mem2_start = region_base_address
                        self.mem2_exists = True 
                        
            elif not MEM1_found and info.RegionSize == 0x2000000 and info.Type == MEM_MAPPED:
                page_info = PSAPI_WORKING_SET_EX_INFORMATION()
                page_info.VirtualAddress = info.BaseAddress
                
                if ctypes.windll.psapi.QueryWorkingSetEx(
                    self.handle, 
                    pointer(page_info), 
                    sizeof(PSAPI_WORKING_SET_EX_INFORMATION)
                ):
                    print(page_info.Valid)
                    if (page_info.Valid):
                        self.address_start = info.BaseAddress
                        MEM1_found = True 
                
            if MEM1_found and self.mem2_exists:
                break 
        
        if self.address_start == 0:
            return False 
        
        return True
    
    def read_ram(self, offset, size):
        buffer = (ctypes.c_char*size)()
        read = ctypes.c_ulong(0)
        
        result = ctypes.windll.kernel32.ReadProcessMemory(
            self.handle, 
            ctypes.c_void_p(self.address_start+offset), 
            ctypes.pointer(buffer),
            size,
            ctypes.pointer(read))
        return result and read.value == size, buffer
    
    def write_ram(self, offset, data):
        buffer = (ctypes.c_char*len(data))(*data)
        read = ctypes.c_ulong(0)
        
        result = ctypes.windll.kernel32.WriteProcessMemory(
            self.handle, 
            ctypes.c_void_p(self.address_start+offset), 
            ctypes.pointer(buffer),
            len(data),
            ctypes.pointer(read))
        
        return result and read.value == len(data)
    
    def read_uint32(self, addr):
        assert addr >= 0x80000000
        success, value = self.read_ram(addr-0x80000000, 4)

        if success:
            return struct.unpack(">I", value)[0]
        else:
            return None

    def read_float(self, addr):
        assert addr >= 0x80000000
        success, value = self.read_ram(addr - 0x80000000, 4)

        if success:
            return struct.unpack(">f", value)[0]
        else:
            return None

    def write_float(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, struct.pack(">f", val))

    
"""with open("ctypes.txt", "w") as f:
    for a in ctypes.__dict__:
        f.write(str(a))
        f.write("\n")"""
        
if __name__ == "__main__":
    dolphin = Dolphin()

    if dolphin.find_dolphin():

        print("Found Dolphin!")
    else:
        print("Didn't find Dolphin")

    print(dolphin.pid, dolphin.handle)

    if dolphin.get_emu_info():
        print("We found MEM1 and/or MEM2!", dolphin.address_start, dolphin.mem2_start)
    else:
        print("We didn't find it...")
    print(dolphin.write_ram(0, b"GMS"))
    success, result = dolphin.read_ram(0, 8)
    print(result[0:8])
    
    print(dolphin.write_ram(0, b"AWA"))
    success, result = dolphin.read_ram(0, 8)
    print(result[0:8])