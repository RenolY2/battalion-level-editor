import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import re
import os

from .gl_canvas import GLCanvas
from .constants import FACTION_NAMES, FACTION_ABBR
from .lua_parser import parse_mission_positions, update_lua_content


class LuaScriptPreviewer:
    def __init__(self, root, assets_folder=None, update_queue=None):
        self.root = root
        self.root.title("BW2 | Campaign Mission Mover | Made by: Jasper_Zebra")
        self.root.geometry("1400x800")
        
        self.position_data = []
        self.current_file = None
        self.assets_folder = assets_folder
        self.update_queue = update_queue
        
        self.create_widgets()

    def create_widgets(self):
        # Main container
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Code viewer
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # Right panel - OpenGL viewport
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # === LEFT PANEL ===
        toolbar = ttk.Frame(left_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Open Lua File", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save Lua File", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save Background Settings", command=self.save_background_settings).pack(side=tk.LEFT, padx=2)

        code_label = ttk.Label(left_frame, text="Lua Script:")
        code_label.pack(anchor=tk.W, padx=5)
        
        self.code_text = scrolledtext.ScrolledText(
            left_frame, wrap=tk.NONE, 
            font=("Consolas", 10),
            bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white"
        )
        self.code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === RIGHT PANEL ===
        controls_frame = ttk.Frame(right_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Faction buttons
        faction_frame = ttk.LabelFrame(controls_frame, text="Faction", padding=5)
        faction_frame.pack(side=tk.LEFT, padx=5)
        
        self.faction_buttons = []
        for abbr, name, idx in zip(FACTION_ABBR, FACTION_NAMES, range(5)):
            btn = ttk.Button(
                faction_frame, text=abbr, width=4,
                command=lambda i=idx: self.select_faction(i)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.faction_buttons.append(btn)
        
        self.info_label = ttk.Label(controls_frame, text="No data loaded")
        self.info_label.pack(side=tk.LEFT, padx=10)
        
        # OpenGL Canvas
        self.gl_canvas = GLCanvas(right_frame, assets_folder=self.assets_folder, width=640, height=480)
        self.gl_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.gl_canvas.animate = 1
        self.gl_canvas.controller = self
        
        # Load assets after a short delay
        self.root.after(100, self.load_assets)
    
    def load_assets(self):
        """Load game assets"""
        if self.gl_canvas.texture_manager.has_texture("mission_button"):
            self.info_label.config(text="Assets loaded successfully")
        else:
            self.info_label.config(text="Assets not found in 'assets' folder")
    
    def open_file(self):
        """Open and load a Lua file"""
        filename = filedialog.askopenfilename(
            title="Select Lua Script",
            filetypes=[("Lua Files", "*.lua"), ("All Files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            self.current_file = filename

            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()

            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(1.0, content)
            self.apply_syntax_highlighting()
            
            # Set assets folder
            lua_dir = os.path.dirname(filename)
            assets_path = os.path.join(lua_dir, "assets")
            
            if os.path.exists(assets_path):
                self.gl_canvas.assets_folder = assets_path
                self.gl_canvas.texture_manager.assets_folder = assets_path
            
            self.load_assets()
            self.parse_positions()
            
            self.info_label.config(text=f"Loaded: {os.path.basename(filename)}")
            print(f"✅ Loaded Lua file: {filename}")
            
            messagebox.showinfo(
                "File Loaded",
                f"Successfully loaded:\n{os.path.basename(filename)}"
            )
        
        except Exception as e:
            self.info_label.config(text=f"Error loading file: {str(e)}")
            print(f"❌ Error loading Lua file: {e}")
            messagebox.showerror(
                "Error Loading File",
                f"Failed to load file:\n{str(e)}"
            )

    def save_file(self):
        """Save current Lua code to file"""
        if not self.current_file:
            self.info_label.config(text="No file loaded to save")
            messagebox.showwarning(
                "No File Loaded",
                "Please open a Lua file before saving."
            )
            return

        try:
            content = self.code_text.get(1.0, tk.END).strip()
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content + "\n")
            self.info_label.config(text=f"Saved: {os.path.basename(self.current_file)}")
            print(f"✅ Saved changes to {self.current_file}")
            
            messagebox.showinfo(
                "File Saved",
                f"Successfully saved:\n{os.path.basename(self.current_file)}"
            )
        except Exception as e:
            self.info_label.config(text=f"Error saving file: {str(e)}")
            print(f"❌ Error saving file: {e}")
            messagebox.showerror(
                "Error Saving File",
                f"Failed to save file:\n{str(e)}"
            )

    def save_background_settings(self):
        """Save current background settings to constants.py"""
        try:
            constants_path = os.path.join(os.path.dirname(__file__), "constants.py")
            
            with open(constants_path, 'r') as f:
                content = f.read()
            
            # Build the new BACKGROUND_SETTINGS dictionary
            settings_lines = ["# Background position, scale, and rotation for each campaign\nBACKGROUND_SETTINGS = {"]
            
            for idx in range(5):
                settings = self.gl_canvas.faction_backgrounds[idx]
                faction_name = FACTION_NAMES[idx]
                x = int(settings['x'])
                y = int(settings['y'])
                scale = settings['scale']
                rotation = int(settings['rotation'])
                comma = "," if idx < 4 else ""
                settings_lines.append(f"    {idx}: {{'x': {x}, 'y': {y}, 'scale': {scale:.2f}, 'rotation': {rotation}}}{comma}       # {faction_name}")
            
            settings_lines.append("}")
            new_settings = "\n".join(settings_lines)
            
            # Replace the old BACKGROUND_SETTINGS
            pattern = r'# Background position.*?\nBACKGROUND_SETTINGS = \{[^}]+\}'
            updated_content = re.sub(pattern, new_settings, content, flags=re.DOTALL)
            
            with open(constants_path, 'w') as f:
                f.write(updated_content)
            
            messagebox.showinfo("Saved", "Background settings saved to constants.py")
            print("✅ Background settings saved to constants.py")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")
            print(f"❌ Error saving settings: {e}")

    def apply_syntax_highlighting(self):
        """Apply basic Lua syntax highlighting"""
        keywords = ['function', 'end', 'local', 'return', 'if', 'then', 'else', 
                   'elseif', 'for', 'while', 'do', 'repeat', 'until', 'break']
        
        self.code_text.tag_config("keyword", foreground="#569cd6")
        self.code_text.tag_config("string", foreground="#ce9178")
        self.code_text.tag_config("comment", foreground="#6a9955")
        self.code_text.tag_config("number", foreground="#b5cea8")
        
        content = self.code_text.get(1.0, tk.END)
        
        # Highlight keywords
        for keyword in keywords:
            start = 1.0
            while True:
                pos = self.code_text.search(r'\m' + keyword + r'\M', start, 
                                           tk.END, regexp=True)
                if not pos:
                    break
                end = f"{pos}+{len(keyword)}c"
                self.code_text.tag_add("keyword", pos, end)
                start = end
        
        # Highlight strings
        for match in re.finditer(r'"[^"]*"', content):
            start_idx = f"1.0+{match.start()}c"
            end_idx = f"1.0+{match.end()}c"
            self.code_text.tag_add("string", start_idx, end_idx)
        
        # Highlight comments
        for match in re.finditer(r'--[^\n]*', content):
            start_idx = f"1.0+{match.start()}c"
            end_idx = f"1.0+{match.end()}c"
            self.code_text.tag_add("comment", start_idx, end_idx)
        
        # Highlight numbers
        for match in re.finditer(r'\b\d+\.?\d*\b', content):
            start_idx = f"1.0+{match.start()}c"
            end_idx = f"1.0+{match.end()}c"
            self.code_text.tag_add("number", start_idx, end_idx)
    
    def parse_positions(self):
        """Parse MissionPositionTable from the Lua code"""
        content = self.code_text.get(1.0, tk.END)
        self.position_data = parse_mission_positions(content)
        
        self.gl_canvas.set_position_data(self.position_data)
        self.info_label.config(text=f"Parsed {len(self.position_data)} factions")
        
        if self.position_data:
            self.select_faction(0)
        else:
            print("WARNING: No position data to display!")

    def select_faction(self, faction_idx):
        """Select a faction and display its campaign positions"""
        if faction_idx < 0 or faction_idx >= len(self.position_data):
            print(f"ERROR: Cannot select faction {faction_idx}")
            return
        
        self.gl_canvas.set_campaign(faction_idx)
        
        positions = self.position_data[faction_idx]
        print(f"Selected {FACTION_NAMES[faction_idx]}: {len(positions)} missions")
        self.info_label.config(text=f"{FACTION_NAMES[faction_idx]}: {len(positions)} missions")

    def on_position_changed(self):
        """Update Lua code text with modified coordinates"""
        content = self.code_text.get(1.0, tk.END)
        updated_content = update_lua_content(content, self.position_data)
        
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, updated_content)
        self.apply_syntax_highlighting()
        print("Lua coordinates updated from drag")
        
        # Send update through queue
        if self.update_queue:
            try:
                current_campaign = self.gl_canvas.current_campaign
                positions_with_ids = [
                    pos for pos in self.position_data[current_campaign] 
                    if 'ID' in pos and pos['ID'] is not None
                ]
                if positions_with_ids:
                    self.update_queue.put((current_campaign, positions_with_ids))
            except Exception as e:
                print(f"Error sending update: {e}")


def main(args=None, assets_folder=None, update_queue=None):
    root = tk.Tk()
    app = LuaScriptPreviewer(root, assets_folder=assets_folder, update_queue=update_queue)
    root.mainloop()


if __name__ == "__main__":
    main()