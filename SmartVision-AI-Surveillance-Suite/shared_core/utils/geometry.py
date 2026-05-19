"""Geometry helpers for zones, lines, and object centers."""

from __future__ import annotations

from typing import Iterable


Point = tuple[float, float]
BBox = tuple[float, float, float, float]


def bbox_center(box: BBox) -> Point:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def bbox_area(box: BBox) -> float:
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def point_in_polygon(point: Point, polygon: Iterable[Point]) -> bool:
    """Ray-casting point-in-polygon test for configured restricted zones."""

    x, y = point
    pts = list(polygon)
    inside = False
    if len(pts) < 3:
        return False

    j = len(pts) - 1
    for i, pi in enumerate(pts):
        xi, yi = pi
        xj, yj = pts[j]
        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
        if intersects:
            inside = not inside
        j = i
    return inside
