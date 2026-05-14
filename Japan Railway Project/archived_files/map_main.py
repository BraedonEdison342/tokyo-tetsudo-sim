
import streamlit as st
import time
from data_node_builder import *
from streamlit_folium import st_folium
def result_path_func(result_path, total_distance, station_node_coordinates):
    print("\n✨ Optimal Path Found!")
    print(f"Total Nodes in Path: {len(result_path)}")
    print(f"Perceived Distance (Including Penalties): {total_distance:.2f} units")
    
    readable_path_steps = []
    visual_path_coordinates_temp = []
    station_coordinates = []
    station_names = []
    
    for node in result_path:
        associated_way_ids = node_to_way_index.get(node, [])
        
        if associated_way_ids:
            way_name = way_name_map.get(associated_way_ids[0], "Transfer Point")
            node_coordinate = track_node_coordinates.get(node)
            if node_coordinate:
                visual_path_coordinates_temp.append(node_coordinate)
        else:
            way_name = station_name_map.get(node, "Station Link")
            lat = station_node_coordinates[node]['lat']
            lon = station_node_coordinates[node]['lon']
            station_coordinates.append([lat, lon])
            station_names.append(way_name)

        if not readable_path_steps or readable_path_steps[-1] != way_name:
            readable_path_steps.append(way_name)
            
    print(f"Calculated Path Center: {calculate_center_coordinates(visual_path_coordinates_temp)}")
    
    # Build coordinate list for Folium polyline
    visual_path_coordinates = [[coord['lat'], coord['lon']] for coord in visual_path_coordinates_temp]
    
    # Prepend start station and append end station to ensure map line connects seamlessly
    if station_coordinates:
        visual_path_coordinates.insert(0, [station_coordinates[0][0], station_coordinates[0][1]])
        visual_path_coordinates.append([station_coordinates[-1][0], station_coordinates[-1][1]])
    
    # ----------------------- MAPPER --------------------------------
    map_center = calculate_center_coordinates(visual_path_coordinates_temp)
    interactive_map = folium.Map(location=map_center, zoom_start=13)
    
    folium.PolyLine(visual_path_coordinates, color="blue", weight=5, opacity=0.8).add_to(interactive_map)
    for i in range(len(station_coordinates)):
        folium.Marker(station_coordinates[i], popup=station_names[i]).add_to(interactive_map)
    
    interactive_map = map_all_stations(station_name_map, station_elements, interactive_map, station_coordinates)
    interactive_map.save('map.html')
    folium.Map()
    print("\nRoute Details:")
    print(" ➔ ".join(readable_path_steps))

if __name__ == "__main__":
    (rail_network_graph, station_name_map, track_node_coordinates, 
     station_node_coordinates, node_to_way_index, way_name_map, 
     station_elements) = setup()
    # st.sidebar.button(on_click=st.rerun())
    result_path = None
    
    # interactive_map = folium.Map(location=[35.6895, 139.6917], zoom_start=13)
    # interactive_map = map_all_stations(station_name_map, station_elements, interactive_map, station_node_coordinates)
    # interactive_map.save('map.html')
    
    # ---------------- PATHFINDER INTERACTION ---------------- 

    # Initialize the 'memory' for our stations

    if 'start_station' not in st.session_state:
        st.session_state.start_station = None

    if 'goal_station' not in st.session_state:
        st.session_state.goal_station = None
    
    if st.session_state.goal_station and st.session_state.start_station:
    # 1. Create the reverse map once for quick lookups
        reverse_station_map = {name: node_id for node_id, name in station_name_map.items()}
        
        # 2. Get the potential IDs from the map
        start_id = reverse_station_map.get(st.session_state.start_station)
        goal_id = reverse_station_map.get(st.session_state.goal_station)

        # 3. Validation Check: Do these IDs exist and have connections?
        if start_id in rail_network_graph and goal_id in rail_network_graph:
            # Success! Now we call the Dijkstra function
            result_path, total_distance = find_shortest_path_dijkstra(
                rail_network_graph, int(start_id), int(goal_id)
            )
            
            # Visualize the result
            result_path_func(result_path, total_distance, station_node_coordinates)
        else:
            st.error("One of the selected stations could not be found in the network graph. ⚠️")
    map_center = [35.6895, 139.6917]

    interactive_map = folium.Map(location=map_center, zoom_start=13)
    
    # Add all stations
    interactive_map = map_all_stations(station_name_map, station_elements, interactive_map, station_node_coordinates)
    
    if result_path:
        visual_path = [[track_node_coordinates[n]['lat'], track_node_coordinates[n]['lon']] 
                       for n in result_path if n in track_node_coordinates]
        
        folium.PolyLine(visual_path, color="blue", weight=5, opacity=0.8).add_to(interactive_map)
        st.success(f"Route found! Total distance: {total_distance:.2f} units")  
    with st.sidebar:
        st.title("Settings")
        if st.button("Rerun"):
            st.rerun()
        if st.button("Clear"):
            st.session_state.start_station = None
            st.session_state.goal_station = None
            st.rerun()
        if st.chat_input(placeholder=f"{st.session_state.start_station}", key='start_node'):
            st.session_state.start_station = st.session_state['start_node']
            st.rerun()
            pass
        if st.chat_input(placeholder=f"{st.session_state.goal_station}", key='goal_node'):
            st.session_state.goal_station = st.session_state['goal_node']
            st.rerun()
            pass

    map_output = st_folium(interactive_map)
    print(map_output)
    if map_output and map_output.get('last_object_clicked'):
        if st.session_state.start_station is None:
            st.session_state.start_station = map_output['last_object_clicked_tooltip']
            # st.rerun()
        elif st.session_state.goal_station is None:
            st.session_state.goal_station = map_output['last_object_clicked_tooltip']
            # st.rerun()
        else:
            st.session_state.start_station = user_goal
            st.session_state.goal_station = map_output['last_object_clicked_tooltip']
            # st.rerun()
