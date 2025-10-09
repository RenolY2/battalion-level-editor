import re
from .constants import MISSION_IDS

def parse_mission_positions(lua_content):
    """
    Parse MissionPositionTable from Lua code.
    
    Returns:
        List of campaigns, where each campaign is a list of position dicts
        Each position dict has keys: 'X', 'Y', and optionally 'ID'
    """
    position_data = []
    
    print("=" * 50)
    print("PARSING POSITIONS")
    print("=" * 50)
    
    # Find the MissionPositionTable
    pattern = r'MissionPositionTable\s*=\s*\{(.+?)\n\}'
    match = re.search(pattern, lua_content, re.DOTALL)
    
    if not match:
        print("ERROR: MissionPositionTable not found!")
        return position_data
    
    print("Found MissionPositionTable!")
    table_content = match.group(1)
    
    # Use stack-based approach to find top-level campaign arrays
    depth = 0
    campaign_start = -1
    campaigns_text = []
    
    for i, char in enumerate(table_content):
        if char == '{':
            if depth == 0:
                campaign_start = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and campaign_start != -1:
                campaigns_text.append(table_content[campaign_start:i+1])
                campaign_start = -1
    
    print(f"Found {len(campaigns_text)} campaigns")
    
    # Parse each campaign
    for campaign_idx, campaign_text in enumerate(campaigns_text):
        positions = []
        
        # Find all X/Y coordinate pairs
        for mission_idx, match in enumerate(re.finditer(
            r'\{X\s*=\s*(\d+),\s*Y\s*=\s*(\d+)\}\s*(?:,\s*)?(?:--\s*(\d+))?', 
            campaign_text
        )):
            x = int(match.group(1))
            y = int(match.group(2))
            obj_id = match.group(3)
            
            position_data_entry = {'X': x, 'Y': y}
            
            # Use parsed ID if available, otherwise use dictionary
            if obj_id:
                position_data_entry['ID'] = int(obj_id)
            elif campaign_idx in MISSION_IDS and mission_idx < len(MISSION_IDS[campaign_idx]):
                position_data_entry['ID'] = MISSION_IDS[campaign_idx][mission_idx]
            
            positions.append(position_data_entry)
        
        if positions:
            print(f"  Campaign {campaign_idx + 1}: found {len(positions)} missions")
            position_data.append(positions)
    
    print(f"Total factions parsed: {len(position_data)}")
    print("=" * 50)
    
    return position_data


def generate_lua_table(position_data):
    """
    Generate Lua MissionPositionTable code from position data.
    
    Args:
        position_data: List of campaigns with position dicts
        
    Returns:
        String containing the Lua table code
    """
    table_lines = ["MissionPositionTable = {"]
    
    for campaign_idx, campaign_positions in enumerate(position_data):
        table_lines.append("  {")
        
        for pos_idx, pos in enumerate(campaign_positions):
            x = pos['X']
            y = pos['Y']
            comma = "," if pos_idx < len(campaign_positions) - 1 else ""
            
            # Include ID comment if available
            if 'ID' in pos and pos['ID'] is not None:
                obj_id = pos['ID']
                table_lines.append(f"    {{X = {x}, Y = {y}}}{comma} -- {obj_id}")
            else:
                table_lines.append(f"    {{X = {x}, Y = {y}}}{comma}")
        
        comma = "," if campaign_idx < len(position_data) - 1 else ""
        table_lines.append(f"  }}{comma}")
    
    table_lines.append("}")
    
    return "\n".join(table_lines)


def update_lua_content(original_content, position_data):
    """
    Update Lua content with new position data.
    
    Args:
        original_content: Original Lua file content
        position_data: Updated position data
        
    Returns:
        Updated Lua content string
    """
    new_table = generate_lua_table(position_data)
    
    # Replace old table with new one
    pattern = r'MissionPositionTable\s*=\s*\{.+?\n\}'
    updated_content = re.sub(pattern, new_table, original_content, flags=re.DOTALL)
    
    return updated_content