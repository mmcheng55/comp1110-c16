"""
utils.py
--------
Shared utility functions used across controllers and views.

Functions
---------
first_value
    Retrieve the first non-empty value from a dict by trying multiple keys.
coerce_float
    Safely convert an arbitrary value to ``float``.
format_stop_name
    Convert a CamelCase stop name into a human-readable spaced string.
normalize_stop_name
    Produce a lowercase, whitespace-free version of a stop name for
    stable equality comparisons.
"""

import re


def first_value(source: dict, keys: list[str]):
    """Return the first non-empty value found for the given keys.

    Iterates *keys* in order and returns the first value in *source* that is
    not ``None`` and not the empty string.  Returns ``None`` if no matching
    value is found.

    Parameters
    ----------
    source:
        The dictionary to search.
    keys:
        Ordered list of key names to try.
    """
    for key in keys:
        value = source.get(key)
        if value is not None and value != "":
            return value
    return None


def coerce_float(value):
    """Safely coerce *value* to :class:`float`.

    Returns ``None`` if *value* is ``None`` or cannot be converted (e.g. an
    incompatible type or a non-numeric string).

    Parameters
    ----------
    value:
        The value to convert.
    """
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def format_stop_name(stop_name: str) -> str:
    """Format a CamelCase stop name into a space-separated human-readable string.

    Uses a regex that identifies word boundaries between capital-letter runs
    and mixed-case words so that e.g. ``"CentralStation"`` becomes
    ``"Central Station"``.

    Parameters
    ----------
    stop_name:
        The raw stop name string (typically CamelCase).

    Returns
    -------
    str
        The formatted, space-separated name, or the original string if no
        words could be extracted.
    """
    words = re.findall(r"[A-Z]+(?=$|[A-Z][a-z])|[A-Z]?[a-z]+", stop_name)
    return " ".join(words) if words else stop_name


def normalize_stop_name(stop_name: str) -> str:
    """Remove all whitespace and lowercase a stop name for stable comparison.

    Used when two stop names need to be compared regardless of spacing or
    capitalisation differences (e.g. ``"Central Station"`` vs
    ``"centralstation"``).

    Parameters
    ----------
    stop_name:
        The stop name to normalise.

    Returns
    -------
    str
        The normalised string.
    """
    return re.sub(r"\s+", "", stop_name).lower()