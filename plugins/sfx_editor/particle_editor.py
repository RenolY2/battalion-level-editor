import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import re
import os
from PIL import Image, ImageTk
import tkinter.colorchooser as colorchooser

from theme_manager import ThemeManager
from utils import create_military_background

class ParticleEffectEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Battalion Wars SFX Editor | Made By: Jasper_Zebra | Version 2.0")
        self.root.geometry("1100x850")
        
        # Set application icon
        self.set_app_icon()
        
        # Apply Battalion Wars 2 theme
        theme_manager = ThemeManager(root)
        self.style, self.colors = theme_manager.setup_theme()
        
        self.file_path = None
        self.file_content = None
        self.editable_values = {}  # Store editable values
        
        # Create background
        self.bg_image = create_military_background(950, 700)
        self.bg_label = tk.Label(root, image=self.bg_image)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.setup_ui()
    
    def set_app_icon(self):
        """Set the application icon"""
        try:
            # Look for the icon in the assets folder
            icon_path = os.path.join("assets", "sfx_editor_icon.png")
            
            # Check if the icon file exists
            if os.path.exists(icon_path):
                # Load the icon with PIL and set it as the window icon
                icon = Image.open(icon_path)
                photo_icon = ImageTk.PhotoImage(icon)
                self.root.iconphoto(True, photo_icon)
                self.update_status("ICON LOADED SUCCESSFULLY")
            else:
                self.update_status("WARNING: ICON FILE NOT FOUND")
                print(f"Icon file not found at {icon_path}")
        except Exception as e:
            self.update_status("WARNING: FAILED TO LOAD ICON")
            print(f"Failed to set application icon: {str(e)}")
    
    def update_status(self, message):
        """Update status bar message - used before status_var is initialized"""
        if hasattr(self, 'status_var'):
            self.status_var.set(message)
        else:
            # Store for later when status_var is created
            self._pending_status = message
            
    def setup_ui(self):
        """Setup the user interface components"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10", style="Military.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title with military stencil style
        title_frame = ttk.Frame(main_frame, style="TitleBG.TFrame")
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="BATTALION WARS SFX EDITOR", style='Title.TLabel')
        title_label.pack(fill=tk.X, pady=10)
        
        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="MISSION FILE", padding="5", style="Military.TLabelframe")
        file_frame.pack(fill=tk.X, pady=5)
        
        self.file_label = ttk.Label(file_frame, text="No file selected", style="FileText.TLabel")
        self.file_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_button = ttk.Button(file_frame, text="SELECT", command=self.browse_file, style="Military.TButton")
        self.browse_button.pack(side=tk.RIGHT, padx=5)
        
        # Create a PanedWindow to split the file viewer and parameter editor
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left panel - File viewer
        self.setup_file_viewer(paned_window)
        
        # Right panel - Tabbed parameter editor
        param_frame = ttk.Frame(paned_window, style="Military.TFrame")
        paned_window.add(param_frame, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(param_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Add tabs for different parameter types
        self.setup_color_tab()
        self.setup_size_tab()
        self.setup_emission_tab()
        self.setup_movement_tab()
        self.setup_visual_tab()
        self.setup_trail_tab()
        
        # Action buttons
        button_frame = ttk.Frame(main_frame, style="Military.TFrame")
        button_frame.pack(fill=tk.X, pady=10)
        
        self.apply_button = ttk.Button(button_frame, text="APPLY CHANGES", 
                                    command=self.apply_changes, 
                                    style="Deploy.TButton")
        self.apply_button.pack(side=tk.RIGHT, padx=5)
        
        # Status bar - military-style
        status_frame = ttk.Frame(self.root, style="Status.TFrame")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="SYSTEM READY")
        if hasattr(self, '_pending_status'):
            self.status_var.set(self._pending_status)
            delattr(self, '_pending_status')
            
        self.status_bar = ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_bar.pack(fill=tk.X)

    def on_tab_change(self, event):
        """Handle tab change events to update parameter highlighting"""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        
        # Clear all highlight tags first
        self.file_viewer.tag_remove("highlight", "1.0", "tk.END")
        
        # If no file loaded, do nothing
        if not self.file_content:
            return
        
        # Highlight parameters based on selected tab
        if selected_tab == "ORDNANCE COLOR":
            self.highlight_color_values()
        elif selected_tab == "SIZE":
            self.highlight_size_values()
        elif selected_tab == "EMISSION":
            self.highlight_emission_values()
        elif selected_tab == "MOVEMENT":
            self.highlight_movement_values()
        elif selected_tab == "VISUAL":
            self.highlight_visual_values()
        elif selected_tab == "TRAIL":
            self.highlight_trail_values()

    def highlight_color_values(self):
        """Highlight all the color values in the file viewer"""
        # Find and highlight Start_Red values
        pattern_start_red = r'(Start_Red NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_red, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("red_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Find and highlight Start_Green values
        pattern_start_green = r'(Start_Green NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_green, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("green_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Find and highlight Start_Blue values
        pattern_start_blue = r'(Start_Blue NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_blue, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("blue_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Find and highlight Start_Alpha values
        pattern_start_alpha = r'(Start_Alpha NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_alpha, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("alpha_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
            
        # Find and highlight End values and Transition values too
        for color, tag in [
            ("End_Red", "red_value"), 
            ("End_Green", "green_value"), 
            ("End_Blue", "blue_value"),
            ("End_Alpha", "alpha_value"),
            ("Transition_Red", "red_value"),
            ("Transition_Green", "green_value"),
            ("Transition_Blue", "blue_value"),
            ("Transition_Alpha", "alpha_value")
        ]:
            pattern = fr'({color} NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
            for match in re.finditer(pattern, self.file_content):
                start_idx = f"1.0+{match.start(2)}c"
                end_idx = f"1.0+{match.end(2)}c"
                self.file_viewer.tag_add(tag, start_idx, end_idx)
                self.file_viewer.tag_add("highlight", start_idx, end_idx)

    def highlight_size_values(self):
        """Highlight size-related parameters in the file viewer"""
        # Radius values
        pattern_radius = r'(Radius NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_radius, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("size_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Final_Radius values
        pattern_final = r'(Final_Radius )(\d+\.\d+)'
        for match in re.finditer(pattern_final, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("size_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Width and Start_Width values
        for param in ["Width", "Start_Width"]:
            pattern = fr'({param} )(\d+\.\d+)'
            for match in re.finditer(pattern, self.file_content):
                start_idx = f"1.0+{match.start(2)}c"
                end_idx = f"1.0+{match.end(2)}c"
                self.file_viewer.tag_add("size_value", start_idx, end_idx)
                self.file_viewer.tag_add("highlight", start_idx, end_idx)

    def highlight_emission_values(self):
        """Highlight emission-related parameters in the file viewer"""
        # Emit_Per_Turn values
        pattern_emit = r'(Emit_Per_Turn NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_emit, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("emission_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Life values
        pattern_life = r'(Life )(-?\d+)'
        for match in re.finditer(pattern_life, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("emission_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)

    def highlight_movement_values(self):
        """Highlight movement-related parameters in the file viewer"""
        # Initial Velocity values
        for param in ["Initial_Velocity_X", "Initial_Velocity_Y", "Initial_Velocity_Z"]:
            pattern = fr'({param} NUMBER_VERSION_2\n\*\*\*\*1: )(-?\d+\.\d+)'
            for match in re.finditer(pattern, self.file_content):
                start_idx = f"1.0+{match.start(2)}c"
                end_idx = f"1.0+{match.end(2)}c"
                self.file_viewer.tag_add("movement_value", start_idx, end_idx)
                self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Velocity_Randomness
        pattern_random = r'(Velocity_Randomness NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_random, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("movement_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Gravity values
        for param in ["GravityScalar", "GravityPC NUMBER_VERSION_2\n****1:"]:
            pattern = fr'({param} )(-?\d+\.\d+)'
            for match in re.finditer(pattern, self.file_content):
                start_idx = f"1.0+{match.start(2)}c"
                end_idx = f"1.0+{match.end(2)}c"
                self.file_viewer.tag_add("movement_value", start_idx, end_idx)
                self.file_viewer.tag_add("highlight", start_idx, end_idx)

    def highlight_visual_values(self):
        """Highlight visual-related parameters in the file viewer"""
        # Blend_Mode
        pattern_blend = r'(Blend_Mode )(\d+)'
        for match in re.finditer(pattern_blend, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("visual_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Anim_Speed
        pattern_anim = r'(Anim_Speed )(\d+\.\d+)'
        for match in re.finditer(pattern_anim, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("visual_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Cylinder_Length
        pattern_cylinder = r'(Cylinder_Length NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_cylinder, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("visual_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)

    def highlight_trail_values(self):
        """Highlight trail-related parameters in the file viewer"""
        # Num_Points
        pattern_points = r'(Num_Points )(\d+)'
        for match in re.finditer(pattern_points, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("trail_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Wiggle_Factor
        pattern_wiggle = r'(Wiggle_Factor )(\d+\.\d+)'
        for match in re.finditer(pattern_wiggle, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("trail_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)
        
        # Disperse_Rate
        pattern_disperse = r'(Disperse_Rate )(\d+\.\d+)'
        for match in re.finditer(pattern_disperse, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("trail_value", start_idx, end_idx)
            self.file_viewer.tag_add("highlight", start_idx, end_idx)

    def setup_size_tab(self):
        """Setup size parameters tab"""
        size_frame = ttk.Frame(self.notebook, style="Size.TFrame")
        self.notebook.add(size_frame, text="SIZE")

        # Create slider controls for size parameters
        param_frame = ttk.LabelFrame(size_frame, text="SIZE PARAMETERS", padding="5", style="Military.TLabelframe")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        param_grid = ttk.Frame(param_frame, style="Military.TFrame")
        param_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Radius parameters
        ttk.Label(param_grid, text="RADIUS:", style="Military.TLabel").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.radius_var = tk.DoubleVar(value=1.0)
        radius_slider = ttk.Scale(param_grid, from_=0.1, to=5.0, variable=self.radius_var, orient=tk.HORIZONTAL)
        radius_slider.grid(row=0, column=1, padx=5, pady=10, sticky=tk.EW)
        self.radius_value = ttk.Label(param_grid, text="1.000", style='Value.TLabel')
        self.radius_value.grid(row=0, column=2, padx=5, pady=10)
        radius_slider.bind("<Motion>", lambda e: self.update_value_label(self.radius_var, self.radius_value))
        
        # Final radius parameters
        ttk.Label(param_grid, text="FINAL RADIUS:", style="Military.TLabel").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        self.final_radius_var = tk.DoubleVar(value=2.0)
        final_radius_slider = ttk.Scale(param_grid, from_=0.1, to=10.0, variable=self.final_radius_var, orient=tk.HORIZONTAL)
        final_radius_slider.grid(row=1, column=1, padx=5, pady=10, sticky=tk.EW)
        self.final_radius_value = ttk.Label(param_grid, text="2.000", style='Value.TLabel')
        self.final_radius_value.grid(row=1, column=2, padx=5, pady=10)
        final_radius_slider.bind("<Motion>", lambda e: self.update_value_label(self.final_radius_var, self.final_radius_value))
        
        # Trail width
        ttk.Label(param_grid, text="TRAIL WIDTH:", style="Military.TLabel").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        self.width_var = tk.DoubleVar(value=0.25)
        width_slider = ttk.Scale(param_grid, from_=0.05, to=1.0, variable=self.width_var, orient=tk.HORIZONTAL)
        width_slider.grid(row=2, column=1, padx=5, pady=10, sticky=tk.EW)
        self.width_value = ttk.Label(param_grid, text="0.250", style='Value.TLabel')
        self.width_value.grid(row=2, column=2, padx=5, pady=10)
        width_slider.bind("<Motion>", lambda e: self.update_value_label(self.width_var, self.width_value))
        
        param_grid.columnconfigure(1, weight=1)

    def setup_emission_tab(self):
        """Setup emission parameters tab"""
        emission_frame = ttk.Frame(self.notebook, style="Emission.TFrame")
        self.notebook.add(emission_frame, text="EMISSION")

        param_frame = ttk.LabelFrame(emission_frame, text="EMISSION PARAMETERS", padding="5", style="Military.TLabelframe")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        param_grid = ttk.Frame(param_frame, style="Military.TFrame")
        param_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Emit_Per_Turn parameter
        ttk.Label(param_grid, text="EMIT RATE:", style="Military.TLabel").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.emit_rate_var = tk.DoubleVar(value=1.0)
        emit_rate_slider = ttk.Scale(param_grid, from_=0.1, to=5.0, variable=self.emit_rate_var, orient=tk.HORIZONTAL)
        emit_rate_slider.grid(row=0, column=1, padx=5, pady=10, sticky=tk.EW)
        self.emit_rate_value = ttk.Label(param_grid, text="1.000", style='Value.TLabel')
        self.emit_rate_value.grid(row=0, column=2, padx=5, pady=10)
        emit_rate_slider.bind("<Motion>", lambda e: self.update_value_label(self.emit_rate_var, self.emit_rate_value))
        
        # Life parameter
        ttk.Label(param_grid, text="LIFE:", style="Military.TLabel").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        self.life_var = tk.DoubleVar(value=15.0)
        life_slider = ttk.Scale(param_grid, from_=-2, to=30.0, variable=self.life_var, orient=tk.HORIZONTAL)
        life_slider.grid(row=1, column=1, padx=5, pady=10, sticky=tk.EW)
        self.life_value = ttk.Label(param_grid, text="15.000", style='Value.TLabel')
        self.life_value.grid(row=1, column=2, padx=5, pady=10)
        life_slider.bind("<Motion>", lambda e: self.update_value_label(self.life_var, self.life_value))
        
        param_grid.columnconfigure(1, weight=1)

    def setup_movement_tab(self):
        """Setup movement parameters tab"""
        movement_frame = ttk.Frame(self.notebook, style="Movement.TFrame")
        self.notebook.add(movement_frame, text="MOVEMENT")

        param_frame = ttk.LabelFrame(movement_frame, text="MOVEMENT PARAMETERS", padding="5", style="Military.TLabelframe")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        param_grid = ttk.Frame(param_frame, style="Military.TFrame")
        param_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initial Velocity X
        ttk.Label(param_grid, text="VELOCITY X:", style="Military.TLabel").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.velocity_x_var = tk.DoubleVar(value=0.0)
        velocity_x_slider = ttk.Scale(param_grid, from_=-1.0, to=1.0, variable=self.velocity_x_var, orient=tk.HORIZONTAL)
        velocity_x_slider.grid(row=0, column=1, padx=5, pady=10, sticky=tk.EW)
        self.velocity_x_value = ttk.Label(param_grid, text="0.000", style='Value.TLabel')
        self.velocity_x_value.grid(row=0, column=2, padx=5, pady=10)
        velocity_x_slider.bind("<Motion>", lambda e: self.update_value_label(self.velocity_x_var, self.velocity_x_value))
        
        # Initial Velocity Y
        ttk.Label(param_grid, text="VELOCITY Y:", style="Military.TLabel").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        self.velocity_y_var = tk.DoubleVar(value=0.0)
        velocity_y_slider = ttk.Scale(param_grid, from_=-1.0, to=1.0, variable=self.velocity_y_var, orient=tk.HORIZONTAL)
        velocity_y_slider.grid(row=1, column=1, padx=5, pady=10, sticky=tk.EW)
        self.velocity_y_value = ttk.Label(param_grid, text="0.000", style='Value.TLabel')
        self.velocity_y_value.grid(row=1, column=2, padx=5, pady=10)
        velocity_y_slider.bind("<Motion>", lambda e: self.update_value_label(self.velocity_y_var, self.velocity_y_value))
        
        # Initial Velocity Z
        ttk.Label(param_grid, text="VELOCITY Z:", style="Military.TLabel").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        self.velocity_z_var = tk.DoubleVar(value=0.0)
        velocity_z_slider = ttk.Scale(param_grid, from_=-1.0, to=1.0, variable=self.velocity_z_var, orient=tk.HORIZONTAL)
        velocity_z_slider.grid(row=2, column=1, padx=5, pady=10, sticky=tk.EW)
        self.velocity_z_value = ttk.Label(param_grid, text="0.000", style='Value.TLabel')
        self.velocity_z_value.grid(row=2, column=2, padx=5, pady=10)
        velocity_z_slider.bind("<Motion>", lambda e: self.update_value_label(self.velocity_z_var, self.velocity_z_value))
        
        # Velocity Randomness
        ttk.Label(param_grid, text="RANDOMNESS:", style="Military.TLabel").grid(row=3, column=0, padx=5, pady=10, sticky=tk.W)
        self.velocity_random_var = tk.DoubleVar(value=0.01)
        velocity_random_slider = ttk.Scale(param_grid, from_=0.0, to=0.1, variable=self.velocity_random_var, orient=tk.HORIZONTAL)
        velocity_random_slider.grid(row=3, column=1, padx=5, pady=10, sticky=tk.EW)
        self.velocity_random_value = ttk.Label(param_grid, text="0.010", style='Value.TLabel')
        self.velocity_random_value.grid(row=3, column=2, padx=5, pady=10)
        velocity_random_slider.bind("<Motion>", lambda e: self.update_value_label(self.velocity_random_var, self.velocity_random_value))
        
        # Gravity Scale
        ttk.Label(param_grid, text="GRAVITY:", style="Military.TLabel").grid(row=4, column=0, padx=5, pady=10, sticky=tk.W)
        self.gravity_var = tk.DoubleVar(value=0.0)
        gravity_slider = ttk.Scale(param_grid, from_=-0.1, to=0.1, variable=self.gravity_var, orient=tk.HORIZONTAL)
        gravity_slider.grid(row=4, column=1, padx=5, pady=10, sticky=tk.EW)
        self.gravity_value = ttk.Label(param_grid, text="0.000", style='Value.TLabel')
        self.gravity_value.grid(row=4, column=2, padx=5, pady=10)
        gravity_slider.bind("<Motion>", lambda e: self.update_value_label(self.gravity_var, self.gravity_value))
        
        param_grid.columnconfigure(1, weight=1)

    def setup_visual_tab(self):
        """Setup visual parameters tab"""
        visual_frame = ttk.Frame(self.notebook, style="Visual.TFrame")
        self.notebook.add(visual_frame, text="VISUAL")

        param_frame = ttk.LabelFrame(visual_frame, text="VISUAL PARAMETERS", padding="5", style="Military.TLabelframe")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        param_grid = ttk.Frame(param_frame, style="Military.TFrame")
        param_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Blend Mode
        ttk.Label(param_grid, text="BLEND MODE:", style="Military.TLabel").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        blend_modes = ["0 - Normal", "1 - Additive", "2 - Multiply", "3 - Screen"]
        self.blend_mode_var = tk.StringVar(value=blend_modes[0])
        blend_mode_menu = ttk.Combobox(param_grid, textvariable=self.blend_mode_var, values=blend_modes, state="readonly")
        blend_mode_menu.grid(row=0, column=1, padx=5, pady=10, sticky=tk.EW)
        
        # Animation Speed
        ttk.Label(param_grid, text="ANIM SPEED:", style="Military.TLabel").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        self.anim_speed_var = tk.DoubleVar(value=1.0)
        anim_speed_slider = ttk.Scale(param_grid, from_=0.1, to=2.0, variable=self.anim_speed_var, orient=tk.HORIZONTAL)
        anim_speed_slider.grid(row=1, column=1, padx=5, pady=10, sticky=tk.EW)
        self.anim_speed_value = ttk.Label(param_grid, text="1.000", style='Value.TLabel')
        self.anim_speed_value.grid(row=1, column=2, padx=5, pady=10)
        anim_speed_slider.bind("<Motion>", lambda e: self.update_value_label(self.anim_speed_var, self.anim_speed_value))
        
        # Cylinder Length (for cone effects)
        ttk.Label(param_grid, text="CYLINDER LENGTH:", style="Military.TLabel").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        self.cylinder_length_var = tk.DoubleVar(value=2.0)
        cylinder_length_slider = ttk.Scale(param_grid, from_=0.5, to=10.0, variable=self.cylinder_length_var, orient=tk.HORIZONTAL)
        cylinder_length_slider.grid(row=2, column=1, padx=5, pady=10, sticky=tk.EW)
        self.cylinder_length_value = ttk.Label(param_grid, text="2.000", style='Value.TLabel')
        self.cylinder_length_value.grid(row=2, column=2, padx=5, pady=10)
        cylinder_length_slider.bind("<Motion>", lambda e: self.update_value_label(self.cylinder_length_var, self.cylinder_length_value))
        
        param_grid.columnconfigure(1, weight=1)

    def setup_trail_tab(self):
        """Setup trail parameters tab"""
        trail_frame = ttk.Frame(self.notebook, style="Trail.TFrame")
        self.notebook.add(trail_frame, text="TRAIL")

        param_frame = ttk.LabelFrame(trail_frame, text="TRAIL PARAMETERS", padding="5", style="Military.TLabelframe")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        param_grid = ttk.Frame(param_frame, style="Military.TFrame")
        param_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Num Points
        ttk.Label(param_grid, text="TRAIL POINTS:", style="Military.TLabel").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.num_points_var = tk.DoubleVar(value=10.0)
        num_points_slider = ttk.Scale(param_grid, from_=3, to=30, variable=self.num_points_var, orient=tk.HORIZONTAL)
        num_points_slider.grid(row=0, column=1, padx=5, pady=10, sticky=tk.EW)
        self.num_points_value = ttk.Label(param_grid, text="10", style='Value.TLabel')
        self.num_points_value.grid(row=0, column=2, padx=5, pady=10)
        num_points_slider.bind("<Motion>", lambda e: self.update_value_label(self.num_points_var, self.num_points_value, is_int=True))
        
        # Wiggle Factor
        ttk.Label(param_grid, text="WIGGLE FACTOR:", style="Military.TLabel").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        self.wiggle_var = tk.DoubleVar(value=0.0)
        wiggle_slider = ttk.Scale(param_grid, from_=0.0, to=20.0, variable=self.wiggle_var, orient=tk.HORIZONTAL)
        wiggle_slider.grid(row=1, column=1, padx=5, pady=10, sticky=tk.EW)
        self.wiggle_value = ttk.Label(param_grid, text="0.000", style='Value.TLabel')
        self.wiggle_value.grid(row=1, column=2, padx=5, pady=10)
        wiggle_slider.bind("<Motion>", lambda e: self.update_value_label(self.wiggle_var, self.wiggle_value))
        
        # Disperse Rate
        ttk.Label(param_grid, text="DISPERSE RATE:", style="Military.TLabel").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        self.disperse_var = tk.DoubleVar(value=0.0)
        disperse_slider = ttk.Scale(param_grid, from_=0.0, to=0.1, variable=self.disperse_var, orient=tk.HORIZONTAL)
        disperse_slider.grid(row=2, column=1, padx=5, pady=10, sticky=tk.EW)
        self.disperse_value = ttk.Label(param_grid, text="0.000", style='Value.TLabel')
        self.disperse_value.grid(row=2, column=2, padx=5, pady=10)
        disperse_slider.bind("<Motion>", lambda e: self.update_value_label(self.disperse_var, self.disperse_value))
        
        param_grid.columnconfigure(1, weight=1)

    def setup_file_viewer(self, parent):
        """Setup the file viewer panel"""
        file_viewer_frame = ttk.LabelFrame(parent, text="FILE CONTENTS", padding="5", style="Military.TLabelframe")
        
        # Create a Text widget for viewing the file
        self.file_viewer = scrolledtext.ScrolledText(
            file_viewer_frame, 
            wrap=tk.WORD,
            width=50,
            height=25,
            font=("Courier New", 9),
            bg=self.colors['border'],
            fg=self.colors['foreground'],
            insertbackground=self.colors['foreground']
        )
        self.file_viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure tags for highlighting
        self.file_viewer.tag_configure("red_value", foreground=self.colors['accent1'], background="#401010")
        self.file_viewer.tag_configure("green_value", foreground=self.colors['accent3'], background="#104010")
        self.file_viewer.tag_configure("blue_value", foreground=self.colors['accent4'], background="#102040")
        self.file_viewer.tag_configure("alpha_value", foreground="#FFFFFF", background="#404040")
        
        # Tags for other parameter types
        self.file_viewer.tag_configure("size_value", foreground="#FFFFFF", background=self.colors['size_tab_bg'])
        self.file_viewer.tag_configure("emission_value", foreground="#FFFFFF", background=self.colors['emission_tab_bg'])
        self.file_viewer.tag_configure("movement_value", foreground="#FFFFFF", background=self.colors['movement_tab_bg'])
        self.file_viewer.tag_configure("visual_value", foreground="#FFFFFF", background=self.colors['visual_tab_bg'])
        self.file_viewer.tag_configure("trail_value", foreground="#FFFFFF", background=self.colors['trail_tab_bg'])
        
        # Generic highlight tag
        self.file_viewer.tag_configure("highlight", background="#303030")
        
        # Make the text read-only
        self.file_viewer.config(state=tk.DISABLED)
        
        # Add the frame to the parent paned window
        parent.add(file_viewer_frame, weight=2)

    def setup_color_tab(self):
        """Setup the color editor tab"""
        color_frame = ttk.Frame(self.notebook, style="Color.TFrame")
        self.notebook.add(color_frame, text="ORDNANCE COLOR")

        # Color editor
        color_editor = ttk.LabelFrame(color_frame, text="COLOR CONTROLS", padding="5", style="Military.TLabelframe")
        color_editor.pack(fill=tk.BOTH, expand=True)
        
        # Current values display
        self.setup_current_values(color_editor)
        
        # Color picker
        self.setup_color_pickers(color_editor)
        
        # RGB sliders
        self.setup_rgb_sliders(color_editor)
        
        # Color preview
        self.setup_color_preview(color_editor)
        
        # Description
        self.setup_description(color_editor)

    def setup_current_values(self, parent):
        """Setup the current values display"""
        self.current_values_frame = ttk.LabelFrame(parent, text="CURRENT VALUES", padding="5", style="Military.TLabelframe")
        self.current_values_frame.pack(fill=tk.X, pady=5)
        
        # Create a grid for current values
        current_grid = ttk.Frame(self.current_values_frame, style="Military.TFrame")
        current_grid.pack(fill=tk.X, pady=5, padx=5)
        
        # Headers
        ttk.Label(current_grid, text="TYPE", style="ValueHeader.TLabel").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(current_grid, text="START", style="ValueHeader.TLabel").grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(current_grid, text="END", style="ValueHeader.TLabel").grid(row=0, column=2, padx=5, pady=2)
        ttk.Label(current_grid, text="TRANS", style="ValueHeader.TLabel").grid(row=0, column=3, padx=5, pady=2)
        
        # RED values
        red_label = ttk.Label(current_grid, text="RED", foreground=self.colors['accent1'], style="Military.TLabel")
        red_label.grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        
        self.red_start_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.red_start_val.grid(row=1, column=1, padx=5, pady=2)
        
        self.red_end_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.red_end_val.grid(row=1, column=2, padx=5, pady=2)
        
        self.red_trans_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.red_trans_val.grid(row=1, column=3, padx=5, pady=2)
        
        # GREEN values
        green_label = ttk.Label(current_grid, text="GREEN", foreground=self.colors['accent3'], style="Military.TLabel")
        green_label.grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        
        self.green_start_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.green_start_val.grid(row=2, column=1, padx=5, pady=2)
        
        self.green_end_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.green_end_val.grid(row=2, column=2, padx=5, pady=2)
        
        self.green_trans_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.green_trans_val.grid(row=2, column=3, padx=5, pady=2)
        
        # BLUE values
        blue_label = ttk.Label(current_grid, text="BLUE", foreground=self.colors['accent4'], style="Military.TLabel")
        blue_label.grid(row=3, column=0, padx=5, pady=2, sticky=tk.W)
        
        self.blue_start_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.blue_start_val.grid(row=3, column=1, padx=5, pady=2)
        
        self.blue_end_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.blue_end_val.grid(row=3, column=2, padx=5, pady=2)
        
        self.blue_trans_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.blue_trans_val.grid(row=3, column=3, padx=5, pady=2)
        
        # ALPHA values
        alpha_label = ttk.Label(current_grid, text="OPACITY", style="Military.TLabel")
        alpha_label.grid(row=4, column=0, padx=5, pady=2, sticky=tk.W)
        
        self.alpha_start_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.alpha_start_val.grid(row=4, column=1, padx=5, pady=2)
        
        self.alpha_end_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.alpha_end_val.grid(row=4, column=2, padx=5, pady=2)
        
        self.alpha_trans_val = ttk.Label(current_grid, text="-", style="Value.TLabel")
        self.alpha_trans_val.grid(row=4, column=3, padx=5, pady=2)
    
    def setup_color_pickers(self, parent):
        """Setup color picker buttons"""
        preset_frame = ttk.Frame(parent, style="Military.TFrame")
        preset_frame.pack(fill=tk.X, pady=5)

        ttk.Label(preset_frame, text="COLOR SELECTION:", style="Military.TLabel").pack(side=tk.LEFT, padx=5)

        self.color_picker_button = ttk.Button(
            preset_frame, 
            text="CUSTOM COLOR", 
            command=self.open_color_picker, 
            style="Military.TButton"
        )
        self.color_picker_button.pack(side=tk.LEFT, padx=5)
    
    def setup_rgb_sliders(self, parent):
        """Setup RGB and Alpha sliders"""
        rgb_frame = ttk.Frame(parent, style="Military.TFrame")
        rgb_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Red slider
        red_label_frame = ttk.Frame(rgb_frame, style="RedLabel.TFrame")
        red_label_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(red_label_frame, text="RED:", style="Military.TLabel").pack(padx=3, pady=2)
        
        self.red_var = tk.DoubleVar(value=0.7)
        self.red_slider = ttk.Scale(rgb_frame, from_=0.0, to=1.0, variable=self.red_var, orient=tk.HORIZONTAL, style="Red.Horizontal.TScale")
        self.red_slider.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        self.red_value = ttk.Label(rgb_frame, text="0.700", style='Value.TLabel')
        self.red_value.grid(row=0, column=2, padx=5, pady=5)
        self.red_slider.bind("<Motion>", lambda e: self.update_value_label(self.red_var, self.red_value))
        
        # Green slider
        green_label_frame = ttk.Frame(rgb_frame, style="GreenLabel.TFrame")
        green_label_frame.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(green_label_frame, text="GREEN:", style="Military.TLabel").pack(padx=3, pady=2)
        
        self.green_var = tk.DoubleVar(value=0.3)
        self.green_slider = ttk.Scale(rgb_frame, from_=0.0, to=1.0, variable=self.green_var, orient=tk.HORIZONTAL, style="Green.Horizontal.TScale")
        self.green_slider.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        self.green_value = ttk.Label(rgb_frame, text="0.300", style='Value.TLabel')
        self.green_value.grid(row=1, column=2, padx=5, pady=5)
        self.green_slider.bind("<Motion>", lambda e: self.update_value_label(self.green_var, self.green_value))
        
        # Blue slider
        blue_label_frame = ttk.Frame(rgb_frame, style="BlueLabel.TFrame")
        blue_label_frame.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(blue_label_frame, text="BLUE:", style="Military.TLabel").pack(padx=3, pady=2)
        
        self.blue_var = tk.DoubleVar(value=0.5)
        self.blue_slider = ttk.Scale(rgb_frame, from_=0.0, to=1.0, variable=self.blue_var, orient=tk.HORIZONTAL, style="Blue.Horizontal.TScale")
        self.blue_slider.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        
        self.blue_value = ttk.Label(rgb_frame, text="0.500", style='Value.TLabel')
        self.blue_value.grid(row=2, column=2, padx=5, pady=5)
        self.blue_slider.bind("<Motion>", lambda e: self.update_value_label(self.blue_var, self.blue_value))
        
        # Alpha slider
        alpha_label_frame = ttk.Frame(rgb_frame, style="AlphaLabel.TFrame")
        alpha_label_frame.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(alpha_label_frame, text="OPACITY:", style="Military.TLabel").pack(padx=3, pady=2)
        
        self.alpha_var = tk.DoubleVar(value=1.0)
        self.alpha_slider = ttk.Scale(rgb_frame, from_=0.0, to=1.0, variable=self.alpha_var, orient=tk.HORIZONTAL, style="Alpha.Horizontal.TScale")
        self.alpha_slider.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        
        self.alpha_value = ttk.Label(rgb_frame, text="1.000", style='Value.TLabel')
        self.alpha_value.grid(row=3, column=2, padx=5, pady=5)
        self.alpha_slider.bind("<Motion>", lambda e: self.update_value_label(self.alpha_var, self.alpha_value))
        
        rgb_frame.columnconfigure(1, weight=1)
    
    def extract_parameters(self):
        """Extract parameters from the file content"""
        if not self.file_content:
            self.status_var.set("ERROR: NO FILE LOADED")
            return

        # SIZE TAB PARAMETERS
        # Extract Radius values
        radius_pattern = r'Radius NUMBER_VERSION_2\n\*\*\*\*1: (\d+\.\d+)'
        radius_match = re.search(radius_pattern, self.file_content)
        if radius_match and hasattr(self, 'radius_var'):
            self.radius_var.set(float(radius_match.group(1)))
            self.update_value_label(self.radius_var, self.radius_value)
        
        # Extract Final_Radius values
        final_radius_pattern = r'Final_Radius (\d+\.\d+)'
        final_radius_match = re.search(final_radius_pattern, self.file_content)
        if final_radius_match and hasattr(self, 'final_radius_var'):
            self.final_radius_var.set(float(final_radius_match.group(1)))
            self.update_value_label(self.final_radius_var, self.final_radius_value)
        
        # Extract Width values
        width_pattern = r'Width (\d+\.\d+)'
        width_match = re.search(width_pattern, self.file_content)
        if width_match and hasattr(self, 'width_var'):
            self.width_var.set(float(width_match.group(1)))
            self.update_value_label(self.width_var, self.width_value)
        
        # Also check for Start_Width
        start_width_pattern = r'Start_Width (\d+\.\d+)'
        start_width_match = re.search(start_width_pattern, self.file_content)
        if start_width_match and hasattr(self, 'width_var') and not width_match:
            self.width_var.set(float(start_width_match.group(1)))
            self.update_value_label(self.width_var, self.width_value)
        
        # EMISSION TAB PARAMETERS
        # Extract Emit_Per_Turn values
        emit_pattern = r'Emit_Per_Turn NUMBER_VERSION_2\n\*\*\*\*1: (\d+\.\d+)'
        emit_match = re.search(emit_pattern, self.file_content)
        if emit_match and hasattr(self, 'emit_rate_var'):
            self.emit_rate_var.set(float(emit_match.group(1)))
            self.update_value_label(self.emit_rate_var, self.emit_rate_value)
        
        # Extract Life values
        life_pattern = r'Life (-?\d+)'
        life_match = re.search(life_pattern, self.file_content)
        if life_match and hasattr(self, 'life_var'):
            self.life_var.set(float(life_match.group(1)))
            self.update_value_label(self.life_var, self.life_value)
        
        # MOVEMENT TAB PARAMETERS
        # Extract Initial_Velocity values
        velocity_x_pattern = r'Initial_Velocity_X NUMBER_VERSION_2\n\*\*\*\*1: (-?\d+\.\d+)'
        velocity_x_match = re.search(velocity_x_pattern, self.file_content)
        if velocity_x_match and hasattr(self, 'velocity_x_var'):
            self.velocity_x_var.set(float(velocity_x_match.group(1)))
            self.update_value_label(self.velocity_x_var, self.velocity_x_value)
        
        velocity_y_pattern = r'Initial_Velocity_Y NUMBER_VERSION_2\n\*\*\*\*1: (-?\d+\.\d+)'
        velocity_y_match = re.search(velocity_y_pattern, self.file_content)
        if velocity_y_match and hasattr(self, 'velocity_y_var'):
            self.velocity_y_var.set(float(velocity_y_match.group(1)))
            self.update_value_label(self.velocity_y_var, self.velocity_y_value)
        
        velocity_z_pattern = r'Initial_Velocity_Z NUMBER_VERSION_2\n\*\*\*\*1: (-?\d+\.\d+)'
        velocity_z_match = re.search(velocity_z_pattern, self.file_content)
        if velocity_z_match and hasattr(self, 'velocity_z_var'):
            self.velocity_z_var.set(float(velocity_z_match.group(1)))
            self.update_value_label(self.velocity_z_var, self.velocity_z_value)
        
        # Extract Velocity_Randomness
        velocity_random_pattern = r'Velocity_Randomness NUMBER_VERSION_2\n\*\*\*\*1: (\d+\.\d+)'
        velocity_random_match = re.search(velocity_random_pattern, self.file_content)
        if velocity_random_match and hasattr(self, 'velocity_random_var'):
            self.velocity_random_var.set(float(velocity_random_match.group(1)))
            self.update_value_label(self.velocity_random_var, self.velocity_random_value)
        
        # Extract GravityScalar or GravityPC
        gravity_pattern = r'GravityScalar (-?\d+\.\d+)'
        gravity_match = re.search(gravity_pattern, self.file_content)
        if not gravity_match:
            gravity_pattern = r'GravityPC NUMBER_VERSION_2\n\*\*\*\*1: (-?\d+\.\d+)'
            gravity_match = re.search(gravity_pattern, self.file_content)
        
        if gravity_match and hasattr(self, 'gravity_var'):
            self.gravity_var.set(float(gravity_match.group(1)))
            self.update_value_label(self.gravity_var, self.gravity_value)
        
        # VISUAL TAB PARAMETERS
        # Extract Blend_Mode
        blend_pattern = r'Blend_Mode (\d+)'
        blend_match = re.search(blend_pattern, self.file_content)
        if blend_match and hasattr(self, 'blend_mode_var'):
            blend_value = int(blend_match.group(1))
            if 0 <= blend_value < 4:
                blend_modes = ["0 - Normal", "1 - Additive", "2 - Multiply", "3 - Screen"]
                self.blend_mode_var.set(blend_modes[blend_value])
        
        # Extract Anim_Speed
        anim_speed_pattern = r'Anim_Speed (\d+\.\d+)'
        anim_speed_match = re.search(anim_speed_pattern, self.file_content)
        if anim_speed_match and hasattr(self, 'anim_speed_var'):
            self.anim_speed_var.set(float(anim_speed_match.group(1)))
            self.update_value_label(self.anim_speed_var, self.anim_speed_value)
        
        # Extract Cylinder_Length
        cylinder_length_pattern = r'Cylinder_Length NUMBER_VERSION_2\n\*\*\*\*1: (\d+\.\d+)'
        cylinder_length_match = re.search(cylinder_length_pattern, self.file_content)
        if cylinder_length_match and hasattr(self, 'cylinder_length_var'):
            self.cylinder_length_var.set(float(cylinder_length_match.group(1)))
            self.update_value_label(self.cylinder_length_var, self.cylinder_length_value)
        
        # TRAIL TAB PARAMETERS
        # Extract Num_Points
        num_points_pattern = r'Num_Points (\d+)'
        num_points_match = re.search(num_points_pattern, self.file_content)
        if num_points_match and hasattr(self, 'num_points_var'):
            self.num_points_var.set(float(num_points_match.group(1)))
            self.update_value_label(self.num_points_var, self.num_points_value, is_int=True)
        
        # Extract Wiggle_Factor
        wiggle_pattern = r'Wiggle_Factor (\d+\.\d+)'
        wiggle_match = re.search(wiggle_pattern, self.file_content)
        if wiggle_match and hasattr(self, 'wiggle_var'):
            self.wiggle_var.set(float(wiggle_match.group(1)))
            self.update_value_label(self.wiggle_var, self.wiggle_value)
        
        # Extract Disperse_Rate
        disperse_pattern = r'Disperse_Rate (\d+\.\d+)'
        disperse_match = re.search(disperse_pattern, self.file_content)
        if disperse_match and hasattr(self, 'disperse_var'):
            self.disperse_var.set(float(disperse_match.group(1)))
            self.update_value_label(self.disperse_var, self.disperse_value)
        
        # Display status message
        self.status_var.set("PARAMETERS EXTRACTED SUCCESSFULLY")

    def setup_color_preview(self, parent):
        """Setup color preview area"""
        preview_frame = ttk.Frame(parent, style="Preview.TFrame")
        preview_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(preview_frame, text="VISUAL REPORT:", style="Military.TLabel").pack(side=tk.LEFT, padx=5)
        
        # Canvas for color preview with military-style border
        preview_container = ttk.Frame(preview_frame, style="PreviewBorder.TFrame")
        preview_container.pack(side=tk.LEFT, padx=10)
        
        self.color_preview = tk.Canvas(preview_container, width=120, height=40, bg="#B34D80", highlightthickness=0)
        self.color_preview.pack(padx=2, pady=2)
        
        # Hex color display
        self.hex_color = ttk.Label(preview_frame, text="#B34D80", style='Value.TLabel')
        self.hex_color.pack(side=tk.LEFT, padx=10)
        
        self.update_preview()
        
        # Bind slider movement to update preview
        self.red_slider.bind("<B1-Motion>", lambda e: self.update_preview())
        self.green_slider.bind("<B1-Motion>", lambda e: self.update_preview())
        self.blue_slider.bind("<B1-Motion>", lambda e: self.update_preview())
    
    def setup_description(self, parent):
        """Setup description text"""
        desc_frame = ttk.Frame(parent, style="Military.TFrame")
        desc_frame.pack(fill=tk.X, pady=5)
        
        desc_text = ttk.Label(
            desc_frame, 
            text="Modify the RGB and Opacity values using the sliders above.\nAny highlighted values in the file will be updated when you apply changes.",
            style="Desc.TLabel",
            justify=tk.LEFT
        )
        desc_text.pack(padx=5, pady=5, anchor=tk.W)
    
    def browse_file(self):
        """Browse for a particle effect file to load"""
        file_path = filedialog.askopenfilename(
            title="Select Particle Effect File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.file_path = file_path
            self.file_label.config(text=os.path.basename(file_path))
            
            try:
                with open(file_path, 'r') as file:
                    self.file_content = file.read()
                    
                self.display_file_content()
                
                # Extract all parameter values from the file
                self.extract_editable_values()  # Extract color values (your existing method)
                self.extract_parameters()       # Extract all other parameters
                
                self.status_var.set(f"LOADED: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def display_file_content(self):
        """Display file content in the viewer with highlighted editable parts"""
        self.file_viewer.config(state=tk.NORMAL)
        self.file_viewer.delete(1.0, tk.END)
        self.file_viewer.insert(tk.END, self.file_content)
        
        # Highlight the editable values (color values)
        self.highlight_color_values()
        
        self.file_viewer.config(state=tk.DISABLED)
    
    def highlight_color_values(self):
        """Highlight all the color values in the file viewer"""
        # Find and highlight Start_Red values
        pattern_start_red = r'(Start_Red NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_red, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("red_value", start_idx, end_idx)
            self.file_viewer.tag_add("editable", start_idx, end_idx)
        
        # Find and highlight Start_Green values
        pattern_start_green = r'(Start_Green NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_green, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("green_value", start_idx, end_idx)
            self.file_viewer.tag_add("editable", start_idx, end_idx)
        
        # Find and highlight Start_Blue values
        pattern_start_blue = r'(Start_Blue NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_blue, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("blue_value", start_idx, end_idx)
            self.file_viewer.tag_add("editable", start_idx, end_idx)
        
        # Find and highlight Start_Alpha values
        pattern_start_alpha = r'(Start_Alpha NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
        for match in re.finditer(pattern_start_alpha, self.file_content):
            start_idx = f"1.0+{match.start(2)}c"
            end_idx = f"1.0+{match.end(2)}c"
            self.file_viewer.tag_add("alpha_value", start_idx, end_idx)
            self.file_viewer.tag_add("editable", start_idx, end_idx)
            
        # Find and highlight End values and Transition values too
        for color, tag in [
            ("End_Red", "red_value"), 
            ("End_Green", "green_value"), 
            ("End_Blue", "blue_value"),
            ("End_Alpha", "alpha_value"),
            ("Transition_Red", "red_value"),
            ("Transition_Green", "green_value"),
            ("Transition_Blue", "blue_value"),
            ("Transition_Alpha", "alpha_value")
        ]:
            pattern = fr'({color} NUMBER_VERSION_2\n\*\*\*\*1: )(\d+\.\d+)'
            for match in re.finditer(pattern, self.file_content):
                start_idx = f"1.0+{match.start(2)}c"
                end_idx = f"1.0+{match.end(2)}c"
                self.file_viewer.tag_add(tag, start_idx, end_idx)
                self.file_viewer.tag_add("editable", start_idx, end_idx)
    
    def open_color_picker(self):
        # Get current RGB values from sliders
        r = int(self.red_var.get() * 255)
        g = int(self.green_var.get() * 255)
        b = int(self.blue_var.get() * 255)
        current_color = f"#{r:02x}{g:02x}{b:02x}"
        
        # Open color chooser dialog
        color_result = colorchooser.askcolor(
            color=current_color,
            title="CUSTOM COLOR SELECTION"
        )
        
        # If a color was selected (not cancelled)
        if color_result[1]:
            # color_result is a tuple: ((r, g, b), hex_string)
            r, g, b = color_result[0]
            
            # Update slider values (0-1 range)
            self.red_var.set(r / 255)
            self.green_var.set(g / 255)
            self.blue_var.set(b / 255)
            
            # Update value labels
            self.update_value_label(self.red_var, self.red_value)
            self.update_value_label(self.green_var, self.green_value)
            self.update_value_label(self.blue_var, self.blue_value)
            
            # Update color preview
            self.update_preview()

    def extract_editable_values(self):
        """Extract editable values from the file content"""
        self.editable_values = {}
        
        # Get current values for Start_Red, End_Red, etc.
        for color_type in ["Red", "Green", "Blue", "Alpha"]:
            # Get Start values
            pattern_start = fr'Start_{color_type} NUMBER_VERSION_2\n\*\*\*\*1: (\d+\.\d+)'
            match = re.search(pattern_start, self.file_content)
            if match:
                self.editable_values[f"Start_{color_type}"] = float(match.group(1))
            
            # Get End values
            pattern_end = fr'End_{color_type} NUMBER_VERSION_2\n\*\*\*\*1: (\d+\.\d+)'
            match = re.search(pattern_end, self.file_content)
            if match:
                self.editable_values[f"End_{color_type}"] = float(match.group(1))
            
            # Get Transition values
            pattern_trans = fr'Transition_{color_type} NUMBER_VERSION_2\n\*\*\*\*1: (\d+\.\d+)'
            match = re.search(pattern_trans, self.file_content)
            if match:
                self.editable_values[f"Transition_{color_type}"] = float(match.group(1))
        
        # Update the current values display
        self.update_current_values_display()
        
        # Set the sliders to match the first Start values found
        if "Start_Red" in self.editable_values:
            self.red_var.set(self.editable_values["Start_Red"])
        if "Start_Green" in self.editable_values:
            self.green_var.set(self.editable_values["Start_Green"])
        if "Start_Blue" in self.editable_values:
            self.blue_var.set(self.editable_values["Start_Blue"])
        if "Start_Alpha" in self.editable_values:
            self.alpha_var.set(self.editable_values["Start_Alpha"])
        
        # Update slider value labels
        self.update_value_label(self.red_var, self.red_value)
        self.update_value_label(self.green_var, self.green_value)
        self.update_value_label(self.blue_var, self.blue_value)
        self.update_value_label(self.alpha_var, self.alpha_value)
        
        # Update the color preview
        self.update_preview()
    
    def update_current_values_display(self):
        """Update the display of current values"""
        # Update RED values
        if "Start_Red" in self.editable_values:
            self.red_start_val.config(text=f"{self.editable_values['Start_Red']:.3f}")
        if "End_Red" in self.editable_values:
            self.red_end_val.config(text=f"{self.editable_values['End_Red']:.3f}")
        if "Transition_Red" in self.editable_values:
            self.red_trans_val.config(text=f"{self.editable_values['Transition_Red']:.3f}")
        
        # Update GREEN values
        if "Start_Green" in self.editable_values:
            self.green_start_val.config(text=f"{self.editable_values['Start_Green']:.3f}")
        if "End_Green" in self.editable_values:
            self.green_end_val.config(text=f"{self.editable_values['End_Green']:.3f}")
        if "Transition_Green" in self.editable_values:
            self.green_trans_val.config(text=f"{self.editable_values['Transition_Green']:.3f}")
        
        # Update BLUE values
        if "Start_Blue" in self.editable_values:
            self.blue_start_val.config(text=f"{self.editable_values['Start_Blue']:.3f}")
        if "End_Blue" in self.editable_values:
            self.blue_end_val.config(text=f"{self.editable_values['End_Blue']:.3f}")
        if "Transition_Blue" in self.editable_values:
            self.blue_trans_val.config(text=f"{self.editable_values['Transition_Blue']:.3f}")
        
        # Update ALPHA values
        if "Start_Alpha" in self.editable_values:
            self.alpha_start_val.config(text=f"{self.editable_values['Start_Alpha']:.3f}")
        if "End_Alpha" in self.editable_values:
            self.alpha_end_val.config(text=f"{self.editable_values['End_Alpha']:.3f}")
        if "Transition_Alpha" in self.editable_values:
            self.alpha_trans_val.config(text=f"{self.editable_values['Transition_Alpha']:.3f}")
    
    def update_value_label(self, var, label, is_int=False):
        """Update the displayed value for a slider"""
        try:
            if is_int:
                value = int(var.get())
                label.config(text=f"{value}")
            else:
                value = var.get()
                label.config(text=f"{value:.3f}")
        except (ValueError, tk.TclError):
            # Handle potential errors if slider is being dragged
            pass
    
    def update_preview(self):
        r = int(self.red_var.get() * 255)
        g = int(self.green_var.get() * 255)
        b = int(self.blue_var.get() * 255)
        color = f"#{r:02x}{g:02x}{b:02x}"
        self.color_preview.config(bg=color)
        self.hex_color.config(text=color.upper())
    
    def apply_pink(self):
        self.red_var.set(0.7)
        self.green_var.set(0.3)
        self.blue_var.set(0.5)
        self.update_preview()
        self.update_value_label(self.red_var, self.red_value)
        self.update_value_label(self.green_var, self.green_value)
        self.update_value_label(self.blue_var, self.blue_value)
    
    def apply_blue(self):
        self.red_var.set(0.2)
        self.green_var.set(0.3)
        self.blue_var.set(0.8)
        self.update_preview()
        self.update_value_label(self.red_var, self.red_value)
        self.update_value_label(self.green_var, self.green_value)
        self.update_value_label(self.blue_var, self.blue_value)
    
    def apply_green(self):
        self.red_var.set(0.3)
        self.green_var.set(0.7)
        self.blue_var.set(0.3)
        self.update_preview()
        self.update_value_label(self.red_var, self.red_value)
        self.update_value_label(self.green_var, self.green_value)
        self.update_value_label(self.blue_var, self.blue_value)
    
    def apply_red(self):
        self.red_var.set(0.8)
        self.green_var.set(0.2)
        self.blue_var.set(0.2)
        self.update_preview()
        self.update_value_label(self.red_var, self.red_value)
        self.update_value_label(self.green_var, self.green_value)
        self.update_value_label(self.blue_var, self.blue_value)
    
    def apply_changes(self):
        """Apply all parameter changes to the file"""
        if not self.file_path or not self.file_content:
            messagebox.showerror("Error", "No file loaded")
            return
        
        # Create modified content with regex replacements
        modified_content = self.file_content
        
        # COLOR TAB PARAMETERS
        # Get RGB values from color sliders
        red = f"{self.red_var.get():.6f}"
        green = f"{self.green_var.get():.6f}"
        blue = f"{self.blue_var.get():.6f}"
        alpha = f"{self.alpha_var.get():.6f}"
        
        # Replace Red values
        modified_content = re.sub(
            r'(Start_Red NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + red,
            modified_content
        )
        
        modified_content = re.sub(
            r'(End_Red NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + red,
            modified_content
        )
        
        modified_content = re.sub(
            r'(Transition_Red NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + red,
            modified_content
        )
        
        # Replace Green values
        modified_content = re.sub(
            r'(Start_Green NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + green,
            modified_content
        )
        
        modified_content = re.sub(
            r'(End_Green NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + green,
            modified_content
        )
        
        modified_content = re.sub(
            r'(Transition_Green NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + green,
            modified_content
        )
        
        # Replace Blue values
        modified_content = re.sub(
            r'(Start_Blue NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + blue,
            modified_content
        )
        
        modified_content = re.sub(
            r'(End_Blue NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + blue,
            modified_content
        )
        
        modified_content = re.sub(
            r'(Transition_Blue NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + blue,
            modified_content
        )
        
        # Replace Alpha values
        modified_content = re.sub(
            r'(Start_Alpha NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + alpha,
            modified_content
        )
        
        modified_content = re.sub(
            r'(End_Alpha NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + alpha,
            modified_content
        )
        
        modified_content = re.sub(
            r'(Transition_Alpha NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
            r'\g<1>' + alpha,
            modified_content
        )
        
        # SIZE TAB PARAMETERS
        # Replace Radius values
        if hasattr(self, 'radius_var'):
            modified_content = re.sub(
                r'(Radius NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
                f'\\g<1>{self.radius_var.get():.6f}',
                modified_content
            )
        
        # Replace Final_Radius values
        if hasattr(self, 'final_radius_var'):
            modified_content = re.sub(
                r'(Final_Radius )\d+\.\d+',
                f'\\g<1>{self.final_radius_var.get():.6f}',
                modified_content
            )
        
        # Replace Width values
        if hasattr(self, 'width_var'):
            modified_content = re.sub(
                r'(Width )\d+\.\d+',
                f'\\g<1>{self.width_var.get():.6f}',
                modified_content
            )
            
            # Also update Start_Width if it exists
            modified_content = re.sub(
                r'(Start_Width )\d+\.\d+',
                f'\\g<1>{self.width_var.get():.6f}',
                modified_content
            )
        
        # EMISSION TAB PARAMETERS
        # Replace Emit_Per_Turn values
        if hasattr(self, 'emit_rate_var'):
            modified_content = re.sub(
                r'(Emit_Per_Turn NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
                f'\\g<1>{self.emit_rate_var.get():.6f}',
                modified_content
            )
        
        # Replace Life values
        if hasattr(self, 'life_var'):
            modified_content = re.sub(
                r'(Life )(-?\d+)',
                f'\\g<1>{int(self.life_var.get())}',
                modified_content
            )
        
        # MOVEMENT TAB PARAMETERS
        # Replace Initial_Velocity values
        if hasattr(self, 'velocity_x_var'):
            modified_content = re.sub(
                r'(Initial_Velocity_X NUMBER_VERSION_2\n\*\*\*\*1: )-?\d+\.\d+',
                f'\\g<1>{self.velocity_x_var.get():.6f}',
                modified_content
            )
        
        if hasattr(self, 'velocity_y_var'):
            modified_content = re.sub(
                r'(Initial_Velocity_Y NUMBER_VERSION_2\n\*\*\*\*1: )-?\d+\.\d+',
                f'\\g<1>{self.velocity_y_var.get():.6f}',
                modified_content
            )
        
        if hasattr(self, 'velocity_z_var'):
            modified_content = re.sub(
                r'(Initial_Velocity_Z NUMBER_VERSION_2\n\*\*\*\*1: )-?\d+\.\d+',
                f'\\g<1>{self.velocity_z_var.get():.6f}',
                modified_content
            )
        
        # Replace Velocity_Randomness
        if hasattr(self, 'velocity_random_var'):
            modified_content = re.sub(
                r'(Velocity_Randomness NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
                f'\\g<1>{self.velocity_random_var.get():.6f}',
                modified_content
            )
        
        # Replace GravityScalar and GravityPC values
        if hasattr(self, 'gravity_var'):
            modified_content = re.sub(
                r'(GravityScalar )-?\d+\.\d+',
                f'\\g<1>{self.gravity_var.get():.6f}',
                modified_content
            )
            
            modified_content = re.sub(
                r'(GravityPC NUMBER_VERSION_2\n\*\*\*\*1: )-?\d+\.\d+',
                f'\\g<1>{self.gravity_var.get():.6f}',
                modified_content
            )
        
        # VISUAL TAB PARAMETERS
        # Replace Blend_Mode
        if hasattr(self, 'blend_mode_var'):
            blend_value = int(self.blend_mode_var.get().split(' - ')[0])
            modified_content = re.sub(
                r'(Blend_Mode )\d+',
                f'\\g<1>{blend_value}',
                modified_content
            )
        
        # Replace Anim_Speed
        if hasattr(self, 'anim_speed_var'):
            modified_content = re.sub(
                r'(Anim_Speed )\d+\.\d+',
                f'\\g<1>{self.anim_speed_var.get():.6f}',
                modified_content
            )
        
        # Replace Cylinder_Length
        if hasattr(self, 'cylinder_length_var'):
            modified_content = re.sub(
                r'(Cylinder_Length NUMBER_VERSION_2\n\*\*\*\*1: )\d+\.\d+',
                f'\\g<1>{self.cylinder_length_var.get():.6f}',
                modified_content
            )
        
        # TRAIL TAB PARAMETERS
        # Replace Num_Points
        if hasattr(self, 'num_points_var'):
            modified_content = re.sub(
                r'(Num_Points )\d+',
                f'\\g<1>{int(self.num_points_var.get())}',
                modified_content
            )
        
        # Replace Wiggle_Factor
        if hasattr(self, 'wiggle_var'):
            modified_content = re.sub(
                r'(Wiggle_Factor )\d+\.\d+',
                f'\\g<1>{self.wiggle_var.get():.6f}',
                modified_content
            )
        
        # Replace Disperse_Rate
        if hasattr(self, 'disperse_var'):
            modified_content = re.sub(
                r'(Disperse_Rate )\d+\.\d+',
                f'\\g<1>{self.disperse_var.get():.6f}',
                modified_content
            )
        
        # Save the modified content back to the file
        try:
            with open(self.file_path, 'w') as file:
                file.write(modified_content)
            
            # Update the displayed file content
            self.file_content = modified_content
            self.display_file_content()
            self.extract_editable_values()  # Update displayed color values
            
            messagebox.showinfo("SUCCESS", f"Changes deployed to {os.path.basename(self.file_path)}")
            self.status_var.set(f"MISSION COMPLETE: {os.path.basename(self.file_path)} UPDATED")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes: {str(e)}")