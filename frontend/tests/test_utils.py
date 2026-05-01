import pytest
from utils import first_value, coerce_float, format_stop_name, normalize_stop_name

def test_first_value():
    assert first_value({"a": 1, "b": 2}, ["c", "b", "a"]) == 2
    assert first_value({"a": 1, "b": ""}, ["b", "a"]) == 1
    assert first_value({"a": None}, ["a", "b"]) is None

def test_coerce_float():
    assert coerce_float("3.14") == 3.14
    assert coerce_float(42) == 42.0
    assert coerce_float("not a float") is None
    assert coerce_float(None) is None

def test_format_stop_name():
    assert format_stop_name("CentralStation") == "Central Station"
    assert format_stop_name("TsimShaTsui") == "Tsim Sha Tsui"
    assert format_stop_name("already spaced") == "already spaced"

def test_normalize_stop_name():
    assert normalize_stop_name("Central Station") == "centralstation"
    assert normalize_stop_name("Tsim Sha Tsui") == "tsimshatsui"
    assert normalize_stop_name("  KennedyTown  ") == "kennedytown"
