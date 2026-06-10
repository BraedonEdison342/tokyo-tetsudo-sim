from data_node_builder import *
import pickle
import pandas as pd

def name_assigner(row):
    name_to_ref = {
        # =====================================================================
        # === JR EAST (MAIN COMMUTER & REGIONAL NETWORK) ======================
        # =====================================================================
        # --- Yamanote Loop ---
        "Yamanote Line": ["JY"],
        "Yamanote Line (Inner Loop)": ["JY"],
        "Yamanote Line (Outer Loop)": ["JY"],
        
        # --- Chuo Line Variants ---
        "Chūō Line": ["JC"],
        "Chuo Line": ["JC"],
        "Chūō Line (Rapid)": ["JC"],
        "Chuo Line (Rapid)": ["JC"],
        "Chūō Line Rapid": ["JC"],
        "Chuo Line Rapid": ["JC"],
        "Chūō Line (Local)": ["JB"],
        "Chuo Line (Local)": ["JB"],
        "Chūō Line Local": ["JB"],
        "Chuo Line Local": ["JB"],
        "Chūō-Sōbu Line": ["JB"],
        "Chuo-Sobu Line": ["JB"],
        "Chūō-Sōbu Line Local": ["JB"],
        "Chuo-Sobu Line Local": ["JB"],
        "Chūō-Sōbu Line (Local)": ["JB"],
        "Chuo-Sobu Line (Local)": ["JB"],
        
        # --- Keihin-Tohoku & Negishi Corridor ---
        "Keihin-Tōhoku Line": ["JK"],
        "Keihin-Tohoku Line": ["JK"],
        "Keihin-Tōhoku Line (Local)": ["JK"],
        "Keihin-Tohoku Line (Local)": ["JK"],
        "Keihin-Tōhoku Line (Rapid)": ["JK"],
        "Keihin-Tohoku Line (Rapid)": ["JK"],
        "Negishi Line": ["JK"],
        "Keihin-Tōhoku・Negishi Line": ["JK"],
        "Keihin-Tohoku-Negishi Line": ["JK"],
        
        # --- Saikyo & Kawagoe ---
        "Saikyō Line": ["JA"],
        "Saikyo Line": ["JA"],
        "Saikyō Line (Rapid)": ["JA"],
        "Saikyo Line (Rapid)": ["JA"],
        "Saikyō Line (Commuter Rapid)": ["JA"],
        "Saikyo Line (Commuter Rapid)": ["JA"],
        "Kawagoe Line": ["JA"],
        
        # --- Shonan-Shinjuku Corridor ---
        "Shōnan-Shinjuku Line": ["JS"],
        "Shonan-Shinjuku Line": ["JS"],
        "Shōnan-Shinjuku Line (Local)": ["JS"],
        "Shonan-Shinjuku Line (Local)": ["JS"],
        "Shōnan-Shinjuku Line (Rapid)": ["JS"],
        "Shonan-Shinjuku Line (Rapid)": ["JS"],
        "Shōnan-Shinjuku Line (Special Rapid)": ["JS"],
        "Shonan-Shinjuku Line (Special Rapid)": ["JS"],
        
        # --- Tokaido / Takasaki / Utsunomiya Trunk Routes ---
        "Tōkaidō Line": ["JT"],
        "Tokaido Line": ["JT"],
        "Tōkaidō Main Line": ["JT"],
        "Tokaido Main Line": ["JT"],
        "Ueno-Tokyo Line": ["JU"],
        "Takasaki Line": ["JU"],
        "Takasaki Line (Local)": ["JU"],
        "Takasaki Line (Rapid)": ["JU"],
        "Utsunomiya Line": ["JU"],
        "Utsunomiya Line (Local)": ["JU"],
        "Tōhoku Main Line": ["JU"],
        "Tohoku Main Line": ["JU"],
        "Tōhoku Main Line (Utsunomiya Line)": ["JU"],
        
        # --- Sobu Main & Yokosuka Connectors ---
        "Sōbu Rapid Line": ["JO"],
        "Sobu Rapid Line": ["JO"],
        "Sōbu Line (Rapid)": ["JO"],
        "Sobu Line (Rapid)": ["JO"],
        "Sōbu Main Line": ["JO"],
        "Sobu Main Line": ["JO"],
        "Yokosuka Line": ["JO"],
        "Yokosuka・Sōbu Rapid Line": ["JO"],
        "Yokosuka-Sobu Rapid Line": ["JO"],
        
        # --- Joban Line Trunk & Local Networks ---
        "Jōban Line": ["JJ"],
        "Joban Line": ["JJ"],
        "Jōban Line (Rapid)": ["JJ"],
        "Joban Line (Rapid)": ["JJ"],
        "Jōban Line Rapid": ["JJ"],
        "Joban Line Rapid": ["JJ"],
        "Jōban Main Line": ["JJ"],
        "Joban Main Line": ["JJ"],
        "Jōban Line (Local)": ["JL"],
        "Joban Line (Local)": ["JL"],
        "Jōban Line Local": ["JL"],
        "Joban Line Local": ["JL"],
        
        # --- Peripheral Commuter Loops ---
        "Musashino Line": ["JM"],
        "Keiyō Line": ["JE"],
        "Keiyo Line": ["JE"],
        "Keiyō Line (Local)": ["JE"],
        "Keiyo Line (Local)": ["JE"],
        "Keiyō Line (Rapid)": ["JE"],
        "Keiyo Line (Rapid)": ["JE"],
        "Yokohama Line": ["JH"],
        "Nambu Line": ["JN"],
        "Nambu Branch Line": ["JN"],
        "Tsurumi Line": ["JI"],
        "Sagami Line": ["SG"],
        "Hachikō Line": ["JR"],
        "Hachiko Line": ["JR"],
        "Itsukaichi Line": ["JC"],
        "Ōme Line": ["JC"],
        "Ome Line": ["JC"],

        # =====================================================================
        # === TOKYO METRO SUBWAYS =============================================
        # =====================================================================
        "Tokyo Metro Ginza Line": ["G"],
        "Ginza Line": ["G"],
        "Tokyo Metro Marunouchi Line": ["M"],
        "Marunouchi Line": ["M"],
        "Tokyo Metro Marunouchi Line Branch Line": ["Mb"],
        "Marunouchi Line Branch Line": ["Mb"],
        "Tokyo Metro Hibiya Line": ["H"],
        "Hibiya Line": ["H"],
        "Tokyo Metro Tōzai Line": ["T"],
        "Tokyo Metro Tozai Line": ["T"],
        "Tōzai Line": ["T"],
        "Tozai Line": ["T"],
        "Tokyo Metro Chiyoda Line": ["C"],
        "Chiyoda Line": ["C"],
        "Tokyo Metro Yūrakuchō Line": ["Y"],
        "Tokyo Metro Yurakucho Line": ["Y"],
        "Yūrakuchō Line": ["Y"],
        "Yurakucho Line": ["Y"],
        "Tokyo Metro Hanzōmon Line": ["Z"],
        "Tokyo Metro Hanzomon Line": ["Z"],
        "Hanzōmon Line": ["Z"],
        "Hanzomon Line": ["Z"],
        "Tokyo Metro Namboku Line": ["N"],
        "Namboku Line": ["N"],
        "Tokyo Metro Fukutoshin Line": ["F"],
        "Fukutoshin Line": ["F"],

        # =====================================================================
        # === TOEI SUBWAYS ====================================================
        # =====================================================================
        "Toei Asakusa Line": ["A"],
        "Asakusa Line": ["A"],
        "Toei Mita Line": ["I"],
        "Mita Line": ["I"],
        "Toei Shinjuku Line": ["S"],
        "Shinjuku Line": ["S"],
        "Toei Ōedo Line": ["E"],
        "Toei Oedo Line": ["E"],
        "Ōedo Line": ["E"],
        "Oedo Line": ["E"],

        # =====================================================================
        # === PRIVATE RAILWAYS (MAJOR GREATER TOKYO NETWORKS) =================
        # =====================================================================
        # --- Odakyu Lines ---
        "Odakyu Odawara Line": ["OH"],
        "Odakyu Electric Railway Odawara Line": ["OH"],
        "Odakyu Enoshima Line": ["OE"],
        "Odakyu Tama Line": ["OT"],
        
        # --- Keio Lines ---
        "Keiō Line": ["KO"],
        "Keio Line": ["KO"],
        "Keiō Electric Railway Line": ["KO"],
        "Keio Electric Railway Line": ["KO"],
        "Keiō New Line": ["KO"],
        "Keio New Line": ["KO"],
        "Keiō Sagamihara Line": ["KO"],
        "Keio Sagamihara Line": ["KO"],
        "Keiō Takao Line": ["KO"],
        "Keio Takao Line": ["KO"],
        "Keiō Inokashira Line": ["IN"],
        "Keio Inokashira Line": ["IN"],
        "Inokashira Line": ["IN"],
        
        # --- Seibu Lines ---
        "Seibu Ikebukuro Line": ["SI"],
        "Seibu Shinjuku Line": ["SS"],
        "Seibu Haijima Line": ["SS"],
        "Seibu Tamako Line": ["ST"],
        "Seibu Kokubunji Line": ["SK"],
        "Seibu Seibu-en Line": ["SK"],
        "Seibu Tamagawa Line": ["ST"],
        "Seibu Toshima Line": ["SI"],
        "Seibu Sayama Line": ["SI"],
        
        # --- Tobu Lines ---
        "Tobu Skytree Line": ["TS"],
        "Tōbu Skytree Line": ["TS"],
        "Tobu Isesaki Line": ["TI"],
        "Tōbu Isesaki Line": ["TI"],
        "Tobu Tojo Line": ["TJ"],
        "Tōbu Tōjō Line": ["TJ"],
        "Tobu Tojo Main Line": ["TJ"],
        "Tōbu Tōjō Main Line": ["TJ"],
        "Tobu Noda Line": ["TD"],
        "Tōbu Noda Line": ["TD"],
        "Tobu Urban Park Line": ["TD"],
        "Tōbu Urban Park Line": ["TD"],
        "Tobu Kameido Line": ["TS"],
        "Tobu Daishi Line": ["TS"],
        
        # --- Keisei Lines ---
        "Keisei Main Line": ["KS"],
        "Keisei Electric Railway Main Line": ["KS"],
        "Keisei Oshiage Line": ["KS"],
        "Keisei Chiba Line": ["KS"],
        "Keisei Kanamachi Line": ["KS"],
        "Keisei Narita Sky Access Line": ["KS"],
        "Hokuso Line": ["HS"],
        "Hokusō Line": ["HS"],
        
        # --- Tokyu Lines ---
        "Tokyu Toyoko Line": ["TY"],
        "Tōkyū Tōyoko Line": ["TY"],
        "Tokyu Den-en-toshi Line": ["DT"],
        "Tōkyū Den-en-toshi Line": ["DT"],
        "Tokyu Meguro Line": ["MG"],
        "Tōkyū Meguro Line": ["MG"],
        "Tokyu Oimachi Line": ["OM"],
        "Tōkyū Ōimachi Line": ["OM"],
        "Tokyu Ikegami Line": ["IK"],
        "Tōkyū Ikegami Line": ["IK"],
        "Tokyu Tamagawa Line": ["TM"],
        "Tōkyū Tamagawa Line": ["TM"],
        "Tokyu Setagaya Line": ["SG"],
        "Tōkyū Setagaya Line": ["SG"],
        
        # --- Keikyu Lines ---
        "Keikyu Main Line": ["KK"],
        "Keikyū Main Line": ["KK"],
        "Keikyu Electric Railway Main Line": ["KK"],
        "Keikyū Electric Railway Main Line": ["KK"],
        "Keikyu Airport Line": ["KK"],
        "Keikyū Airport Line": ["KK"],
        "Keikyu Kurihama Line": ["KK"],
        "Keikyū Kurihama Line": ["KK"],
        "Keikyu Zushi Line": ["KK"],
        "Keikyū Zushi Line": ["KK"],
        
        # --- Expressways / Peripheral Transit Systems ---
        "Tsukuba Express": ["TX"],
        "Tokyo Monorail": ["MO"],
        "Rinkai Line": ["R"],
        "Yurikamome": ["U"],
        "Saitama Rapid Railway Line": ["SR"],
        "Saitama Railway Line": ["SR"],
        "Toyo Rapid Railway Line": ["TR"],
        "Tōyō Rapid Railway Line": ["TR"],
        "Enoshima Electric Railway": ["EN"],
        "Shonan Monorail": ["SM"],
        "Shōnan Monorail": ["SM"]
    }
    src = row['source']
    dest = row['end']

    # --- SITUATION 1: Platform-to-Platform (Both are State Tuples) ---
    if isinstance(src, tuple) and isinstance(dest, tuple):
        src_name = src[1]
        dst_name = dest[1]
        if src_name == dst_name:
            return "Internal Transfer"
        else:
            return f"Platform Transfer: {src_name} -> {dst_name}"

    # --- SITUATION 2: Platform-to-Track (Departing a Station Hub) ---
    elif isinstance(src, tuple) and not isinstance(dest, tuple):
        if dest in station_node_coordinates:
            return station_name_map.get(dest, f"Station Node {dest}")
        else:
            try:
                way_idx_list = node_to_way_index.get(dest)
                if way_idx_list:
                    line_name = way_name_map.get(way_idx_list[0])
                    return name_to_ref.get(line_name, line_name if line_name else f"Way ID {way_idx_list[0]}")
                return f"Track Node {dest}"
            except:
                return f"Track Node {dest}"

    # --- SITUATION 3: Track-to-Platform (Arriving at a Station Hub) ---
    elif not isinstance(src, tuple) and isinstance(dest, tuple):
        if src in station_node_coordinates:
            return station_name_map.get(src, f"Station Node {src}")
        else:
            try:
                way_idx_list = node_to_way_index.get(src)
                if way_idx_list:
                    line_name = way_name_map.get(way_idx_list[0])
                    return name_to_ref.get(line_name, line_name if line_name else f"Way ID {way_idx_list[0]}")
                return f"Track Node {src}"
            except:
                return f"Track Node {src}"

    # --- SITUATION 4: Track-to-Track (Cruising on Open Line) ---
    elif not isinstance(src, tuple) and not isinstance(dest, tuple):
        if src in station_node_coordinates:
            return station_name_map.get(src, f"Station Node {src}")
        else:
            try:
                # Resolve way indexes safely
                way_idx_list = node_to_way_index.get(src)
                if not way_idx_list:
                    way_idx_list = node_to_way_index.get(dest)
                
                if way_idx_list:
                    line_name = way_name_map.get(way_idx_list[0])
                    if line_name:
                        # Attempt Dictionary match, Fallback to String name, Fallback to Way Index, Fallback to Node Int
                        return name_to_ref.get(line_name, line_name)
                    return f"Way ID {way_idx_list[0]}"
                return src # If completely isolated, return raw ID
            except:
                return src

    return None
    
def track_filter(row):
    if row['name'] == 'Internal Transfer' or 'Platform Transfer' in row['name'] or row['name'] in stations:
        return 'FALSE'
    else:
        return 'TRUE'
if __name__ == "__main__":

    # ------------------ Data Loading ------------------
    
    print("Loading network graph data...")
    (rail_network_graph, station_name_map, track_node_coordinates, 
     station_node_coordinates, node_to_way_index, way_name_map, 
     station_elements) = setup(True)
    stations = [
        "Akihabara", "Asakusa", "Chiba", "Ebisu", "Ginza", "Hachijo", "Hachioji", "Hamamatsucho", 
        "Haneda Airport", "Harajuku", "Higashi-shinjuku", "Iidabashi", "Ikebukuro", "Kamata", 
        "Kanda", "Kawasaki", "Kita-senju", "Mac", "Machida", "Marunouchi", "Meguro", "Minami-senju", 
        "Mitaka", "Musashino", "Nagatacho", "Nishi-nippori", "Nishi-shinjuku", "Odaiba", "Oimachi", 
        "Okubo", "Omotesando", "Oonuma", "Oosaki", "Ota", "Otemachi", "Roppongi", "Shibuya", 
        "Shin-kiba", "Shin-okubo", "Shin-yokohama", "Shinagawa", "Shimbashi", "Shinjuku", "Suidobashi", 
        "Tachikawa", "Takanawa Gateway", "Tokyo", "Ueno", "Yokohama", "Yonago", "Yotsuya", "Yoyogi"
    ]
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
 
    # Load the CSV file
    df = pd.read_csv('../kepler_tokyo_transit/data.csv')
    df['source'] = df['start_node'].map(index_to_state)
    df['end'] = df['end_node'].map(index_to_state)
    df['name'] = df.apply(name_assigner, axis=1)
    df['transfer'] = df.apply(track_filter, axis=1)
    

    output_path = '../kepler_tokyo_transit/data_enriched.csv'
    print(f"Saving final dataset to {output_path}...")

    df.drop(columns=['source', 'end'])
    df.to_csv(output_path, index=False)
    print(df)
    

