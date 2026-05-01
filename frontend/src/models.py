"""
models.py
---------
Pydantic data models representing the core domain objects of the transport network.

These models are used to deserialize and validate JSON responses from the backend
and provide a structured, type-safe representation within the frontend application.
"""
from __future__ import annotations

from typing import Any, Tuple
from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator


class Stop(BaseModel):
    """Represents a transit stop (e.g. a train station or bus stop).

    A stop is uniquely identified by its `stop_name` (case-sensitive).
    It also holds display coordinates (`normalized_position_on_screen`) for mapping.
    """
    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        extra="forbid",
    )

    stop_name: str = Field(alias="stopName")
    """The canonical name of the stop."""

    normalized_position_on_screen: Tuple[float, float] = Field(
        validation_alias=AliasChoices("normalizedPositionOnScreen", "segmentTransportationType"),
        serialization_alias="segmentTransportationType",
    )
    """The (x, y) coordinates of the stop, normalized between 0.0 and 1.0."""

    @field_validator("normalized_position_on_screen", mode="before")
    @classmethod
    def coerce_normalized_position(cls, value: Any) -> Tuple[float, float]:
        """Convert dictionary or list representations into a tuple."""
        if isinstance(value, dict):
            return (value.get("x", 0.0), value.get("y", 0.0))
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("normalized_position_on_screen")
    @classmethod
    def validate_normalized_position(cls, value: Tuple[float, float]) -> Tuple[float, float]:
        """Ensure the position coordinates are within the [0, 1] range."""
        x, y = value
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError("normalized_position_on_screen must be within [0, 1] for both x and y")
        return value

    # Match C# equality semantics: StopName-only equality
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stop):
            return NotImplemented
        return self.stop_name == other.stop_name

    def __hash__(self) -> int:
        return hash(self.stop_name)


class Segment(BaseModel):
    """Represents a connection (edge) between two stops in the transit network.

    A segment includes metadata such as the transportation type, the line it
    belongs to, cost, time, and a scenic index for routing algorithms.
    """
    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        extra="forbid",
    )

    from_stop: Stop = Field(validation_alias=AliasChoices("from", "fromStop"), serialization_alias="from")
    """The starting stop of the segment."""
    to_stop: Stop = Field(validation_alias=AliasChoices("to", "toStop"), serialization_alias="to")
    """The destination stop of the segment."""
    segment_transportation_type: str = Field(
        validation_alias=AliasChoices("type", "segmentTransportationType"),
        serialization_alias="type",
    )
    """The mode of transport (e.g., 'Train', 'Bus', 'Walk')."""
    line: str | None = Field(
        default=None,
        validation_alias=AliasChoices("line", "lineCode", "routeName", "route"),
        serialization_alias="line",
    )
    """The line or route identifier (e.g., 'TWL', 'KTL'), if applicable."""
    fare_dollars: float = Field(validation_alias=AliasChoices("fare", "fareDollars"), serialization_alias="fare")
    """The fare cost of traveling on this segment in dollars."""
    time_min: int = Field(validation_alias=AliasChoices("time", "timeMinutes"), serialization_alias="time")
    """The estimated travel time on this segment in minutes."""
    scenic_index: int = Field(validation_alias=AliasChoices("scenic", "scenicIndex"), serialization_alias="scenic")
    """A subjective score indicating how scenic the segment is."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Segment):
            return False
        return (
            self.from_stop == other.from_stop
            and self.to_stop == other.to_stop
            and self.segment_transportation_type == other.segment_transportation_type
            and self.line == other.line
            and self.fare_dollars == other.fare_dollars
            and self.time_min == other.time_min
            and self.scenic_index == other.scenic_index
        )

    def __hash__(self) -> int:
        return hash((self.from_stop, self.to_stop))


class TransportNetwork(BaseModel):
    """Represents the entire transport network containing all stops and segments."""
    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        extra="forbid",
    )

    all_stops: list[Stop] = Field(alias="stops")
    """List of all available stops in the network."""
    all_segments: list[Segment] = Field(alias="segments")
    """List of all available segments connecting the stops."""


class Route(BaseModel):
    """Represents a calculated path or route through the transport network.

    It aggregates statistics for the entire journey, such as total cost,
    total distance, time, and a computed score based on user preferences.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )

    rank: int | None = Field(
        default=None,
        validation_alias=AliasChoices("rank", "routeRank", "ranking"),
        serialization_alias="rank",
    )
    """The rank of this route among alternatives."""
    description: str | None = Field(
        default=None,
        validation_alias=AliasChoices("description", "routeDescription", "summary"),
        serialization_alias="description",
    )
    """A human-readable description of the route path."""
    total_cost: float | None = Field(
        default=None,
        validation_alias=AliasChoices("totalCost", "totalFare", "fareDollars", "cost"),
        serialization_alias="totalCost",
    )
    """Total fare cost for the route."""
    total_distance_km: float | None = Field(
        default=None,
        validation_alias=AliasChoices("totalDistanceKm", "distanceKm", "distanceKM"),
        serialization_alias="totalDistanceKm",
    )
    """Total travel distance in kilometers."""
    travel_time_minutes: float | None = Field(
        default=None,
        validation_alias=AliasChoices("travelTimeMinutes", "durationMinutes", "timeMinutes", "totalTimeMinutes"),
        serialization_alias="travelTimeMinutes",
    )
    """Total travel time in minutes."""
    transfer_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("transferCount", "transfers", "numberOfTransfers"),
        serialization_alias="transferCount",
    )
    """Number of transfers (line or mode changes) required on this route."""
    score: float | None = Field(
        default=None,
        validation_alias=AliasChoices("score", "routeScore", "totalScore", "rankingScore", "finalScore", "weightedScore"),
        serialization_alias="score",
    )
    """Computed score of the route based on the selected weighting criteria."""
    transport_modes: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("transportModes", "modes", "segmentTransportationTypes"),
        serialization_alias="transportModes",
    )
    """A list of transport modes used sequentially in the route."""
    raw_payload: dict[str, Any] | None = None
    """The original raw JSON payload from the backend for this route."""
