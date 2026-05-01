import pytest
from controller.fare_controller import FareController
from controller.route_controller import RouteController
from models import Route

def test_derive_route_values_from_segments():
    controller = RouteController(navigator=None)
    segments = [
        {"from": {"stopName": "A"}, "to": {"stopName": "B"}, "type": "Train", "line": "Line1", "fare": 2.0, "time": 5, "scenic": 1},
        {"from": {"stopName": "B"}, "to": {"stopName": "C"}, "type": "Train", "line": "Line2", "fare": 3.0, "time": 10, "scenic": 2}
    ]
    derived = controller._derive_route_values_from_segments(segments)
    
    assert derived["total_cost"] == 5.0
    assert derived["travel_time_minutes"] == 15.0
    assert derived["score"] == 3.0
    assert derived["transfer_count"] == 1  # 1 transfer from Line1 to Line2
    assert derived["description"] == "A -> B -> C"
    assert derived["transport_modes"] == ["Train", "Train"]

def test_apply_weighted_scores():
    controller = RouteController(navigator=None)
    # Route 1: Expensive, fast
    r1 = Route(totalCost=10.0, travelTimeMinutes=20.0, score=5.0, raw_payload={})
    # Route 2: Cheap, slow
    r2 = Route(totalCost=5.0, travelTimeMinutes=30.0, score=2.0, raw_payload={})
    
    # Using sort_choice="1" (Cheapest: high fare weight)
    routes = controller._apply_weighted_scores([r1, r2], sort_choice="1")
    
    # Fare diff: max=10, min=5. 
    # r1 fare_score = 0
    # r2 fare_score = 1
    # Check that r2 gets a higher score for "Cheapest"
    assert r2.score > r1.score

    # Using sort_choice="2" (Fastest: high time weight)
    routes2 = controller._apply_weighted_scores([r1, r2], sort_choice="2")
    
    # Check that r1 gets a higher score for "Fastest"
    assert r1.score > r2.score


def test_derive_route_values_uses_path_specific_fare_provider():
    controller = RouteController(navigator=None)
    fare_controller = FareController(navigator=None)
    fare_controller.fares = {
        "mtr": {
            ("a", "c"): 7.5,
            ("c", "a"): 7.5,
        },
        "bus": {
            ("a", "c"): 11.0,
            ("c", "a"): 11.0,
        },
        "tram": {},
    }

    segments = [
        {"from": {"stopName": "A"}, "to": {"stopName": "B"}, "type": "Train", "line": "TWL", "fare": 2.0, "time": 5, "scenic": 1},
        {"from": {"stopName": "B"}, "to": {"stopName": "C"}, "type": "Train", "line": "TWL", "fare": 3.0, "time": 5, "scenic": 1},
    ]

    derived = controller._derive_route_values_from_segments(segments, fare_controller)

    assert derived["total_cost"] == 7.5
