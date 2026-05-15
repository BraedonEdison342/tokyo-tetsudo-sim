from data_node_builder import setup
import numpy as np
import cupy as cp
import cudf
import cugraph
import pickle
from tqdm import tqdm

if __name__ == "__main__":
    print("🚂 Step 1: Loading Raw Data...")
    (
        rail_network_graph, station_name_map, track_node_coordinates, 
        station_node_coordinates, node_to_way_index, way_name_map, station_elements
    ) = setup(True)
    
    WILD = ["Tokyo Metro", "Toei", "JR", "Line", "Subway", "JR East"]
    station_ids = [node['id'] for node in station_elements]
    station_ids_set = set(station_ids)
    
    node_inventory = {}
    state_edge = []

    print("🏗️ Step 2: Building Skyscraper States...")
    # Basic Inventory
    for u, neighbors in rail_network_graph.items():
        if u not in node_inventory: node_inventory[u] = set()
        for v, (weight, line) in neighbors.items():
            if v not in node_inventory: node_inventory[v] = set()
            node_inventory[u].add(line)
            node_inventory[v].add(line)

    # Propagate rail line names through "Station Link"
    for u in station_ids_set:
        if u in rail_network_graph:
            for neighbor_id, (weight, edge_type) in rail_network_graph[u].items():
                if edge_type == "Station Link":
                    neighbor_lines = node_inventory.get(neighbor_id, set())
                    for real_line in neighbor_lines:
                        if real_line not in ["Station Link", "Station Walk", "Internal Transfer"]:
                            node_inventory[u].add(real_line)

    # Tracks
    for u, neighbors in rail_network_graph.items():
        u_is_hub = (u in station_ids_set and len(node_inventory[u]) > 1)
        for v, (weight, line) in neighbors.items():
            v_is_hub = (v in station_ids_set and len(node_inventory[v]) > 1)
            src_state = (u, line) if u_is_hub else u
            dst_state = (v, line) if v_is_hub else v
            state_edge.append((dst_state, src_state, float(weight))) # Reversed

    # Elevators & Stairs
    for u, lines in node_inventory.items():
        if u in station_ids_set and len(lines) > 1:
            line_list = list(lines)
            for line in line_list:
                state_edge.append(((u, line), u, 50.0))
                state_edge.append((u, (u, line), 2050.0))
            for i in range(len(line_list)):
                line_a = line_list[i]
                for j in range(i + 1, len(line_list)):
                    line_b = line_list[j]
                    is_same_base = ((line_a in line_b and line_a not in WILD) or 
                                    (line_b in line_a and line_b not in WILD))
                    cost = 0.0 if is_same_base else 2050.0
                    state_edge.append(((u, line_a), (u, line_b), cost))
                    state_edge.append(((u, line_b), (u, line_a), cost))

    # Deterministic Index Mapping
    unique_states = set()
    for dst, src, weight in state_edge:
        unique_states.add(dst)
        unique_states.add(src)
        
    # SORTING prevents the index mismatch bug!
    all_states = sorted(list(unique_states), key=str)
    state_to_index = {state: idx for idx, state in enumerate(all_states)}
    index_to_state = {idx: state for idx, state in enumerate(all_states)}

    print("⚙️ Step 3: Preparing cuDF Edge List...")
    # THE FIX 1: Swap src and dst to build the REVERSED graph!
    df = cudf.DataFrame({
        'source': [state_to_index[dst] for dst, src, w in state_edge], 
        'destination': [state_to_index[src] for dst, src, w in state_edge], 
        'weight': [w for d, s, w in state_edge]
    })

    G = cugraph.Graph(directed=True)
    G.from_cudf_edgelist(df, source='source', destination='destination', edge_attr='weight')

    print("⚙️ Step 4: Calculating Routes on GPU...")
    num_states = len(state_to_index)
    num_stations = len(station_ids)
    lookup_table_gpu = cp.full((num_states, num_stations), -1, dtype=cp.int32)

    for i, station_id in enumerate(tqdm(station_ids, desc="Mapping Stations")):
        if station_id in state_to_index:
            target_idx = state_to_index[station_id]
            results = cugraph.sssp(G, source=target_idx, cutoff=100000)
            
            vertices = cp.asarray(results['vertex'])
            predecessors = cp.asarray(results['predecessor'])
            lookup_table_gpu[vertices, i] = predecessors
            
            lookup_table_gpu[target_idx, i] = target_idx

    print(f"✅ Success! Table Shape: {lookup_table_gpu.shape}")
    
    print("💾 Step 5: Saving to Disk (Slim Data)...")
    # Save the numbers (Very fast, ~75MB)
    np.save('railway_lookup_table.npy', cp.asnumpy(lookup_table_gpu))
    
    # Save the dictionary blueprint (Tiny, ~5MB)
    with open('state_mappings.pkl', 'wb') as f:
        pickle.dump({
            'state_to_index': state_to_index,
            'index_to_state': index_to_state,
            'station_ids': station_ids
        }, f)
        
    print("🎉 All done! You can now run the Agent.")