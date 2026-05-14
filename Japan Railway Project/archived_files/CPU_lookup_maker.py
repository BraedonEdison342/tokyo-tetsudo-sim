from data_node_builder import *
import numpy as np
import time
import multiprocessing as mp
from tqdm import tqdm

global_graph = None
global_id_to_idx = {}
global_idx_to_id = {}
global_line_to_id = {}
global_array_base = None
global_counter = None

def init_worker(shared_graph, shared_id_to_idx, shared_idx_to_id, shared_line_to_id, shared_array_base, shared_counter):
    global global_graph, global_id_to_idx, global_idx_to_id, global_line_to_id, global_array_base, global_counter
    global_graph = shared_graph
    global_id_to_idx = shared_id_to_idx
    global_idx_to_id = shared_idx_to_id
    global_line_to_id = shared_line_to_id
    global_array_base = shared_array_base
    global_counter = shared_counter

def calculate_chunk(chunk_indices, num_stations):
    lookup_table = np.frombuffer(global_array_base, dtype=np.uint16).reshape((num_stations, num_stations))

    for node_1_idx in chunk_indices:
        node_1_id = global_idx_to_id[node_1_idx]
        
        # 1. Run Dijkstra (returns map: (node, line) -> first_step_node_id)
        first_step_map, costs = find_all_paths_from_source_optimized(global_graph, node_1_id, global_line_to_id)
        
        # 2. Collapse States to Nodes
        best_known_costs = {}
        for (node_2_id, line_id), first_step_node_id in first_step_map.items():
            if node_2_id not in global_id_to_idx: continue
            
            c = costs[(node_2_id, line_id)]
            # Only update if this is the cheapest way we've found to reach this physical node
            if node_2_id not in best_known_costs or c < best_known_costs[node_2_id]:
                best_known_costs[node_2_id] = c
                
                node_2_idx = global_id_to_idx[node_2_id]
                next_node_idx = global_id_to_idx[first_step_node_id]
                lookup_table[node_1_idx, node_2_idx] = next_node_idx
        
        with global_counter.get_lock():
            global_counter.value += 1

if __name__ == "__main__":
    # Load raw data
    (rail_graph, _, _, _, _, way_map, _) = setup(True)
    
    # 1. Exhaustive Line-to-ID Mapping
    all_lines = set()
    for neighbors in rail_graph.values():
        for _, line_val in neighbors.items():
            all_lines.add(line_val[1]) # line_val is (dist, line)
            
    line_to_id = {name: idx for idx, name in enumerate(all_lines, start=1) if isinstance(name, str)}
    line_to_id.update({"Initial": 0, "Station Link": -1, "Internal Transfer": -2, "Station Walk": -3})

    # 2. Ensure Graph is pure integers
    int_graph = {}
    for u, neighbors in rail_graph.items():
        int_graph[u] = {v: (w, line_to_id.get(l, 0) if isinstance(l, str) else l) for v, (w, l) in neighbors.items()}

    # 3. Indexing
    sorted_nodes = sorted(int_graph.keys())
    id_to_idx = {node: i for i, node in enumerate(sorted_nodes)}
    idx_to_id = {i: node for i, node in enumerate(sorted_nodes)}
    num_stations = len(idx_to_id)

    # 4. Shared Memory
    global_array_base = mp.RawArray('H', num_stations * num_stations)
    table = np.frombuffer(global_array_base, dtype=np.uint16).reshape((num_stations, num_stations))
    table.fill(65535)
    shared_counter = mp.Value('i', 0)
    
    # 5. Chunking
    chunk_size = 250
    chunks = [list(range(num_stations))[i:i + chunk_size] for i in range(0, num_stations, chunk_size)]
    tasks = [(c, num_stations) for c in chunks]

    print(f"🚀 Calculating {num_stations} nodes...")
    with mp.Pool(processes=8, initializer=init_worker, initargs=(int_graph, id_to_idx, idx_to_id, line_to_id, global_array_base, shared_counter)) as pool:
        result = pool.starmap_async(calculate_chunk, tasks)
        with tqdm(total=num_stations, unit="node") as pbar:
            last = 0
            while not result.ready():
                curr = shared_counter.value
                pbar.update(curr - last)
                last = curr
                time.sleep(0.5)
            pbar.update(num_stations - last)

    np.save("lookup_table", table)