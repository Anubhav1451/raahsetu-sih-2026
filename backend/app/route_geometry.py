"""Assemble directed OSM shapes without smoothing or inventing road points."""

import math


def assemble_geometry(edges, nodes):
    coordinates = []
    warnings = []
    for edge in edges:
        start = (nodes[edge.u].lon, nodes[edge.u].lat)
        end = (nodes[edge.v].lon, nodes[edge.v].lat)
        points = list(edge.geometry)
        if len(points) < 2 or any(
            not (math.isfinite(x) and math.isfinite(y) and -180 <= x <= 180 and -90 <= y <= 90)
            for x, y in points
        ):
            raise ValueError(f"Invalid road geometry: {edge.id}")

        def near(a, b):
            return abs(a[0] - b[0]) <= 1e-6 and abs(a[1] - b[1]) <= 1e-6

        if near(points[-1], start) and near(points[0], end):
            points.reverse()
        if not near(points[0], start) or not near(points[-1], end):
            raise ValueError(f"Road geometry endpoints do not match directed edge {edge.id}")
        if coordinates and not near(coordinates[-1], points[0]):
            raise ValueError(f"Disconnected route geometry at {edge.id}")
        for point in points:
            if not coordinates or tuple(coordinates[-1]) != tuple(point):
                coordinates.append(point)
    return {"type": "LineString", "coordinates": coordinates}, warnings
