import subprocess
import os
from lib.model_rendering import TexturedModel


def superbmd_to_obj(src):
    subprocess.call(["lib/superbmd/SuperBMD.exe", src, "lib/temp/temp.obj", "--exportobj"])


def clear_temp_folder():
    for file in os.listdir("lib/temp/"):
        try:
            os.remove(os.path.join("lib/temp/", file))
        except Exception as err:
            print("Failed to remove", os.path.join("lib/temp/", file), str(err))
            pass


def load_textured_bmd(inputbmd):
    superbmd_to_obj(inputbmd)
    return TexturedModel.from_obj_path("lib/temp/temp.obj", rotate=True)

