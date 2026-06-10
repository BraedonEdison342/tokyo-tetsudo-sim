import json
import math
import heapq
# import folium
from data_stations import *

def load_json(file_path):
    """Loads a JSON file with UTF-8 encoding."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def create_node_to_way_index(elements):
    """Maps every node ID to a list of way IDs it belongs to."""
    node_to_way_map = {}
    for element in elements:
        way_id = element['id']
        nodes = element.get('nodes', [])
        for node_id in nodes:
            if node_id not in node_to_way_map:
                node_to_way_map[node_id] = []
            node_to_way_map[node_id].append(way_id)
    return node_to_way_map

def get_dead_end_coordinates(elements, node_to_way_map):
    """Identifies nodes used by only one way and extracts their latitude/longitude."""
    dead_end_ids = {node_id for node_id, ways in node_to_way_map.items() if len(ways) == 1}
    dead_end_coords = {}
    for element in elements:
        nodes = element.get('nodes', [])
        geometry = element.get('geometry', [])
        if not nodes or not geometry:
            continue
        if nodes[0] in dead_end_ids: 
            dead_end_coords[nodes[0]] = geometry[0]
        if nodes[-1] in dead_end_ids: 
            dead_end_coords[nodes[-1]] = geometry[-1]
    return dead_end_coords

def bin_spatially(coordinates_dict, precision, is_station=False):
    """Groups node IDs into buckets based on rounded coordinates."""
    if is_station:
        # Pass precision down to node_cord to fix the hardcoded precision-4 bug
        return node_cord(coordinates_dict, precision)
    
    spatial_bins = {}
    for node_id, position in coordinates_dict.items():
        bucket_key = (round(position['lat'], precision), round(position['lon'], precision))
        if bucket_key not in spatial_bins: 
            spatial_bins[bucket_key] = []
        spatial_bins[bucket_key].append(node_id)
    return spatial_bins

def calculate_haversine_distance(lat_1, lon_1, lat_2, lon_2):
    """Calculates the great-circle distance between two GPS coordinates in meters."""
    lat_1, lon_1 = math.radians(lat_1), math.radians(lon_1)
    lat_2, lon_2 = math.radians(lat_2), math.radians(lon_2)
    
    delta_lat = lat_1 - lat_2
    delta_lon = lon_1 - lon_2
    
    a = (math.sin(delta_lat / 2) ** 2) + \
        math.cos(lat_1) * math.cos(lat_2) * (math.sin(delta_lon / 2) ** 2)
        
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    earth_radius_meters = 6371000
    return earth_radius_meters * c

def build_adjacency_list(elements, spatial_bins, wider_spatial_bins, station_bins, track_coordinates, way_name_map):
    """
    Builds a weighted adjacency list representing the railway network.
    Structure: adjacency_list[node_u] = { node_v: (distance_in_meters, line_name) }
    """
    adjacency_list = {}

    # 1. Standard Track Connections
    for element in elements:
        if element.get('type') != 'way': 
            continue
        if element.get('service') == 'crossover': 
            continue
        if element.get('service') == 'yard': 
            continue
            
        nodes = element.get('nodes', [])
        tags = element.get('tags', {})
        line_name = way_name_map.get(element['id'], "Unknown Line")
        is_oneway = tags.get('oneway') == 'yes'

        for i in range(len(nodes) - 1):
            u, v = nodes[i], nodes[i + 1]
            
            # Fetch GPS coordinates for both nodes
            pos_u = track_coordinates.get(u)
            pos_v = track_coordinates.get(v)
            
            if pos_u and pos_v:
                distance = calculate_haversine_distance(pos_u['lat'], pos_u['lon'], pos_v['lat'], pos_v['lon'])
            else:
                distance = 1.0  # Fallback weight if coordinates are missing

            # Initialize sub-dictionaries
            if u not in adjacency_list: adjacency_list[u] = {}
            if v not in adjacency_list: adjacency_list[v] = {}

            # Assign weighted connections WITH line identity
            adjacency_list[u][v] = (distance, line_name)
            if not is_oneway:
                adjacency_list[v][u] = (distance, line_name)

    # 2. Dead-End Bridges (Track-to-Track gaps)
    for bucket_key, nodes in spatial_bins.items():
        if len(nodes) > 1:
            for u in nodes:
                for v in nodes:
                    if u != v:
                        pos_u, pos_v = track_coordinates.get(u), track_coordinates.get(v)
                        if pos_u and pos_v:
                            distance = calculate_haversine_distance(pos_u['lat'], pos_u['lon'], pos_v['lat'], pos_v['lon'])
                        else:
                            distance = 1.0
                            
                        if u not in adjacency_list: adjacency_list[u] = {}
                        if v not in adjacency_list: adjacency_list[v] = {}
                        
                        adjacency_list[u][v] = (distance, "Internal Transfer")
                        adjacency_list[v][u] = (distance, "Internal Transfer")

    # 3. Station Gateways (Fuzzy Linking to prevent overshooting)
    station_bridge_penalty = 50.0
    
    # We loop through station_bins instead of track bins to ensure 
    # every station gets a chance to find a track.
    for bucket_key, stations_list in station_bins.items():
        if isinstance(stations_list, int): stations_list = [stations_list]
        
        # Look in the station's bucket AND all 8 surrounding buckets for tracks
        lat_step, lon_step = 0.001, 0.001 # Matches Precision 3
        
        for i in [-lat_step, 0, lat_step]:
            for j in [-lon_step, 0, lon_step]:
                neighbor_key = (round(bucket_key[0] + i, 3), round(bucket_key[1] + j, 3))
                
                if neighbor_key in wider_spatial_bins:
                    track_nodes = wider_spatial_bins[neighbor_key]
                    
                    for s_id in stations_list:
                        for t_id in track_nodes:
                            if t_id not in adjacency_list: adjacency_list[t_id] = {}
                            if s_id not in adjacency_list: adjacency_list[s_id] = {}
                            
                            # Link track to station
                            adjacency_list[t_id][s_id] = (station_bridge_penalty, "Station Link")
                            adjacency_list[s_id][t_id] = (station_bridge_penalty, "Station Link")

        # 4. Link multiple platform nodes together (The "Nippori Hub" Fix)
        if len(stations_list) > 1:
            for i in range(len(stations_list)):
                for j in range(i + 1, len(stations_list)):
                    s1, s2 = stations_list[i], stations_list[j]
                    adjacency_list.setdefault(s1, {})[s2] = (10.0, "Internal Transfer")
                    adjacency_list.setdefault(s2, {})[s1] = (10.0, "Internal Transfer")
        
    return adjacency_list

def build_adjacency_list_optimized(elements, spatial_bins, wider_spatial_bins, station_bins, track_coordinates, way_name_map, station_elements , node_to_way_index):
    """
    Builds a weighted adjacency list representing the railway network.
    Structure: adjacency_list[node_u] = { node_v: (distance_in_meters, line_name) }
    """
    station_name_map = create_way_name_map(station_elements)
    adjacency_list = {}
    way_ref_map = create_way_ref_map(elements)
    station_ref_map = create_way_ref_map(station_elements)
    
    # Fast lookup dictionary for station GPS
    station_coords = {el['id']: {'lat': el['lat'], 'lon': el['lon']} for el in station_elements}
    
    name_to_ref = {
        # === JR EAST (MAIN COMMUTER NETWORK) ===
        "Yamanote Line": ["JY"],
        
        # Chuo Line Variants (Macron & Standard)
        "Chūō Line": ["JC"],
        "Chuo Line": ["JC"],
        "Chūō Line (Rapid)": ["JC"],
        "Chuo Line (Rapid)": ["JC"],
        "Chūō-Sōbu Line": ["JB"],
        "Chuo-Sobu Line": ["JB"],
        "Chūō-Sōbu Line Local": ["JB"],
        "Chuo-Sobu Line Local": ["JB"],
        
        # Keihin-Tohoku & Negishi
        "Keihin-Tōhoku Line": ["JK"],
        "Keihin-Tohoku Line": ["JK"],
        "Negishi Line": ["JK"],
        
        # Saikyo & Shonan-Shinjuku
        "Saikyō Line": ["JA"],
        "Saikyo Line": ["JA"],
        "Shōnan-Shinjuku Line": ["JS"],
        "Shonan-Shinjuku Line": ["JS"],
        
        # Tokaido / Ueno-Tokyo / Takasaki / Utsunomiya Corridors
        "Tōkaidō Line": ["JT"],
        "Tokaido Line": ["JT"],
        "Ueno-Tokyo Line": ["JU"],
        "Takasaki Line": ["JU"],
        "Utsunomiya Line": ["JU"],
        "Tōhoku Main Line": ["JU"],
        "Tohoku Main Line": ["JU"],
        
        # Sobu Main & Yokosuka Extensions
        "Sōbu Rapid Line": ["JO"],
        "Sobu Rapid Line": ["JO"],
        "Sōbu Main Line": ["JO"],
        "Sobu Main Line": ["JO"],
        "Yokosuka Line": ["JO"],
        
        # Joban Line
        "Jōban Line": ["JJ"],
        "Joban Line": ["JJ"],
        "Jōban Line (Rapid)": ["JJ"],
        "Joban Line (Rapid)": ["JJ"],
        "Jōban Line (Local)": ["JL"],
        "Joban Line (Local)": ["JL"],
        
        # Peripheral Commuter Outer Loops
        "Musashino Line": ["JM"],
        "Keiyō Line": ["JE"],
        "Keiyo Line": ["JE"],
        "Yokohama Line": ["JH"],
        "Nambu Line": ["JN"],
        "Tsurumi Line": ["JI"],
        "Sagami Line": ["JH"],
        "Hachikō Line": ["JR"],
        "Hachiko Line": ["JR"],
        "Itsukaichi Line": ["JC"],
        "Ōme Line": ["JC"],
        "Ome Line": ["JC"],

        # === TOKYO METRO SUBWAYS ===
        "Tokyo Metro Ginza Line": ["G"],
        "Tokyo Metro Marunouchi Line": ["M"],
        "Tokyo Metro Hibiya Line": ["H"],
        "Tokyo Metro Tōzai Line": ["T"],
        "Tokyo Metro Tozai Line": ["T"],
        "Tokyo Metro Chiyoda Line": ["C"],
        "Tokyo Metro Yūrakuchō Line": ["Y"],
        "Tokyo Metro Yurakucho Line": ["Y"],
        "Tokyo Metro Hanzōmon Line": ["Z"],
        "Tokyo Metro Hanzomon Line": ["Z"],
        "Tokyo Metro Namboku Line": ["N"],
        "Tokyo Metro Fukutoshin Line": ["F"],

        # === TOEI SUBWAYS ===
        "Toei Asakusa Line": ["A"],
        "Toei Mita Line": ["I"],
        "Toei Shinjuku Line": ["S"],
        "Toei Ōedo Line": ["E"],
        "Toei Oedo Line": ["E"],

        # === PRIVATE RAILWAYS (MAJOR GREATER TOKYO COMMUTER NETWORKS) ===
        # Odakyu
        "Odakyu Odawara Line": ["OH"],
        "Odakyu Enoshima Line": ["OE"],
        "Odakyu Tama Line": ["OT"],
        
        # Keio
        "Keiō Line": ["KO"],
        "Keio Line": ["KO"],
        "Keiō New Line": ["KO"],
        "Keio New Line": ["KO"],
        "Keiō Sagamihara Line": ["KO"],
        "Keio Sagamihara Line": ["KO"],
        "Keiō Inokashira Line": ["IN"],
        "Keio Inokashira Line": ["IN"],
        
        # Seibu
        "Seibu Ikebukuro Line": ["SI"],
        "Seibu Shinjuku Line": ["SS"],
        "Seibu Haijima Line": ["SS"],
        "Seibu Tamako Line": ["ST"],
        "Seibu Kokubunji Line": ["SK"],
        
        # Tobu
        "Tobu Skytree Line": ["TS"],
        "Tobu Isesaki Line": ["TI"],
        "Tobu Tojo Line": ["TJ"],
        "Tōbu Tōjō Line": ["TJ"],
        "Tobu Noda Line": ["TD"],
        "Tobu Urban Park Line": ["TD"],
        
        # Keisei (Chiba Connections)
        "Keisei Main Line": ["KS"],
        "Keisei Oshiage Line": ["KS"],
        "Keisei Chiba Line": ["KS"],
        
        # Tokyu (Kanagawa/Yokohama Connections)
        "Tokyu Toyoko Line": ["TY"],
        "Tōkyū Tōyoko Line": ["TY"],
        "Tokyu Den-en-toshi Line": ["DT"],
        "Tokyu Meguro Line": ["MG"],
        "Tokyu Oimachi Line": ["OM"],
        "Tokyu Ikegami Line": ["IK"],
        
        # Keikyu (South Tokyo / Yokohama Gateway)
        "Keikyu Main Line": ["KK"],
        "Keikyū Main Line": ["KK"],
        "Keikyu Airport Line": ["KK"],
        "Keikyu Kurihama Line": ["KK"],
        
        # Other Express / Transit Lines
        "Tsukuba Express": ["TX"],
        "Tokyo Monorail": ["MO"],
        "Rinkai Line": ["R"],
        "Yurikamome": ["U"]
    }
    
    for node in elements:
        tags = node.get('tags', {})
        name = tags.get('name:en') or tags.get('name:ja')
        ref = tags.get('ref')

        if ref and name:
            ref = ref.split(";")
            if name not in name_to_ref:
                name_to_ref[name] = ref
                
    # 1. Standard Track Connections
    for element in elements:
        if element.get('type') != 'way': 
            continue
        if element.get('service') == 'yard': 
            continue
            
        nodes = element.get('nodes', [])
        tags = element.get('tags', {})
        line_name = way_name_map.get(element['id'], "Unknown Line")
        is_oneway = tags.get('oneway') == 'yes'

        for i in range(len(nodes) - 1):
            u, v = nodes[i], nodes[i + 1]
            
            # Fetch GPS coordinates for both nodes
            pos_u = track_coordinates.get(u)
            pos_v = track_coordinates.get(v)
            
            if pos_u and pos_v:
                distance = calculate_haversine_distance(pos_u['lat'], pos_u['lon'], pos_v['lat'], pos_v['lon'])
            else:
                distance = 400 # Fallback weight if coordinates are missing

            # Initialize sub-dictionaries
            if u not in adjacency_list: adjacency_list[u] = {}
            if v not in adjacency_list: adjacency_list[v] = {}

            # Assign weighted connections WITH line identity
            adjacency_list[u][v] = (distance, line_name)
            if not is_oneway:
                adjacency_list[v][u] = (distance, line_name)

    # 2. Dead-End Bridges (Track-to-Track gaps)
    for bucket_key, nodes in spatial_bins.items():
        if len(nodes) > 1:
            for u in nodes:
                for v in nodes:
                    if u != v:
                        pos_u, pos_v = track_coordinates.get(u), track_coordinates.get(v)
                        if pos_u and pos_v:
                            distance = calculate_haversine_distance(pos_u['lat'], pos_u['lon'], pos_v['lat'], pos_v['lon'])
                        else:
                            distance = 1.0
                            
                        if u not in adjacency_list: adjacency_list[u] = {}
                        if v not in adjacency_list: adjacency_list[v] = {}
                        
                        adjacency_list[u][v] = (distance, "Internal Transfer")
                        adjacency_list[v][u] = (distance, "Internal Transfer")

    # 3. Station Gateways (Fuzzy Linking to prevent overshooting)
    for bucket_key, stations_list in station_bins.items():
        if isinstance(stations_list, int): stations_list = [stations_list]
        
        for i in [-0.004, -0.003, -0.002, -0.001, 0, 0.001, 0.002, 0.003, 0.004]:
            for j in [-0.004, -0.003, -0.002, -0.001, 0, 0.001, 0.002, 0.003, 0.004]:
                neighbor_key = (round(bucket_key[0] + i, 3), round(bucket_key[1] + j, 3))
                
                if neighbor_key in wider_spatial_bins:
                    track_nodes = wider_spatial_bins[neighbor_key]
                    
                    for s_id in stations_list:
                        s_refs = station_ref_map.get(s_id, [])
                        pos_s = station_coords.get(s_id) # Fetch Station GPS
                        
                        for t_id in track_nodes:
                            way_ids = node_to_way_index.get(t_id, [])
                            pos_t = track_coordinates.get(t_id) # Fetch Track GPS
                            
                            if pos_s and pos_t:
                                physical_dist = calculate_haversine_distance(pos_s['lat'], pos_s['lon'], pos_t['lat'], pos_t['lon'])
                                
                                for w_id in way_ids:
                                    t_refs = way_ref_map.get(w_id, [])

                                    # If the map data forgot the ref, look it up by name!
                                    if not t_refs:
                                        t_name = way_name_map.get(w_id, "")
                                        t_refs = name_to_ref.get(t_name, [])
                                        
                                        # --- THE FUZZY MATCH FIX ---
                                        if not t_refs:
                                            for known_name, known_ref in name_to_ref.items():
                                                if known_name in t_name:
                                                    t_refs = known_ref
                                                    break
                                    
                                    is_match = False
                                    is_tag_match = False
                                    
                                    # 1. Check if the tags match
                                    if s_refs and t_refs:
                                        is_tag_match = any(any(s_code.startswith(t_code) for t_code in t_refs) for s_code in s_refs)
                                    
                                    # 🛑 THE DYNAMIC RADIUS FIX (V2)
                                    if is_tag_match:
                                        # High Confidence: Tags match perfectly. Allow wide net.
                                        if physical_dist <= 400.0:
                                            is_match = True
                                            
                                    else:
                                        # Low Confidence: Tags are missing OR they just don't match.
                                        # 75m choked massive hubs. 300m caused sub-surface parachuting. 
                                        # 150m is the spatial sweet spot for Tokyo stations.
                                        if physical_dist <= 150.0:
                                            is_match = True 

                                    if is_match:
                                        link_cost = physical_dist + 50.0 
                                        # Link the STATION NODE (s_id) to the TRACK NODE (t_id)
                                        adjacency_list.setdefault(t_id, {})[s_id] = (link_cost, "Station Link")
                                        adjacency_list.setdefault(s_id, {})[t_id] = (link_cost, "Station Link")
                            

        # 4. Link multiple platform nodes together (The "Nippori Hub" Fix)
        if len(stations_list) > 1:
            for i in range(len(stations_list)):
                for j in range(i + 1, len(stations_list)):
                    s1, s2 = stations_list[i], stations_list[j]
                    adjacency_list.setdefault(s1, {})[s2] = (10.0, "Internal Transfer")
                    adjacency_list.setdefault(s2, {})[s1] = (10.0, "Internal Transfer")

        
    return adjacency_list

def create_way_name_map(elements):
    """Creates a fast lookup dictionary: Way ID -> Best available English or Japanese name."""
    way_name_map = {}
    for element in elements:
        tags = element.get('tags', {})
        name = tags.get('name:en') or tags.get('name:ja') or f"Way {element['id']}"
        way_name_map[element['id']] = name
    return way_name_map

def create_way_ref_map(elements):
    way_ref_map = {}
    for node in elements:
        tags = node.get('tags', {})
        id = node['id']
        
        # --- THE FIX ---
        # Check for 'ref', but also check 'station_code' (used by JR) 
        # and 'railway:ref' just to be safe!
        ref = tags.get('ref') or tags.get('station_code') or tags.get('railway:ref')
        
        if ref:
            # Split by semicolon if there are multiple lines
            way_ref_map[id] = ref.split(";")
        else:
            way_ref_map[id] = []
            
    return way_ref_map

def simplify_graph(adjacency_list, station_ids):
    """Reduces the graph for BOTH one-way and two-way tracks safely."""
    station_set = set(station_ids)
    
    # Build a reverse lookup to find who points TO a node
    incoming = {}
    for u, neighbors in adjacency_list.items():
        for v, data in neighbors.items():
            if v not in incoming: incoming[v] = {}
            incoming[v][u] = data

    # Create static list of candidates to avoid dictionary size errors during loop
    candidates = list(adjacency_list.keys())

    for node in candidates:
        if node in station_set or node not in adjacency_list: 
            continue

        out_edges = adjacency_list[node]
        in_edges = incoming.get(node, {})

        # ==========================================
        # CASE 1: TWO-WAY TRACK (2 in, 2 out)
        # ==========================================
        if len(out_edges) == 2 and len(in_edges) == 2:
            # Ensure the exact same 2 neighbors point in and out
            if set(out_edges.keys()) != set(in_edges.keys()): 
                continue

            (n_a, (d_a, l_a)), (n_c, (d_c, l_c)) = list(out_edges.items())
            
            # Protect Gateways & Hub Transfers
            if l_a in ["Station Link", "Internal Transfer", "Virtual Hub Link"] or l_c in ["Station Link", "Internal Transfer", "Virtual Hub Link"]:
                continue

            if l_a != l_c: continue # Must be the same line name

            # SQUASH TWO-WAY
            total_dist = d_a + d_c
            
            # Wire A to C
            adjacency_list[n_a][n_c] = (total_dist, l_a)
            incoming[n_c][n_a] = (total_dist, l_a)
            
            # Wire C to A
            adjacency_list[n_c][n_a] = (total_dist, l_a)
            incoming[n_a][n_c] = (total_dist, l_a)

            # Cleanup
            del adjacency_list[n_a][node]
            del adjacency_list[n_c][node]
            incoming[n_a].pop(node, None)
            incoming[n_c].pop(node, None)
            del adjacency_list[node]
            if node in incoming: del incoming[node]

        # ==========================================
        # CASE 2: ONE-WAY TRACK (1 in, 1 out)
        # ==========================================
        elif len(out_edges) == 1 and len(in_edges) == 1:
            n_out, (d_out, l_out) = list(out_edges.items())[0]
            n_in, (d_in, l_in) = list(in_edges.items())[0]

            # Protect Gateways & Hub Transfers
            if l_out in ["Station Link", "Internal Transfer", "Virtual Hub Link"] or l_in in ["Station Link", "Internal Transfer", "Virtual Hub Link"]:
                continue

            if l_out != l_in: continue # Must be same line
            if n_out == n_in: continue # Don't squash a self-loop
            
            # SQUASH ONE-WAY
            total_dist = d_in + d_out
            
            # Wire IN directly to OUT
            adjacency_list[n_in][n_out] = (total_dist, l_out)
            incoming[n_out][n_in] = (total_dist, l_out)
            
            # Cleanup
            del adjacency_list[n_in][node]
            incoming[n_out].pop(node, None)
            del adjacency_list[node]
            if node in incoming: del incoming[node]

    return adjacency_list

# Normalize: Remove "station", everything in parentheses, and extra spaces
def normalize_hub(name):
    import re
    name = name.replace("station", "")
    name = re.sub(r'\(.*\)', '', name)  # Remove (JR), (Toei), etc.
    name = re.sub(r'\[.*\]', '', name)  # Remove [JR], [Toei], etc.
    return name.strip()

def find_shortest_path_dijkstra(adjacency_list, start_node, goal_node):
    # Virtual distance penalty (in meters) for switching lines
    TRANSFER_PENALTY = 2000.0  
    SMALL_FEE = 50.0  # Penalty for switching platforms in the same station

    if start_node not in adjacency_list or goal_node not in adjacency_list:
        return None, float('inf')

    priority_queue = [(0.0, start_node, "Initial")]
    cheapest_costs = {(start_node, "Initial"): 0.0}
    parent_states = {}

    while priority_queue:
        current_cost, u, active_line = heapq.heappop(priority_queue)

        if u == goal_node:
            path = []
            curr_state = (u, active_line)
            while curr_state in parent_states:
                path.append(curr_state[0])
                curr_state = parent_states[curr_state]
            path.append(start_node)
            return path[::-1], current_cost

        if current_cost > cheapest_costs.get((u, active_line), float('inf')):
            continue

        for v, (weight, edge_line_name) in adjacency_list.get(u, {}).items():
            move_cost = weight
            
            is_transfer_link = edge_line_name in ["Station Link", "Internal Transfer"]
            is_walk = edge_line_name == "Station Walk"

            if is_transfer_link:
                # Scenario: Moving through the station hub 🏢
                # Preserve memory; don't charge the switch penalty yet.
                next_line = active_line
            
            elif is_walk:
                # Scenario: Walking between different station markers 🚶‍♂️
                if active_line != "Initial":  # FIX: Don't charge 10k to walk to the first train!
                    if not (active_line.startswith("Way") or edge_line_name.startswith("Way")):
                        move_cost += TRANSFER_PENALTY
                next_line = "Initial" # Reset for a fresh start at the destination
            
            else:
                # Scenario: Boarding an actual train line (the "Boarding Gate") 🚄
                if active_line != "Initial" and edge_line_name != active_line:
                    
                    # 🛑 STOP FAKE PENALTIES & BLOCK WILDCARD BRIDGES
                    # Prevent generic network tags from acting as free transfer portals
                    generic_wildcards = ["Tokyo Metro", "Toei", "JR", "Line", "Subway", "JR East"]
                    
                    is_same_base_line = False
                    if (active_line in edge_line_name and active_line not in generic_wildcards) or \
                       (edge_line_name in active_line and edge_line_name not in generic_wildcards):
                        is_same_base_line = True
                    
                    if not is_same_base_line:
                        if not (active_line.startswith("Way") or edge_line_name.startswith("Way")):
                            move_cost += (TRANSFER_PENALTY + SMALL_FEE)
                
                # CLOSE THE UNNAMED TRACK LOOPHOLE
                if edge_line_name.startswith("Way") and active_line != "Initial" and not active_line.startswith("Way"):
                    next_line = active_line
                else:
                    next_line = edge_line_name
                    
            new_cost = current_cost + move_cost
                    
            
            if new_cost < cheapest_costs.get((v, next_line), float('inf')):
                cheapest_costs[(v, next_line)] = new_cost
                parent_states[(v, next_line)] = (u, active_line)
                heapq.heappush(priority_queue, (new_cost, v, next_line))

    return None, float('inf')

def find_all_paths_from_source(adjacency_list, start_node):
    """
    Performs Dijkstra's Algorithm to find shortest paths to ALL reachable nodes.
    Returns: (parent_states, cheapest_costs)
    """
    # 🛑 Match the upgraded penalties!
    TRANSFER_PENALTY = 10000.0  
    SMALL_FEE = 50.0

    if start_node not in adjacency_list:
        return {}, {}

    priority_queue = [(0.0, start_node, "Initial")]
    cheapest_costs = {(start_node, "Initial"): 0.0}
    parent_states = {}

    while priority_queue:
        current_cost, u, active_line = heapq.heappop(priority_queue)

        if current_cost > cheapest_costs.get((u, active_line), float('inf')):
            continue

        for v, (weight, edge_line_name) in adjacency_list.get(u, {}).items():
            move_cost = weight
            
            is_transfer_link = edge_line_name in ["Station Link", "Internal Transfer"]
            is_walk = edge_line_name == "Station Walk"

            if is_transfer_link:
                # Scenario: Moving through the station hub 🏢
                next_line = active_line
            
            elif is_walk:
                # Scenario: Walking between different station markers 🚶‍♂️
                if active_line != "Initial":  # Don't charge to walk to the first train
                    if not (active_line.startswith("Way") or edge_line_name.startswith("Way")):
                        move_cost += TRANSFER_PENALTY
                next_line = "Initial" # Reset for a fresh start at the destination
            
            else:
                # Scenario: Boarding an actual train line (the "Boarding Gate") 🚄
                if active_line != "Initial" and edge_line_name != active_line:
                    
                    # 🛑 STOP FAKE PENALTIES & BLOCK WILDCARD BRIDGES
                    generic_wildcards = ["Tokyo Metro", "Toei", "JR", "Line", "Subway", "JR East"]
                    
                    is_same_base_line = False
                    if (active_line in edge_line_name and active_line not in generic_wildcards) or \
                       (edge_line_name in active_line and edge_line_name not in generic_wildcards):
                        is_same_base_line = True
                    
                    if not is_same_base_line:
                        if not (active_line.startswith("Way") or edge_line_name.startswith("Way")):
                            move_cost += (TRANSFER_PENALTY + SMALL_FEE)
                
                # 🛑 CLOSE THE UNNAMED TRACK LOOPHOLE
                if edge_line_name.startswith("Way") and active_line != "Initial" and not active_line.startswith("Way"):
                    next_line = active_line
                else:
                    next_line = edge_line_name
                    
            new_cost = current_cost + move_cost
            
            if new_cost < cheapest_costs.get((v, next_line), float('inf')):
                cheapest_costs[(v, next_line)] = new_cost
                parent_states[(v, next_line)] = (u, active_line)
                heapq.heappush(priority_queue, (new_cost, v, next_line))

    return parent_states, cheapest_costs

def get_first_step(start_node, goal_node, parent_states, cheapest_costs):
    """
    Traces the parent_states backward from the goal to find the 
    very first node to move to from the start_node.
    """
    # 1. Find which 'state' (node, line) reached the goal cheapest
    best_final_state = None
    min_cost = float('inf')
    for (node, line), cost in cheapest_costs.items():
        if node == goal_node and cost < min_cost:
            min_cost = cost
            best_final_state = (node, line)

    if not best_final_state or best_final_state[0] == start_node:
        return None

    # 2. Backtrack until the parent is the start_node
    curr_state = best_final_state
    path = []
    while curr_state in parent_states:
        prev_state = parent_states[curr_state]
        path.append(prev_state)
        if prev_state[0] == start_node:
            return (curr_state[0], path) # This is our first step!
        curr_state = prev_state
        
    return None

def calculate_center_coordinates(coordinate_list):
    """Calculates the center (average) lat/lon of a list of coordinate dictionaries."""
    if not coordinate_list:
        return (0.0, 0.0)
    
    total_lat = sum(coord['lat'] for coord in coordinate_list)
    total_lon = sum(coord['lon'] for coord in coordinate_list)
    total_points = len(coordinate_list)
    
    return (total_lat / total_points, total_lon / total_points)

def map_all_stations(station_name_map, station_elements, interactive_map, station_node_coordinates):
    station_coordinates = []
    station_names = []
    for node in station_elements:
        node_name = node['id']
        way_name = station_name_map.get(node_name, "Station Link")
        lat = node['lat']
        lon = node['lon']
        station_coordinates.append([lat, lon])
        station_names.append(way_name)
    
    for i in range(len(station_coordinates)):
            folium.Marker(station_coordinates[i], popup=station_names[i], tooltip=station_names[i], name=station_names[i]).add_to(interactive_map)
    return interactive_map
    
def setup(optimized):
    """Handles data ingestion, indexing, and graph construction."""
    print("📦 Packing logistics data...")
    raw_station_data = load_json('tokyo_railway_station.json')
    cleaned_track_data = load_json('tokyo_railway_cleaned.json')

    track_elements = cleaned_track_data.get('elements', [])
    station_elements = raw_station_data.get('elements', [])

    # 🛑 FIX 1: CLOSE THE WORMHOLE
    # Safely extract coordinates from BOTH 'node' elements and 'way' geometry
    track_node_coordinates = {}
    for element in track_elements:
        # Grab standalone nodes
        if element.get('type') == 'node':
            track_node_coordinates[element['id']] = {'lat': element['lat'], 'lon': element['lon']}
        # Grab embedded way geometry
        elif element.get('type') == 'way' and 'geometry' in element:
            for node_id, geom in zip(element.get('nodes', []), element.get('geometry', [])):
                track_node_coordinates[node_id] = {'lat': geom['lat'], 'lon': geom['lon']}
    
    # Map station node IDs to their exact coordinates
    station_node_coordinates = {
        el['id']: {'lat': el['lat'], 'lon': el['lon']} for el in station_elements
    }

    # Graph Indexing
    node_to_way_index = create_node_to_way_index(track_elements)
    dead_end_coordinates = get_dead_end_coordinates(track_elements, node_to_way_index)
    way_name_map = create_way_name_map(track_elements)
    station_name_map = create_way_name_map(station_elements)

    # 🛑 FIX 2: HEAL THE YAMANOTE LINE
    # Changed precision from 5 to 4 to bridge mapping gaps up to ~11 meters.
    spatial_groups = bin_spatially(dead_end_coordinates, precision=4)
    wider_spatial_groups = bin_spatially(track_node_coordinates, precision=3)
    station_spatial_bins = bin_spatially(station_elements, precision=3, is_station=True)

    print("🛠️  Forging structural network connections...")
    if optimized is True:
        rail_network_graph = build_adjacency_list_optimized(
            track_elements, spatial_groups, wider_spatial_groups, 
            station_spatial_bins, track_node_coordinates, way_name_map, station_elements, node_to_way_index
        )
    else:
        rail_network_graph = build_adjacency_list(
            track_elements, spatial_groups, wider_spatial_groups, 
            station_spatial_bins, track_node_coordinates, way_name_map
        )

    # Return everything as a tuple for easy unpacking
    name_groups = {}
    for station in station_elements:
        name = station_name_map.get(station['id'])
        if name not in name_groups:
            name_groups[name] = []
        name_groups[name].append(station)

    # Link stations within 1000m
    MAX_WALK_METERS = 1000
    
    for bucket_key, stations_in_bucket in station_spatial_bins.items():
        if isinstance(stations_in_bucket, int): stations_in_bucket = [stations_in_bucket]
        
        for i in [-0.001, 0, 0.001]:
            for j in [-0.001, 0, 0.001]:
                neighbor_key = (round(bucket_key[0] + i, 3), round(bucket_key[1] + j, 3))
                if neighbor_key in station_spatial_bins:
                    neighbor_stations = station_spatial_bins[neighbor_key]
                    if isinstance(neighbor_stations, int): neighbor_stations = [neighbor_stations]
                    
                    for s1_id in stations_in_bucket:
                        for s2_id in neighbor_stations:
                            if s1_id == s2_id: continue
                            
                            p1, p2 = station_node_coordinates[s1_id], station_node_coordinates[s2_id]
                            dist = calculate_haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
                            
                            if dist < MAX_WALK_METERS:
                                raw_name1 = station_name_map.get(s1_id, "").lower()
                                raw_name2 = station_name_map.get(s2_id, "").lower()
                                
                                name1 = normalize_hub(raw_name1)
                                name2 = normalize_hub(raw_name2)
                                if name1 == name2:
                                    link_type = "Internal Transfer"
                                else:
                                    link_type = "Station Walk"
                                
                                rail_network_graph.setdefault(s1_id, {})[s2_id] = (dist, link_type)
                                rail_network_graph.setdefault(s2_id, {})[s1_id] = (dist, link_type)
                                
    station_ids = [node['id'] for node in station_elements]

    if optimized is True:
        rail_network_graph = simplify_graph(rail_network_graph, station_ids)

    return (
        rail_network_graph, 
        station_name_map, 
        track_node_coordinates, 
        station_node_coordinates, 
        node_to_way_index, 
        way_name_map, 
        station_elements
    )
if __name__ == "__main__":
    (rail_network_graph, station_name_map, track_node_coordinates, 
     station_node_coordinates, node_to_way_index, way_name_map, 
     station_elements) = setup(True)
    
    # ---------------- PATHFINDER INTERACTION ---------------- #

    user_start = input("Please input start: Node ID or Station Name       | ")
    user_goal = input("Please input destination: Node ID or Station Name | ")
    # user_start = 'Oku-Tama'
    # user_goal = 'Keisei Takasago'

    try:
        for key, value in station_name_map.items():
            if value == user_start:
                node_id = int(key)
                if node_id in rail_network_graph and len(rail_network_graph[node_id]) > 0:
                    user_start = node_id
                    break
        for key, value in station_name_map.items():
            if value == user_goal:
                node_id = int(key)
                if node_id in rail_network_graph and len(rail_network_graph[node_id]) > 0:
                    user_goal = node_id
                    break
    except:
        print("Not valid Key")

    print(f"\n🧠 Searching for optimal route using Dijkstra's Algorithm...")
    print("\n🔍 Diagnosing Shinjuku Gateways:")
    # Look at all nodes directly connected to the Shinjuku station node
    for gateway_node, (dist, link_type) in rail_network_graph.get(user_start, {}).items():
        if link_type == "Station Link":
            # Look at what actual train lines those gateway tracks connect to
            for track_node, (t_dist, train_line) in rail_network_graph.get(gateway_node, {}).items():
                if train_line not in ["Station Link", "Internal Transfer"]:
                    print(f"  ➔ Can board: {train_line}")
    result_path, total_distance = find_shortest_path_dijkstra(rail_network_graph, user_start, user_goal)

    # ---------------- 6. PATH FORMATTING & DISPLAY ----------------
   
    if result_path:
        print("\n✨ Optimal Path Found!")
        print(f"Total Nodes in Path: {len(result_path)}")
        print(f"Perceived Distance (Including Penalties): {total_distance:.2f} units")
        
        readable_path_steps = []
        visual_path_coordinates_temp = []
        station_coordinates = []
        station_names = []
        
        last_line_name = None
        recent_stations = [] 
        
        for u in result_path:
            associated_way_ids = node_to_way_index.get(u, [])
            
            # 1. GENERATE MAP VISUALS
            if associated_way_ids:
                node_coordinate = track_node_coordinates.get(u)
                if node_coordinate:
                    visual_path_coordinates_temp.append(node_coordinate)
            else:
                lat = station_node_coordinates[u]['lat']
                lon = station_node_coordinates[u]['lon']
                station_coordinates.append([lat, lon])
                station_names.append(station_name_map.get(u, "Station"))

            # 2. BUILD READABLE ROUTE (WITH PASSING STATIONS DETECTED)
            if associated_way_ids:
                way_name = way_name_map.get(associated_way_ids[0], "Transfer Point")
                
                # Check if we transitioned onto a new train line
                if last_line_name != way_name:
                    readable_path_steps.append(f"\n🚄 [{way_name}]")
                    last_line_name = way_name
                
                # Scan neighbors to identify physical stations we are crossing
                for neighbor, (dist, link_type) in rail_network_graph.get(u, {}).items():
                    if link_type == "Station Link" and neighbor in station_name_map:
                        passed_station = station_name_map[neighbor]
                        
                        # Only add the station if it isn't in our recent memory
                        if passed_station not in recent_stations:
                            readable_path_steps.append(passed_station)
                            recent_stations.append(passed_station)
                            
                            # Keep the memory small (last 3 stations)
                            if len(recent_stations) > 3:
                                recent_stations.pop(0)
            else:
                # Handle walking transfers inside hubs
                st_name = station_name_map.get(u, "Walking Path")
                if st_name not in recent_stations:
                    readable_path_steps.append(f"\n🚶 {st_name}")
                    recent_stations.append(st_name)
                    if len(recent_stations) > 3:
                        recent_stations.pop(0)
                    last_line_name = None  # Reset line tracking since we are off the tracks
        
        print(f"Calculated Path Center: {calculate_center_coordinates(visual_path_coordinates_temp)}")
        
        # Build coordinate list for Folium polyline
        visual_path_coordinates = [[coord['lat'], coord['lon']] for coord in visual_path_coordinates_temp]
        
        if station_coordinates:
            visual_path_coordinates.insert(0, [station_coordinates[0][0], station_coordinates[0][1]])
            visual_path_coordinates.append([station_coordinates[-1][0], station_coordinates[-1][1]])
        
        #----------------------- MAPPER --------------------------------
        map_center = calculate_center_coordinates(visual_path_coordinates_temp)
        interactive_map = folium.Map(location=map_center, zoom_start=13)
        
        folium.PolyLine(visual_path_coordinates, color="blue", weight=5, opacity=0.8).add_to(interactive_map)
        for i in range(len(station_coordinates)):
            folium.Marker(station_coordinates[i], popup=station_names[i]).add_to(interactive_map)
        
        interactive_map = map_all_stations(station_name_map, station_elements, interactive_map, station_node_coordinates)
        interactive_map.save('map.html')
        
        print("\nRoute Details:")
        # Join cleanly and patch up line-break artifacts
        route_output = " ➔ ".join(readable_path_steps)
        print(route_output.replace(" ➔ \n", "\n").replace("\n ➔ ", "\n").strip())
    else:
        print("\n❌ No path exists between those nodes.")
        
    #     #----------------------- MAPPER --------------------------------
    #     map_center = calculate_center_coordinates(visual_path_coordinates_temp)
    #     interactive_map = folium.Map(location=map_center, zoom_start=13)
        
    #     folium.PolyLine(visual_path_coordinates, color="blue", weight=5, opacity=0.8).add_to(interactive_map)
    #     for i in range(len(station_coordinates)):
    #         folium.Marker(station_coordinates[i], popup=station_names[i]).add_to(interactive_map)
        
    #     interactive_map = map_all_stations(station_name_map, station_elements, interactive_map, station_node_coordinates)
    #     interactive_map.save('map.html')
    #     folium.Map()
    #     print("\nRoute Details:")
    #     print(" ➔ ".join(readable_path_steps))
    # else:
    #     print("\n❌ No path exists between those nodes.")