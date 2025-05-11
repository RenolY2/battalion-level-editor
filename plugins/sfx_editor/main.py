import tkinter as tk
import sys
from particle_editor import ParticleEffectEditor

if __name__ == "__main__":
    root = tk.Tk()
    app = ParticleEffectEditor(root)
    
    # Check if a file path was provided as an argument
    if len(sys.argv) > 1:
        # Load the specified file
        file_path = sys.argv[1]
        app.file_path = file_path
        app.file_label.config(text=file_path.split('/')[-1].split('\\')[-1])
        
        # Read the file content
        try:
            with open(file_path, 'r') as file:
                app.file_content = file.read()
            
            # Display the content and extract parameters
            app.display_file_content()
            app.extract_editable_values()
            app.extract_parameters()
            
            # Update status
            app.status_var.set(f"LOADED: {file_path}")
        except Exception as e:
            app.status_var.set(f"ERROR: {str(e)}")
    
    root.mainloop()