import requests
from .base_crawler import BaseProvider

TRAM_JSON_URL = "https://static.data.gov.hk/td/routes-fares-geojson/JSON_TRAM.json"

class TramDataProvider(BaseProvider):
    def fetch_network(self) -> dict:
        response = requests.get(TRAM_JSON_URL, timeout=20)
        response.encoding = 'utf-8-sig'
        response.raise_for_status()
        return self._parse_tram_network_json(response.json())

    @staticmethod
    def _stop_payload(stop_name: str, x: float, y: float) -> dict:
        return {
            "stopName": stop_name,
            "segmentTransportationType": {"x": x, "y": y},
        }

    def _parse_tram_network_json(self, data: dict) -> dict:
        features = data.get("features", [])
        if not features:
            raise ValueError("Tram JSON is empty or missing features")

        stops_by_name: dict[str, dict] = {}
        line_sequences: dict[tuple[int, int], list[tuple[int, str, float]]] = {}

        for feature in features:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})

            stop_name = (props.get("stopNameE") or "").strip()
            route_id = props.get("routeId")
            route_seq = props.get("routeSeq")
            stop_seq = props.get("stopSeq")
            fare = props.get("fullFare", 3.0)
            coords = geom.get("coordinates", [0.0, 0.0])

            if not stop_name or route_id is None or route_seq is None or stop_seq is None:
                continue

            x, y = 0.0, 0.0
            if len(coords) >= 2:
                x, y = coords[0], coords[1]

            stops_by_name.setdefault(stop_name, self._stop_payload(stop_name, float(x), float(y)))

            route_key = (route_id, route_seq)
            line_sequences.setdefault(route_key, []).append((stop_seq, stop_name, float(fare)))

        if not stops_by_name:
            raise ValueError("No station data parsed from Tram JSON")

        segments: list[dict] = []
        seen = set()

        for route_key, entries in line_sequences.items():
            ordered = sorted(entries, key=lambda item: item[0])
            route_name = f"{ordered[0][1]} - {ordered[-1][1]}"
            for current, nxt in zip(ordered, ordered[1:]):
                from_name = current[1]
                to_name = nxt[1]
                fare = current[2]

                if from_name == to_name:
                    continue

                undirected_edge_key = (route_name, min(from_name, to_name), max(from_name, to_name))

                if undirected_edge_key in seen:
                    continue

                seen.add(undirected_edge_key)

                base_segment = {
                    "type": "Tram",
                    "line": route_name,
                    "fare": fare,
                    "time": 2,
                    "scenic": 5,
                }

                segments.append({**base_segment, "from": stops_by_name[from_name], "to": stops_by_name[to_name]})
                segments.append({**base_segment, "from": stops_by_name[to_name], "to": stops_by_name[from_name]})

        if not segments:
            raise ValueError("No segment data parsed from Tram JSON")

        walking_links = {
            "Queensway (Admiralty MTR Station) (East bound)": "Admiralty",
            "Queensway (Admiralty MTR Station) (West bound)": "Admiralty",
            "Shau Kei Wan Terminus": "Shau Kei Wan",
            "Causeway Bay Terminus": "Causeway Bay",
            "North Point Terminus": "North Point",
            "Western Market Terminus": "Sheung Wan",
            "Kennnedy Town Terminus": "Kennedy Town",
            "Des Voeux Road Central (Pedder Street) (East bound)": "Central",
            "Des Voeux Road Central (Pedder Street) (West bound)": "Central",
            "Johnston Road (Wan Chai MTR Station) (East bound)": "Wan Chai",
            "Johnston Road (Wan Chai MTR Station) (West bound)": "Wan Chai",
        }
        walking_links.update({v: k for k, v in walking_links.items()})

        for tram_stop_name, mtr_stop_name in walking_links.items():
            if tram_stop_name in stops_by_name:
                tram_stop = stops_by_name[tram_stop_name]
                x = tram_stop["segmentTransportationType"]["x"]
                y = tram_stop["segmentTransportationType"]["y"]
                mtr_stop = self._stop_payload(mtr_stop_name, x, y)
                
                if mtr_stop_name not in stops_by_name:
                    stops_by_name[mtr_stop_name] = mtr_stop
                else:
                    mtr_stop = stops_by_name[mtr_stop_name]

                walk_segment = {
                    "type": "Walk",
                    "line": "Walking Transfer",
                    "fare": 0.0,
                    "time": 5,
                    "scenic": 20,
                }

                segments.append({**walk_segment, "from": tram_stop, "to": mtr_stop})
                segments.append({**walk_segment, "from": mtr_stop, "to": tram_stop})

        return {"stops": list(stops_by_name.values()), "segments": segments}
