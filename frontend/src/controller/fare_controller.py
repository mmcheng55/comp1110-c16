from .fare_provider import MtrFareProvider, BusFareProvider, TramFareProvider
from utils import normalize_stop_name

class FareController:
    def __init__(self, navigator=None):
        self.navigator = navigator
        self.fares = {}
        self.providers = {
            "mtr": MtrFareProvider(),
            "bus": BusFareProvider(),
            "tram": TramFareProvider(),
        }
        
        # Load fares in the background right away
        import threading
        threading.Thread(target=self.update_fares_from_all, daemon=True).start()

    def update_fares_from_all(self):
        new_fares = {}
        for provider_key, provider in self.providers.items():
            new_fares[provider_key] = provider.fetch_fares()
        self.fares = new_fares
        return self.fares

    def _infer_provider_key(self, path: list[dict] | None = None) -> str | None:
        if not path:
            return None

        for segment in path:
            if not isinstance(segment, dict):
                continue
            mode = segment.get("type")
            if not mode and isinstance(segment.get("segmentProperties"), dict):
                mode = segment["segmentProperties"].get("type")
            if not mode:
                continue

            mode_lower = str(mode).strip().lower()
            if mode_lower in ("train", "mtr"):
                return "mtr"
            if mode_lower == "bus":
                return "bus"
            if mode_lower == "tram":
                return "tram"

        return None

    def get_fare(self, src: str, dest: str, path: list[dict] | None = None) -> float | None:
        src_norm = normalize_stop_name(src)
        dest_norm = normalize_stop_name(dest)
        provider_key = self._infer_provider_key(path)

        if provider_key:
            provider_fares = self.fares.get(provider_key, {})
            return provider_fares.get((src_norm, dest_norm))

        for provider_fares in self.fares.values():
            fare = provider_fares.get((src_norm, dest_norm))
            if fare is not None:
                return fare
        return None
