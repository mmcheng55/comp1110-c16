import requests
from config import BACKEND_URL
from .route_provider.mtr_crawler import MtrDataProvider
from .route_provider.bus_crawler import BusDataProvider
from .route_provider.tram_crawler import TramDataProvider

class NetworkCrawlController:
    def __init__(self, navigator):
        self.navigator = navigator
        self.mtr_provider = MtrDataProvider()
        self.bus_provider = BusDataProvider()
        self.tram_provider = TramDataProvider()

    def import_network_from_all_crawlers(self) -> tuple[bool, str]:
        try:
            mtr_payload = self.mtr_provider.fetch_network()
            bus_payload = self.bus_provider.fetch_network()
            tram_payload = self.tram_provider.fetch_network()
            
            # Merge stops based on unique stopName
            seen_stops = set()
            merged_stops = []
            for stop in mtr_payload.get("stops", []) + bus_payload.get("stops", []) + tram_payload.get("stops", []):
                if stop["stopName"] not in seen_stops:
                    seen_stops.add(stop["stopName"])
                    merged_stops.append(stop)

            # Merge segments (could have duplicates, but assuming distinct lists or handled by backend)
            merged_segments = mtr_payload.get("segments", []) + bus_payload.get("segments", []) + tram_payload.get("segments", [])

            network_payload = {
                "stops": merged_stops,
                "segments": merged_segments
            }

            post_response = requests.post(
                f"{BACKEND_URL}/network/set",
                json=network_payload,
                timeout=20,
            )
            post_response.raise_for_status()

            return (
                True,
                f"Network updated successfully ({len(network_payload['stops'])} stops, {len(network_payload['segments'])} segments).",
            )
        except Exception as error:
            return (False, f"Failed to update network: {error}")
