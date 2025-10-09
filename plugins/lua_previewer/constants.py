# Mission object IDs per campaign
MISSION_IDS = {
    0: [20001882, 20001884, 20001886, 20001888, 20001890],  # Solar Empire
    1: [20001835, 20001837, 20001839],                       # Western Frontier
    2: [20001855, 20001858, 20001861, 20001864],            # Anglo Isles
    3: [20001870, 20001872, 20001874],                       # Iron Legion
    4: [20001832, 20001844, 20001847, 20001850]             # Tundran Territories
}

# Bezier gap values per faction (SE, WF, AI, IL, TT)
FACTION_GAPS = [12, 20, 12, 12, 12]

# Faction names and abbreviations
FACTION_NAMES = [
    "Solar Empire",
    "Western Frontier", 
    "Anglo Isles",
    "Iron Legion",
    "Tundran Territories"
]

FACTION_ABBR = ["SE", "WF", "AI", "IL", "TT"]

# Background position, scale, and rotation for each campaign
BACKGROUND_SETTINGS = {
    0: {'x': -40, 'y': -140, 'scale': 1.95, 'rotation': 0},       # Solar Empire
    1: {'x': 640, 'y': 190, 'scale': 2.45, 'rotation': 5},       # Western Frontier
    2: {'x': -930, 'y': -380, 'scale': 2.50, 'rotation': 0},       # Anglo Isles
    3: {'x': -490, 'y': -10, 'scale': 2.00, 'rotation': 15},       # Iron Legion
    4: {'x': 310, 'y': 220, 'scale': 2.45, 'rotation': 10}       # Tundran Territories
}