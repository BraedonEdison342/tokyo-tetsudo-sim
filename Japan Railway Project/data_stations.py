import json

def load_json(file_path):
    """Loads a JSON file with UTF-8 encoding."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def node_cord(elements, f):
    """Returns a dictionary mapping rounded (lat, lon) to Node ID."""
    cords = {}
    for node in elements:
        lat = node.get('lat')
        lon = node.get('lon')
        node_id = node.get('id')
        if lat and lon:
            # Rounding to 4 decimal places (~11m precision) to match track data
            cords[(round(lat, 3), round(lon, 3))] = node_id
    return cords

if __name__ == "__main__":
    print("📍 Loading Station Data...")
    try:
        station_data = load_json("OSM_data/tokyo_railway_station.json")
        station_elements = station_data.get('elements', [])
        
        station_map = node_cord(station_elements, None)
        print(f"Successfully mapped {len(station_map)} station locations.")
        
        # Example: Print the first 5 stations found
        for i, (coords, node_id) in enumerate(station_map.items()):
            print(f"ID: {node_id} at {coords}")
            if i >= 4: break
            
    except FileNotFoundError:
        print("Error: 'tokyo_railway_station.json' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")