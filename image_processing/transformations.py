# HIT137 Group Assignment 3 | Semester 2, 2026
# Allocated student: Redwan Rahman Rupom | Student ID: 397409
# Component: OpenCV Image Processing
# AI-assisted preparation; see docs/AI_ASSISTANCE.md.

"""Polymorphic transformations and disjoint-target random plan generation."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from .errors import TileOperationError
from .model import validate_grid

if TYPE_CHECKING:
    from .model import PuzzleBoard

TRANSFORMATION_COUNTS = MappingProxyType({3: 6, 4: 12, 5: 20})


def _non_negative(index: int) -> None:
    if type(index) is not int or index < 0:
        raise TileOperationError("A target must be a non-negative integer.")


class Transformation(ABC):
    """Shared interface: the planner/board need not branch during application."""

    @property
    @abstractmethod
    def targets(self) -> tuple[int, ...]:
        """Every tile position affected by this operation."""

    @abstractmethod
    def apply(self, board: PuzzleBoard) -> None:
        """Apply the operation to current board positions."""

    @abstractmethod
    def inverse(self) -> Transformation:
        """Return the exact inverse operation."""

    @abstractmethod
    def as_dict(self) -> dict[str, object]:
        """Return JSON-serialisable audit information."""


@dataclass(frozen=True)
class Swap(Transformation):
    first: int
    second: int

    def __post_init__(self) -> None:
        _non_negative(self.first)
        _non_negative(self.second)
        if self.first == self.second:
            raise TileOperationError("A swap needs two different targets.")

    @property
    def targets(self) -> tuple[int, ...]:
        return self.first, self.second

    def apply(self, board: PuzzleBoard) -> None:
        board.swap(self.first, self.second)

    def inverse(self) -> Transformation:
        return self

    def as_dict(self) -> dict[str, object]:
        return {"type": "swap", "targets": list(self.targets)}


@dataclass(frozen=True)
class Rotate(Transformation):
    target: int
    degrees: int

    def __post_init__(self) -> None:
        _non_negative(self.target)
        if type(self.degrees) is not int or self.degrees not in (90, 180, 270):
            raise TileOperationError("Rotation must be 90, 180, or 270 degrees clockwise.")

    @property
    def targets(self) -> tuple[int, ...]:
        return (self.target,)

    def apply(self, board: PuzzleBoard) -> None:
        board.rotate(self.target, self.degrees)

    def inverse(self) -> Transformation:
        return Rotate(self.target, 360 - self.degrees)

    def as_dict(self) -> dict[str, object]:
        return {"type": "rotate", "targets": list(self.targets), "degrees_cw": self.degrees}


@dataclass(frozen=True)
class Flip(Transformation):
    target: int
    direction: str

    def __post_init__(self) -> None:
        _non_negative(self.target)
        if self.direction not in ("horizontal", "vertical"):
            raise TileOperationError("Flip direction must be horizontal or vertical.")

    @property
    def targets(self) -> tuple[int, ...]:
        return (self.target,)

    def apply(self, board: PuzzleBoard) -> None:
        board.flip(self.target, self.direction)

    def inverse(self) -> Transformation:
        return self

    def as_dict(self) -> dict[str, object]:
        return {"type": "flip", "targets": list(self.targets), "direction": self.direction}


class ScramblePlanner:
    """Generate all operations BEFORE any pixels or board state are modified.

    With N tiles, K operations, and S swaps, K + S distinct tiles are needed.
    Limiting S to N - K makes exact counts compatible with no repeated targets.
    At least one swap, one rotation and one flip occur in EVERY generated plan.
    A seed is optional and intended for tests, not for normal gameplay.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def generate(self, grid_size: int) -> tuple[Transformation, ...]:
        validate_grid(grid_size)
        tile_count = grid_size**2
        operation_count = TRANSFORMATION_COUNTS[grid_size]
        max_swaps = min(tile_count - operation_count, operation_count - 2)
        swap_count = self._random.randint(1, max_swaps)
        rotate_count = self._random.randint(1, operation_count - swap_count - 1)
        flip_count = operation_count - swap_count - rotate_count

        available = list(range(tile_count))
        self._random.shuffle(available)
        actions: list[Transformation] = []
        for _ in range(swap_count):
            actions.append(Swap(available.pop(), available.pop()))
        for _ in range(rotate_count):
            actions.append(Rotate(available.pop(), self._random.choice((90, 180, 270))))
        for _ in range(flip_count):
            actions.append(Flip(available.pop(), self._random.choice(("horizontal", "vertical"))))
        self._random.shuffle(actions)
        return tuple(actions)
