# RouteSync POI Data - Worldwide EV Charging Stations

[![Total Stations](https://img.shields.io/badge/Stations-112%2C104+-blue)](stats.json)
[![Version](https://img.shields.io/badge/Version-3.0.0-green)](manifest.json)
[![Source](https://img.shields.io/badge/Source-OpenStreetMap-orange)]()

The world's largest open EV charging station database for the **RouteSync** navigation app.

## Database v3.0.0

| Metric | Value |
|--------|-------|
| Total Stations | 112,104+ |
| Tiles | 2,908 |
| Coverage | 80+ countries |
| Sources | OpenStreetMap, NREL/AFDC |
| Last Updated | April 2026 |

## Data Sources

1. **OpenStreetMap** (via Overpass API) — Worldwide coverage
2. **NREL/AFDC** — US Alternative Fuel Data
3. **Geofabrik PBF** — Local OSM data extraction

## RouteSync POI Format v1.5.0+

### Tile Structure
```
tiles/poi-tile-{lat}-{lon}.json
```

Each tile covers a 1° x 1° geographic area and contains all charging stations within it.

### Station Object
```json
{
  "id": "osm-123456789",
  "name": "Tesla Supercharger München",
  "type": "charging_station",
  "lat": 48.135125,
  "lon": 11.581981,
  "operator": "Tesla",
  "address": {
    "street": "Leopoldstraße",
    "housenumber": "12",
    "postcode": "80802",
    "city": "München",
    "country": "DE"
  },
  "power": {
    "max_kw": 250.0,
    "sockets": [
      {"type": "CCS Combo 2", "kw": 250.0, "count": 8},
      {"type": "Type 2", "kw": 22.0, "count": 4}
    ],
    "capacity": 12
  },
  "source": "osm",
  "amenities": {"fee": true}
}
```

## API Integration

### Load Manifest
```javascript
const manifest = await fetch('manifest.json').then(r => r.json());
```

### Load Tile
```javascript
const tile = await fetch(`tiles/poi-tile-${lat}-${lon}.json`).then(r => r.json());
```

### Find Nearest Station
```javascript
function findNearest(lat, lon, stations) {
  return stations.reduce((nearest, s) => {
    const dist = Math.hypot(s.lat - lat, s.lon - lon);
    return dist < nearest.dist ? {station: s, dist} : nearest;
  }, {station: null, dist: Infinity});
}
```

## Top Operators

| Operator | Stations |
|----------|---------|
| Unknown | 30,000+ |
| Tesla | 4,000+ |
| Allego | 2,800+ |
| Province of South Holland | 2,800+ |
| ChargePoint | 2,000+ |
| TotalEnergies | 1,500+ |
| Vattenfall InCharge | 1,100+ |

## License

This data is derived from OpenStreetMap and is licensed under the [Open Database License (ODbL) v1.0](LICENSE).

## Contributing

Data is automatically updated from OpenStreetMap. For corrections, please edit the OSM data directly at [openstreetmap.org](https://www.openstreetmap.org).

---

**Built for RouteSync** — The Future of EV Navigation
