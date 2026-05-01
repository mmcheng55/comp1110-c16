import pytest
from pydantic import ValidationError
from models import Stop, Segment

def test_stop_validation():
    stop = Stop(stopName="Central", segmentTransportationType={"x": 0.5, "y": 0.3})
    assert stop.stop_name == "Central"
    assert stop.normalized_position_on_screen == (0.5, 0.3)

    # Test coordinate boundaries out of range [0, 1]
    with pytest.raises(ValidationError):
        Stop(stopName="Invalid", segmentTransportationType={"x": 1.5, "y": 0.0})

def test_segment_equality():
    s1 = Stop(stopName="A", segmentTransportationType=[0, 0])
    s2 = Stop(stopName="B", segmentTransportationType=[1, 1])
    
    seg1 = Segment(
        fromStop=s1, toStop=s2, type="Train", line="TWL",
        fareDollars=5.0, timeMinutes=10, scenicIndex=3
    )
    seg2 = Segment(
        fromStop=s1, toStop=s2, type="Train", line="TWL",
        fareDollars=5.0, timeMinutes=10, scenicIndex=3
    )
    seg3 = Segment(
        fromStop=s1, toStop=s2, type="Bus", line="101",
        fareDollars=5.0, timeMinutes=10, scenicIndex=3
    )
    
    assert seg1 == seg2
    assert seg1 != seg3
