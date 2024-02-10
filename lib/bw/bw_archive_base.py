import io
import struct
from array import array

from .helper import read_uint32, write_uint32


class BWResource(object):
    def __init__(self, name, size, memview):
        self.name = name
        self._size = size
        self._data = memview
        self._fileobj = io.BytesIO(self._data)

    @property
    def fileobj(self):
        return self._fileobj

    # File object and data object should be kept up to date together when
    # one of them is changed.
    @fileobj.setter
    def fileobj(self, fobj):
        if self._fileobj is not None:
            self._fileobj.close()

        self._fileobj = fobj
        self._data = fobj.getbuffer()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._fileobj.close()

        self._data = data
        self._fileobj = io.BytesIO(self._data)
    
    def write(self, file):
        name, length, data = self.pack()
        
        file.write(name)
        write_uint32(file, length)
        file.write(data)
    
    def pack(self):
        #data = self.fileobj.read()
        data = self._data#self.fileobj.getbuffer()
        #print(self.name, len(data))
        return self.name, len(data), data

    # Interpret a data entry as a section. If cls is given, an instance of that will be returned.
    # When using cls, offset is unused.
    def as_section(self, offset=0, cls=None):
        if cls is None:
            return BWSection(self.name, self._size, self._data, section_offset=offset)
        else:
            return cls(self.name, self._size, self._data)
            
class BWResourceFromData(BWResource):
    def __init__(self, name, data):
        self.name = name 
        self._fileobj = None
        self.fileobj = data # data should be BytesIO

class BWSection(BWResource):
    def __init__(self, name, size, memview, section_offset=0):
        super().__init__(name, size, memview)

        self.entries = []
        self._header = self._data[0:section_offset]
        self._fileobj.seek(section_offset)

        while self._fileobj.tell() < self._size:
            name, size, entry_memview = read_section(self._fileobj, memview)
            res_obj = BWResource(name, size, entry_memview)

            self.entries.append(res_obj)

    def pack(self):
        packed = io.BytesIO()

        packed.write(self._header)

        section_size = len(self._header)

        for entry in self.entries:
            name, size, data = entry.pack()

            packed.write(name)
            assert size == len(data)
            packed.write(struct.pack("I", size))

            packed.write(data)

            # 4 bytes for the ID, 4 bytes for the length, and the rest is from the data
            section_size += 4 + 4 + len(data)

        packed_data = packed.getvalue()
        packed.close()

        return self.name, section_size, packed_data

    def as_section(self, offset=0, cls=None):
        return self


class BWArchiveBase(BWSection):
    # f should be a file open in binary mode
    def __init__(self, f):
        # We read the content of the file into memory and put it in a bytearray,
        # which is necessary so the content can be modified.
        file_content = bytearray(f.read())
        #file_content = array("B", f.read())


        super().__init__(name=None, size=len(file_content), memview=file_content)

    def write(self, f):
        unused, size, data = self.pack()
        f.write(data)



def read_section(f, memview):
    name = f.read(4)
    size = read_uint32(f)

    offset = f.tell()
    data = memoryview(memview[offset:(offset+size)])#f.read(data_len)
    f.seek(size, io.SEEK_CUR)

    #print(len(memview), len(f.getbuffer()))
    return name, size, data
