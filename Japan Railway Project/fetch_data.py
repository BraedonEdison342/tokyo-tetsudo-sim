import requests
import json

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass Query: Isolate mainline tracks inside the Tokyo boundary
query = """
[out:json][timeout:120];
area["name:en"="Tokyo"]->.searchArea;
(
  node["railway"="station"](area.searchArea);
);
out geom;
"""

# Custom headers to bypass anti-scraping rules
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'TokyoTransitResilienceEngine/1.0 (developer-workspace)'
}

def main():
    print("📡 Connecting to Overpass API to fetch Tokyo railway data...")
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, headers=headers)
        
        if response.status_code == 200:
            raw_data = response.json()
            
            output_file = "OSM_data/tokyo_railway_station.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=4)
                
            elements_count = len(raw_data.get('elements', []))
            print(f"✅ Success! Saved {elements_count} track segments to '{output_file}'")
        else:
            print(f"❌ Failed. Server responded with Status Code {response.status_code}")
            print(f"Details: {response.text}")
            
    except Exception as e:
        print(f"❌ An error occurred during transmission: {e}")

if __name__ == "__main__":
    main()