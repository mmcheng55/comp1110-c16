import json
import os
from .base_fare import BaseFareProvider
from utils import normalize_stop_name

class BusFareProvider(BaseFareProvider):
    def fetch_fares(self) -> dict:
        fares = {}
        json_path = os.path.join(os.path.dirname(__file__), "bus_fares.json")
        if not os.path.exists(json_path):
            return fares
            
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for entry in data:
                    src = normalize_stop_name(entry.get("from", ""))
                    dest = normalize_stop_name(entry.get("to", ""))
                    fare = float(entry.get("fare", 0))
                    if src and dest:
                        fares[(src, dest)] = fare
                        fares[(dest, src)] = fare
        except Exception as e:
            print(f"Failed to load bus fares: {e}")
            
        return fares

