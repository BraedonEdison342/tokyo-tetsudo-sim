import os
import requests
import json

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bounding Box covering Tokyo, Kanagawa (Yokohama), Saitama, and Chiba
# Format: [south, west, north, east]
BBOX = "35.15,139.15,36.05,140.55"

# Query 1: Only fetch stations within the Greater Tokyo bounding box
STATIONS_QUERY = f"""
[out:json][timeout:120];
(
  node["railway"="station"]({BBOX});
);
out body;
"""

# Query 2: Fetch physical tracks along with their internal coordinate nodes
# Query 2: Fetch physical tracks with inline geometry arrays
RAILS_QUERY = f"""
[out:json][timeout:240];
(
  way["railway"~"rail|subway|light_rail|tram|monorail"]({BBOX});
);
out geom;
"""

HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'GreaterTokyoTransitEngine/2.5 (developer-workspace)'
}

def fetch_and_save(query, output_filename, data_type):
    print(f"📡 Querying Overpass API for Greater Tokyo {data_type}...")
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, headers=HEADERS)
        
        if response.status_code == 200:
            raw_data = response.json()
            elements_count = len(raw_data.get('elements', []))
            
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=4)
                
            print(f"✅ Success! Saved {elements_count} {data_type} elements to '{output_filename}'\n")
        else:
            print(f"❌ Failed to fetch {data_type}. Server responded with Code {response.status_code}")
            print(f"Details: {response.text}\n")
            
    except Exception as e:
        print(f"❌ An error occurred during the transmission of {data_type}: {e}\n")

def main():
    # Make sure the target directory exists
    os.makedirs("OSM_data", exist_ok=True)
    
    print("🚀 Starting Greater Tokyo Regional Railway Extraction Engine\n")
    
    # 1. Fetch and process Stations
    stations_file = "OSM_data/tokyo_railway_stations.json"
    fetch_and_save(STATIONS_QUERY, stations_file, "STATIONS")
    
    # 2. Fetch and process Rail Tracks
    rails_file = "OSM_data/tokyo_railway_raw.json"
    fetch_and_save(RAILS_QUERY, rails_file, "RAILS (TRACK SECTIONS)")

if __name__ == "__main__":
    main()