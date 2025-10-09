import os
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from pyopengltk import OpenGLFrame

from .constants import FACTION_GAPS, BACKGROUND_SETTINGS
from .bezier_utils import quadratic_bezier
from .texture_manager import TextureManager


class GLCanvas(OpenGLFrame):
    """OpenGL canvas for rendering the campaign map with background and mission buttons"""
    
    def __init__(self, parent, assets_folder=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.position_data = []
        self.current_campaign = 0
        self.icon_size = 48
        self.zoom = 1.0
        self.assets_folder = assets_folder if assets_folder else "assets"
        
        # Texture manager
        self.texture_manager = TextureManager(self.assets_folder)
        
        # Gap values per faction
        self.faction_gaps = FACTION_GAPS
        
        # Mission button dragging
        self.dragging = None
        
        # Background positioning controls
        self.background_manual_mode = True  # Set to False to disable manual positioning
        
        # Store settings per faction
        self.faction_backgrounds = {}
        for idx in range(5):
            settings = BACKGROUND_SETTINGS.get(idx, {'x': 0, 'y': 0, 'scale': 1.0, 'rotation': 0})
            self.faction_backgrounds[idx] = {
                'x': settings.get('x', 0),
                'y': settings.get('y', 0),
                'scale': settings.get('scale', 1.0),
                'rotation': settings.get('rotation', 0)
            }
        
        # Current active background settings (for current faction)
        self.temp_bg_x = self.faction_backgrounds[0]['x']
        self.temp_bg_y = self.faction_backgrounds[0]['y']
        self.temp_bg_scale = self.faction_backgrounds[0]['scale']
        self.temp_bg_rotation = self.faction_backgrounds[0]['rotation']
        
        # Set focus policy so widget can receive keyboard events
        self.focus_set()
        
        # Bind events
        self.bind("<MouseWheel>", self.on_mouse_wheel)
        self.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down
        self.bind("<ButtonPress-1>", self.on_mouse_down)
        self.bind("<B1-Motion>", self.on_mouse_drag)
        self.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.bind("<KeyPress-w>", self.on_key_press)  # W = move up
        self.bind("<KeyPress-a>", self.on_key_press)  # A = move left
        self.bind("<KeyPress-s>", self.on_key_press)  # S = move down
        self.bind("<KeyPress-d>", self.on_key_press)  # D = move right
        self.bind("<KeyPress-q>", self.on_key_press)  # Q = rotate left
        self.bind("<KeyPress-e>", self.on_key_press)  # E = rotate right
        self.bind("<KeyPress-r>", self.on_key_press)  # R = scale up
        self.bind("<KeyPress-f>", self.on_key_press)  # F = scale down

    def on_key_press(self, event):
        """Handle keyboard input for background positioning, scaling, and rotation"""
        move_step = 10  # pixels to move per key press
        rotate_step = 5  # degrees to rotate per key press
        scale_step = 0.05  # scale change per key press
        
        if event.keysym == 'w':  # W - move up
            self.temp_bg_y -= move_step
            print(f"Background position: x={int(self.temp_bg_x)}, y={int(self.temp_bg_y)}")
        elif event.keysym == 's':  # S - move down
            self.temp_bg_y += move_step
            print(f"Background position: x={int(self.temp_bg_x)}, y={int(self.temp_bg_y)}")
        elif event.keysym == 'a':  # A - move left
            self.temp_bg_x -= move_step
            print(f"Background position: x={int(self.temp_bg_x)}, y={int(self.temp_bg_y)}")
        elif event.keysym == 'd':  # D - move right
            self.temp_bg_x += move_step
            print(f"Background position: x={int(self.temp_bg_x)}, y={int(self.temp_bg_y)}")
        elif event.keysym == 'q':  # Q - rotate left (counter-clockwise)
            self.temp_bg_rotation -= rotate_step
            print(f"Background rotation: {self.temp_bg_rotation}°")
        elif event.keysym == 'e':  # E - rotate right (clockwise)
            self.temp_bg_rotation += rotate_step
            print(f"Background rotation: {self.temp_bg_rotation}°")
        elif event.keysym == 'r':  # R - scale up
            self.temp_bg_scale += scale_step
            self.temp_bg_scale = min(5.0, self.temp_bg_scale)  # Max 5x
            print(f"Background scale: {self.temp_bg_scale:.2f}x")
        elif event.keysym == 'f':  # F - scale down
            self.temp_bg_scale -= scale_step
            self.temp_bg_scale = max(0.1, self.temp_bg_scale)  # Min 0.1x
            print(f"Background scale: {self.temp_bg_scale:.2f}x")
        
        # Save to faction storage after any change
        self.faction_backgrounds[self.current_campaign] = {
            'x': self.temp_bg_x,
            'y': self.temp_bg_y,
            'scale': self.temp_bg_scale,
            'rotation': self.temp_bg_rotation
        }

    def set_campaign(self, campaign_idx):
        """Set the current campaign to display"""
        # Save current faction's background settings before switching
        if self.background_manual_mode:
            self.faction_backgrounds[self.current_campaign] = {
                'x': self.temp_bg_x,
                'y': self.temp_bg_y,
                'scale': self.temp_bg_scale,
                'rotation': self.temp_bg_rotation
            }
        
        # Switch to new campaign
        self.current_campaign = campaign_idx
        
        # Load new faction's background settings
        if self.background_manual_mode:
            self.temp_bg_x = self.faction_backgrounds[campaign_idx]['x']
            self.temp_bg_y = self.faction_backgrounds[campaign_idx]['y']
            self.temp_bg_scale = self.faction_backgrounds[campaign_idx]['scale']
            self.temp_bg_rotation = self.faction_backgrounds[campaign_idx]['rotation']
            print(f"Loaded background for campaign {campaign_idx}: x={self.temp_bg_x}, y={self.temp_bg_y}, scale={self.temp_bg_scale:.2f}, rotation={self.temp_bg_rotation}°")

    def set_position_data(self, data):
        """Update the position data to render"""
        self.position_data = data

    def initgl(self):
        """Initialize OpenGL settings"""
        glClearColor(0.18, 0.18, 0.18, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        
        # Setup projection
        self.update_projection()
        
        # Load default assets
        self.load_default_assets()

    def load_default_assets(self):
        """Load default game assets from the assets folder"""
        # Load mission button icon
        button_path = os.path.join(self.assets_folder, "button_Level_S_n.png")
        self.texture_manager.load_texture("mission_button", button_path)
        
        # Load bezier dot sprite sheet (2x2 grid)
        dot_path = os.path.join(self.assets_folder, "Map_link_dot_1.png")
        self.texture_manager.load_spritesheet("bezier_dot", dot_path, 2, 2)
        
        # Load world map background
        world_map_path = os.path.join(self.assets_folder, "world_map.png")
        self.texture_manager.load_texture("world_map", world_map_path)
        
        print(f"Assets folder: {self.assets_folder}")
        print(f"Available textures: {list(self.texture_manager.textures.keys())}")

    def on_mouse_wheel(self, event):
        """Handle mouse wheel zoom"""
        if event.num == 5 or event.delta < 0:  # Scroll down
            self.zoom *= 0.9
        elif event.num == 4 or event.delta > 0:  # Scroll up
            self.zoom *= 1.1
        
        self.zoom = max(0.1, min(10.0, self.zoom))
        self.update_projection()
        
    def update_projection(self):
        """Update the orthographic projection based on window size"""
        if self.width <= 0 or self.height <= 0:
            return
            
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        half_w = (self.width / 2) / self.zoom
        half_h = (self.height / 2) / self.zoom
        center_x = self.width / 2
        center_y = self.height / 2
        glOrtho(center_x - half_w, center_x + half_w, 
                center_y + half_h, center_y - half_h, -1000, 1000)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
    
    def screen_to_game_coords(self, screen_x, screen_y):
        """Convert screen coordinates to game coordinate system"""
        game_x = (screen_x - self.width / 2) + 320
        game_y = (screen_y - self.height / 2) + 240
        return game_x, game_y
    
    def game_to_screen_coords(self, game_x, game_y):
        """Convert game coordinates to screen coordinates"""
        screen_x = self.width / 2 + (game_x - 320)
        screen_y = self.height / 2 + (game_y - 240)
        return screen_x, screen_y

    def find_button_at(self, x, y):
        """Check if mouse click is on a mission button"""
        if not self.position_data or self.current_campaign >= len(self.position_data):
            return None
        positions = self.position_data[self.current_campaign]
        half_size = self.icon_size / 2
        for idx, pos in enumerate(positions):
            sx, sy = self.game_to_screen_coords(pos['X'], pos['Y'])
            if abs(x - sx) < half_size and abs(y - sy) < half_size:
                return idx
        return None
    
    def on_mouse_down(self, event):
        """Handle mouse button press - start dragging mission button"""
        self.focus_set()
        
        idx = self.find_button_at(event.x, event.y)
        if idx is not None:
            self.dragging = idx
            print(f"Started dragging mission {idx}")

    def on_mouse_drag(self, event):
        """Handle mouse drag - move mission button"""
        if self.dragging is not None:
            game_x, game_y = self.screen_to_game_coords(event.x, event.y)
            positions = self.position_data[self.current_campaign]
            positions[self.dragging]['X'] = int(game_x)
            positions[self.dragging]['Y'] = int(game_y)

    def on_mouse_up(self, event):
        """Handle mouse button release"""
        if self.dragging is not None:
            print(f"Released mission {self.dragging}")
            if hasattr(self, 'controller') and hasattr(self.controller, "on_position_changed"):
                self.controller.on_position_changed()
            self.dragging = None

    def draw_background(self):
        """Draw the 2D world map background with transformation"""
        if not self.texture_manager.has_texture("world_map"):
            return
        
        texture = self.texture_manager.get_texture("world_map")
        glBindTexture(GL_TEXTURE_2D, texture['id'])
        
        # Get settings
        if self.background_manual_mode:
            map_width = texture['width'] * self.temp_bg_scale
            map_height = texture['height'] * self.temp_bg_scale
            offset_x = self.temp_bg_x
            offset_y = self.temp_bg_y
            rotation = self.temp_bg_rotation
        else:
            settings = self.faction_backgrounds[self.current_campaign]
            map_width = texture['width'] * settings['scale']
            map_height = texture['height'] * settings['scale']
            offset_x = settings['x']
            offset_y = settings['y']
            rotation = settings.get('rotation', 0)
        
        # Center position
        center_x = self.width / 2 + offset_x
        center_y = self.height / 2 + offset_y
        
        glPushMatrix()
        
        # Move to center, rotate, then draw
        glTranslatef(center_x, center_y, 0)
        glRotatef(rotation, 0, 0, 1)  # Rotate around Z axis
        
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(-map_width/2, -map_height/2)
        glTexCoord2f(1, 0)
        glVertex2f(map_width/2, -map_height/2)
        glTexCoord2f(1, 1)
        glVertex2f(map_width/2, map_height/2)
        glTexCoord2f(0, 1)
        glVertex2f(-map_width/2, map_height/2)
        glEnd()
        
        glPopMatrix()

    def draw_textured_quad(self, x, y, size, texture_name):
        """Draw a textured quad at the specified position"""
        if not self.texture_manager.has_texture(texture_name):
            return
        
        texture = self.texture_manager.get_texture(texture_name)
        glBindTexture(GL_TEXTURE_2D, texture['id'])
        
        half_size = size / 2
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(x - half_size, y - half_size)
        glTexCoord2f(1, 0)
        glVertex2f(x + half_size, y - half_size)
        glTexCoord2f(1, 1)
        glVertex2f(x + half_size, y + half_size)
        glTexCoord2f(0, 1)
        glVertex2f(x - half_size, y + half_size)
        glEnd()
    
    def draw_sprite(self, x, y, texture_name):
        """Draw a sprite at exact size"""
        if not self.texture_manager.has_texture(texture_name):
            return
        
        texture = self.texture_manager.get_texture(texture_name)
        glBindTexture(GL_TEXTURE_2D, texture['id'])
        
        w = texture['width']
        h = texture['height']
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(x, y)
        glTexCoord2f(1, 0)
        glVertex2f(x + w, y)
        glTexCoord2f(1, 1)
        glVertex2f(x + w, y + h)
        glTexCoord2f(0, 1)
        glVertex2f(x, y + h)
        glEnd()
    
    def render_bezier_curve(self, pos1, pos2, gap):
        """Render a bezier curve between two positions using dots"""
        if not self.texture_manager.has_texture("bezier_dot_0_0"):
            return
        
        x1, y1 = self.game_to_screen_coords(pos1['X'], pos1['Y'])
        x2, y2 = self.game_to_screen_coords(pos2['X'], pos2['Y'])
        
        points = quadratic_bezier(x1, y1, x2, y2, gap, 10, reverse_perpendicular=True)
        
        layer_order = ["bezier_dot_0_0", "bezier_dot_0_1", "bezier_dot_1_0", "bezier_dot_1_1"]
        
        dot_texture = self.texture_manager.get_texture("bezier_dot_0_0")
        half_w = dot_texture['width'] / 2
        half_h = dot_texture['height'] / 2
        
        for px, py in points:
            for layer_name in layer_order:
                self.draw_sprite(px - half_w, py - half_h, layer_name)
    
    def redraw(self):
        """Main render function"""
        if self.width <= 0 or self.height <= 0:
            return
            
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        self.update_projection()
        
        # Layer 1: Draw world map background
        self.draw_background()
        
        if not self.position_data or self.current_campaign >= len(self.position_data):
            return
        
        positions = self.position_data[self.current_campaign]
        if not positions:
            return
        
        gap = self.faction_gaps[self.current_campaign]
        
        # Layer 2: Draw bezier curves
        for i in range(1, len(positions)):
            pos1 = positions[i - 1]
            pos2 = positions[i]
            self.render_bezier_curve(pos1, pos2, gap)
        
        # Layer 3: Draw mission buttons (on top)
        if self.texture_manager.has_texture("mission_button"):
            for idx, pos in enumerate(positions):
                screen_x, screen_y = self.game_to_screen_coords(pos['X'], pos['Y'])
                
                button_texture = self.texture_manager.get_texture("mission_button")
                half_w = button_texture['width'] / 2
                half_h = button_texture['height'] / 2
                
                self.draw_sprite(screen_x - half_w, screen_y - half_h, "mission_button")