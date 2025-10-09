import os
from OpenGL.GL import *
from PIL import Image
import numpy as np

class TextureManager:
    """Handles loading and managing OpenGL textures"""
    
    def __init__(self, assets_folder=None):
        self.assets_folder = assets_folder if assets_folder else "assets"
        self.textures = {}
    
    def load_texture(self, name, image_path):
        """Load a single texture from file"""
        try:
            if not os.path.exists(image_path):
                print(f"Texture file not found: {image_path}")
                return False
                
            img = Image.open(image_path)
            img = img.convert("RGBA")
            img_data = np.array(list(img.getdata()), np.uint8)
            
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 
                        0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            
            self.textures[name] = {
                'id': texture_id,
                'width': img.width,
                'height': img.height
            }
            print(f"Loaded texture: {name} ({img.width}x{img.height})")
            return True
        except Exception as e:
            print(f"Error loading texture {name}: {e}")
            return False
    
    def load_spritesheet(self, base_name, image_path, grid_w, grid_h):
        """Load a spritesheet and split into individual textures"""
        try:
            if not os.path.exists(image_path):
                print(f"Spritesheet file not found: {image_path}")
                return False
                
            img = Image.open(image_path)
            img = img.convert("RGBA")
            
            sheet_w, sheet_h = img.size
            sprite_w = sheet_w // grid_w
            sprite_h = sheet_h // grid_h
            
            # Extract each sprite
            for row in range(grid_h):
                for col in range(grid_w):
                    left = col * sprite_w
                    top = row * sprite_h
                    right = left + sprite_w
                    bottom = top + sprite_h
                    
                    sprite_img = img.crop((left, top, right, bottom))
                    sprite_data = np.array(list(sprite_img.getdata()), np.uint8)
                    
                    texture_id = glGenTextures(1)
                    glBindTexture(GL_TEXTURE_2D, texture_id)
                    
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                    
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, sprite_w, sprite_h, 
                                0, GL_RGBA, GL_UNSIGNED_BYTE, sprite_data)
                    
                    sprite_name = f"{base_name}_{row}_{col}"
                    self.textures[sprite_name] = {
                        'id': texture_id,
                        'width': sprite_w,
                        'height': sprite_h
                    }
            
            print(f"Loaded spritesheet: {base_name} ({grid_w}x{grid_h} sprites, each {sprite_w}x{sprite_h})")
            return True
        except Exception as e:
            print(f"Error loading spritesheet {base_name}: {e}")
            return False
    
    def get_texture(self, name):
        """Get a loaded texture by name"""
        return self.textures.get(name)
    
    def has_texture(self, name):
        """Check if texture exists"""
        return name in self.textures