import os
import sys
import re
import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bw_editor

class MSVector:
    """Position object compatible with the renderer (has .x and .z)"""
    def __init__(self, x=0.0, z=0.0):
        self.x = x
        self.z = z

class Plugin(object):
    def __init__(self):
        # Basic plugin setup
        self.name = "GUI Renderer"
        self.actions = [("Open GUI Renderer", self.open_gui_renderer)]
        print("GUI Renderer plugin has been initialized")
        
        # Store a reference to the window
        self.renderer_window = None
        self.editor_ref = None
        
    def open_gui_renderer(self, editor: "bw_editor.LevelEditor"):
        self.editor_ref = editor

        if not self._is_frontend2_loaded(editor):
            print("ERROR: Frontend2.xml must be loaded to use the GUI Renderer")
            from widgets.editor_widgets import open_error_dialog
            open_error_dialog("Please load Frontend2.xml before opening the GUI Renderer", editor)
            return

        # Ensure Lua folder points to Frontend2.xml_lua
        if hasattr(editor, "lua_workbench") and editor.lua_workbench is not None:
            lua_folder = os.path.splitext(os.path.basename(editor.current_gen_path))[0] + ".xml_lua"
            lua_path = os.path.join(os.path.dirname(editor.current_gen_path), lua_folder)
            editor.lua_workbench.workdir = lua_path
            print("Lua workdir set to:", editor.lua_workbench.workdir)

        level_data = self._prepare_level_data(editor)
        lua_data = self._get_lua_data(editor)

        try:
            from PyQt6.QtWidgets import QApplication
            from .ui_renderer.main import GUIRendererWindow

            app = QApplication.instance()
            if app is None:
                import sys
                app = QApplication(sys.argv if hasattr(sys, 'argv') else [])

            self.renderer_window = GUIRendererWindow(level_data, lua_data, editor)
            self.renderer_window.show()
            self.renderer_window.raise_()
            self.renderer_window.activateWindow()

            print("GUI Renderer window opened successfully")

        except Exception as e:
            print(f"Error opening GUI Renderer: {str(e)}")
            import traceback
            traceback.print_exc()

    def _parse_lua_table(self, lua_text: str, table_name: str):
        """Extract and parse a Lua table (basic arrays/dictionaries only)."""
        pattern = rf"{table_name}\s*=\s*{{(.*?)\n}}"
        match = re.search(pattern, lua_text, re.DOTALL)
        if not match:
            print(f"[Lua Parser] Could not find table: {table_name}")
            return None

        table_text = match.group(1)
        # Convert Lua-style braces to Python brackets
        table_text = table_text.replace("{", "[").replace("}", "]")
        # Replace Lua comments
        table_text = re.sub(r"--.*", "", table_text)
        try:
            return ast.literal_eval("[" + table_text + "]")
        except Exception as e:
            print(f"[Lua Parser] Error parsing {table_name}: {e}")
            return None

    def load_campaign_lua(self):
        """Load Campaign.lua and extract important data for the GUI renderer."""
        if not self.editor_ref or not self.editor_ref.current_gen_path:
            print("[Lua Loader] No editor or XML loaded.")
            return None

        lua_folder = os.path.splitext(self.editor_ref.current_gen_path)[0] + ".xml_lua"
        lua_path = os.path.join(lua_folder, "Campaign.lua")

        if not os.path.exists(lua_path):
            print("[Lua Loader] Campaign.lua not found:", lua_path)
            return None

        with open(lua_path, "r", encoding="utf-8") as f:
            lua_text = f.read()

        mission_positions = self._parse_lua_table(lua_text, "MissionPositionTable")
        faction_colors = self._parse_lua_table(lua_text, "FactionBGColours")

        print("[Lua Loader] Loaded Campaign.lua successfully")
        print("  Missions:", len(mission_positions) if mission_positions else 0)
        print("  Factions:", len(faction_colors) if faction_colors else 0)

        return {
            "MissionPositionTable": mission_positions,
            "FactionBGColours": faction_colors,
        }

    def _is_frontend2_loaded(self, editor: "bw_editor.LevelEditor") -> bool:
        """Check if Frontend2.xml is currently loaded"""
        if editor.current_gen_path is None:
            return False
        
        # Check if the filename contains "Frontend2"
        filename = os.path.basename(editor.current_gen_path)
        return "frontend2" in filename.lower()
    
    def _prepare_level_data(self, editor: "bw_editor.LevelEditor"):
        """Extract relevant GUI data from the loaded level"""
        level_data = {
            'pages': {},
            'textures': [],
            'all_widgets': {}
        }
        
        if editor.level_file is None:
            return level_data
        
        # Helper function to get widget data
        def get_widget_data(obj, obj_id):
            """Extract data from a widget object"""
            widget_data = {
                'id': obj_id,
                'type': obj.type,
                'name': getattr(obj, 'customname', None) or getattr(obj, 'lua_name', '') or f"{obj.type}_{obj_id}",
                'texture': None,
                'position': None,
                'size': None,
                'uv_pos': None,
                'uv_size': None,
                'colour': None,
                'z_depth': None,
                'children': [],
                'obj_ref': obj,  # Store reference to the actual object
                'pos_obj_ref': None,  # Store reference to position object
                'msVector_ref': None  # Store reference to the actual msVector object
            }
            
            # Get texture if available
            if hasattr(obj, 'mpTexture') and obj.mpTexture is not None:
                if hasattr(obj.mpTexture, 'mName'):
                    widget_data['texture'] = obj.mpTexture.mName
            
            # Get position (mpPos) - it's a pointer to cGUIMetaVector
            if hasattr(obj, 'mpPos') and obj.mpPos is not None:
                pos_obj = obj.mpPos
                widget_data['position'] = self._get_vector_value(pos_obj)
                widget_data['pos_obj_ref'] = pos_obj  # Store the position object reference
                
                # Debug: Verify we have the right object
                print(f"Widget {obj_id} has pos_obj type: {type(pos_obj)}, id: {getattr(pos_obj, 'id', 'no id')}")
                if hasattr(pos_obj, 'msVector'):
                    print(f"  msVector current value: {pos_obj.msVector}")

            # Get size (mpSize)
            if hasattr(obj, 'mpSize') and obj.mpSize is not None:
                size_obj = obj.mpSize
                widget_data['size'] = self._get_vector_value(size_obj)
                
                # Store size msVector reference if it exists and is an object
                if hasattr(size_obj, 'msVector') and hasattr(size_obj.msVector, 'x'):
                    widget_data['size_msVector_ref'] = size_obj.msVector
            
            # Get UV position
            if hasattr(obj, 'mpUVPos') and obj.mpUVPos is not None:
                uv_pos_obj = obj.mpUVPos
                widget_data['uv_pos'] = self._get_vector_value(uv_pos_obj)
            
            # Get UV size
            if hasattr(obj, 'mpUVSize') and obj.mpUVSize is not None:
                uv_size_obj = obj.mpUVSize
                widget_data['uv_size'] = self._get_vector_value(uv_size_obj)
            
            # Get Z depth
            if hasattr(obj, 'meZDepth'):
                widget_data['z_depth'] = obj.meZDepth
            
            return widget_data
        
        def build_widget_tree(widget_obj, visited=None):
            """Recursively build widget tree from object"""
            if visited is None:
                visited = set()
            
            if widget_obj is None or widget_obj.id in visited or widget_obj.deleted:
                return None
            
            visited.add(widget_obj.id)
            
            # Get widget data
            widget_data = get_widget_data(widget_obj, widget_obj.id)
            
            # Get child widgets from mWidgetArray
            if hasattr(widget_obj, 'mWidgetArray'):
                widget_array = widget_obj.mWidgetArray
                if isinstance(widget_array, list):
                    for child_obj in widget_array:
                        if child_obj is not None and not child_obj.deleted:
                            child_widget = build_widget_tree(child_obj, visited)
                            if child_widget:
                                widget_data['children'].append(child_widget)
                elif widget_array is not None and not widget_array.deleted:
                    child_widget = build_widget_tree(widget_array, visited)
                    if child_widget:
                        widget_data['children'].append(child_widget)
            
            return widget_data
        
        # Find all pages and build their widget trees
        for obj_id, obj in editor.level_file.objects.items():
            if obj.type == "cGUIPage":
                page_name = getattr(obj, 'customname', None) or getattr(obj, 'lua_name', '') or f"Page_{obj_id}"
                
                page_data = {
                    'id': obj_id,
                    'name': page_name,
                    'widgets': [],
                    'script_name': None,
                    'script_path': None
                }
                
                # Get the Lua script name through the pointer chain
                # cGUIPage -> mpScript (cInitialisationScriptEntity) -> mpScript (cGameScriptResource) -> mName
                if hasattr(obj, 'mpScript') and obj.mpScript is not None:
                    init_script = obj.mpScript
                    if hasattr(init_script, 'mpScript') and init_script.mpScript is not None:
                        game_script = init_script.mpScript
                        if hasattr(game_script, 'mName'):
                            script_name = game_script.mName
                            page_data['script_name'] = script_name
                            
                            # Try to find the lua file
                            if editor.current_gen_path:
                                level_dir = os.path.dirname(editor.current_gen_path)
                                lua_folder = os.path.splitext(os.path.basename(editor.current_gen_path))[0] + ".xml_lua"
                                lua_path = os.path.join(level_dir, lua_folder, script_name + ".lua")
                                
                                if os.path.exists(lua_path):
                                    page_data['script_path'] = lua_path
                
                # Get widgets from mWidgetArray
                if hasattr(obj, 'mWidgetArray'):
                    widget_array = obj.mWidgetArray
                    if isinstance(widget_array, list):
                        for widget_obj in widget_array:
                            if widget_obj is not None and not widget_obj.deleted:
                                widget_tree = build_widget_tree(widget_obj)
                                if widget_tree:
                                    page_data['widgets'].append(widget_tree)
                    elif widget_array is not None and not widget_array.deleted:
                        widget_tree = build_widget_tree(widget_array)
                        if widget_tree:
                            page_data['widgets'].append(widget_tree)
                
                level_data['pages'][obj_id] = page_data
            
            # Collect texture resources
            elif obj.type == "cTextureResource":
                level_data['textures'].append({
                    'name': obj.mName,
                    'id': obj_id
                })
        
        # Print summary
        print(f"Found {len(level_data['pages'])} pages:")
        for page_id, page in level_data['pages'].items():
            total_widgets = self._count_widgets(page['widgets'])
            script_info = f" [{page['script_name']}.lua]" if page.get('script_name') else ""
            print(f"  - {page['name']}: {total_widgets} widgets{script_info}")
        
        return level_data
    
    def update_mission_position_table(self):
        """
        Update the MissionPositionTable in the Lua script with the current widget positions.
        """
        if not self.editor_ref or not self.editor_ref.level_file:
            print("No editor reference or level file loaded")
            return

        # Collect positions by mission_id
        mission_positions = {}
        for page in getattr(self.renderer_window, 'current_page', {}).get('widgets', []):
            def collect_positions(widget):
                if 'mission_id' in widget and 'position' in widget:
                    mission_positions[widget['mission_id']] = widget['position']
                for c in widget.get('children', []):
                    collect_positions(c)
            collect_positions(page)

        # Lua file path
        lua_path = getattr(self.renderer_window, 'current_page', {}).get('script_path')
        if not lua_path or not os.path.exists(lua_path):
            print("Lua script not found")
            return

        # Read Lua
        with open(lua_path, 'r', encoding='utf-8') as f:
            lua_lines = f.readlines()

        # Find MissionPositionTable block
        start_idx = end_idx = None
        for i, line in enumerate(lua_lines):
            if 'MissionPositionTable' in line:
                start_idx = i
            elif start_idx is not None and line.strip().startswith('}'):
                end_idx = i
                break

        if start_idx is None or end_idx is None:
            print("MissionPositionTable block not found in Lua script")
            return

        # Flatten mission IDs (same as assign_mission_ids)
        mission_id_table = [
            [20001882, 20001884, 20001886, 20001888, 20001890],
            [20001835, 20001837, 20001839],
            [20001855, 20001858, 20001861, 20001864],
            [20001870, 20001872, 20001874],
            [20001832, 20001844, 20001847, 20001850]
        ]

        # Build new Lua table lines
        new_table_lines = ["MissionPositionTable = {\n"]
        for campaign in mission_id_table:
            new_table_lines.append("  {\n")
            for mid in campaign:
                pos = mission_positions.get(mid, {'x': 0, 'y': 0})
                new_table_lines.append(f"    {{X = {int(pos['x'])}, Y = {int(pos['y'])}}}, -- {mid}\n")
            new_table_lines.append("  },\n")
        new_table_lines.append("}\n")

        # Replace old block
        lua_lines = lua_lines[:start_idx] + new_table_lines + lua_lines[end_idx + 1:]

        # Write back
        with open(lua_path, 'w', encoding='utf-8') as f:
            f.writelines(lua_lines)

        print(f"MissionPositionTable updated in {lua_path}")

    def sync_widgets_to_lua_and_xml(self):
        """
        Update XML mpPos objects from widget positions and rebuild Lua MissionPositionTable.
        """
        mission_table = []

        # Loop through each page or faction of widgets
        for faction_idx, widgets in enumerate(self._get_mission_widget_pages()):
            faction_positions = []

            for widget in widgets:
                mp_pos_id = widget.get('mpPos')  # ID of cGUIVectorVector
                pos = widget.get('position')     # {'x': 213, 'y': 148}

                if mp_pos_id and pos:
                    # Update XML object
                    vector_obj = self.xml_objects.get(mp_pos_id)
                    if vector_obj:
                        vector_obj.find('Attribute[@name="msVector"]/Item').text = f"{pos['x']},{pos['y']}"
                        print(f"Updated XML mpPos {mp_pos_id} → {pos['x']},{pos['y']}")

                    # Append to Lua table
                    faction_positions.append({'X': pos['x'], 'Y': pos['y'], 'ID': widget.get('mission_id')})

            if faction_positions:
                mission_table.append(faction_positions)

        # Build Lua string
        lua_str = "MissionPositionTable = {\n"
        for faction in mission_table:
            lua_str += "  {\n"
            for pos in faction:
                lua_str += f"    {{X = {pos['X']}, Y = {pos['Y']}}}, -- {pos['ID']}\n"
            lua_str += "  },\n"
        lua_str += "}\n"

        # Save Lua file (e.g., Campaign.lua)
        lua_filename = "Campaign.lua"
        self.save_lua_file(lua_filename, lua_str)
        print(f"Updated {lua_filename} with {len(mission_table)} factions.")

    def write_mission_ids_to_lua(self):
        """Write the mission IDs from the widgets into Campaign.lua"""
        if self.editor_ref is None:
            print("Editor reference not set; cannot write mission IDs")
            return

        # Determine the Lua file path
        lua_folder = os.path.splitext(self.editor_ref.current_gen_path)[0] + ".xml_lua"
        lua_file_path = os.path.join(os.path.dirname(self.editor_ref.current_gen_path), lua_folder, "Campaign.lua")

        if not os.path.exists(lua_file_path):
            print(f"Campaign.lua not found at {lua_file_path}")
            return

        # Collect mission widgets
        mission_widgets = [w for w in getattr(self, 'widgets', []) if w.get('name', '').startswith("Mission_")]
        mission_widgets.sort(key=lambda w: w.get('name'))  # Sort to match order in Lua

        if not mission_widgets:
            print("No mission widgets found to write")
            return

        # Build Lua table string
        lua_lines = ["MissionPositionTable = {"]
        for i, widget in enumerate(mission_widgets):
            lua_lines.append(f"    [{i+1}] = {widget.get('mission_id', 0)},")
        lua_lines.append("}\n")

        # Read existing file
        with open(lua_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace existing MissionPositionTable or append if missing
        import re
        if "MissionPositionTable" in content:
            content = re.sub(
                r"MissionPositionTable\s*=\s*\{.*?\}\s*",
                "\n".join(lua_lines),
                content,
                flags=re.DOTALL
            )
        else:
            content += "\n" + "\n".join(lua_lines)

        # Write back
        with open(lua_file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Mission IDs written to {lua_file_path}")

    def assign_mission_ids(self):
        """Assign mission IDs to widgets and store them"""
        # Mission ID table
        mission_id_table = [
            [20001882, 20001884, 20001886, 20001888, 20001890],
            [20001835, 20001837, 20001839],
            [20001855, 20001858, 20001861, 20001864],
            [20001870, 20001872, 20001874],
            [20001832, 20001844, 20001847, 20001850]
        ]
        flat_mission_ids = [mid for campaign in mission_id_table for mid in campaign]

        # Collect widgets
        self.widgets = [w for w in self.editor_ref.renderer_window.level_data['pages'][1]['widgets'] 
                        if w.get('name', '').startswith("Mission_")]

        if len(self.widgets) != len(flat_mission_ids):
            print("Warning: Number of mission widgets does not match Lua IDs!")

        for widget, mid in zip(self.widgets, flat_mission_ids):
            widget['mission_id'] = mid

    def _get_vector_value(self, vector_obj):
        """Extract x, z values from a cGUIMetaVector object (z is used as y for 2D)"""
        try:
            # Check for mValue first (some types)
            if hasattr(vector_obj, 'mValue'):
                val = vector_obj.mValue
                if hasattr(val, 'x') and hasattr(val, 'z'):
                    # Use z as the vertical coordinate for 2D UI
                    return {'x': val.x, 'y': val.z}
                elif hasattr(val, 'x') and hasattr(val, 'y'):
                    return {'x': val.x, 'y': val.y}
                elif hasattr(val, '__iter__') and len(val) >= 2:
                    return {'x': val[0], 'y': val[1]}
            
            # Check for msVector (cGUIVectorVector type)
            if hasattr(vector_obj, 'msVector'):
                val = vector_obj.msVector
                # msVector is sVectorXZ format like "0.0,-16.0" (x, z)
                if isinstance(val, str):
                    parts = val.split(',')
                    if len(parts) >= 2:
                        # First value is X, second is Z (which we use as Y for screen)
                        return {'x': float(parts[0]), 'y': float(parts[1])}
                elif hasattr(val, 'x') and hasattr(val, 'z'):
                    return {'x': val.x, 'y': val.z}
                elif hasattr(val, 'x') and hasattr(val, 'y'):
                    return {'x': val.x, 'y': val.y}
                elif hasattr(val, '__iter__') and len(val) >= 2:
                    return {'x': val[0], 'y': val[1]}
            
            # Check for direct x, z attributes
            if hasattr(vector_obj, 'x') and hasattr(vector_obj, 'z'):
                return {'x': vector_obj.x, 'y': vector_obj.z}
            
            # Check for direct x, y attributes
            if hasattr(vector_obj, 'x') and hasattr(vector_obj, 'y'):
                return {'x': vector_obj.x, 'y': vector_obj.y}
                
        except Exception as e:
            print(f"Error extracting vector value: {e}")
            pass
        
        return None
    
    def _count_widgets(self, widgets):
        """Recursively count all widgets including children"""
        count = len(widgets)
        for widget in widgets:
            count += self._count_widgets(widget.get('children', []))
        return count
    
    def _get_lua_data(self, editor: "bw_editor.LevelEditor"):
        """Get Lua script data for Frontend2"""
        lua_data = {
            'scripts': {},
            'entity_init': {}
        }
        
        # Check if lua workbench is available
        if not hasattr(editor, 'lua_workbench') or editor.lua_workbench is None:
            print("WARNING: Lua workbench not available")
            return lua_data
        
        # Get EntityInitialise data if available
        if hasattr(editor.lua_workbench, 'entityinit'):
            lua_data['entity_init'] = dict(editor.lua_workbench.entityinit.reflection_ids)
        
        # Get script resources from level file
        if editor.level_file is not None:
            for obj_id, obj in editor.level_file.objects.items():
                if obj.type == "cGameScriptResource" and hasattr(obj, 'mName'):
                    script_name = obj.mName
                    if script_name:
                        # Try to read the script content
                        try:
                            lua_data['scripts'][script_name] = {
                                'id': obj_id,
                                'name': script_name
                            }
                        except Exception as e:
                            print(f"Error reading script {script_name}: {e}")
        
        return lua_data
    
    def unload(self):
        """Called when the plugin is unloaded"""
        # Close the renderer window if it's open
        if self.renderer_window:
            try:
                self.renderer_window.close()
            except:
                pass
        
        print("GUI Renderer plugin has been unloaded")