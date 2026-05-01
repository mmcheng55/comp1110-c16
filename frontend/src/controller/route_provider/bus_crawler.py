from .base_crawler import BaseProvider


class BusDataProvider(BaseProvider):
    def __init__(self):
        self.custom_network = self._build_custom_network()

    @staticmethod
    def _stop_payload(stop_name: str) -> dict:
        return {
            "stopName": stop_name,
            "segmentTransportationType": {"x": 0.0, "y": 0.0},
        }

    @classmethod
    def _build_custom_network(cls) -> dict:
        route_specs = [
            {"line": "A10", "from": "Airport", "to": "HKU", "fare": 60.0, "time": 10, "scenic": 0},
            {"line": "A22", "from": "Airport", "to": "To Kwa Wan", "fare": 60.0, "time": 10, "scenic": 0},
            {"line": "A29", "from": "Airport", "to": "Kowloon Bay", "fare": 60.0, "time": 10, "scenic": 0},
            {"line": "HK1", "from": "Tsim Sha Tsui", "to": "Wong Tai Sin", "fare": 60.0, "time": 10, "scenic": 100},
            {"line": "H1", "from": "Tsim Sha Tsui", "to": "Sheung Wan", "fare": 60.0, "time": 10, "scenic": 100},
        ]

        stops_by_name: dict[str, dict] = {}
        segments: list[dict] = []

        for route in route_specs:
            from_stop = stops_by_name.setdefault(route["from"], cls._stop_payload(route["from"]))
            to_stop = stops_by_name.setdefault(route["to"], cls._stop_payload(route["to"]))
            segment_base = {
                "type": "Bus",
                "line": route["line"],
                "fare": route["fare"],
                "time": route["time"],
                "scenic": route["scenic"],
            }
            segments.append({**segment_base, "from": from_stop, "to": to_stop})
            segments.append({**segment_base, "from": to_stop, "to": from_stop})

        return {"stops": list(stops_by_name.values()), "segments": segments}

    def fetch_network(self) -> dict:
        return self.custom_network
