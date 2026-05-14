import numpy as np
import pickle
from data_node_builder import setup

if __name__ == "__main__":
    print("-------------- Loading Raw Network ----------------")
    (rail_network_graph, station_name_map, track_node_coordinates, 
     station_node_coordinates, node_to_way_index, way_name_map, 
     station_elements) = setup(True)

    print("-------------- Loading GPU Blueprint --------------")
    # Load the exact dictionaries the GPU used, preventing all index bugs
    try:
        with open('state_mappings.pkl', 'rb') as f:
            mappings = pickle.load(f)
            
        state_to_index = mappings['state_to_index']
        index_to_state = mappings['index_to_state']
        station_ids = mappings['station_ids']
    except FileNotFoundError:
        print("❌ Error: Run the GPU Builder script first to generate the mappings!")
        exit()

    # Map goal stations to their specific Column Index (0 to 795)
    station_id_to_col = {sid: i for i, sid in enumerate(station_ids)}
    while True:
        print("-------------- 🚉 Navigation 🚉 ------------------")
        start_input = input("Enter Start Station ID or Name: ")
        goal_input = input("Enter Goal Station ID or Name: ")

        start_node_id = None
        goal_node_id = None

        # Resolve inputs to real Node IDs
        for key, value in station_name_map.items():
            if value == start_input or key == start_input:
                if int(key) in rail_network_graph: start_node_id = int(key)
            if value == goal_input or key == goal_input:
                if int(key) in rail_network_graph: goal_node_id = int(key)

        if not start_node_id or not goal_node_id:
            print("❌ Invalid Station Name or ID.")
            exit()

        # Translate to Matrix Coordinates
        try:
            start_row_idx = state_to_index[start_node_id]  # The lobby state
            goal_col_idx = station_id_to_col[goal_node_id] # The column index
        except KeyError:
            print("❌ One of these stations is disconnected from the main state map.")
            exit()

        print("-------------- Loading the Brain ------------------")
        # mmap_mode reads the file directly from disk without blowing up RAM
        lookup_table = np.load('railway_lookup_table.npy', mmap_mode='r')

        print("-------------- Calculating Path --------------------")
        current_row = start_row_idx
        route_indices = [current_row] 

        # We stop when the STATE of the current row is exactly the goal lobby ID
        while index_to_state[current_row] != goal_node_id:
            next_step = lookup_table[current_row, goal_col_idx].item()
            
            if next_step == -1:
                print("❌ Route interrupted (unreachable path).")
                break
                
            route_indices.append(next_step)
            current_row = next_step

        print(f"\n✨ Route Found! {len(route_indices)}\n")
        last_station_name = None
        
        # --- Translation Layer ---
        for idx in route_indices:
            state = index_to_state[idx]
            
            # Determine if we are on a platform or a standard track
            if isinstance(state, tuple):
                node_id, line_name = state
                location_type = f"Platform ({line_name})"
            else:
                node_id = state
                location_type = "Lobby / Track"
            
            # Get real-world name
            station_name = station_name_map.get(int(node_id), "TRACK")
            if station_name == "TRACK":
                way_id = node_to_way_index[node_id][0]
                station_name = way_name_map[way_id]

            # Print output cleanly, combining identical track nodes into one line
            if last_station_name != station_name:
                print(f"📍 {station_name} [{location_type}] (Node: {node_id})")
            elif isinstance(state, tuple):
                print(f"   ↳ Transfer to: {line_name}")
                
            last_station_name = station_name