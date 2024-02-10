import ctypes
import struct
from struct import pack, unpack
from ctypes import wintypes, sizeof, addressof, POINTER, pointer
from ctypes.wintypes import DWORD, ULONG, LONG, WORD
from multiprocessing import shared_memory

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


# The find_dolphin function is based on WindowsDolphinProcess::findPID() from 
# aldelaro5's Dolphin memory engine
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
        self.memory = None 
        
    def reset(self):
        self.pid = -1
        self.memory = None 

    def address_valid(self, addr):
        return 0x80000000 <= addr <= 0x81FFFFFF

    def find_dolphin(self, skip_pids=[]):
        entry = PROCESSENTRY32()
        
        entry.dwSize = sizeof(PROCESSENTRY32)
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, NULL)
        print(addressof(entry), hex(addressof(entry)))
        a = ULONG(addressof(entry))
        
        self.pid = -1
        
        if ctypes.windll.kernel32.Process32First(snapshot, pointer(entry)):   
            if entry.th32ProcessID not in skip_pids and entry.szExeFile in (b"Dolphin.exe", b"DolphinQt2.exe", b"DolphinWx.exe"):
                self.pid = entry.th32ProcessID 
            else:
                while ctypes.windll.kernel32.Process32Next(snapshot, pointer(entry)):
                    if entry.th32ProcessID in skip_pids:
                        continue
                    if entry.szExeFile in (b"Dolphin.exe", b"DolphinQt2.exe", b"DolphinWx.exe"):
                        self.pid = entry.th32ProcessID 
                    
            
        ctypes.windll.kernel32.CloseHandle(snapshot)
        
        if self.pid == -1:
            return False 
        
        return True
    
    def init_shared_memory(self):
        try:
            self.memory = shared_memory.SharedMemory('dolphin-emu.'+str(self.pid))
            return True
        except FileNotFoundError:
            return False
        
    def read_ram(self, offset, size):
        return self.memory.buf[offset:offset+size]
    
    def write_ram(self, offset, data):
        self.memory.buf[offset:offset+len(data)] = data
    
    def read_uint32(self, addr):
        assert addr >= 0x80000000
        value = self.read_ram(addr-0x80000000, 4)

        if not value:
            return None
        else:
            return unpack(">I", value)[0]
    
    def write_uint32(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, pack(">I", val))

    def read_float(self, addr):
        assert addr >= 0x80000000
        value = self.read_ram(addr - 0x80000000, 4)

        if not value:
            return None
        else:
            return unpack(">f", value)[0]

    def write_float(self, addr, val):
        assert addr >= 0x80000000
        return self.write_ram(addr - 0x80000000, pack(">f", val))

    
"""with open("ctypes.txt", "w") as f:
    for a in ctypes.__dict__:
        f.write(str(a))
        f.write("\n")"""
        
if __name__ == "__main__":
    dolphin = Dolphin()
    import multiprocessing 
    
    if dolphin.find_dolphin():

        print("Found Dolphin!")
    else:
        print("Didn't find Dolphin")

    print(dolphin.pid)
    
    dolphin.init_shared_memory()
    if dolphin.init_shared_memory():
        print("We found MEM1 and/or MEM2!")
    else:
        print("We didn't find it...")
    
    import random 
    randint = random.randint
    from timeit import default_timer
    
    start = default_timer()
    
    print("Testing Shared Memory Method")
    start = default_timer()
    count = 500000
    for i in range(count):
        value = randint(0, 2**32-1)
        dolphin.write_uint32(0x80000000, value)
        
        result = dolphin.read_uint32(0x80000000)
        assert result == value
    diff = default_timer()-start 
    print(count/diff, "per sec")
    print("time: ", diff)
    