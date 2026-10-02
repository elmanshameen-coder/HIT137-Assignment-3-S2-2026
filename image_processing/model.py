# HIT137 Group Assignment 3 | Semester 2, 2026
# Allocated student: Redwan Rahman Rupom | Student ID: 397409
# Component: OpenCV Image Processing
# AI-assisted preparation; see docs/AI_ASSISTANCE.md.

"""Puzzle state independent of Tkinter, move counters, and hint limits.

Pixels are stored in OpenCV's BGR order. Each tile keeps its unmodified pixels.
Its orientation is represented canonically as a horizontal reflection followed
by 0, 1, 2, or 3 clockwise quarter turns. This represents all eight square
orientations, including combinations of rotation and reflection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

from .errors import ConfigurationError, TileOperationError

if TYPE_CHECKING:
    from .transformations import Transformation

ImageArray = NDArray[np.uint8]
SUPPORTED_GRIDS = (3, 4, 5)


def validate_grid(grid_size: int) -> None:
    """Reject unsupported sizes instead of silently choosing another size."""
    if type(grid_size) is not int or grid_size not in SUPPORTED_GRIDS:
        raise ConfigurationError("Grid size must be 3, 4, or 5.")


def validate_bgr(image: ImageArray) -> None:
    """Validate the public, three-channel, eight-bit BGR array contract."""
    if (
        not isinstance(image, np.ndarray)
        or image.dtype != np.uint8
        or image.ndim != 3
        or image.shape[2] != 3
        or image.shape[0] == 0
        or image.shape[1] == 0
    ):
        raise ConfigurationError("Expected a non-empty uint8 image with shape (H, W, 3).")


def validate_index(index: int, tile_count: int) -> None:
    if type(index) is not int or not 0 <= index < tile_count:
        raise TileOperationError(f"Tile index must be an integer in 0..{tile_count - 1}.")


@dataclass(frozen=True)
class PreparationInfo:
    """Image sizes are (width, height); content is not stretched to a square."""

    source_size: tuple[int, int]
    resized_size: tuple[int, int]
    output_size: tuple[int, int]
    fit_mode: str


@dataclass(frozen=True)
class TileState:
    """Read-only metadata, safe for the group's GUI/gameplay code to inspect."""

    current_index: int
    original_index: int
    rotation_degrees: int
    mirrored: bool

    @property
    def is_correct(self) -> bool:
        return (
            self.current_index == self.original_index
            and self.rotation_degrees == 0
            and not self.mirrored
        )


class _Tile:
    """Encapsulated original pixels and a lossless orientation state."""

    def __init__(self, original_index: int, pixels: ImageArray) -> None:
        self.original_index = original_index
        self._original = pixels.copy()
        self.quarter_turns = 0
        self.mirrored = False

    def rotate(self, degrees: int) -> None:
        self.quarter_turns = (self.quarter_turns + degrees // 90) % 4

    def flip(self, direction: str) -> None:
        # H R^k = R^-k H, and V = R^2 H. This matters after mixed actions.
        offset = 0 if direction == "horizontal" else 2
        self.quarter_turns = (offset - self.quarter_turns) % 4
        self.mirrored = not self.mirrored

    def reset(self) -> None:
        self.quarter_turns = 0
        self.mirrored = False

    def pixels(self) -> ImageArray:
        image = self._original.copy()
        if self.mirrored:
            image = cv2.flip(image, 1)
        rotate_codes = {
            1: cv2.ROTATE_90_CLOCKWISE,
            2: cv2.ROTATE_180,
            3: cv2.ROTATE_90_COUNTERCLOCKWISE,
        }
        if self.quarter_turns:
            image = cv2.rotate(image, rotate_codes[self.quarter_turns])
        return image


class PuzzleBoard:
    """A square tile board. Public image/metadata access never exposes state.

    Indices run left to right, top to bottom, starting at zero. A swap acts on
    two CURRENT positions, not on original tile IDs. The GUI owns selections,
    move counters, hint limits, and the decision to lock input after completion.
    """

    def __init__(
        self,
        original_bgr: ImageArray,
        grid_size: int = 3,
        preparation: PreparationInfo | None = None,
    ) -> None:
        validate_grid(grid_size)
        validate_bgr(original_bgr)
        height, width = original_bgr.shape[:2]
        if height != width or width % grid_size:
            raise ConfigurationError("Board must be square and evenly divisible by its grid.")
        self._grid_size = grid_size
        self._tile_size = width // grid_size
        self._original = original_bgr.copy()
        self._preparation = preparation
        self._scramble_plan: tuple[Transformation, ...] = ()
        self._tiles = []
        for index in range(grid_size * grid_size):
            row, column = divmod(index, grid_size)
            y, x = row * self._tile_size, column * self._tile_size
            pixels = self._original[y : y + self._tile_size, x : x + self._tile_size]
            self._tiles.append(_Tile(index, pixels))

    @property
    def grid_size(self) -> int:
        return self._grid_size

    @property
    def tile_size(self) -> int:
        return self._tile_size

    @property
    def tile_count(self) -> int:
        return self._grid_size**2

    @property
    def image_size(self) -> tuple[int, int]:
        return (self._original.shape[1], self._original.shape[0])

    @property
    def preparation(self) -> PreparationInfo | None:
        return self._preparation

    @property
    def original_bgr(self) -> ImageArray:
        return self._original.copy()

    @property
    def scramble_plan(self) -> tuple[Transformation, ...]:
        """The immutable initial plan, not a history of later player moves."""
        return self._scramble_plan

    @property
    def tile_states(self) -> tuple[TileState, ...]:
        return tuple(
            TileState(i, tile.original_index, tile.quarter_turns * 90, tile.mirrored)
            for i, tile in enumerate(self._tiles)
        )

    @property
    def incorrect_indices(self) -> tuple[int, ...]:
        return tuple(state.current_index for state in self.tile_states if not state.is_correct)

    @property
    def is_solved(self) -> bool:
        return not self.incorrect_indices

    def tile_pixels(self, index: int) -> ImageArray:
        validate_index(index, self.tile_count)
        return self._tiles[index].pixels()

    def swap(self, first: int, second: int) -> None:
        validate_index(first, self.tile_count)
        validate_index(second, self.tile_count)
        if first == second:
            raise TileOperationError("A swap needs two different tile positions.")
        self._tiles[first], self._tiles[second] = self._tiles[second], self._tiles[first]

    def rotate(self, index: int, degrees: int = 90) -> None:
        validate_index(index, self.tile_count)
        if type(degrees) is not int or degrees not in (90, 180, 270):
            raise TileOperationError("Rotation must be 90, 180, or 270 degrees clockwise.")
        self._tiles[index].rotate(degrees)

    def flip(self, index: int, direction: str = "horizontal") -> None:
        validate_index(index, self.tile_count)
        if direction not in ("horizontal", "vertical"):
            raise TileOperationError("Flip direction must be horizontal or vertical.")
        self._tiles[index].flip(direction)

    def reassemble_bgr(self) -> ImageArray:
        """Join clean transformed tiles into ONE image, without UI overlays."""
        rows = []
        for row in range(self._grid_size):
            start = row * self._grid_size
            rows.append(cv2.hconcat([t.pixels() for t in self._tiles[start : start + self._grid_size]]))
        return cv2.vconcat(rows)

    def restore(self) -> None:
        """Restore every position/orientation, including later player changes.

        The GUI must also reset its move/score counters and selection/hint state.
        Initial scramble metadata is retained as an audit record only.
        """
        self._tiles.sort(key=lambda tile: tile.original_index)
        for tile in self._tiles:
            tile.reset()

    def index_at(self, x: int, y: int) -> int | None:
        """Map image-local pixel coordinates; outside clicks return None.

        The GUI must subtract any canvas/image offset before calling this.
        """
        width, height = self.image_size
        if (
            type(x) is not int
            or type(y) is not int
            or not 0 <= x < width
            or not 0 <= y < height
        ):
            return None
        return (y // self._tile_size) * self._grid_size + x // self._tile_size

    def apply_initial_scramble(self, plan: tuple[Transformation, ...]) -> None:
        """Validate the WHOLE plan before changing this fresh, solved board.

        Both ends of a swap count as targeted tiles. Validation is separate
        from application, so an invalid plan cannot partially scramble a board.
        """
        from .transformations import Flip, Rotate, Swap

        if self._scramble_plan or not self.is_solved:
            raise TileOperationError("Initial scrambling requires a fresh solved board.")
        if not isinstance(plan, tuple) or not plan:
            raise TileOperationError("Scramble plan must be a non-empty tuple.")
        targets: list[int] = []
        for action in plan:
            if type(action) not in (Swap, Rotate, Flip):
                raise TileOperationError("Unsupported initial transformation.")
            for target in action.targets:
                validate_index(target, self.tile_count)
                targets.append(target)
        if len(targets) != len(set(targets)):
            raise TileOperationError("An initial scramble cannot target a tile twice.")
        for action in plan:
            action.apply(self)
        self._scramble_plan = plan
