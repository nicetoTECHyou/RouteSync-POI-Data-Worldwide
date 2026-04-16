# RouteSync Charging Station Database

<div align="center">

**Die größte Open-Source Ladesäulen-Datenbank für RouteSync**
**The largest open-source EV charging station database for RouteSync**

[![Format](https://img.shields.io/badge/Format-RouteSync%20POI%20v1.5.0-blue)](#)
[![Stations](https://img.shields.io/badge/Stations-87%2C272+-green)](#)
[![Tiles](https://img.shields.io/badge/Tiles-597-orange)](#)
[![License](https://img.shields.io/badge/License-ODbL%20v1.0-yellow)](#)
[![Data Sources](https://img.shields.io/badge/Sources-OSM%20%2B%20NREL%2FAFDC-informational)](#)

</div>

---

## Übersicht / Overview

Diese Datenbank enthält **87.272+ eindeutige EV-Ladestationen** in einem optimierten Format für die [RouteSync](https://github.com/nicetoTECHyou/RouteSync-POI-Data) App. Die Daten wurden aus mehreren Quellen aggregiert, bereinigt, dedupliziert und mit vollständigen Details angereichert.

This database contains **87,272+ unique EV charging stations** in an optimized format for the [RouteSync](https://github.com/nicetoTECHyou/RouteSync-POI-Data) app. Data has been aggregated from multiple sources, cleaned, deduplicated, and enriched with full details.

### Abdeckung / Coverage

| Region | Stationen | Länder |
|--------|-----------|--------|
| Europa | ~87.000 | 22+ Länder |
| Nordamerika | ~200 | USA |
| **Gesamt / Total** | **87.272** | **23+** |

### Top 10 Länder / Top 10 Countries

| Land / Country | Stationen |
|---------------|-----------|
| Deutschland (DE) | 34.778 |
| Frankreich (FR) | 17.765 |
| Niederlande (NL) | 10.131 |
| Großbritannien (GB) | 4.980 |
| Italien (IT) | 4.006 |
| Spanien (ES) | 3.132 |
| Norwegen (NO) | 1.894 |
| Schweiz (CH) | 1.722 |
| Dänemark (DK) | 1.714 |
| Schweden (SE) | 429 |

---

## Datenquellen / Data Sources

| Quelle | Beschreibung | Stationen |
|--------|-------------|-----------|
| **OpenStreetMap** | Globale crowd-sourced Kartendaten via Overpass API | ~105.600 |
| **NREL/AFDC** | US Dept. of Energy Alternative Fuel Data Center | ~6.600 |
| **(Deduplizierung)** | Entfernung von Duplikaten (50m Radius) | -25.000 |

---

## Datenformat / Data Format

### Dateistruktur / File Structure

```
RouteSync-Charging-Stations/
├── README.md                    # Diese Datei / This file
├── LICENSE                      # ODbL v1.0 Lizenz
├── manifest.json                # Tile-Index mit Metadaten
├── stats.json                   # Detaillierte Statistiken
├── .gitignore                   # Git Ignore Regeln
├── .github/
│   └── workflows/
│       └── regenerate.yml       # Wöchentliche Auto-Aktualisierung
├── scripts/
│   ├── generate.py              # Vollständiger Generierungsskript
│   └── convert_to_routesync.py  # Konvertierungspipeline
└── tiles/
    ├── poi-tile-34-44.json      # Tile-Dateien (Lat-Lon Grid)
    ├── poi-tile-36--2.json
    ├── poi-tile-48-11.json
    └── ... (597 Dateien)
```

### Tile-Format / Tile Format

Jede Tile-Datei folgt dem **RouteSync POI v1.5.0+** Standard:

```json
{
  "format": "routesync-poi-v1.5.0",
  "tile": {
    "lat": 52,
    "lon": 13,
    "bounds": {
      "south": 52,
      "north": 53,
      "west": 13,
      "east": 14
    }
  },
  "generated": "2026-04-16T14:52:46Z",
  "count": 234,
  "pois": [
    {
      "id": "osm-12345678",
      "name": "EnBW Ladestation Berlin Mitte",
      "type": "charging_station",
      "lat": 52.520006,
      "lon": 13.404954,
      "operator": "EnBW",
      "address": {
        "street": "Friedrichstraße 123",
        "postcode": "10117",
        "city": "Berlin",
        "country": "DE"
      },
      "power": {
        "max_kw": 150,
        "capacity": 4,
        "sockets": [
          {
            "type": "CCS (Type 2)",
            "kw": 150,
            "count": 2
          },
          {
            "type": "Type 2",
            "kw": 22,
            "count": 2
          }
        ]
      },
      "amenities": {
        "opening_hours": "Mo-Fr 06:00-22:00",
        "fee": true,
        "payment_methods": ["Credit Card", "RFID"],
        "wheelchair": true,
        "nearby_services": ["restaurant", "wifi"]
      },
      "source": "osm",
      "tags": {
        "access": "yes",
        "brand": "EnBW",
        "network": "EnBW HyperNetz"
      }
    }
  ]
}
```

### POI-Felder / POI Fields

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `id` | String | Eindeutige ID (`osm-12345` oder `nrel-67890`) |
| `name` | String | Anzeigename der Ladestation |
| `type` | String | Immer `charging_station` |
| `lat` | Float | Breitengrad (6 Dezimalstellen) |
| `lon` | Float | Längengrad (6 Dezimalstellen) |
| `operator` | String | Bereinigter Operator-Name |
| `address` | Object | Adresse (street, city, postcode, country) |
| `power` | Object | Leistung (max_kw, capacity, sockets[]) |
| `power.sockets[].type` | String | Steckertyp (CCS, CHAdeMO, Type 2, etc.) |
| `power.sockets[].kw` | Float | Leistung pro Stecker in kW |
| `power.sockets[].count` | Integer | Anzahl der Stecker |
| `amenities` | Object | Zusätzliche Infos (Öffnungszeiten, Bezahlung, etc.) |
| `source` | String | Datenquelle (`osm` oder `nrel`) |

### Unterstützte Steckertypen / Supported Connector Types

| Steckertyp | Typisch kW | Häufigkeit |
|-----------|-----------|-----------|
| Type 2 | 22 | 84.886 |
| CCS (Type 2) | 50-300 | 46.706 |
| CHAdeMO | 50 | 9.392 |
| Schuko | 2.3 | 9.131 |
| Tesla Supercharger | 150-250 | 3.329 |
| Type 1 (J1772) | 7.2 | 514 |
| CEE Blau (16A) | 3.7 | 308 |
| CCS (Type 1) | 50 | 109 |

### Top Betreiber / Top Operators

| Betreiber | Stationen |
|-----------|-----------|
| SG Zuid-Holland | 2.864 |
| Allego | 2.830 |
| Gemeente Den Haag | 2.102 |
| TotalEnergies | 1.546 |
| Vattenfall InCharge | 1.198 |
| EnBW | 1.172 |
| Tesla | 1.125 |
| Izivia | 1.012 |
| Enel X | 935 |
| Bouygues E&S | 668 |

---

## Leistungsklassen / Power Distribution

| Klasse | Leistung | Stationen |
|--------|---------|-----------|
| DC Schnellladung | 50+ kW | 11.894 |
| Schnellladung | 22-50 kW | 25.194 |
| Normalladung | 7-22 kW | 6.449 |
| Langsamladung | < 7 kW | 2.212 |
| Unbekannt | - | 41.523 |

---

## Nutzung in RouteSync / Usage in RouteSync

1. Lade das Repository herunter / Download this repository
2. Kopiere den `tiles/` Ordner in dein RouteSync-Projekt / Copy the `tiles/` folder to your RouteSync project
3. RouteSync lädt automatisch die benötigten Tiles basierend auf der GPS-Position / RouteSync automatically loads needed tiles based on GPS position

---

## Automatische Aktualisierung / Auto-Update

Die Datenbank wird wöchentlich über GitHub Actions automatisch aktualisiert:

- **Montag 03:00 UTC**: Neue Daten von Overpass API & NREL
- **Konvertierung**: Rohdaten → RouteSync POI Format
- **Deduplizierung**: Doppelte Stationen entfernen
- **Commit & Push**: Automatisches Update des Repos

---

## Datenverbesserung / Data Enhancement

Jede Station wird automatisch angereichert mit:

- **Bereinigte Operator-Namen** (z.B. "EnBW Energie Baden-Württemberg AG" → "EnBW")
- **Intelligente Namensgebung** (Operator + Marke + Standort)
- **Leistungsdaten** (max kW, Steckertypen, Anzahl)
- **Adressen** (Straße, PLZ, Stadt, Land)
- **Amenities** (Öffnungszeiten, Bezahlung, Barrierefreiheit, Services)
- **Stecker-Typ-Normalisierung** (einheitliche Benennung)

---

## Mitmachen / Contributing

Beiträge sind willkommen! Insbesondere:

- Korrektur von Stationen (falsche Daten, geschlossene Stationen)
- Neue Datenquellen hinzufügen
- Verbesserung der Konvertierungspipeline
- Übersetzungen und Dokumentation

---

## Lizenz / License

Dieses Projekt ist unter der **Open Database License (ODbL) v1.0** lizenziert.

Die OpenStreetMap-Daten stehen unter der [Open Database License](https://opendatacommons.org/licenses/odbl/).
Die NREL/AFDC-Daten sind Public Domain (US Government).

© 2026 RouteSync Charging Station Database Contributors
