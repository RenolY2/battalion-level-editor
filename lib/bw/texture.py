import os
import sys
import multiprocessing as mp

from OpenGL.GL import *
from io import BytesIO
from array import array
from struct import Struct


from PyQt5.QtGui import QImage, QPainter
from math import ceil, floor
from timeit import default_timer

from .read_binary import *
from lib.bw.bwtex import Texture, BW1Texture, BW2Texture


def process(queuein, queueout):
    while True:
        tex = queuein.get()


class TextureArchive(object):
    def __init__(self, archive):
        self.cachefolder = os.path.join(os.path.dirname(sys.argv[0]), "texture_cache")
        if not os.path.exists(self.cachefolder):
            os.mkdir(self.cachefolder)

        self.cached_textures = {}
        for filename in os.listdir(self.cachefolder):
            if filename.endswith(".png"):
                self.cached_textures[filename.replace(".png", "")] = True

        self.game = archive.get_game()

        self.textures = {}
        self.texture_decoded_data = {}
        for texture in archive.textures:
            texture.data_ready = False
            name = bytes(texture.res_name).lower()
            self.textures[name] = texture


            name2 = name.strip(b"\x00").decode("ascii")
            self.textures[name2] = texture


        self._cached = {}
        self.tex = glGenTextures(1)
        self.placeholder = Texture("PlaceHolder")
        self.placeholder.create_dummy(64, 64)

        self.texture_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.texture_processor = mp.Process(target=process, args=(self.texture_queue, self.result_queue))


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

            # Sometimes level terrain uses a dummy texture
            if texname == "Dummy":
                dummy = True
            else:
                return None

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
            print("Generating dummy texture")
            tex.generate_dummy(32, 32)
            tex.loaded = True
        else:
            if texname in self.cached_textures:
                tex = Texture.from_png(texname, os.path.join(self.cachefolder, texname+".png"))
            else:

                f = self.textures[texname].fileobj
                f.seek(0)

                if self.game == "BW1":
                    tex = BW1Texture.from_file(f, ignoremips=True)
                elif self.game == "BW2":
                    tex = BW2Texture.from_file(f, ignoremips=True)

                tex.dump_to_file(os.path.join(self.cachefolder, texname+".png"))

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
            return self._cached[texname]
        else:
            self.initialize_texture(texname)
            return self.load_texture(texname)

