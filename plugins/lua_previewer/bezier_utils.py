import math

def quadratic_bezier(x1, y1, x2, y2, gap, segments, reverse_perpendicular=False):
    """
    Generate points along a quadratic bezier curve.
    Matches the game's QuadraticBezier function.
    """
    points = []
    
    # Calculate midpoint
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    
    # Calculate perpendicular offset for control point
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    
    if length == 0:
        return points
    
    # Perpendicular vector
    perp_x = -dy / length
    perp_y = dx / length
    
    if reverse_perpendicular:
        perp_x = -perp_x
        perp_y = -perp_y
    
    # Control point offset by 'gap'
    ctrl_x = mid_x + perp_x * gap
    ctrl_y = mid_y + perp_y * gap
    
    # Generate curve points
    for i in range(segments + 1):
        t = i / segments
        one_minus_t = 1 - t
        
        x = (one_minus_t * one_minus_t * x1 + 
             2 * one_minus_t * t * ctrl_x + 
             t * t * x2)
        
        y = (one_minus_t * one_minus_t * y1 + 
             2 * one_minus_t * t * ctrl_y + 
             t * t * y2)
        
        points.append((x, y))
    
    return points