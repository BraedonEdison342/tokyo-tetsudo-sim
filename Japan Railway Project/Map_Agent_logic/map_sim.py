import cupy as np
import cudf as cp
import cupyx
import pickle
import time
from data_node_builder import setup
# import keyboard

# Column indices for the agent table
CURR, WORK, HOME, RAND, TARGET, STATE, START, END = 0, 1, 2, 3, 4, 5, 6, 7

def tick(agent_table, lookup_table, col_to_state, sleep_duration, num_states, lat_lon_reference):
    """
    Primary simulation loop that handles time, shift triggers, and movement.
    """
    tick_time = 0
    arrived_total = 0
    # Outside the loop - allocated exactly ONCE
    hourly_edge_buffer = []
    while True:
        total_minutes = tick_time // 6
        current_hour = (total_minutes // 60) % 24
        
        # ------------------ Shift Triggers ------------------
        if tick_time % 360 == 0:
            print(f"Current Simulation Time: {current_hour}:00 -----------------------------")

            # CRITICAL FIX: Convert TARGET column IDs to State IDs to check arrival
            target_states = col_to_state[agent_table[:, TARGET]]
            finish = (agent_table[:, CURR] == target_states) & (agent_table[:, STATE] == 1)
            agent_table[finish, STATE] = 0
            print(agent_table[:, CURR])
            # Morning Trigger: Home to Work
            start_mask = (agent_table[:, START] == current_hour) & (agent_table[:, STATE] == 0)
            agent_table[start_mask, TARGET] = agent_table[start_mask, WORK]
            agent_table[start_mask, STATE] = 1
            
            # Evening Trigger: Work to Home
            end_mask = (agent_table[:, END] == current_hour) & (agent_table[:, STATE] == 0)
            agent_table[end_mask, TARGET] = agent_table[end_mask, HOME]
            agent_table[end_mask, STATE] = 1

            active_mask = (agent_table[:, STATE] == 1)
            active_agents = np.flatnonzero(active_mask)
      
            print(f"{arrived_total} Agents have made it to their destination!")
            print(f"{np.size(active_agents)} Agents are in transit")
            arrived_total = 0
            if len(hourly_edge_buffer) >0:
                # Finds all array slots that aren't zero
                all_movements = np.concatenate(hourly_edge_buffer)
                unique_edges, counts = np.unique(all_movements, return_counts=True)
                start_node = unique_edges // num_states
                end_node = unique_edges % num_states

                df = cp.DataFrame({
                    'current_hour': current_hour,
                    'start_node': start_node, 
                    'end_node': end_node,
                    'counts': counts,
                    'start_lon': 0.0,
                    'start_lat': 0.0,
                    'end_lon': 0.0,
                    'end_lat': 0.0
                })


                df['start_lon'] = lat_lon_reference['lon'].iloc[df['start_node']].values
                df['start_lat'] = lat_lon_reference['lat'].iloc[df['start_node']].values
                df['end_lon'] = lat_lon_reference['lon'].iloc[df['end_node']].values
                df['end_lat'] = lat_lon_reference['lat'].iloc[df['end_node']].values

                df.to_parquet(f"../parquet_files/{current_hour}.parquet")

                hourly_edge_buffer = []


                # time.sleep(1)
                commuter_count = np.sum(start_mask) + np.sum(end_mask)
                if commuter_count > 0:
                    print(f"Log: {commuter_count} agents started commuting.")

        # ------------------ Movement Engine ------------------
        if np.any(active_agents):
            curr_nodes = agent_table[active_agents, CURR]
            target_cols = agent_table[active_agents, TARGET]
            
            # 1. Check for arrivals using the col_to_state map
            target_states = col_to_state[target_cols]
            arrived_mask = (curr_nodes == target_states)
            
            arrived_indices = active_agents[arrived_mask]
            arrived_total += len(arrived_indices)
            agent_table[arrived_indices, STATE] = 0
            
            # 2. Filter remaining active agents
            active_agents = active_agents[~arrived_mask]
            
            if active_agents.size > 0:
                curr_nodes = agent_table[active_agents, CURR]
                target_cols = agent_table[active_agents, TARGET]
                
                # 3. Look up next steps
                next_steps = lookup_table[curr_nodes, target_cols]
                
                # 4. CRITICAL FIX: Handle Unreachable (-1) Paths safely
                valid_moves = (next_steps != -1)
                
                agents_to_move = active_agents[valid_moves]

                agent_cord = agent_table[agents_to_move, CURR]
                next_step_cord = next_steps[valid_moves]
                # 1. Create a mask where the nodes are NOT the same
                movement_mask = (agent_cord != next_step_cord)

                # 2. Use that mask to select only the rows that changed
                agent_cord_cleaned = agent_cord[movement_mask]
                next_step_cord_cleaned = next_step_cord[movement_mask]

                paring_array = (agent_cord_cleaned * num_states) + next_step_cord_cleaned
                hourly_edge_buffer.append(paring_array)
                
                agent_table[agents_to_move, CURR] = next_steps[valid_moves]
   
                # time.sleep(1000)

                # Deactivate agents that hit a dead end so they don't loop infinitely
                stuck_agents = active_agents[~valid_moves]
                agent_table[stuck_agents, STATE] = 0 

        # ------------------ Loop Maintenance ------------------
        tick_time += 1



if __name__ == "__main__":
    # ------------------ Data Loading ------------------
    print("Loading network graph data...")
    (rail_network_graph, station_name_map, track_node_coordinates, 
     station_node_coordinates, node_to_way_index, way_name_map, 
     station_elements) = setup(True)

    print("Loading state mappings...")
    try:
        with open('./state_mappings.pkl', 'rb') as f:
            mappings = pickle.load(f)
        state_to_index = mappings['state_to_index']
        station_ids = mappings['station_ids']
        index_to_state = mappings['index_to_state']
    except FileNotFoundError:
        print("Error: state_mappings.pkl not found. Run the builder script first.")
        exit()
    num_states = len(state_to_index)

    node_lat = [0.0] * num_states
    node_lon = [0.0] * num_states
    for i in range(num_states):
        state = index_to_state[i]
        node_id = state[0] if isinstance(state, tuple) else state  

        if node_id in station_node_coordinates:
            node_lat[i] = station_node_coordinates[node_id]['lat']
            node_lon[i] = station_node_coordinates[node_id]['lon']
        else:
            node_lat[i] = track_node_coordinates[node_id]['lat']
            node_lon[i] = track_node_coordinates[node_id]['lon']

    lat_lon_reference = cp.DataFrame({
        'lat': node_lat, 
        'lon': node_lon
    }).astype('float64')

   # ------------------ Population Setup ------------------
    num_agents = 1000000
    
    print(f"Initializing {num_agents} agents...")

    # 1. Create a bridge array mapping Column IDs back to State IDs
    valid_col_indices = []
    valid_state_indices = []
    col_to_state_cpu = [-1] * len(station_ids)
    
    for i, sid in enumerate(station_ids):
        if sid in state_to_index:
            valid_col_indices.append(i)
            valid_state_indices.append(state_to_index[sid])
            col_to_state_cpu[i] = state_to_index[sid]
            
    valid_col_indices = np.array(valid_col_indices)
    valid_state_indices = np.array(valid_state_indices)
    col_to_state = np.array(col_to_state_cpu, dtype=np.int32) # Sent to GPU
    num_goals = len(valid_col_indices)
    print(len(valid_state_indices))
    print(num_goals)
    print(num_states)

    # 2. Set up departure probabilities 
    hours = np.arange(24)
    start_probs = [0.005, 0.002, 0.002, 0.002, 0.002, 0.010, 
                   0.050, 0.230, 0.400, 0.150, 0.050, 0.020, 
                   0.005, 0.005, 0.005, 0.005, 0.020, 0.005, 
                   0.004, 0.004, 0.004, 0.003, 0.010, 0.007]
    
    # 3. Generate randomized choices for valid indices
    curr_choice = np.random.randint(0, num_goals, size=num_agents)
    work_choice = np.random.randint(0, num_goals, size=num_agents)
    home_choice = np.random.randint(0, num_goals, size=num_agents)
    rand_choice = np.random.randint(0, num_goals, size=num_agents)
    
    # Assign STATE indices to CURR, and COLUMN indices to Targets
    current_locs = valid_state_indices[curr_choice]
    work_locs = valid_col_indices[work_choice]
    home_locs = valid_col_indices[home_choice]
    random_locs = valid_col_indices[rand_choice]
    
    work_starts = np.random.choice(hours, size=num_agents, p=start_probs)
    work_ends = (work_starts + 9) % 24
    
    # Assemble the master agent table
    agent_table = np.column_stack(( 
        current_locs, 
        work_locs, 
        home_locs, 
        random_locs, 
        work_locs.copy(), 
        np.zeros(num_agents, dtype=np.int8), 
        work_starts,
        work_ends
    )).astype(np.int64)

    # ------------------ Start Simulation ------------------
    print("Loading lookup table and starting ticks...")
    lookup_table = np.load('./railway_lookup_table.npy', mmap_mode='r')
    
    # Pass the bridge array into the tick loop
    tick(agent_table, lookup_table, col_to_state, 0.001, num_states, lat_lon_reference)