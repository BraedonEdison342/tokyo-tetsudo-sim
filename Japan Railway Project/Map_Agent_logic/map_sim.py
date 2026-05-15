import numpy as np
import pickle
import time
from data_node_builder import setup
import keyboard

# Column indices for the agent table
CURR, WORK, HOME, RAND, TARGET, STATE, START, END = 0, 1, 2, 3, 4, 5, 6, 7

def tick(agent_table, lookup_table, sleep_duration):
    """
    Primary simulation loop that handles time, shift triggers, and movement.
    """
    tick_time = 0
    arrived_total = 0

    
    while True:
        # ------------------ Update Clock ------------------
        total_minutes = tick_time // 6
        current_hour = (total_minutes // 60) % 24
        
        # ------------------ Shift Triggers ------------------
        # We only check for new commuters at the start of each simulated hour
        if tick_time % 360 == 0:
            
            # print("Press 'Space' to pass one hour \n")
            # keyboard.wait('space') 
            print(f"Current Simulation Time: {current_hour}:00 -----------------------------")

            finish = (agent_table[:, CURR] == agent_table[:, TARGET]) & (agent_table[:, STATE] == 1)
            agent_table[finish, STATE] = 0
            # Morning Trigger: Home to Work
            # Finds idle agents whose start time is now
            start_mask = (agent_table[:, START] == current_hour) & (agent_table[:, STATE] == 0)
            agent_table[start_mask, TARGET] = agent_table[start_mask, WORK]
            agent_table[start_mask, STATE] = 1
            
            # Evening Trigger: Work to Home
            # Finds idle agents whose end time is now
            end_mask = (agent_table[:, END] == current_hour) & (agent_table[:, STATE] == 0)
            agent_table[end_mask, TARGET] = agent_table[end_mask, HOME]
            agent_table[end_mask, STATE] = 1

            active_mask = (agent_table[:, STATE] == 1)
            active_agents = np.flatnonzero(active_mask)
      

            print(f"{arrived_total} Agents have made it to their destination!")
            print(f"{np.size(active_agents)} Agents are in transit")
            arrived_total = 0

            commuter_count = np.sum(start_mask) + np.sum(end_mask)
            if commuter_count > 0:
                print(f"Log: {commuter_count} agents started commuting.")

        # ------------------ Movement Engine ------------------
        # Identify all agents currently on the tracks

        if np.any(active_agents):
            # Check for arrivals: If current location matches target, deactivate them
            arrived_mask = (agent_table[active_agents, CURR] == agent_table[active_agents, TARGET])
            arrived_indices = active_agents[arrived_mask]
            arrived_total = len(arrived_indices) + arrived_total
            agent_table[arrived_indices, STATE] = 0
            active_agents = active_agents[~arrived_mask]
            
            if active_agents.size > 0:
                curr_nodes = agent_table[active_agents, CURR]
                target_nodes = agent_table[active_agents, TARGET]
                agent_table[active_agents, CURR] = lookup_table[curr_nodes, target_nodes]

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
        with open('Map_Agent_logic\state_mappings.pkl', 'rb') as f:
            mappings = pickle.load(f)
        state_to_index = mappings['state_to_index']
        station_ids = mappings['station_ids']
    except FileNotFoundError:
        print("Error: state_mappings.pkl not found. Run the builder script first.")
        exit()

    # ------------------ Population Setup ------------------
    num_agents = 1000000
    num_states = len(state_to_index)
    num_goals = len(station_ids)
    
    print(f"Initializing {num_agents} agents...")

    # Set up realistic departure probabilities for Tokyo
    hours = np.arange(24)
    start_probs = [0.005, 0.002, 0.002, 0.002, 0.002, 0.010, 
                   0.050, 0.230, 0.400, 0.150, 0.050, 0.020, 
                   0.005, 0.005, 0.005, 0.005, 0.020, 0.005, 
                   0.004, 0.004, 0.004, 0.003, 0.010, 0.007]
    
    # Generate randomized table data
    current_locs = np.random.randint(0, num_states, size=num_agents)
    work_locs = np.random.randint(0, num_goals, size=num_agents)
    home_locs = np.random.randint(0, num_goals, size=num_agents)
    random_locs = np.random.randint(0, num_goals, size=num_agents)
    work_starts = np.random.choice(hours, size=num_agents, p=start_probs)
    work_ends = (work_starts + 9) % 24
    
    # Assemble the master agent table
    agent_table = np.column_stack((
        current_locs, 
        work_locs, 
        home_locs, 
        random_locs, 
        work_locs.copy(), # Initial target set to work
        np.zeros(num_agents, dtype=np.int8), # Initial state (idle)
        work_starts,
        work_ends
    )).astype(np.int32)

    # ------------------ Start Simulation ------------------
    print("Loading lookup table and starting ticks...")
    lookup_table = np.load('Map_Agent_logic\\railway_lookup_table.npy', mmap_mode='r')
    
    tick(agent_table, lookup_table, 0.001)