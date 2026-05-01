from .base_fare import BaseFareProvider
from controller.route_provider.tram_crawler import TramDataProvider
from utils import normalize_stop_name

class TramFareProvider(BaseFareProvider):
    """Provides flat fare structure for Tram."""
    def fetch_fares(self) -> dict[tuple[str, str], float]:
        provider = TramDataProvider()
        try:
            network = provider.fetch_network()
        except Exception:
            return {}

        stops = [s["stopName"] for s in network.get("stops", [])]
        fares = {}
        for s1 in stops:
            s1_norm = normalize_stop_name(s1)
            for s2 in stops:
                s2_norm = normalize_stop_name(s2)
                if s1_norm != s2_norm:
                    fares[(s1_norm, s2_norm)] = 3.3
        return fares
