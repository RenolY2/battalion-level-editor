from OpenGL.GL import *
from .model_rendering import BW1Model, BW2Model
from .bw_archive import BWArchive
from .texture import TextureArchive


class BWModelHandler(object):
    def __init__(self):
        self.models = {}
        self.textures = None

    @classmethod
    def from_file(cls, f):
        bwmodels = cls()

        bwarc = BWArchive(f)
        bwmodels.textures = TextureArchive(bwarc)

        for modeldata in bwarc.models:
            name = str(modeldata.res_name, encoding="ascii")
            print(name, modeldata)
            if bwarc.is_bw2():
                model = BW2Model()
            else:
                model = BW1Model()
            data = modeldata.entries[0]
            data.fileobj.seek(0)
            f = data.fileobj
            model.from_file(f)
            bwmodels.models[name] = model

        return bwmodels

    def rendermodel(self, name, mtx, bwterrain, offset):
        """pos = bwmatrix.position
        x,y = int((pos.x+2048)*0.25), int((pos.z+2048)*0.25)
        if x >= 0 and x < 4096 and y >= 0 and y < 4096:
            if bwterrain.pointdata[x][y] is not None:
                y = bwterrain.pointdata[x][y][0]/32.0
            else:
                y = pos.y"""

        glPushMatrix()

        #glTranslatef(pos.x, pos.z, y)

        """glMultMatrixf([mtx.a1, mtx.a2, mtx.a3, mtx.a4,
                       mtx.b1, mtx.b2, mtx.b3, mtx.b4,
                       mtx.c1, mtx.c2, mtx.c3, mtx.c4,
                       mtx.d1, mtx.d2, mtx.d3, mtx.d4])"""
        #glRotatef(90, 1, 0, 0)
        """glMultMatrixf([mtx.a1, mtx.b1, mtx.c1, mtx.d1,
                       mtx.a2, mtx.b2, mtx.c2, mtx.d2,
                       mtx.a3, mtx.b3, mtx.c3, mtx.d3,
                       mtx.a4, mtx.b4, mtx.c4, mtx.d4])"""
        glMultMatrixf([ 1.0, 0.0, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 0.0, 1.0])

        #glMultMatrixf([mtx.a1, mtx.a2, mtx.a3, mtx.a4,
        #               mtx.b1, mtx.b2, mtx.b3, mtx.b4,
        #               mtx.c1, mtx.c2, mtx.c3, mtx.c4,
        #               mtx.d1, mtx.d2, mtx.d3, mtx.d4])
        glMultMatrixf(mtx)

        model = self.models[name]
        model.render(self.textures, None)

        glPopMatrix()



if __name__ == "__main__":
    with open("C1_OnPatrol_Level.res", "rb") as f:
        bwmodels = BWModelHandler.from_file(f)