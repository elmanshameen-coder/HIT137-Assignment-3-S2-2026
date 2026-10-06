# HIT137 Assignment 3 - Semester 2, 2026
# Name: Md. Arshad Bin Ayyub
# Student ID: s400486
# Contribution: OOP design - Tile, PuzzleState and reversible transformations.
# Includes encapsulation, inheritance, polymorphism and class interaction.

"""OOP models for the HIT137 image puzzle.

Positions use (row, column), starting at zero. The GUI should change a puzzle
through PuzzleState, so its counters, selection and completion stay consistent.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from random import choice


def _position(value):
    """Validate a non-negative grid position."""
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(type(number) is not int or number < 0 for number in value)):
        raise ValueError("Position must contain two non-negative integers.")
    return tuple(value)


class Tile:
    """Keep one tile's original image, location and orientation together."""

    def __init__(self, original_position, image_data=None, *,
                 current_position=None, rotation=0,
                 flipped_horizontal=False, flipped_vertical=False):
        if type(rotation) is not int or rotation % 90 != 0:
            raise ValueError("Rotation must be a multiple of 90 degrees.")
        if (type(flipped_horizontal) is not bool
                or type(flipped_vertical) is not bool):
            raise ValueError("Flip statuses must be True or False.")
        self._original_position = _position(original_position)
        self._current_position = _position(
            original_position if current_position is None else current_position)
        self._rotation = rotation % 360
        self._flipped_horizontal = flipped_horizontal
        self._flipped_vertical = flipped_vertical
        self._image_data = deepcopy(image_data)

    @property
    def original_position(self):
        return self._original_position

    @property
    def current_position(self):
        return self._current_position

    @property
    def rotation(self):
        """Clockwise rotation: 0, 90, 180 or 270 degrees."""
        return self._rotation

    @property
    def flipped_horizontal(self):
        return self._flipped_horizontal

    @property
    def flipped_vertical(self):
        return self._flipped_vertical

    @property
    def image_data(self):
        """Return a copy so callers cannot overwrite the original image."""
        return deepcopy(self._image_data)

    def is_correct(self):
        # Two flips equal a 180-degree turn, so these can cancel each other.
        normal = (self._rotation == 0 and not self._flipped_horizontal
                  and not self._flipped_vertical)
        cancelled = (self._rotation == 180 and self._flipped_horizontal
                     and self._flipped_vertical)
        return (self._current_position == self._original_position
                and (normal or cancelled))

    def get_display_image(self):
        """Return the oriented image using OpenCV; keep original pixels intact."""
        if self._image_data is None:
            raise ValueError("This tile has no image data.")
        import cv2

        image = deepcopy(self._image_data)
        # Flip flags refer to the original image axes. Rotate after these flips.
        if self._flipped_horizontal:
            image = cv2.flip(image, 1)
        if self._flipped_vertical:
            image = cv2.flip(image, 0)
        rotations = {90: cv2.ROTATE_90_CLOCKWISE,
                     180: cv2.ROTATE_180,
                     270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        if self._rotation:
            image = cv2.rotate(image, rotations[self._rotation])
        return image

    # Internal changes are used by transformations and PuzzleState.
    def _move_to(self, position):
        self._current_position = _position(position)

    def _rotate(self, angle):
        self._rotation = (self._rotation + angle) % 360

    def _flip(self, axis):
        # A screen-horizontal flip becomes an original-vertical flip after a
        # quarter turn. This also makes mixed rotate/flip operations reversible.
        if self._rotation in (90, 270):
            axis = "vertical" if axis == "horizontal" else "horizontal"
        if axis == "horizontal":
            self._flipped_horizontal = not self._flipped_horizontal
        else:
            self._flipped_vertical = not self._flipped_vertical

    def _reset(self):
        self._current_position = self._original_position
        self._rotation = 0
        self._flipped_horizontal = False
        self._flipped_vertical = False


class Transformation(ABC):
    """Common interface for reversible operations on tiles."""

    def __init__(self, *tiles):
        if not tiles or any(not isinstance(tile, Tile) for tile in tiles):
            raise TypeError("Transformations require Tile objects.")
        self._tiles = tuple(tiles)
        self._applied = False

    @property
    def tiles(self):
        return self._tiles

    @property
    def is_applied(self):
        return self._applied

    def _check_apply(self):
        if self._applied:
            raise RuntimeError("This transformation is already applied.")

    def _check_undo(self):
        if not self._applied:
            raise RuntimeError("Apply the transformation before undoing it.")

    @abstractmethod
    def apply(self):
        """Apply this transformation."""

    @abstractmethod
    def undo(self):
        """Reverse this transformation in reverse application order."""


class SwapTransformation(Transformation):
    def __init__(self, first_tile, second_tile):
        super().__init__(first_tile, second_tile)
        if first_tile is second_tile:
            raise ValueError("A swap needs two different tiles.")

    def _swap(self):
        first, second = self._tiles
        first_position = first.current_position
        first._move_to(second.current_position)
        second._move_to(first_position)

    def apply(self):
        self._check_apply()
        self._swap()
        self._applied = True

    def undo(self):
        self._check_undo()
        self._swap()
        self._applied = False


class RotateTransformation(Transformation):
    def __init__(self, tile, angle=90):
        super().__init__(tile)
        if type(angle) is not int or angle not in (90, 180, 270):
            raise ValueError("Choose a clockwise rotation of 90, 180 or 270.")
        self._angle = angle

    def apply(self):
        self._check_apply()
        self._tiles[0]._rotate(self._angle)
        self._applied = True

    def undo(self):
        self._check_undo()
        self._tiles[0]._rotate(-self._angle)
        self._applied = False


class FlipTransformation(Transformation):
    def __init__(self, tile, axis="horizontal"):
        super().__init__(tile)
        if axis not in ("horizontal", "vertical"):
            raise ValueError("Flip axis must be horizontal or vertical.")
        self._axis = axis

    def apply(self):
        self._check_apply()
        self._tiles[0]._flip(self._axis)
        self._applied = True

    def undo(self):
        self._check_undo()
        self._tiles[0]._flip(self._axis)
        self._applied = False


class PuzzleState:
    """Manage a complete round and coordinate the Tile and Transformation classes."""

    MAX_HINTS = 3

    def __init__(self, tiles, grid_size=3):
        if type(grid_size) is not int or grid_size not in (3, 4, 5):
            raise ValueError("Grid size must be 3, 4 or 5.")
        self._tiles = list(tiles)
        if (len(self._tiles) != grid_size ** 2
                or any(not isinstance(tile, Tile) for tile in self._tiles)):
            raise ValueError("Supply exactly grid_size squared Tile objects.")
        positions = {(row, column) for row in range(grid_size)
                     for column in range(grid_size)}
        if {tile.original_position for tile in self._tiles} != positions:
            raise ValueError("Every original grid position must occur once.")
        if {tile.current_position for tile in self._tiles} != positions:
            raise ValueError("Every current grid position must occur once.")
        self._grid_size = grid_size
        self._selected_tile = None
        self._moves = 0
        self._hints_used = 0
        self._active_hint = None
        self._history = []
        self._refresh_completion()

    @property
    def tiles(self):
        """An immutable view of the tiles list."""
        return tuple(self._tiles)

    @property
    def grid_size(self):
        return self._grid_size

    @property
    def selected_tile(self):
        return self._selected_tile

    @property
    def moves(self):
        return self._moves

    @property
    def hints_used(self):
        return self._hints_used

    @property
    def active_hint(self):
        """(current position, original position), or None."""
        return self._active_hint

    @property
    def completed(self):
        return self._completed

    @property
    def locked(self):
        return self._locked

    @property
    def incorrect_tiles(self):
        return tuple(tile for tile in self._tiles if not tile.is_correct())

    @property
    def incorrect_count(self):
        return len(self.incorrect_tiles)

    @property
    def can_hint(self):
        return not self._locked and self._hints_used < self.MAX_HINTS

    def get_tile_at(self, position):
        """Return None for invalid/off-image positions, rather than crashing."""
        try:
            position = _position(position)
        except ValueError:
            return None
        if any(number >= self._grid_size for number in position):
            return None
        return next(tile for tile in self._tiles
                    if tile.current_position == position)

    def _check_transformation(self, transformation):
        if not isinstance(transformation, Transformation):
            raise TypeError("Expected a Transformation object.")
        if any(tile not in self._tiles for tile in transformation.tiles):
            raise ValueError("All affected tiles must belong to this puzzle.")
        transformation._check_apply()

    def _refresh_completion(self):
        self._completed = all(tile.is_correct() for tile in self._tiles)
        self._locked = self._completed
        if self._locked:
            self._selected_tile = None

    def scramble(self, transformations):
        """Apply a prepared batch without counting it as player moves.

        Call once on a fresh, solved board. The image-processing component
        chooses random transformations and their count. No tile is targeted
        twice in this batch, as required by the marking rubric.
        """
        if self._history or self._moves or not self._completed:
            raise RuntimeError("Scramble a fresh board, or call solve() first.")
        transformations = list(transformations)
        if not transformations:
            raise ValueError("Supply at least one scramble transformation.")
        targeted = set()
        for transformation in transformations:
            self._check_transformation(transformation)
            for tile in transformation.tiles:
                if tile in targeted:
                    raise ValueError("A scramble must not target a tile twice.")
                targeted.add(tile)
        try:
            for transformation in transformations:
                transformation.apply()  # Polymorphism: the same call for each type.
                self._history.append(transformation)
        except Exception:
            for transformation in reversed(self._history):
                transformation.undo()
            self._history.clear()
            raise
        self._selected_tile = None
        self._active_hint = None
        self._hints_used = 0
        self._refresh_completion()

    def execute(self, transformation):
        """Apply any Transformation subclass and count exactly one player move."""
        if self._locked:
            return False
        self._check_transformation(transformation)
        transformation.apply()
        self._history.append(transformation)
        self._moves += 1
        self._selected_tile = None
        self._active_hint = None
        self._refresh_completion()
        return True

    def select_tile(self, position):
        """First click selects, same click deselects, second tile click swaps."""
        if self._locked:
            return False
        tile = self.get_tile_at(position)
        if tile is None:
            return False
        if self._selected_tile is None:
            self._selected_tile = tile
        elif tile is self._selected_tile:
            self._selected_tile = None
        else:
            return self.execute(SwapTransformation(self._selected_tile, tile))
        return True

    def rotate_tile(self, position, angle=90):
        if self._locked:
            return False
        tile = self.get_tile_at(position)
        if tile is None:
            return False
        return self.execute(RotateTransformation(tile, angle))

    def flip_tile(self, position, axis="horizontal"):
        if self._locked:
            return False
        tile = self.get_tile_at(position)
        if tile is None:
            return False
        return self.execute(FlipTransformation(tile, axis))

    def request_hint(self):
        """Mark an incorrect tile and its home; a move clears the hint."""
        if not self.can_hint:
            return None
        tile = choice(self.incorrect_tiles)
        self._active_hint = (tile.current_position, tile.original_position)
        self._hints_used += 1
        return self._active_hint

    def solve(self):
        """Undo moves and scrambling, clear counters, and lock the solved board."""
        for transformation in reversed(self._history):
            transformation.undo()
        self._history.clear()
        # Also support tiles supplied with an initial, non-default orientation.
        for tile in self._tiles:
            tile._reset()
        self._moves = 0
        self._hints_used = 0
        self._selected_tile = None
        self._active_hint = None
        self._refresh_completion()
