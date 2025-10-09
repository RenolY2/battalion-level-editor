import os
import multiprocessing
from typing import TYPE_CHECKING
import time
import threading

if TYPE_CHECKING:
    import bw_editor


class Plugin(object):
    def __init__(self):
        self.name = "Mission Mover v1.0"
        self.actions = [("Select Campaign Lua", self.open_lua_previewer)]
        print("Lua Script Previewer plugin has been initialized")
        
        self.previewer_process = None
        self.editor_ref = None
        self.update_queue = None
        self.monitor_thread = None
        self.monitoring = False
        
    def open_lua_previewer(self, editor: "bw_editor.LevelEditor"):
        """Open the Lua Script Previewer in a separate process"""
        self.editor_ref = editor
        
        print("Launching Lua Script Previewer...")
        
        try:
            from plugins.lua_previewer.bw2_lua_previewer import main
            
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            assets_path = os.path.join(plugin_dir, "lua_previewer", "assets")
            
            # Create queue for inter-process communication
            self.update_queue = multiprocessing.Queue()
            
            # Start monitoring thread to check for updates
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_updates, daemon=True)
            self.monitor_thread.start()
            
            process = multiprocessing.Process(
                target=main, 
                args=([], assets_path, self.update_queue)
            )
            process.daemon = True
            process.start()
            self.previewer_process = process
            
            print(f"Lua Script Previewer opened as process: {self.previewer_process.pid}")
            print(f"Assets path: {assets_path}")
        except Exception as e:
            print(f"Error opening Lua Script Previewer: {str(e)}")
    
    def _monitor_updates(self):
        """Monitor the queue for position updates from the previewer"""
        while self.monitoring:
            try:
                if not self.update_queue.empty():
                    campaign_idx, positions = self.update_queue.get_nowait()
                    self._update_xml_positions(campaign_idx, positions)
            except Exception as e:
                print(f"Error monitoring updates: {e}")
            time.sleep(0.1)
    
    def _update_xml_positions(self, campaign_idx, positions):
        """Update the XML objects when Lua positions change"""
        
        try:
            level = self.editor_ref.level_file
            
            if not level:
                print("No level file loaded")
                return
            
            # Track if any changes were made
            changes_made = False
            
            # Update each position
            for pos in positions:
                if 'ID' in pos:
                    obj_id = str(pos['ID'])
                    new_x = float(pos['X'])
                    new_y = float(pos['Y'])
                    
                    try:
                        obj = level.objects.get(obj_id)
                        
                        if obj and hasattr(obj, 'type') and obj.type == "cGUIVectorVector":
                            if hasattr(obj, 'msVector'):
                                vec = obj.msVector
                                
                                # Check if values actually changed before updating
                                current_x = vec.x if hasattr(vec, 'x') else (vec[0] if isinstance(vec, (tuple, list)) else None)
                                current_y = vec.z if hasattr(vec, 'z') else (vec[2] if isinstance(vec, (tuple, list)) else None)
                                
                                if current_x != new_x or current_y != new_y:
                                    # Update based on type
                                    if hasattr(vec, 'x') and hasattr(vec, 'z'):
                                        vec.x = new_x
                                        vec.z = new_y
                                    elif isinstance(vec, tuple):
                                        obj.msVector = (new_x, 0, new_y, 0)
                                    elif isinstance(vec, list):
                                        obj.msVector[0] = new_x
                                        obj.msVector[2] = new_y
                                    
                                    print(f"Updated object {obj_id}: X={new_x}, Y={new_y}")
                                    changes_made = True
                                    
                                    # Mark as dirty
                                    if hasattr(obj, 'dirty'):
                                        obj.dirty = True
                                    
                                    # Update XML
                                    if hasattr(obj, 'update_xml'):
                                        obj.update_xml()
                            
                    except Exception as e:
                        print(f"Error updating object {obj_id}: {e}")
                        import traceback
                        traceback.print_exc()
            
            # Only mark as unsaved if changes were actually made
            if changes_made and hasattr(self.editor_ref, 'set_has_unsaved_changes'):
                self.editor_ref.set_has_unsaved_changes(True)
                        
        except Exception as e:
            print(f"Error in _update_xml_positions: {e}")
            import traceback
            traceback.print_exc()

    def unload(self):
        """Called when the plugin is unloaded"""
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        
        if self.previewer_process:
            try:
                self.previewer_process.terminate()
            except:
                pass
        
        print("Lua Script Previewer plugin has been unloaded")