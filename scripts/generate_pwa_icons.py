"""Generate deterministic RaahSetu PNG app icons without third-party image tools."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public"


def inside_round_rect(x: float, y: float, size: int, radius: float) -> bool:
    cx = min(max(x, radius), size - radius)
    cy = min(max(y, radius), size - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def distance_to_segment(
    x: float, y: float, ax: float, ay: float, bx: float, by: float
) -> float:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if not length_sq:
        return math.hypot(x - ax, y - ay)
    position = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length_sq))
    return math.hypot(x - (ax + position * dx), y - (ay + position * dy))


def pixel(x: int, y: int, size: int) -> tuple[int, int, int, int]:
    scale = size / 40
    if not inside_round_rect(x + 0.5, y + 0.5, size, 9 * scale):
        return 7, 12, 17, 255
    # Subtle depth keeps the icon readable on both light and dark launchers.
    blend = y / max(size - 1, 1)
    background = (
        int(14 + 5 * (1 - blend)),
        int(34 + 10 * (1 - blend)),
        int(39 + 11 * (1 - blend)),
        255,
    )
    mint = (114, 230, 177, 255)
    width = 3.5 * scale
    segments = [
        (11, 29, 11, 12),
        (11, 12, 21, 12),
        (21, 12, 27, 17),
        (27, 17, 25, 23),
        (25, 23, 19, 26),
        (19, 26, 28, 29),
    ]
    for ax, ay, bx, by in segments:
        if distance_to_segment(x, y, ax * scale, ay * scale, bx * scale, by * scale) <= width / 2:
            return mint
    if math.hypot(x - 11 * scale, y - 12 * scale) <= 3 * scale:
        return mint
    return background


def write_png(path: Path, size: int) -> None:
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            raw.extend(pixel(x, y, size))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    path.write_bytes(signature + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for filename, size in (("apple-touch-icon.png", 180), ("pwa-192.png", 192), ("pwa-512.png", 512)):
        write_png(PUBLIC / filename, size)
        print(f"Generated {filename} ({size}x{size})")


if __name__ == "__main__":
    main()
