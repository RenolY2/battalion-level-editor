from PIL import Image, ImageTk, ImageDraw

def create_military_background(width, height):
    """Create a military-themed background for the application
    
    Args:
        width (int): Width of the background image
        height (int): Height of the background image
        
    Returns:
        PhotoImage: Tkinter-compatible image for use as background
    """
    # Create a dark background with some texture
    bg = Image.new('RGB', (width, height), (40, 42, 45))
    
    # Draw some subtle grid lines
    draw = ImageDraw.Draw(bg)
    
    # Grid lines
    grid_spacing = 30
    grid_color = (60, 62, 65)
    
    for x in range(0, width, grid_spacing):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
    
    for y in range(0, height, grid_spacing):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
    
    # Add some diagonal stripes in corners for a military feel
    stripe_color = (70, 72, 75)
    for i in range(0, 100, 10):
        # Top left corner
        draw.line([(0, i), (i, 0)], fill=stripe_color, width=3)
        # Bottom right corner
        draw.line([(width-i, height), (width, height-i)], fill=stripe_color, width=3)
    
    # Convert to PhotoImage for Tkinter
    photo = ImageTk.PhotoImage(bg)
    return photo