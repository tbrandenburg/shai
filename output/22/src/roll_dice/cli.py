"""CLI entry for the roll-dice command."""

from __future__ import annotations

import random
from typing import Final

_RANDOM: Final[random.Random] = random.SystemRandom()


def roll_die() -> int:
    """Return a pseudo-random integer between 1 and 6 inclusive."""
    return _RANDOM.randint(1, 6)


def main() -> int:
    value = roll_die()
    print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
