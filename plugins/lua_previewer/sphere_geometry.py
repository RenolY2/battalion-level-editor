import math

def create_sphere_body(radius, slices, stacks, polar_cutoff=0.15):
    """
    Generate sphere body (cylindrical middle section, excluding poles).
    polar_cutoff: fraction of sphere to exclude at top/bottom (0.0-0.5)
    """
    vertices = []
    texcoords = []
    indices = []
    
    # Only generate middle section, skip polar regions
    start_stack = int(stacks * polar_cutoff)
    end_stack = int(stacks * (1.0 - polar_cutoff))
    
    for stack in range(start_stack, end_stack + 1):
        phi = math.pi * stack / stacks
        
        for slice in range(slices + 1):
            theta = 2 * math.pi * slice / slices
            
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            
            vertices.append((x, y, z))
            
            u = 1.0 - (slice / slices)
            v = 1.0 - (stack / stacks)
            texcoords.append((u, v))
    
    # Generate indices for the body section
    adjusted_stacks = end_stack - start_stack
    for stack in range(adjusted_stacks):
        for slice in range(slices):
            first = stack * (slices + 1) + slice
            second = first + slices + 1
            
            indices.append((first, second, first + 1))
            indices.append((second, second + 1, first + 1))
    
    return vertices, texcoords, indices


def create_pole_cap(radius, segments, is_north=True, polar_cutoff=0.15):
    """
    Generate geometry for a polar cap with smooth transition.
    """
    vertices = []
    texcoords = []
    indices = []
    
    rings = 5  # More rings = smoother pole
    
    if is_north:
        phi_start = 0
        phi_end = math.pi * polar_cutoff
    else:
        phi_start = math.pi * (1.0 - polar_cutoff)
        phi_end = math.pi
    
    # Generate vertices in rings from pole to edge
    for ring in range(rings + 1):
        phi = phi_start + (phi_end - phi_start) * (ring / rings)
        y = radius * math.cos(phi)
        ring_radius = radius * math.sin(phi)
        
        # V coordinate: from center (0.5) to edge (0 or 1)
        v_param = ring / rings
        
        for seg in range(segments + 1):
            theta = 2 * math.pi * seg / segments
            x = ring_radius * math.cos(theta)
            z = ring_radius * math.sin(theta)
            
            vertices.append((x, y, z))
            
            # UV from center to edge
            u = 0.5 + (v_param * 0.5) * math.cos(theta)
            v = 0.5 + (v_param * 0.5) * math.sin(theta)
            texcoords.append((u, v))
    
    # Generate quad indices between rings
    for ring in range(rings):
        for seg in range(segments):
            first = ring * (segments + 1) + seg
            second = first + segments + 1
            
            indices.append((first, second, first + 1))
            indices.append((second, second + 1, first + 1))
    
    return vertices, texcoords, indices