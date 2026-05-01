"""
route_controller.py
-------------------
Controller for querying route calculations from the backend.

Provides the :class:`RouteController` which contacts the backend's routing
endpoint, parses the resulting routes, and ranks them based on user preferences.
"""
import requests
from pydantic import ValidationError

from models import Stop, Route
from config import BACKEND_URL
from utils import first_value, coerce_float, format_stop_name, normalize_stop_name

WEIGHT_PRESETS = {
    "1": {"label": "Cheapest", "fare": 0.70, "time": 0.20, "scenic": 0.10},
    "2": {"label": "Fastest", "fare": 0.20, "time": 0.70, "scenic": 0.10},
    "3": {"label": "Most Scenic", "fare": 0.15, "time": 0.15, "scenic": 0.70},
    "4": {"label": "Balanced", "fare": 0.33, "time": 0.34, "scenic": 0.33},
}


class RouteController:
    """Manages the retrieval, formatting, and scoring of transport routes.

    Parameters
    ----------
    navigator : Navigator
        The central view navigator instance.
    """

    def __init__(self, navigator):
        self.navigator = navigator

    def get_route(self, start_stop: Stop, end_stop: Stop, sort_choice: str = "4", fare_controller=None) -> list[Route]:
        """Fetch routes between two stops from the backend and score them.

        Parameters
        ----------
        start_stop : Stop
            The starting stop object.
        end_stop : Stop
            The destination stop object.
        sort_choice : str
            A numeric string ("1", "2", "3", "4") matching `WEIGHT_PRESETS`.

        Returns
        -------
        list[Route]
            A list of the top ranked :class:`~models.Route` objects.
        """
        try:
            request = requests.get(
                f"{BACKEND_URL}/route",
                params={"start": start_stop.stop_name, "end": end_stop.stop_name},
                timeout=100,
            )
            request.raise_for_status()
            routes_data = request.json()

            if isinstance(routes_data, dict):
                routes_data = routes_data.get("routes") or routes_data.get("allRoutes") or []
            elif not isinstance(routes_data, list):
                routes_data = []

            parsed_routes = [
                self._to_route(route, index, fare_controller)
                for index, route in enumerate(routes_data) if isinstance(route, dict)
            ]

            if parsed_routes:
                parsed_routes = self._apply_weighted_scores(parsed_routes, sort_choice)
                return self._sort_routes(parsed_routes, sort_choice)
        except (requests.RequestException, ValidationError, ValueError) as error:
            print(f"Failed to fetch routes: {error}")

        return []

    def _to_route(self, route_data: dict, index: int, fare_controller=None) -> Route:
        """Parse a raw route dictionary into a Route object, deriving missing values."""
        segments = route_data.get("segments") if isinstance(route_data.get("segments"), list) else []
        derived_values = self._derive_route_values_from_segments(segments, fare_controller)

        rank = first_value(route_data, ["rank", "routeRank", "ranking"])
        description = first_value(route_data, ["description", "routeDescription", "summary", "pathDescription"]) or \
                      derived_values["description"] or f"Route {index + 1}"
        total_cost = first_value(route_data, ["totalCost", "totalFare", "fareDollars", "cost"]) or derived_values[
            "total_cost"]
        total_distance = first_value(route_data, ["totalDistanceKm", "distanceKm", "distanceKM"]) or derived_values[
            "total_distance_km"]
        travel_time = first_value(route_data,
                                  ["travelTimeMinutes", "durationMinutes", "timeMinutes", "totalTimeMinutes"]) or \
                      derived_values["travel_time_minutes"]

        # Uses derived exact logic tracking actual line/mode changes, fallbacks to raw route transfers
        transfer_count = derived_values["transfer_count"]
        if transfer_count is None:
            transfer_count = first_value(route_data, ["transferCount", "transfers", "numberOfTransfers"])

        score = first_value(route_data,
                            ["score", "routeScore", "totalScore", "rankingScore", "finalScore", "weightedScore"]) or \
                derived_values["score"]
        transport_modes = first_value(route_data, ["transportModes", "modes", "segmentTransportationTypes"]) or \
                          derived_values["transport_modes"]

        parsed_rank = int(rank) if rank is not None else index + 1
        parsed_cost = float(total_cost) if total_cost is not None else None
        parsed_distance = float(total_distance) if total_distance is not None else None
        parsed_travel_time = float(travel_time) if travel_time is not None and float(travel_time) > 0 else None
        parsed_transfers = int(transfer_count) if transfer_count is not None else None
        parsed_score = float(score) if score is not None else None
        parsed_modes = transport_modes if isinstance(transport_modes, list) else None

        canonical_payload = dict(route_data)
        canonical_payload.update({
            "rank": parsed_rank,
            "description": str(description),
            "totalCost": parsed_cost,
            "totalDistanceKm": parsed_distance,
            "travelTimeMinutes": parsed_travel_time,
            "transferCount": parsed_transfers,
            "score": parsed_score,
            "transportModes": parsed_modes,
        })

        return Route(
            rank=parsed_rank,
            description=str(description),
            total_cost=parsed_cost,
            total_distance_km=parsed_distance,
            travel_time_minutes=parsed_travel_time,
            transfer_count=parsed_transfers,
            score=parsed_score,
            transport_modes=parsed_modes,
            raw_payload=canonical_payload,
        )

    def _derive_route_values_from_segments(self, segments: list[dict], fare_controller=None) -> dict:
        """Calculate aggregate route statistics from an array of segment dictionaries."""
        if not segments:
            return {"description": None, "total_cost": None, "total_distance_km": None, "travel_time_minutes": None,
                    "transfer_count": None, "score": None, "transport_modes": None}

        stop_path, transport_modes = [], []
        total_time, total_distance, total_score = 0.0, 0.0, 0.0
        has_time, has_distance, has_score = False, False, False
        total_cost = 0.0
        has_cost = False

        transfer_count = 0
        prev_mode_line = None
        has_valid_segments = False

        leg_start_stop = None
        current_leg_last_stop = None
        current_leg_key = None
        current_leg_segments = []
        leg_fallback_fare = 0.0

        def close_leg():
            nonlocal total_cost, has_cost
            if not leg_start_stop or not current_leg_last_stop:
                return
            if fare_controller:
                custom_fare = fare_controller.get_fare(
                    str(leg_start_stop),
                    str(current_leg_last_stop),
                    current_leg_segments,
                )
                if custom_fare is not None:
                    total_cost += custom_fare
                    has_cost = True
                    return
            total_cost += leg_fallback_fare
            if leg_fallback_fare > 0:
                has_cost = True

        for segment in segments:
            if not isinstance(segment, dict):
                continue
            has_valid_segments = True

            properties = segment.get("segmentProperties") or segment.get("segmentPropertiesStruct") or {}
            from_stop = segment.get("from") or segment.get("fromStop") or segment.get("fromStopClass") or {}
            to_stop = segment.get("to") or segment.get("toStop") or segment.get("toStopClass") or {}

            from_name = from_stop.get("stopName") if isinstance(from_stop, dict) else None
            to_name = to_stop.get("stopName") if isinstance(to_stop, dict) else None

            mode = first_value(segment, ["type", "segmentTransportationType"]) or first_value(properties, ["type",
                                                                                                           "segmentTransportationType"])
            line = first_value(segment, ["line", "lineCode", "routeName", "route"]) or first_value(properties,
                                                                                                   ["line", "lineCode",
                                                                                                    "routeName",
                                                                                                    "route"])

            current_mode_line = (str(mode).lower() if mode else None, str(line).lower() if line else None)

            if prev_mode_line is not None and current_mode_line != prev_mode_line:
                transfer_count += 1
            prev_mode_line = current_mode_line

            if from_name and not stop_path:
                stop_path.append(format_stop_name(str(from_name)))
            if to_name:
                stop_path.append(format_stop_name(str(to_name)))
            if mode:
                transport_modes.append(str(mode))

            mode_lower = str(mode).lower() if mode else ""
            if mode_lower in ("train", "mtr"):
                leg_key = mode_lower
            else:
                leg_key = (mode_lower, str(line).lower() if line else "")

            if leg_key != current_leg_key:
                if current_leg_key is not None:
                    close_leg()
                current_leg_key = leg_key
                leg_start_stop = from_name
                current_leg_segments = []
                leg_fallback_fare = 0.0

            current_leg_last_stop = to_name
            current_leg_segments.append(segment)

            fare = coerce_float(first_value(segment, ["fare", "fareDollars"])) or coerce_float(
                first_value(properties, ["fare", "fareDollars"]))
            if fare is not None:
                leg_fallback_fare += fare

            distance = coerce_float(first_value(segment, ["distance", "distanceKm", "distanceKM"])) or coerce_float(
                first_value(properties, ["distance", "distanceKm", "distanceKM"]))
            if distance is not None:
                total_distance += distance
                has_distance = True

            time = coerce_float(first_value(segment, ["time", "timeMinutes", "travelTimeMinutes"])) or coerce_float(
                first_value(properties, ["time", "timeMinutes", "travelTimeMinutes"]))
            if time is None and distance is not None:
                speed_kmh = 40.0
                if mode:
                    mode_lower = str(mode).lower()
                    if mode_lower == "train":
                        speed_kmh = 60.0
                    elif mode_lower == "bus":
                        speed_kmh = 40.0
                    elif mode_lower in ["walk", "walking"]:
                        speed_kmh = 5.0
                time = (distance / speed_kmh) * 60.0

            if time is not None and time > 0:
                total_time += time
                has_time = True

            scenic = coerce_float(first_value(segment, ["scenic", "scenicIndex", "score"])) or coerce_float(
                first_value(properties, ["scenic", "scenicIndex", "score"]))
            if scenic is not None:
                total_score += scenic
                has_score = True

        if current_leg_key is not None:
            close_leg()

        return {
            "description": " -> ".join(stop_path) if stop_path else None,
            "total_cost": total_cost if has_cost else None,
            "total_distance_km": total_distance if has_distance else None,
            "travel_time_minutes": total_time if has_time else None,
            "transfer_count": transfer_count if has_valid_segments else None,
            "score": total_score if has_score else None,
            "transport_modes": transport_modes or None,
        }

    def _sort_routes(self, routes: list[Route], sort_choice: str) -> list[Route]:
        """Sort the given routes based on the selected weighting profile."""
        if sort_choice == "2":
            routes.sort(key=lambda route: (-(route.score if route.score is not None else -1.0),
                                           route.travel_time_minutes is None, route.travel_time_minutes or float("inf"),
                                           route.total_cost or float("inf")))
        elif sort_choice == "3":
            routes.sort(
                key=lambda route: (-(route.score if route.score is not None else -1.0), route.transfer_count or 0,
                                   route.travel_time_minutes is None, route.travel_time_minutes or float("inf")))
        elif sort_choice == "4":
            routes.sort(key=lambda route: (-(route.score if route.score is not None else -1.0),
                                           route.travel_time_minutes is None, route.travel_time_minutes or float("inf"),
                                           route.total_cost or float("inf"), route.total_distance_km or float("inf")))
        else:
            routes.sort(key=lambda route: (-(route.score if route.score is not None else -1.0),
                                           route.total_cost or float("inf"), route.total_distance_km or float("inf"),
                                           route.travel_time_minutes is None,
                                           route.travel_time_minutes or float("inf")))

        for index, route in enumerate(routes[:3]):
            route.rank = index + 1
        return routes[:3]

    def _apply_weighted_scores(self, routes: list[Route], sort_choice: str) -> list[Route]:
        """Calculate and attach a normalized score to each route based on user preferences."""
        if not routes:
            return routes

        weights = WEIGHT_PRESETS.get(sort_choice, WEIGHT_PRESETS["4"])
        fares = [route.total_cost or float("inf") for route in routes]
        times = [route.travel_time_minutes or float("inf") for route in routes]
        scenics = [route.score if route.score is not None else 0.0 for route in routes]

        fare_min, fare_max = min(fares), max(fares)
        time_min, time_max = min(times), max(times)
        scenic_min, scenic_max = min(scenics), max(scenics)

        scored_routes: list[Route] = []
        for route in routes:
            fare_score = 1.0 if fare_max == fare_min else (fare_max - (route.total_cost or float("inf"))) / (
                    fare_max - fare_min)
            time_score = 1.0 if time_max == time_min else (time_max - (route.travel_time_minutes or float("inf"))) / (
                    time_max - time_min)
            scenic_score = 1.0 if scenic_max == scenic_min else ((
                                                                     route.score if route.score is not None else 0.0) - scenic_min) / (
                                                                        scenic_max - scenic_min)

            overall_score = (
                    fare_score * weights["fare"] + time_score * weights["time"] + scenic_score * weights["scenic"])
            route.score = round(overall_score, 3)
            if route.raw_payload is not None:
                route.raw_payload["score"] = route.score
            scored_routes.append(route)

        return scored_routes
