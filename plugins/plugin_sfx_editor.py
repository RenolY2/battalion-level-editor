import os
import sys
import subprocess
import multiprocessing
from typing import TYPE_CHECKING
from plugins.sfx_editor.main import main

if TYPE_CHECKING:
    import bw_editor


class Plugin(object):
    def __init__(self):
        # Basic plugin setup
        self.name = "SFX Editor"
        self.actions = [("Open SFX Editor", self.open_sfx_editor),
                        ("Edit Level SFX", self.edit_level_sfx)]
        print("SFX Editor plugin has been initialized")
        
        # Store a reference to the process
        self.sfx_process = None
        self.effect_name = None
        self.editor_ref = None
        
    def open_sfx_editor(self, editor: "bw_editor.LevelEditor"):
        """Open the SFX Editor in a separate process"""
        self.editor_ref = editor
        
        # Path to the sfx_editor directory
        sfx_editor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx_editor")
        
        # Path to the main.py script in sfx_editor
        main_script = os.path.join(sfx_editor_dir, "main.py")

        print("Trying to launch editor")
        print("editor dir", sfx_editor_dir)
        print("main", main_script)

        # Start the editor as a separate process
        try:
            process = multiprocessing.Process(target=main, args=[[]])

            process.daemon = True
            process.start()
            self.sfx_process = process
            
            print(f"SFX Editor opened as process: {self.sfx_process.pid}")
        except Exception as e:
            print(f"Error opening SFX Editor: {str(e)}")
    
    def edit_level_sfx(self, editor: "bw_editor.LevelEditor"):
        """Open the SFX Editor with the selected effect loaded"""
        # Find if any selected object is a special effect
        selected = editor.level_view.selected
        effect_name = None
        
        for obj in selected:
            if obj.type == "cTequilaEffectResource":
                effect_name = obj.mName
                break
        
        if effect_name:
            # Store the effect name for later
            self.effect_name = effect_name
            self.editor_ref = editor
            
            # Path to the sfx_editor directory
            sfx_editor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx_editor")
            
            # Try alternative access paths
            try:
                # First try the original path
                res = editor.file_menu.resource_archive
            except AttributeError:
                # Try the direct attribute
                if hasattr(editor, 'resource_archive'):
                    res = editor.resource_archive
                # Try nested in level_data
                elif hasattr(editor.file_menu, 'level_data') and hasattr(editor.file_menu.level_data, 'resource_archive'):
                    res = editor.file_menu.level_data.resource_archive
                # If none work, print debug info
                else:
                    print("DEBUG: editor attributes:", [attr for attr in dir(editor) if not attr.startswith('_')])
                    print("DEBUG: file_menu attributes:", [attr for attr in dir(editor.file_menu) if not attr.startswith('_')])
                    # Fallback
                    print("Could not find resource_archive, opening editor without file")
                    self.open_sfx_editor(editor)
                    return
            
            try:
                # Check if the effect is in the resource archive
                resource = res.get_resource(b"FEQT", effect_name)
                
                if resource:
                    # Create a temp directory if it doesn't exist
                    temp_dir = os.path.join(sfx_editor_dir, "temp")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    # Extract the effect to a temporary file
                    temp_path = os.path.join(temp_dir, f"{effect_name}.txt")
                    
                    with open(temp_path, "wb") as f:
                        f.write(resource.data)
                    
                    # Open the editor with the file specified
                    try:
                        print(os.path.join(sfx_editor_dir, "main.py"), temp_path)
                        process = multiprocessing.Process(target=main, args=[[os.path.join(sfx_editor_dir, "main.py"), temp_path]])

                        process.daemon = True
                        process.start()
                        self.sfx_process = process

                        print(f"SFX Editor opened with effect {effect_name}")
                    except Exception as e:
                        print(f"Error opening SFX Editor: {str(e)}")
                        # Fall back to opening without a file
                        self.open_sfx_editor(editor)
                else:
                    print(f"ERROR: Effect {effect_name} not found in resource archive")
                    # Open the editor anyway without a file
                    self.open_sfx_editor(editor)
            except Exception as e:
                print(f"Error accessing resource: {str(e)}")
                # Open the editor anyway without a file
                self.open_sfx_editor(editor)
        else:
            print("NO EFFECT SELECTED. SELECT A SPECIAL EFFECT IN THE EDITOR FIRST.")
            # Open editor anyway
            self.open_sfx_editor(editor)

    def before_save(self, editor):
        """Called before the level is saved"""
        # Check if we need to update an effect in the resource archive
        if self.effect_name and self.editor_ref:
            try:
                # Path to the temporary file
                sfx_editor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx_editor")
                temp_path = os.path.join(sfx_editor_dir, "temp", f"{self.effect_name}.txt")
                
                if os.path.exists(temp_path):
                    # Read the file content
                    with open(temp_path, 'rb') as file:
                        binary_data = file.read()
                    
                    # Get the resource
                    res = self.editor_ref.file_menu.resource_archive
                    resource = res.get_resource(b"FEQT", self.effect_name)
                    
                    if resource:
                        # Update the resource in the archive
                        resource.data = binary_data
                        
                        # Mark editor as having unsaved changes
                        self.editor_ref.set_has_unsaved_changes(True)
                        
                        print(f"Effect {self.effect_name} updated in resource archive")
            except Exception as e:
                print(f"Error updating effect: {str(e)}")
    
    def unload(self):
        """Called when the plugin is unloaded"""
        # Terminate the SFX editor process if it's running
        if self.sfx_process:
            try:
                self.sfx_process.terminate()
            except:
                pass
        
        print("SFX Editor plugin has been unloaded")