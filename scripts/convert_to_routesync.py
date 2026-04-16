#!/usr/bin/env python3
"""
RouteSync Charging Station Database Builder v2.0
=================================================
Converts raw OSM and NREL/AFDC data into proper RouteSync POI format.

Features:
- Full OSM tag parsing (connectors, power, operator, address, amenities)
- NREL/AFDC enrichment with US station data
- Intelligent deduplication based on geohash proximity
- Clean naming normalization (German operators, international names)
- Proper RouteSync v1.5.0+ tile format output
"""

import json
import os
import sys
import time
import math
import re
from datetime import datetime, timezone
from collections import defaultdict

# ============================================================
# Configuration
# ============================================================
INPUT_EUROPE_TILES = "/home/z/my-project/download/RouteSync-Charging-Stations/tiles"
INPUT_NREL = "/home/z/my-project/download/charging_raw_data/afdc/nrel_ev_stations.json"
OUTPUT_DIR = "/home/z/my-project/download/RouteSync-Charging-Stations-v2"
TILES_DIR = os.path.join(OUTPUT_DIR, "tiles")
OSM_URL = "https://www.openstreetmap.org/node/"

GEOHASH_PRECISION = 6  # ~1.2km precision for dedup
DEDUP_DISTANCE_KM = 0.05  # 50 meters

# ============================================================
# OSM Tag Mappings for RouteSync
# ============================================================

# Socket type mappings (OSM tag → RouteSync standard name)
SOCKET_MAP = {
    "socket:type2": "Type 2",
    "socket:type2_combo": "CCS (Type 2)",
    "socket:chademo": "CHAdeMO",
    "socket:tesla_supercharger": "Tesla Supercharger",
    "socket:tesla_destination": "Tesla Destination",
    "socket:type1": "Type 1 (J1772)",
    "socket:type1_combo": "CCS (Type 1)",
    "socket:cee_blue": "CEE Blau (16A)",
    "socket:cee_red": "CEE Rot (32A/63A)",
    "socket:schuko": "Schuko",
    "socket:wall_mounted": "Wallbox",
    "socket:domestic_type_f": "Type F (Schuko)",
    "socket:domestic_type_g": "Type G (UK)",
    "socket:domestic_type_d": "Type D (India)",
    "socket:gb_t": "GB/T (China)",
    "socket:scame": "SCAME",
}

# Common operator name normalizations
OPERATOR_ALIASES = {
    "EnBW Energie Baden-Württemberg AG": "EnBW",
    "EnBW Charging GmbH": "EnBW",
    "EnBW": "EnBW",
    "E.ON Energie Deutschland GmbH": "E.ON",
    "E.ON Drive Infrastructure": "E.ON",
    "E.ON": "E.ON",
    "RWE Effizienz GmbH": "RWE",
    "innogy SE": "innogy",
    "innogy eMobility Solutions GmbH": "innogy",
    "TotalEnergies Charging Services": "TotalEnergies",
    "Total Energies Charging Services": "TotalEnergies",
    "Total Energie": "TotalEnergies",
    "TOTAL": "TotalEnergies",
    "Shell Recharge Solutions": "Shell Recharge",
    "Shell Recharge Solutions BV": "Shell Recharge",
    "Ionity GmbH": "IONITY",
    "IONITY": "IONITY",
    "Tesla, Inc.": "Tesla",
    "Tesla Motors": "Tesla",
    "Tesla Supercharger": "Tesla Supercharger",
    "Allego BV": "Allego",
    "Allego GmbH": "Allego",
    "Vattenfall InCharge": "Vattenfall InCharge",
    "Vattenfall": "Vattenfall InCharge",
    "Lidl Deutschland GmbH & Co. KG": "Lidl",
    "LIDL": "Lidl",
    "Kaufland Stiftung & Co. KG": "Kaufland",
    "Aldi Süd GmbH & Co. KG": "ALDI Süd",
    "Aldi Nord GmbH & Co. KG": "ALDI Nord",
    "REWE Markt GmbH": "REWE",
    "Izivia": "Izivia",
    "Smappee": "Smappee",
    "Freshmile": "Freshmile",
    "Bouygues Énergies et Services": "Bouygues E&S",
    "SPBR1": "SPBR1",
    "Maingau Energie GmbH": "Mainova",
    "Stadtwerke München GmbH": "Stadtwerke München",
    "WEMAG": "WEMAG",
    "Stadtwerke": "Stadtwerke",
    "ChargePoint": "ChargePoint",
    "EVgo": "EVgo",
    "Electrify America": "Electrify America",
    "Blink Charging": "Blink",
    "ChargeMaster": "ChargeMaster",
    "Pod Point": "Pod Point",
    "Clever": "Clever",
    "Enel X": "Enel X",
    "EnelX": "Enel X",
    "Enel Distribuzione": "Enel X",
    "Endesa": "Endesa",
    "Iberdrola": "Iberdrola",
    "Gemeente Den Haag": "Gemeente Den Haag",
    "Samenwerkende Gemeenten Zuid-Holland": "SG Zuid-Holland",
    "Stadtwerke": "Stadtwerke",
}

# NREL connector type mappings
NREL_CONNECTOR_MAP = {
    "J1772": {"type": "Type 1 (J1772)", "kw": 7.2},
    "J1772COMBO": {"type": "CCS (Type 1)", "kw": 50},
    "CHADEMO": {"type": "CHAdeMO", "kw": 50},
    "TESLA": {"type": "Tesla Supercharger", "kw": 150},
    "NEMA515": {"type": "NEMA 5-15", "kw": 1.4},
    "NEMA520": {"type": "NEMA 5-20", "kw": 1.9},
    "NEMA1450": {"type": "NEMA 14-50", "kw": 9.6},
    "NEMA620": {"type": "NEMA 6-20", "kw": 4.8},
    "NEMA630": {"type": "NEMA 6-30", "kw": 7.2},
    "NEMA1450P": {"type": "NEMA 14-50P", "kw": 9.6},
    "TESLAHPC": {"type": "Tesla Supercharger", "kw": 250},
}

# Country code mapping from OSM tags
COUNTRY_MAP = {
    "DE": "DE", "AT": "AT", "CH": "CH", "FR": "FR", "IT": "IT",
    "ES": "ES", "NL": "NL", "BE": "BE", "LU": "LU", "PL": "PL",
    "CZ": "CZ", "DK": "DK", "SE": "SE", "NO": "NO", "FI": "FI",
    "GB": "GB", "IE": "IE", "PT": "PT", "GR": "GR", "HR": "HR",
    "SI": "SI", "SK": "SK", "HU": "HU", "RO": "RO", "BG": "BG",
    "IS": "IS", "LT": "LT", "LV": "LV", "EE": "EE", "RU": "RU",
    "UA": "UA", "TR": "TR", "US": "US", "CA": "CA", "JP": "JP",
    "KR": "KR", "CN": "CN", "AU": "AU", "NZ": "NZ", "IN": "IN",
}

# ============================================================
# Helper Functions
# ============================================================

def geohash_encode(lat, lon, precision=6):
    """Simple geohash encoding for deduplication"""
    # Simplified geohash for clustering
    base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range, lon_range = [-90.0, 90.0], [-180.0, 180.0]
    geohash = ""
    bits = 0
    bit_total = 0
    hash_val = 0
    
    while len(geohash) < precision:
        if bit_total % 2 == 0:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon > mid:
                hash_val = (hash_val << 1) | 1
                lon_range[0] = mid
            else:
                hash_val = (hash_val << 1) | 0
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat > mid:
                hash_val = (hash_val << 1) | 1
                lat_range[0] = mid
            else:
                hash_val = (hash_val << 1) | 0
                lat_range[1] = mid
        bit_total += 1
        if bit_total % 5 == 0:
            geohash += base32[hash_val]
            hash_val = 0
    
    return geohash


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in km"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def parse_power_kw(power_str):
    """Parse power output string to kW float"""
    if not power_str:
        return None
    power_str = str(power_str).strip().lower()
    # Remove common suffixes
    power_str = power_str.replace("kw", "").replace(" kw", "").strip()
    try:
        return float(power_str)
    except ValueError:
        # Try to extract number from string like "22 kW" or "up to 150kw"
        match = re.search(r'(\d+(?:\.\d+)?)', power_str)
        if match:
            return float(match.group(1))
    return None


def normalize_operator(raw_name):
    """Normalize operator name to clean display name"""
    if not raw_name:
        return "Unbekannt"
    
    name = raw_name.strip()
    
    # Check aliases first
    if name in OPERATOR_ALIASES:
        return OPERATOR_ALIASES[name]
    
    # Try case-insensitive match
    name_lower = name.lower()
    for alias, clean in OPERATOR_ALIASES.items():
        if alias.lower() == name_lower:
            return clean
    
    # Remove common suffixes
    for suffix in [" GmbH", " GmbH & Co. KG", " AG", " SE", " BV", " S.A.", " Srl",
                    " Ltd", " LLC", " Inc.", " Corp.", " KG", " OHG", " eG",
                    " charging services", " infrastructure"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    
    return name if name else "Unbekannt"


def normalize_name(raw_name, operator, tags):
    """Generate a clean display name for the station"""
    if raw_name and raw_name.strip():
        name = raw_name.strip()
        # Clean up common patterns
        name = re.sub(r'\s+', ' ', name)
        return name
    
    # Generate name from operator + info
    if operator and operator != "Unbekannt":
        extra = []
        if tags.get("brand"):
            extra.append(tags["brand"])
        
        # Add network info
        network = tags.get("network") or tags.get("operator")
        if network and network != operator:
            extra.append(network)
        
        if extra:
            return f"{operator} - {extra[0]}"
        return f"Ladestation {operator}"
    
    # Last resort: generic name based on what we know
    if tags.get("brand"):
        return f"Ladestation {tags['brand']}"
    
    return "Ladeeinrichtung"


def parse_osm_sockets(tags):
    """Parse OSM socket tags into RouteSync socket format"""
    sockets = []
    
    for osm_key, rs_name in SOCKET_MAP.items():
        count_str = tags.get(osm_key)
        if not count_str:
            continue
        
        try:
            count = int(count_str)
        except ValueError:
            # Could be "yes" or something
            if count_str.lower() in ("yes", "true", "1"):
                count = 1
            else:
                continue
        
        # Get power output
        power_kw = None
        output_key = osm_key + ":output"
        output_str = tags.get(output_key, "")
        power_kw = parse_power_kw(output_str)
        
        # Estimate power based on socket type if not specified
        if power_kw is None:
            power_estimates = {
                "Schuko": 2.3, "Type F (Schuko)": 2.3, "CEE Blau (16A)": 3.7,
                "Type 1 (J1772)": 7.2, "Type 2": 22, "Wallbox": 11,
                "CHAdeMO": 50, "CCS (Type 2)": 50, "CCS (Type 1)": 50,
                "Tesla Supercharger": 150, "Tesla Destination": 11,
                "GB/T (China)": 7,
            }
            power_kw = power_estimates.get(rs_name)
        
        sockets.append({
            "type": rs_name,
            "kw": power_kw,
            "count": count
        })
    
    return sockets


def parse_osm_address(tags):
    """Parse OSM address tags into RouteSync address format"""
    addr = {}
    
    street = tags.get("addr:street", "")
    housenumber = tags.get("addr:housenumber", "")
    if street:
        addr["street"] = f"{street} {housenumber}".strip()
    
    postcode = tags.get("addr:postcode", "")
    if postcode:
        addr["postcode"] = postcode
    
    city = tags.get("addr:city", "") or tags.get("addr:town", "") or tags.get("addr:village", "")
    if city:
        addr["city"] = city
    
    country_code = tags.get("addr:country", "").upper()
    if country_code and len(country_code) == 2:
        addr["country"] = country_code
    
    return addr if addr else None


def parse_osm_amenities(tags):
    """Parse OSM amenity tags"""
    amenities = {}
    
    # Opening hours
    if tags.get("opening_hours"):
        amenities["opening_hours"] = tags["opening_hours"]
    
    # Payment
    payment = []
    pay_tags = [k for k in tags if k.startswith("payment:")]
    for pt in pay_tags:
        if tags[pt] in ("yes", "true", "1"):
            payment.append(pt.replace("payment:", "").replace("_", " ").title())
        elif tags[pt] in ("no", "false", "0"):
            pass
    if payment:
        amenities["payment_methods"] = payment
    
    # Auth
    auth = tags.get("authentication:none", "") == "yes"
    if auth:
        amenities["authentication"] = "none"
    elif tags.get("authentication:app"):
        amenities["authentication"] = "app"
    elif tags.get("authentication:rfid"):
        amenities["authentication"] = "rfid"
    
    # Fee
    fee = tags.get("fee", "")
    if fee:
        amenities["fee"] = fee == "yes"
    
    # Parking
    if tags.get("parking:fee"):
        amenities["parking_fee"] = tags["parking:fee"] == "yes"
    
    # Services
    services = []
    if tags.get("toilets") == "yes":
        services.append("toilets")
    if tags.get("shop") or tags.get("convenience"):
        services.append("shop")
    if tags.get("cafe") or tags.get("restaurant") or tags.get("food"):
        services.append("restaurant")
    if tags.get("wifi") == "yes":
        services.append("wifi")
    if tags.get("hotel") or tags.get("tourism") == "hotel":
        services.append("hotel")
    if services:
        amenities["nearby_services"] = services
    
    # Accessibility
    if tags.get("wheelchair") == "yes":
        amenities["wheelchair"] = True
    
    return amenities if amenities else None


def infer_country_from_coords(lat, lon):
    """Rough country inference from coordinates"""
    # Europe
    if 47 <= lat <= 55 and 5 <= lon <= 15:
        return "DE"
    if 46 <= lat <= 49 and 9 <= lon <= 17:
        return "AT"
    if 45.5 <= lat <= 48 and 5.5 <= lon <= 10.5:
        return "CH"
    if 42 <= lat <= 51.5 and -5.5 <= lon <= 8.5:
        return "FR"
    if 36.5 <= lat <= 47.5 and 6.5 <= lon <= 19:
        return "IT"
    if 36 <= lat <= 44 and -9.5 <= lon <= 3.5:
        return "ES"
    if 50.5 <= lat <= 54 and 3 <= lon <= 7.5:
        return "NL"
    if 49.5 <= lat <= 51.5 and 2.5 <= lon <= 6.5:
        return "BE"
    if 48.5 <= lat <= 55.5 and 9.5 <= lon <= 24.5:
        return "PL"
    if 48.5 <= lat <= 51.5 and 11.5 <= lon <= 19:
        return "CZ"
    if 54.5 <= lat <= 58 and 7.5 <= lon <= 13:
        return "DK"
    if 55 <= lat <= 69 and 11 <= lon <= 25:
        return "SE"
    if 58 <= lat <= 71 and 4 <= lon <= 31:
        return "NO"
    if 59.5 <= lat <= 70.5 and 19 <= lon <= 32:
        return "FI"
    if 49.8 <= lat <= 59.5 and -8.5 <= lon <= 2:
        return "GB"
    if 25 <= lat <= 50 and -125 <= lon <= -66:
        return "US"
    if 42 <= lat <= 84 and -141 <= lon <= -52:
        return "CA"
    if 30 <= lat <= 46 and 129 <= lon <= 146:
        return "JP"
    if 33 <= lat <= 39 and 125 <= lon <= 130:
        return "KR"
    return None


def infer_country_from_nrel(nrel_country):
    """Map NREL country codes"""
    mapping = {
        "US": "US", "CA": "CA", "MX": "MX",
    }
    return mapping.get(nrel_country, nrel_country)


def convert_osm_to_routesync(element):
    """Convert a single OSM element to RouteSync POI format"""
    tags = element.get("tags", {})
    
    # Get coordinates
    lat = element.get("lat")
    lon = element.get("lon")
    if lat is None or lon is None:
        # For ways, try center from Overpass "out center"
        if "center" in element:
            lat = element["center"].get("lat")
            lon = element["center"].get("lon")
        if lat is None or lon is None:
            return None
    
    # Parse all fields
    raw_operator = tags.get("operator", "") or tags.get("network", "")
    operator = normalize_operator(raw_operator)
    name = normalize_name(tags.get("name"), operator, tags)
    sockets = parse_osm_sockets(tags)
    address = parse_osm_address(tags)
    amenities = parse_osm_amenities(tags)
    
    # Max power
    max_kw = None
    if sockets:
        powers = [s["kw"] for s in sockets if s["kw"] is not None]
        if powers:
            max_kw = max(powers)
    
    # Capacity
    capacity = None
    cap_str = tags.get("capacity", "")
    if cap_str:
        try:
            capacity = int(cap_str)
        except ValueError:
            pass
    
    # Country
    country = tags.get("addr:country", "").upper()
    if not country or len(country) != 2:
        country = infer_country_from_coords(lat, lon)
    
    # Build address if not from tags
    if not address:
        address = {}
        if country:
            address["country"] = country
    
    # Build POI
    poi = {
        "id": f"osm-{element.get('id', 'unknown')}",
        "name": name,
        "type": "charging_station",
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "operator": operator,
        "address": address,
        "power": {},
        "source": "osm",
        "tags": {
            "access": tags.get("access", ""),
            "fee": tags.get("fee", ""),
            "brand": tags.get("brand", ""),
            "network": tags.get("network", ""),
            "opening_hours": tags.get("opening_hours", ""),
        }
    }
    
    if max_kw is not None:
        poi["power"]["max_kw"] = max_kw
    if sockets:
        poi["power"]["sockets"] = sockets
    if capacity:
        poi["power"]["capacity"] = capacity
    if amenities:
        poi["amenities"] = amenities
    
    # Clean up empty power dict
    if not poi["power"]:
        del poi["power"]
    
    return poi


def convert_nrel_to_routesync(station):
    """Convert a single NREL/AFDC station to RouteSync POI format"""
    lat = station.get("latitude")
    lon = station.get("longitude")
    if lat is None or lon is None:
        return None
    
    # Basic info
    name = station.get("station_name", "") or station.get("facility_type", "")
    if not name:
        name = "Charging Station"
    
    operator = station.get("ev_network", "")
    if not operator or operator in ("Non-Networked", "Unknown", ""):
        operator = station.get("owner_type_code", "")
        if not operator:
            operator = normalize_operator(station.get("station_name", ""))
    
    operator = normalize_operator(operator)
    name = normalize_name(name if station.get("station_name") else None, operator, {})
    
    # Address
    address = {}
    street = station.get("street_address", "")
    if street:
        address["street"] = street
    city = station.get("city", "")
    if city:
        address["city"] = city
    state = station.get("state", "")
    if state:
        address["state"] = state
    zipcode = station.get("zip", "")
    if zipcode:
        address["postcode"] = zipcode
    country = infer_country_from_nrel(station.get("country", ""))
    if country:
        address["country"] = country
    
    # Connectors
    sockets = []
    connector_types = station.get("ev_connector_types", "")
    if connector_types:
        if isinstance(connector_types, list):
            conn_list = connector_types
        else:
            conn_list = connector_types.split(",")
        for conn in conn_list:
            conn = str(conn).strip().upper()
            if conn in NREL_CONNECTOR_MAP:
                info = NREL_CONNECTOR_MAP[conn]
                sockets.append({
                    "type": info["type"],
                    "kw": info["kw"],
                    "count": 1
                })
    
    # Power
    max_kw = None
    dc_fast = station.get("ev_dc_fast_num")
    level2 = station.get("ev_level2_evse_num")
    level1 = station.get("ev_level1_evse_num")
    
    if dc_fast and int(dc_fast) > 0:
        max_kw = max(s["kw"] for s in sockets if s["kw"] and s["kw"] > 40) if sockets else 50
    elif level2 and int(level2) > 0:
        max_kw = 7.2
    elif level1 and int(level1) > 0:
        max_kw = 1.9
    
    # Access
    access_code = station.get("access_code", "")
    access_time = station.get("access_days_time", "")
    
    # Build POI
    poi = {
        "id": f"nrel-{station.get('id', 'unknown')}",
        "name": name,
        "type": "charging_station",
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "operator": operator,
        "address": address if address else None,
        "source": "nrel",
        "tags": {
            "access": access_code.lower() if access_code else "",
            "fee": "yes",
            "network": station.get("ev_network_web", ""),
            "opening_hours": access_time or "",
            "status": station.get("status_code", ""),
        }
    }
    
    power_info = {}
    if max_kw:
        power_info["max_kw"] = max_kw
    if sockets:
        power_info["sockets"] = sockets
    # Total EVSE count
    total_evse = 0
    for field in [dc_fast, level2, level1]:
        if field:
            try:
                total_evse += int(field)
            except:
                pass
    if total_evse:
        power_info["capacity"] = total_evse
    
    if power_info:
        poi["power"] = power_info
    
    # Amenities
    amenities = {}
    if access_time:
        amenities["opening_hours"] = access_time
    if station.get("restricted_access") == "false":
        amenities["public_access"] = True
    if station.get("ev_pricing"):
        amenities["pricing"] = station["ev_pricing"]
    cards = station.get("cards_accepted", "")
    if cards:
        amenities["payment_methods"] = [c.strip() for c in cards.split(",") if c.strip()]
    
    if amenities:
        poi["amenities"] = amenities
    
    return poi


def deduplicate_stations(stations, distance_km=DEDUP_DISTANCE_KM):
    """Remove duplicate stations based on geographic proximity"""
    print(f"Deduplicating {len(stations)} stations (threshold: {distance_km}km)...")
    
    # Group by geohash for efficient comparison
    buckets = defaultdict(list)
    for station in stations:
        gh = geohash_encode(station["lat"], station["lon"], GEOHASH_PRECISION)
        buckets[gh].append(station)
    
    seen = {}
    unique = []
    duplicates = 0
    
    for gh, group in buckets.items():
        for station in group:
            # Check nearby geohash buckets too
            is_dup = False
            check_keys = [gh]
            # Also check neighboring buckets
            for c in group:
                for existing_key in check_keys:
                    if existing_key in seen:
                        for existing in seen[existing_key]:
                            dist = haversine_km(station["lat"], station["lon"],
                                               existing["lat"], existing["lon"])
                            if dist < distance_km:
                                is_dup = True
                                # Keep the one with more data
                                if (len(station.get("power", {}).get("sockets", [])) >
                                    len(existing.get("power", {}).get("sockets", []))):
                                    # Replace existing with this one
                                    unique = [s for s in unique if s["id"] != existing["id"]]
                                    seen[existing_key].remove(existing)
                                    unique.append(station)
                                    seen[gh].append(station)
                                break
                        if is_dup:
                            break
                    if is_dup:
                        break
            
            if not is_dup:
                unique.append(station)
                if gh not in seen:
                    seen[gh] = []
                seen[gh].append(station)
            else:
                duplicates += 1
    
    print(f"  Removed {duplicates} duplicates, {len(unique)} unique stations remain")
    return unique


def build_tiles(stations, output_dir):
    """Build RouteSync tile files from station list"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Group by tile (integer lat/lon)
    tiles = defaultdict(list)
    for station in stations:
        tile_lat = int(station["lat"])
        tile_lon = int(station["lon"])
        tiles[(tile_lat, tile_lon)].append(station)
    
    manifest_tiles = {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for (tile_lat, tile_lon), pois in sorted(tiles.items()):
        filename = f"poi-tile-{tile_lat}-{tile_lon}.json"
        filepath = os.path.join(output_dir, filename)
        
        tile_data = {
            "format": "routesync-poi-v1.5.0",
            "tile": {
                "lat": tile_lat,
                "lon": tile_lon,
                "bounds": {
                    "south": tile_lat,
                    "north": tile_lat + 1,
                    "west": tile_lon,
                    "east": tile_lon + 1,
                }
            },
            "generated": now,
            "count": len(pois),
            "pois": pois
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(tile_data, f, ensure_ascii=False, indent=2)
        
        manifest_tiles[filename] = {
            "lat": tile_lat,
            "lon": tile_lon,
            "count": len(pois),
            "size_bytes": os.path.getsize(filepath),
        }
    
    return manifest_tiles


def build_stats(stations):
    """Build statistics from station list"""
    stats = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_stations": len(stations),
        "total_tiles": 0,
        "database_size_bytes": 0,
        "sources": defaultdict(int),
        "operators": defaultdict(int),
        "countries": defaultdict(int),
        "connector_types": defaultdict(int),
        "power_distribution": {
            "dc_fast_50kw_plus": 0,
            "fast_22_50kw": 0,
            "normal_7_22kw": 0,
            "slow_under_7kw": 0,
            "unknown": 0,
        },
        "amenities_count": 0,
        "with_address": 0,
        "with_operator": 0,
    }
    
    for station in stations:
        # Source
        stats["sources"][station.get("source", "unknown")] += 1
        
        # Operator
        op = station.get("operator", "")
        if op and op != "Unbekannt":
            stats["operators"][op] += 1
            stats["with_operator"] += 1
        
        # Country
        country = station.get("address", {}) or {}
        if isinstance(country, dict):
            cc = country.get("country", "")
        else:
            cc = ""
        if not cc:
            cc = infer_country_from_coords(station["lat"], station["lon"]) or "Unknown"
        stats["countries"][cc] += 1
        
        # Address
        if station.get("address"):
            stats["with_address"] += 1
        
        # Connectors & Power
        sockets = station.get("power", {}).get("sockets", [])
        max_kw = station.get("power", {}).get("max_kw")
        
        for sock in sockets:
            stats["connector_types"][sock["type"]] += sock.get("count", 1)
        
        if max_kw:
            if max_kw >= 50:
                stats["power_distribution"]["dc_fast_50kw_plus"] += 1
            elif max_kw >= 22:
                stats["power_distribution"]["fast_22_50kw"] += 1
            elif max_kw >= 7:
                stats["power_distribution"]["normal_7_22kw"] += 1
            else:
                stats["power_distribution"]["slow_under_7kw"] += 1
        else:
            stats["power_distribution"]["unknown"] += 1
        
        # Amenities
        if station.get("amenities"):
            stats["amenities_count"] += 1
    
    # Convert defaultdicts to regular dicts and sort
    stats["sources"] = dict(sorted(stats["sources"].items(), key=lambda x: -x[1]))
    stats["top_operators"] = dict(sorted(stats["operators"].items(), key=lambda x: -x[1])[:25])
    stats["countries"] = dict(sorted(stats["countries"].items(), key=lambda x: -x[1])[:30])
    stats["connector_types"] = dict(sorted(stats["connector_types"].items(), key=lambda x: -x[1]))
    
    return stats


# ============================================================
# Main Pipeline
# ============================================================

def main():
    print("=" * 60)
    print("RouteSync Charging Station Database Builder v2.0")
    print("=" * 60)
    
    all_stations = []
    
    # Step 1: Load and convert OSM Europe data
    print(f"\n[1/3] Loading OSM Europe tiles from {INPUT_EUROPE_TILES}...")
    osm_count = 0
    skipped = 0
    tile_files = [f for f in os.listdir(INPUT_EUROPE_TILES) if f.endswith(".json")]
    
    for tf in tile_files:
        filepath = os.path.join(INPUT_EUROPE_TILES, tf)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            elements = data.get("pois", data.get("elements", []))
            for elem in elements:
                tags = elem.get("tags", {})
                if tags.get("amenity") in ("charging", "charging_station"):
                    poi = convert_osm_to_routesync(elem)
                    if poi:
                        all_stations.append(poi)
                        osm_count += 1
                    else:
                        skipped += 1
        except Exception as e:
            print(f"  Error reading {tf}: {e}")
    
    print(f"  Processed {len(tile_files)} tiles")
    print(f"  Converted: {osm_count} OSM stations")
    print(f"  Skipped: {skipped} (no coordinates)")
    
    # Step 2: Load and convert NREL/AFDC data
    print(f"\n[2/3] Loading NREL/AFDC data from {INPUT_NREL}...")
    nrel_count = 0
    
    if os.path.exists(INPUT_NREL):
        with open(INPUT_NREL, "r", encoding="utf-8") as f:
            nrel_data = json.load(f)
        
        for station in nrel_data:
            poi = convert_nrel_to_routesync(station)
            if poi:
                all_stations.append(poi)
                nrel_count += 1
        
        print(f"  Converted: {nrel_count} NREL/AFDC stations")
    else:
        print(f"  NREL data file not found, skipping")
    
    print(f"\n  TOTAL raw stations: {len(all_stations)}")
    
    # Step 3: Deduplicate
    print(f"\n[3/3] Deduplicating...")
    all_stations = deduplicate_stations(all_stations)
    
    # Step 4: Build tiles
    print(f"\n[4/5] Building RouteSync tiles...")
    os.makedirs(TILES_DIR, exist_ok=True)
    manifest_tiles = build_tiles(all_stations, TILES_DIR)
    
    # Step 5: Build stats
    print(f"\n[5/5] Building statistics...")
    stats = build_stats(all_stations)
    stats["total_tiles"] = len(manifest_tiles)
    stats["database_size_bytes"] = sum(os.path.getsize(os.path.join(TILES_DIR, f)) 
                                       for f in os.listdir(TILES_DIR))
    stats["database_size_mb"] = round(stats["database_size_bytes"] / (1024*1024), 1)
    
    # Step 6: Write manifest
    manifest = {
        "format": "routesync-poi-v1.5.0",
        "version": "2.0.0",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tiles": manifest_tiles,
        "statistics": {
            "total_stations": len(all_stations),
            "total_tiles": len(manifest_tiles),
            "sources": stats["sources"],
            "top_operators": stats["top_operators"],
            "countries": stats["countries"],
            "connector_types": stats["connector_types"],
            "power_distribution": stats["power_distribution"],
            "with_address": stats["with_address"],
            "with_operator": stats["with_operator"],
            "with_amenities": stats["amenities_count"],
        }
    }
    
    with open(os.path.join(OUTPUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    # Step 7: Write stats
    with open(os.path.join(OUTPUT_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"DATABASE SUMMARY")
    print(f"{'='*60}")
    print(f"Total stations:  {len(all_stations)}")
    print(f"Total tiles:     {len(manifest_tiles)}")
    print(f"Database size:   {stats['database_size_mb']} MB")
    print(f"Sources:         {stats['sources']}")
    print(f"\nTop 10 operators:")
    for op, count in list(stats["top_operators"].items())[:10]:
        print(f"  {op}: {count}")
    print(f"\nTop 10 countries:")
    for cc, count in list(stats["countries"].items())[:10]:
        print(f"  {cc}: {count}")
    print(f"\nPower distribution:")
    for ptype, count in stats["power_distribution"].items():
        print(f"  {ptype}: {count}")
    print(f"\nConnector types:")
    for ctype, count in list(stats["connector_types"].items())[:10]:
        print(f"  {ctype}: {count}")
    
    print(f"\n{'='*60}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"{'='*60}")
    
    return len(all_stations)


if __name__ == "__main__":
    main()
