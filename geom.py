"""Geometry helpers for spatial zone classification."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass
class Point:
    """Represents a 2D point in pixel coordinates."""

    x: float
    y: float


@dataclass
class Polygon:
    """Represents a polygon defined by a sequence of vertices."""

    vertices: Sequence[Point]

    def __post_init__(self) -> None:
        if len(self.vertices) < 3:
            raise ValueError("A polygon requires at least three vertices.")
        # Convert to tuple to avoid accidental mutation of the original sequence.
        self.vertices = tuple(self.vertices)

    def __iter__(self) -> Iterable[Point]:
        """Iterate over points that belong to the polygon."""

        return iter(self.vertices)


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """Return True when the point lies inside or on the boundary of the polygon."""

    x, y = point.x, point.y
    inside = False
    vertices = polygon.vertices
    n = len(vertices)

    for i in range(n):
        j = (i - 1) % n
        xi, yi = vertices[i].x, vertices[i].y
        xj, yj = vertices[j].x, vertices[j].y

        if ((yi > y) != (yj > y)):
            intersect_x = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x == intersect_x:
                return True
            if x < intersect_x:
                inside = not inside
        # Handle points on horizontal edges explicitly.
        min_y, max_y = sorted((yi, yj))
        min_x, max_x = sorted((xi, xj))
        if yi == yj == y and min_x <= x <= max_x:
            return True
        if xi == xj == x and min_y <= y <= max_y:
            return True

    return inside
