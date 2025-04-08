import os
import sys
import multiprocessing as mp

from lib.lua.bwarchivelib import BattalionArchive
from OpenGL.GL import *
from io import BytesIO
from array import array
from struct import Struct
from PIL import Image


from PyQt6.QtGui import QImage, QPainter
from math import ceil, floor
from timeit import default_timer

from .read_binary import *
from lib.bw.bwtex import Texture, BW1Texture, BW2Texture


def process(queuein, queueout):
    while True:
        tex = queuein.get()


class TextureArchive(object):
    def __init__(self, archive: "BattalionArchive"):
        self.cachefolder = os.path.join(os.path.dirname(sys.argv[0]), "texture_cache")
        if not os.path.exists(self.cachefolder):
            os.mkdir(self.cachefolder)

        self.cached_textures = {}
        for filename in os.listdir(self.cachefolder):
            if filename.endswith(".png"):
                self.cached_textures[filename.replace(".png", "")] = True

        self.is_bw1 = archive.textures.is_bw1

        self.textures = {}
        self.texture_decoded_data = {}
        for texture in archive.textures.textures:
            texture.data_ready = False

            self.textures[texture.name.lower()] = texture
            name = bytes(texture.name, encoding="ascii").lower()
            if self.is_bw1:
                name2 = name.ljust(0x10, b"\x00")
            else:
                name2 = name.ljust(0x20, b"\x00")
            self.textures[name2] = texture


        self._cached = {}
        self.tex = glGenTextures(1)
        self.placeholder = Texture("PlaceHolder")
        self.placeholder.create_dummy(64, 64)

        self.texture_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.texture_processor = mp.Process(target=process, args=(self.texture_queue, self.result_queue))

    def clear_cache(self, textures=tuple()):
        for texname in textures:
            texname = texname.lower()
            print("Clearing", texname)
            if texname in self.cached_textures:
                os.remove(os.path.join(self.cachefolder, texname+".png"))
                del self.cached_textures[texname]
                if texname in self._cached:
                    tex, ID = self._cached[texname]
                    tex.loaded = False
            else:
                print(texname, "not found")

    def update_textures(self, archive: "BattalionArchive", force_update=[]):
        force_update_lower = [x.lower() for x in force_update]
        for texture in archive.textures.textures:
            lower = texture.name.lower()
            if lower not in self.textures or lower in force_update_lower:
                texture.data_ready = False

                self.textures[texture.name.lower()] = texture
                name = bytes(texture.name, encoding="ascii").lower()
                if self.is_bw1:
                    name2 = name.ljust(0x10, b"\x00")
                else:
                    name2 = name.ljust(0x20, b"\x00")
                self.textures[name2] = texture

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

            # Sometimes level terrain uses a dummy texture or the texture is missing
            dummy = True

        # f = self.textures[texname].fileobj

        tex = Texture(texname)
        tex.loaded = False
        tex.processed = False
        tex.in_progress = False
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

        if tex.loaded: #tex.is_loaded():
            return self._cached[texname]

        if dummy:
            tex.processed = True
            print("Generating dummy texture for", texname)
            tex.generate_dummy(32, 32)
            tex.loaded = True
        else:
            print("Loading", texname)
            if texname in self.cached_textures:
                print("from cache")
                tex = Texture.from_png(texname, os.path.join(self.cachefolder, texname+".png"))
            else:
                print("from resource")
                f = BytesIO(self.textures[texname].data)
                f.seek(0)

                if self.is_bw1:
                    tex = BW1Texture.from_file(self.textures[texname].name, f, ignoremips=True)
                else:
                    tex = BW2Texture.from_file(self.textures[texname].name, f, ignoremips=True)

                tex.dump_to_file(os.path.join(self.cachefolder, texname+".png"))
                self.cached_textures[texname] = True

            # Hack for mission 5.2: The cave uses a mostly transparent texture that has a rock texture
            # hidden in the transparent parts. Force the alpha to be fully opaque to render it correctly.
            if texname == "c1sncave" or texname == "c1snstalactite":
                texdata = tex.texture
                texdata.putalpha(255)
            self._cached[texname] = (tex, ID)
            tex.loaded = True

        if len(tex.mipmaps) > 0:#tex.success:
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
            image = tex.texture
            size_x, size_y = image.width, image.height
            rgba = image.tobytes()
            glTexImage2D(GL_TEXTURE_2D, 0, 4, size_x, size_y, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba)# b"\x00"*tex.size_x*tex.size_y*4)#tex.rgba)
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
            tex, id = self._cached[texname]
            if tex.loaded:
                return self._cached[texname]
            else:
                return self.load_texture(texname)
        else:
            self.initialize_texture(texname)
            return self.load_texture(texname)


class OpenGLTexture(object):
    def __init__(self, image: Image, min_filter=GL_LINEAR, mag_filter=GL_LINEAR):
        self.img_data = image
        self.id = None

        self.min_filter = min_filter
        self.mag_filter = mag_filter

    @classmethod
    def create_dummy(cls, width, height, min_filter=GL_LINEAR, mag_filter=GL_LINEAR):
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        return cls(img, min_filter, mag_filter)

    def init(self):
        if self.id is None:
            self.id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.id)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, self.min_filter)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, self.mag_filter)

            # glPixelStorei(GL_UNPACK_ROW_LENGTH, tex.size_x)
            # print("call info", tex.size_x, tex.size_y, tex.size_x * tex.size_y * 4, len(tex.rgba))
            # print(ID)
            size_x, size_y = self.img_data.width, self.img_data.height
            rgba = self.img_data.tobytes()
            glTexImage2D(GL_TEXTURE_2D, 0, 4, size_x, size_y, 0, GL_RGB, GL_UNSIGNED_BYTE, rgba)

    def update(self):
        if self.id is not None:
            print(self.id, type(self.id))
            glDeleteTextures(1, int(self.id))
            self.id = None
        self.init()