#!/usr/bin/env python3
"""
RouteSync Charging Station Generator
=====================================
Downloads raw charging station data from multiple sources and saves as
intermediate JSON files. Then run convert_to_routesync.py for final conversion.

Data sources:
- OpenStreetMap via Overpass API (global)
- NREL/AFDC (US & Canada)

Usage:
    python generate.py
    python convert_to_routesync.py
"""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "charging_raw_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_nrel_data():
    """Download NREL/AFDC EV charging station data"""
    print("[NREL] Downloading US/Canada EV charging data...")
    
    all_stations = []
    offset = 0
    LIMIT = 200
    API_KEY = "DEMO_KEY"
    TARGET = 87079
    batch_num = 0
    
    while offset < TARGET:
        url = (f"https://developer.nrel.gov/api/alt-fuel-stations/v1.json"
               f"?fuel_type=ELEC&limit={LIMIT}&offset={offset}&api_key={API_KEY}")
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "RouteSync-Generator/2.0")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            
            stations = data.get("fuel_stations", [])
            if not stations:
                break
            
            all_stations.extend(stations)
            batch_num += 1
            if batch_num % 25 == 1:
                print(f"  Progress: {len(all_stations)}/{TARGET}")
            
            offset += LIMIT
            time.sleep(0.5)
            
        except Exception as e:
            if "429" in str(e):
                print(f"  Rate limited at offset {offset}, waiting 60s...")
                time.sleep(60)
            else:
                print(f"  Error: {e}")
                time.sleep(5)
    
    out_path = os.path.join(OUTPUT_DIR, "afdc", "nrel_ev_stations.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_stations, f)
    
    print(f"[NREL] Downloaded {len(all_stations)} stations")
    return len(all_stations)


def fetch_osm_region(bbox):
    """Query Overpass API for charging stations in a bounding box"""
    south, west, north, east = bbox
    lat_step = min(15, north - south)
    lon_step = min(20, east - west)
    all_elements = []
    
    lat = south
    while lat < north:
        chunk_north = min(lat + lat_step, north)
        lon = west
        while lon < east:
            chunk_east = min(lon + lon_step, east)
            query = (f'[out:json][timeout:250];'
                     f'(node["amenity"="charging"]({lat},{lon},{chunk_north},{chunk_east});'
                     f'way["amenity"="charging"]({lat},{lon},{chunk_north},{chunk_east}););'
                     f'out center;')
            data = urllib.parse.urlencode({"data": query}).encode()
            
            for endpoint in [
                "https://overpass-api.de/api/interpreter",
                "https://overpass.kumi.systems/api/interpreter"
            ]:
                try:
                    req = urllib.request.Request(endpoint, data=data)
                    req.add_header("User-Agent", "RouteSync-Generator/2.0")
                    with urllib.request.urlopen(req, timeout=260) as resp:
                        result = json.loads(resp.read())
                        all_elements.extend(result.get("elements", []))
                        break
                except:
                    time.sleep(30)
            
            time.sleep(5)
            lon = chunk_east
        lat = chunk_north
    
    return all_elements


def fetch_osm_europe():
    """Download OSM charging data for Europe"""
    print("[OSM] Downloading Europe charging data...")
    elements = fetch_osm_region((34, -25, 72, 45))
    
    out_path = os.path.join(OUTPUT_DIR, "osm_europe.json")
    with open(out_path, "w") as f:
        json.dump({"elements": elements}, f)
    
    print(f"[OSM] Europe: {len(elements)} stations")
    return len(elements)


def fetch_osm_world():
    """Download OSM charging data for rest of world"""
    print("[OSM] Downloading rest of world...")
    all_elements = []
    
    for name, bbox in [
        ("north_america", (25, -170, 75, -50)),
        ("south_america", (-60, 85, 15, -30)),
        ("eastern_europe_russia", (45, 25, 75, 180)),
        ("east_asia", (20, 73, 55, 150)),
        ("south_asia", (-10, 65, 35, 100)),
        ("southeast_asia", (-10, 95, 25, 155)),
        ("africa", (-35, -20, 37, 55)),
        ("oceania", (-50, 100, 0, 180)),
    ]:
        print(f"  {name}...", flush=True)
        elements = fetch_osm_region(bbox)
        all_elements.extend(elements)
        print(f"  {name}: {len(elements)}")
    
    out_path = os.path.join(OUTPUT_DIR, "osm_world.json")
    with open(out_path, "w") as f:
        json.dump({"elements": all_elements}, f)
    
    print(f"[OSM] World: {len(all_elements)} stations")
    return len(all_elements)


def main():
    print("=" * 60)
    print("RouteSync Charging Station Generator")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    total = 0
    try: total += fetch_nrel_data()
    except Exception as e: print(f"[NREL] Failed: {e}")
    
    try: total += fetch_osm_europe()
    except Exception as e: print(f"[OSM Europe] Failed: {e}")
    
    try: total += fetch_osm_world()
    except Exception as e: print(f"[OSM World] Failed: {e}")
    
    print(f"\nTotal raw stations: {total}")
    print(f"Next: Run convert_to_routesync.py")


if __name__ == "__main__":
    main()
