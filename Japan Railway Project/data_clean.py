import json

with open('OSM_data/tokyo_railway_raw.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

def is_commuter_track(element):
    # 1. First, get the tags. If there are no tags, we can't verify it, so skip.
    tags = element.get('tags', {})
    
    # 2. Basic Infrastructure Check: 
    # We want standard rails and subways. We skip 'abandoned' or 'construction'.
    railway_type = tags.get('railway')
    if railway_type not in ['rail', 'subway', 'light_rail', 'monorail']:
        return False

    # 3. The "Usage" Rule:
    # We want tracks that carry the actual 670k+ daily commuters.
    usage = tags.get('usage')
    service = tags.get('service')

    # LOGIC: Keep it if it's a 'main' or 'branch' line.
    # ALSO: Keep it if it's a 'crossover' (even if it's not 'main'), 
    # because trains need these to switch tracks!
    if usage in ['main', 'branch'] or service == 'crossover':
        return True
    
    # 4. The "Siding" Safety Net:
    # If a track is marked as a 'siding', 'yard', or 'spur', it's a dead end.
    # In a simulation, these act as "traps" for your algorithms.
    if service in ['siding', 'yard', 'spur']:
        return False

    # If it's none of the above, we'll keep it just in case, 
    # provided it's at least a 'rail' or 'subway'.
    return True

# Apply our refined rules
data['elements'] = [x for x in data['elements'] if is_commuter_track(x)]

with open('tokyo_railway_cleaned.json', 'w', encoding='utf-8') as file:
    json.dump(data, file, indent=4, ensure_ascii=False)

print(f"Done! Refined to {len(data['elements'])} high-priority commuter entries.")