"""Travel-time lookup and documented fallback policies for DispatchGrid.

Policy guarantees:
1. Pairwise entries from travel_times.csv (or injected TravelEntry lists) are always preferred.
2. Negative or malformed travel entries are flagged and never used.
3. Missing travel pairs NEVER silently default to 0 minutes.
4. When allow_coordinate_fallback=True and both locations have valid planar coordinates,
   travel time is computed via the dataset README specification:
   - Euclidean distance * 1.25 road-detour multiplier
   - 30 km/h average speed (2.0 minutes per detour km)
   - Rounded up to 5-minute increments
   Every coordinate-computed lookup is logged as 'coordinate_detour_estimate' so callers
   can surface an explicit validation warning (e.g., for scenario job J101).
5. When allow_coordinate_fallback=False or coordinates are unavailable, lookup returns None
   and Module B rejects the candidate with ReasonCode.MISSING_TRAVEL_DATA.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.schemas.scheduling import Electrician, Job, TravelEntry


@dataclass(frozen=True, slots=True)
class TravelLookupResult:
    """Resolved travel duration, estimated distance, and provenance."""

    travel_time_min: int
    distance_km: float
    source: str


def compute_synthetic_travel_minutes(
    x1_km: float,
    y1_km: float,
    x2_km: float,
    y2_km: float,
) -> tuple[int, float]:
    """Compute synthetic travel minutes and detour distance per data/README.md."""
    euclid_km = math.hypot(x2_km - x1_km, y2_km - y1_km)
    detour_km = round(euclid_km * 1.25, 2)
    if euclid_km == 0.0:
        return 0, 0.0
    raw_minutes = (euclid_km * 1.25) / 30.0 * 60.0
    rounded_minutes = int(math.ceil(raw_minutes / 5.0) * 5)
    return rounded_minutes, detour_km


class TravelMatrix:
    """Deterministic travel-time lookup index with explicit missing-data diagnostics."""

    def __init__(
        self,
        entries: list[TravelEntry] | None = None,
        electricians: list[Electrician] | None = None,
        jobs: list[Job] | None = None,
        allow_coordinate_fallback: bool = True,
    ) -> None:
        self._allow_coordinate_fallback = allow_coordinate_fallback
        self._matrix: dict[tuple[str, str], TravelLookupResult] = {}
        self._known_locations: set[str] = set()
        self._coordinates: dict[str, tuple[float, float]] = {}
        self.invalid_entries: list[str] = []
        self.coordinate_fallback_pairs: set[tuple[str, str]] = set()

        for entry in entries or []:
            if entry.travel_time_min < 0 or entry.distance_km_est < 0 or not math.isfinite(entry.distance_km_est):
                self.invalid_entries.append(
                    f"{entry.from_location_id}->{entry.to_location_id}: "
                    f"travel_time_min={entry.travel_time_min}, distance_km_est={entry.distance_km_est}"
                )
                continue
            self._known_locations.add(entry.from_location_id)
            self._known_locations.add(entry.to_location_id)
            self._matrix[(entry.from_location_id, entry.to_location_id)] = TravelLookupResult(
                travel_time_min=entry.travel_time_min,
                distance_km=entry.distance_km_est,
                source=entry.estimate_type or "matrix_lookup",
            )

        for elec in electricians or []:
            loc_id = elec.effective_start_location_id
            if (
                elec.start_x_km is not None
                and elec.start_y_km is not None
                and math.isfinite(elec.start_x_km)
                and math.isfinite(elec.start_y_km)
            ):
                self._coordinates[loc_id] = (elec.start_x_km, elec.start_y_km)

        for job in jobs or []:
            loc_id = job.effective_location_id
            if (
                job.location_x_km is not None
                and job.location_y_km is not None
                and math.isfinite(job.location_x_km)
                and math.isfinite(job.location_y_km)
            ):
                self._coordinates[loc_id] = (job.location_x_km, job.location_y_km)

    @property
    def row_count(self) -> int:
        return len(self._matrix)

    @property
    def matrix_locations(self) -> set[str]:
        return set(self._known_locations)

    def has_exact_entry(self, from_id: str, to_id: str) -> bool:
        return (from_id, to_id) in self._matrix

    def lookup(
        self,
        from_id: str,
        to_id: str,
        allow_coordinate_fallback: bool | None = None,
    ) -> TravelLookupResult | None:
        """Resolve travel time between two location IDs, or return None if unavailable."""
        exact = self._matrix.get((from_id, to_id))
        if exact is not None:
            return exact

        use_fallback = (
            self._allow_coordinate_fallback
            if allow_coordinate_fallback is None
            else allow_coordinate_fallback
        )

        if from_id == to_id and (from_id in self._known_locations or (use_fallback and from_id in self._coordinates)):
            return TravelLookupResult(travel_time_min=0, distance_km=0.0, source="same_location")

        if use_fallback and from_id in self._coordinates and to_id in self._coordinates:
            x1, y1 = self._coordinates[from_id]
            x2, y2 = self._coordinates[to_id]
            travel_min, dist_km = compute_synthetic_travel_minutes(x1, y1, x2, y2)
            self.coordinate_fallback_pairs.add((from_id, to_id))
            return TravelLookupResult(
                travel_time_min=travel_min,
                distance_km=dist_km,
                source="coordinate_detour_estimate",
            )

        return None

