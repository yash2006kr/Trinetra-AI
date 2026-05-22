"""Geometry helpers for zones, lines, and object centers."""

from __future__ import annotations

from collections.abc import Iterable

Point = tuple[float, float]
BBox = tuple[float, float, float, float]


def bbox_center(box: BBox) -> Point:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def bbox_area(box: BBox) -> float:
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def bbox_iou(a: BBox, b: BBox) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    intersection = bbox_area((ix1, iy1, ix2, iy2))
    if intersection <= 0:
        return 0.0
    union = bbox_area(a) + bbox_area(b) - intersection
    return intersection / max(union, 1e-9)


def bbox_diagonal(box: BBox) -> float:
    x1, y1, x2, y2 = box
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


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
