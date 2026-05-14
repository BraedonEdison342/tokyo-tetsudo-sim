English
High-performance agent-based simulation of the Tokyo railway network.
This project simulates 1,000,000 agents commuting across Tokyo in real-time using OpenStreetMap data. It features a custom "skyscraper" graph architecture for multi-line hubs, GPU-accelerated SSSP pathfinding via cuGraph, and a vectorized NumPy movement engine for massive scale. Includes optimized Dijkstra routing with transfer penalties and coordinate-binning for station-to-track connectivity.

Japanese (日本語)
東京の鉄道網を対象とした高性能なエージェントベースのシミュレーション。
OpenStreetMapのデータを使用し、100万人規模のエージェントの通勤をリアルタイムでシミュレートするプロジェクトです。複数路線が乗り入れるハブ駅を再現する「スカイスクレイパー（摩天楼）」グラフ構造、cuGraphによるGPU加速されたSSSP経路探索、そして大規模処理を可能にするNumPyベクトル化移動エンジンを搭載しています。乗り換えペナルティを考慮したDijkstraルーティングと、座標ビン化による駅・線路接続の最適化を実装しています。
