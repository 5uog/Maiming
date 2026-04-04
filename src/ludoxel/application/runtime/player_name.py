# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from secrets import randbelow

_ADJECTIVES: tuple[str, ...] = (
    "Amber",
    "Aqua",
    "Brisk",
    "Cinder",
    "Clear",
    "Copper",
    "Crimson",
    "Drift",
    "Ember",
    "Golden",
    "Ivory",
    "Jade",
    "Mellow",
    "Mist",
    "Moss",
    "North",
    "Quartz",
    "River",
    "Silver",
    "Spruce",
    "Sunny",
    "Swift",
    "Velvet",
    "Winter",
)

_NOUNS: tuple[str, ...] = (
    "Badger",
    "Comet",
    "Falcon",
    "Finch",
    "Fox",
    "Heron",
    "Lynx",
    "Maple",
    "Otter",
    "Panda",
    "Pine",
    "Raven",
    "Salmon",
    "Stone",
    "Tern",
    "Tiger",
    "Violet",
    "Willow",
    "Wolf",
)


def normalize_player_name(value: object) -> str:
    text = " ".join(str(value or "").split())
    return str(text[:32]).strip()


def has_explicit_player_name(value: object) -> bool:
    return bool(normalize_player_name(value))


def generate_random_player_name() -> str:
    adjective = _ADJECTIVES[randbelow(len(_ADJECTIVES))]
    noun = _NOUNS[randbelow(len(_NOUNS))]
    number = 100 + randbelow(900)
    return f"{adjective}{noun}{number}"


def resolve_session_player_name(explicit_name: object, *, fallback_name: str | None = None) -> str:
    normalized = normalize_player_name(explicit_name)
    if normalized:
        return normalized
    fallback = normalize_player_name(fallback_name)
    if fallback:
        return fallback
    return generate_random_player_name()
