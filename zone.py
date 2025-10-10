"""Zone classification utilities built on top of geometry primitives."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, List, Sequence

from PIL import Image

from geom import Point, Polygon, point_in_polygon

ZONE_LABELS: Final[tuple[str, str, str]] = ("PAINT", "TWO_PT", "THREE_PT")
"""Primary zone labels shared across the application."""


@dataclass(frozen=True)
class Zone:
    """Named polygon representing a logical scoring area."""

    name: str
    polygon: Polygon


def _scale_polygon(
    relative_vertices: Sequence[tuple[float, float]], width: float, height: float
) -> Polygon:
    """Scale vertices expressed as ratios into absolute pixels."""

    points = [Point(x * width, y * height) for x, y in relative_vertices]
    return Polygon(points)


def load_default_zones(image_path: str = "court.png") -> List[Zone]:
    """Create default scoring zones scaled to the supplied court image."""

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Court image not found at {path}. Place court.png alongside app.py."
        )

    with Image.open(path) as image:
        width, height = image.size

    paint = _scale_polygon(
        (
            (0.38, 0.05),
            (0.62, 0.05),
            (0.62, 0.38),
            (0.38, 0.38),
        ),
        width,
        height,
    )

    midrange = _scale_polygon(
        (
            (0.18, 0.0),
            (0.82, 0.0),
            (0.88, 0.44),
            (0.75, 0.75),
            (0.25, 0.75),
            (0.12, 0.44),
        ),
        width,
        height,
    )

    left_corner = _scale_polygon(
        (
            (0.0, 0.44),
            (0.12, 0.44),
            (0.12, 0.94),
            (0.0, 0.94),
        ),
        width,
        height,
    )

    right_corner = _scale_polygon(
        (
            (0.88, 0.44),
            (1.0, 0.44),
            (1.0, 0.94),
            (0.88, 0.94),
        ),
        width,
        height,
    )

    above_break = _scale_polygon(
        (
            (0.0, 0.0),
            (1.0, 0.0),
            (1.0, 0.44),
            (0.88, 0.44),
            (0.74, 0.2),
            (0.26, 0.2),
            (0.12, 0.44),
            (0.0, 0.44),
        ),
        width,
        height,
    )

    return [
        Zone("PAINT", paint),
        Zone("MIDRANGE", midrange),
        Zone("3PT_CORNER", left_corner),
        Zone("3PT_CORNER", right_corner),
        Zone("3PT_ABOVE_BREAK", above_break),
    ]


def classify_point(x: float, y: float, zones: Iterable[Zone]) -> str:
    """Return the label of the first zone that contains the point or UNKNOWN."""

    for zone in zones:
        if point_in_polygon(Point(x, y), zone.polygon):
            return zone.name
    return "UNKNOWN"
