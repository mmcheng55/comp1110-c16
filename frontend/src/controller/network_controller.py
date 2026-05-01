"""
network_controller.py
---------------------
Controller for fetching and managing the transport network graph.

Responsible for retrieving stops and segments from the backend API, and
providing them to the UI, optionally using a local fallback file on failure.
"""
import json
from pathlib import Path
import requests
from pydantic import ValidationError

from models import Stop
from config import BACKEND_URL
from utils import first_value, coerce_float


class NetworkController:
    """Provides methods for querying the transport network state.

    Parameters
    ----------
    navigator : Navigator
        The central view navigator instance.
    """
    def __init__(self, navigator):
        self.navigator = navigator
        self._fallback_data_path = Path(__file__).resolve().parents[2] / "transit_data.json"

    def get_network(self) -> dict:
        """Return the raw network dict with 'stops' and 'segments' keys."""
        try:
            request = requests.get(f"{BACKEND_URL}/network", timeout=10)
            request.raise_for_status()
            network_data = request.json()
            if isinstance(network_data, dict):
                return network_data
            return {}
        except (requests.RequestException, ValueError) as error:
            print(f"Failed to fetch network: {error}. Using fallback data.")
            return self._load_fallback_data()

    def get_stops_by_line(self) -> dict[str, list[Stop]]:
        """Return an ordered dict mapping line code -> list of unique stops on that line."""
        network = self.get_network()
        segments_raw = network.get("segments") or network.get("allSegments") or []

        # Track insertion order per line
        line_stop_names: dict[str, dict[str, None]] = {}
        stop_objects: dict[str, Stop] = {}

        for seg in segments_raw:
            if not isinstance(seg, dict):
                continue
            line = (
                seg.get("line") or seg.get("lineCode") or seg.get("routeName") or seg.get("route")
            )
            if not line:
                continue
            line = str(line)

            from_data = seg.get("from") or seg.get("fromStop") or {}
            to_data = seg.get("to") or seg.get("toStop") or {}

            for stop_data in (from_data, to_data):
                if not isinstance(stop_data, dict):
                    continue
                try:
                    stop = Stop(**stop_data)
                except Exception:
                    continue
                name = stop.stop_name
                stop_objects[name] = stop
                line_stop_names.setdefault(line, {})[name] = None

        return {
            line: [stop_objects[name] for name in names]
            for line, names in sorted(line_stop_names.items())
        }

    def get_stops(self) -> list[Stop]:
        """Retrieve a flat list of all Stop objects in the network."""
        try:
            request = requests.get(f"{BACKEND_URL}/network", timeout=10)
            request.raise_for_status()
            network_data = request.json()
            stops_data = []
            if isinstance(network_data, dict):
                stops_data = network_data.get("stops") or network_data.get("allStops") or []
            elif isinstance(network_data, list):
                stops_data = network_data
            return [Stop(**stop) for stop in stops_data if isinstance(stop, dict)]
        except (requests.RequestException, ValidationError, ValueError) as error:
            print(f"Failed to fetch stops: {error}")
            return self._load_fallback_stops()

    def _build_network_payload(self) -> dict:
        """Construct a full network payload dictionary from fallback data."""
        fallback_data = self._load_fallback_data()

        stops_raw = fallback_data.get("stops") or fallback_data.get("allStops") or []
        segments_raw = fallback_data.get("segments") or fallback_data.get("allSegments") or []

        stops_by_name: dict[str, dict] = {}
        for stop in stops_raw:
            if not isinstance(stop, dict):
                continue
            normalized_stop = self._normalize_stop_for_payload(stop)
            stop_name = normalized_stop.get("stopName")
            if isinstance(stop_name, str) and stop_name:
                stops_by_name[stop_name] = normalized_stop

        segments_payload: list[dict] = []
        for segment in segments_raw:
            if not isinstance(segment, dict):
                continue
            normalized_segment = self._normalize_segment_for_payload(segment)
            if normalized_segment is None:
                continue

            from_stop = normalized_segment["from"]
            to_stop = normalized_segment["to"]
            stops_by_name[from_stop["stopName"]] = from_stop
            stops_by_name[to_stop["stopName"]] = to_stop
            segments_payload.append(normalized_segment)

        return {
            "stops": list(stops_by_name.values()),
            "segments": segments_payload,
        }

    @staticmethod
    def _normalize_stop_for_payload(stop_data: dict) -> dict:
        """Normalize a raw stop dict into the required payload format."""
        stop_name = stop_data.get("stopName")
        if not isinstance(stop_name, str) or not stop_name:
            raise ValueError("Invalid stop payload")

        position = stop_data.get("normalizedPositionOnScreen") or stop_data.get("segmentTransportationType") or {}
        if isinstance(position, dict):
            x_value = position.get("x", 0.0)
            y_value = position.get("y", 0.0)
        elif isinstance(position, (list, tuple)) and len(position) >= 2:
            x_value, y_value = position[0], position[1]
        else:
            x_value, y_value = 0.0, 0.0

        return {
            "stopName": stop_name,
            "segmentTransportationType": {
                "x": float(x_value),
                "y": float(y_value),
            },
        }

    def _normalize_segment_for_payload(self, segment_data: dict) -> dict | None:
        """Normalize a raw segment dict into the required payload format."""
        from_source = segment_data.get("fromStop") or segment_data.get("fromStopClass") or segment_data.get("from")
        to_source = segment_data.get("toStop") or segment_data.get("toStopClass") or segment_data.get("to")
        if not isinstance(from_source, dict) or not isinstance(to_source, dict):
            return None

        from_stop = self._normalize_stop_for_payload(from_source)
        to_stop = self._normalize_stop_for_payload(to_source)
        properties = segment_data.get("segmentProperties") or segment_data.get("segmentPropertiesStruct") or {}
        if not isinstance(properties, dict):
            properties = {}

        mode = first_value(segment_data, ["type", "segmentTransportationType"]) or first_value(properties, ["segmentTransportationType", "type"]) or "Train"
        line = first_value(segment_data, ["line", "lineCode", "routeName", "route", "line_code"]) or first_value(properties, ["line", "lineCode", "routeName", "route", "line_code"])
        distance = coerce_float(first_value(segment_data, ["distance", "distanceKm", "distanceKM"])) or coerce_float(first_value(properties, ["distanceKm", "distanceKM", "distance"]))
        fare = coerce_float(first_value(segment_data, ["fare", "fareDollars", "cost"])) or coerce_float(first_value(properties, ["fareDollars", "fare", "cost"]))
        scenic = coerce_float(first_value(segment_data, ["scenic", "scenicIndex", "score"])) or coerce_float(first_value(properties, ["scenicIndex", "scenic", "score"]))
        time_value = coerce_float(first_value(segment_data, ["time", "timeMinutes", "travelTimeMinutes"])) or coerce_float(first_value(properties, ["time", "timeMinutes", "travelTimeMinutes"]))

        if time_value is None:
            time_value = self._estimate_time_minutes(distance, str(mode))

        payload = {
            "from": from_stop,
            "to": to_stop,
            "type": str(mode),
            "fare": float(fare) if fare is not None else 0.0,
            "time": int(round(time_value)) if time_value is not None else 0,
            "scenic": int(scenic) if scenic is not None else 0,
        }
        if line is not None:
            payload["line"] = str(line)
        return payload

    @staticmethod
    def _estimate_time_minutes(distance_km: float | None, mode: str) -> float:
        """Estimate travel time based on distance and transport mode."""
        if distance_km is None or distance_km <= 0:
            return 0.0

        mode_lower = mode.lower()
        if mode_lower == "train":
            speed_kmh = 60.0
        elif mode_lower == "bus":
            speed_kmh = 40.0
        elif mode_lower in {"walk", "walking"}:
            speed_kmh = 5.0
        else:
            speed_kmh = 40.0

        return (distance_km / speed_kmh) * 60.0

    def _load_fallback_stops(self) -> list[Stop]:
        """Load the list of Stop objects from the local fallback JSON file."""
        try:
            fallback_data = self._load_fallback_data()
            stops_data = fallback_data.get("stops") or fallback_data.get("allStops") or []
            return [Stop(**stop) for stop in stops_data]
        except (OSError, ValueError, ValidationError) as error:
            print(f"Failed to load fallback stops: {error}")
            return []

    def _load_fallback_data(self) -> dict:
        """Load raw network data from the local fallback JSON file."""
        try:
            with self._fallback_data_path.open("r", encoding="utf-8") as fallback_file:
                return json.load(fallback_file)
        except OSError as e:
            print(f"Fallback data not found or unreadable: {e}")
            return {}

