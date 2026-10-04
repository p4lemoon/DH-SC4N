from __future__ import annotations

import random

CREDENTIALS = [
    ("admin", "admin"),
    ("admin", "admin12345"),
    ("admin", "123456"),
    ("admin", "12345"),
    ("default", "tluafed"),
    ("888888", "888888"),
    ("666666", "666666"),
    ("888888", "666666"),
]
_seen = set()
DEFAULT_LIST = [c for c in CREDENTIALS if not (c in _seen or _seen.add(c))]


def get_random(count: int = 5) -> list[tuple[str, str]]:
    sample_size = min(count, len(DEFAULT_LIST))
    return random.sample(DEFAULT_LIST, sample_size)


def get_all() -> list[tuple[str, str]]:
    return list(DEFAULT_LIST)