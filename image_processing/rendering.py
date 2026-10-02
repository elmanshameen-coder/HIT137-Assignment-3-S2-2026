# HIT137 Group Assignment 3 | Semester 2, 2026
# Allocated student: Redwan Rahman Rupom | Student ID: 397409
# Component: OpenCV Image Processing
# AI-assisted preparation; see docs/AI_ASSISTANCE.md.

"""Non-destructive grid/overlay drawing and explicit BGR-to-RGB conversion."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .errors import ConfigurationError
from .model import ImageArray, PuzzleBoard, validate_bgr, validate_grid, validate_index


@dataclass(frozen=True)
class OverlayState:
    """Optional GUI-supplied state. Hint limits/lifetime remain GUI duties.

    hint_index is the CURRENT position of an incorrect tile. Its home on the
    reference image is looked up from the board; it is not assumed to be the
    same index. Additional overlays default OFF in the Task 2 preview.
    """

    selected_index: int | None = None
    hint_index: int | None = None
    show_correct_ticks: bool = False


def bgr_to_rgb(image: ImageArray) -> ImageArray:
    """Return a new contiguous RGB uint8 array, suitable for PIL.Image.fromarray."""
    validate_bgr(image)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def draw_faint_grid(image_bgr: ImageArray, grid_size: int) -> ImageArray:
    """Return a display copy; NEVER burn grid lines into the board's tiles."""
    validate_grid(grid_size)
    validate_bgr(image_bgr)
    height, width = image_bgr.shape[:2]
    if width % grid_size or height % grid_size:
        raise ConfigurationError("Grid lines require evenly divisible dimensions.")
    mask = np.zeros((height, width), dtype=np.uint8)
    for boundary in range(1, grid_size):
        x, y = boundary * width // grid_size, boundary * height // grid_size
        cv2.line(mask, (x, 0), (x, height - 1), 255, 1)
        cv2.line(mask, (0, y), (width - 1, y), 255, 1)
    # Lighten dark boundary pixels and darken light ones. A fixed grey grid
    # would disappear completely on an image of that same grey colour.
    boundary_pixels = mask > 0
    luminance = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    overlay = image_bgr.copy()
    overlay[boundary_pixels] = np.where(luminance[boundary_pixels, None] >= 128, 0, 255)
    return cv2.addWeighted(image_bgr, 0.75, overlay, 0.25, 0)


def _origin(board: PuzzleBoard, index: int) -> tuple[int, int]:
    row, column = divmod(index, board.grid_size)
    return column * board.tile_size, row * board.tile_size


def _circle(image: ImageArray, board: PuzzleBoard, index: int) -> None:
    x, y = _origin(board, index)
    size = board.tile_size
    radius = max(1, size // 4)
    thickness = max(1, min(3, size // 20))
    roi = image[y : y + size, x : x + size]
    if size < 5:
        roi[:] = (255, 0, 0)  # A sub-five-pixel tile cannot contain a legible circle.
    else:
        cv2.circle(roi, (size // 2, size // 2), radius, (255, 0, 0), thickness)


def render_pair(
    board: PuzzleBoard,
    *,
    show_grid: bool = True,
    overlays: OverlayState | None = None,
) -> tuple[ImageArray, ImageArray]:
    """Return (original_rgb, transformed_rgb) with identical dimensions.

    Default: untouched reference at left, faint grid on the puzzle at right.
    The return arrays are copies. Repeated redraws never accumulate grid lines.
    """
    state = overlays or OverlayState()
    for index in (state.selected_index, state.hint_index):
        if index is not None:
            validate_index(index, board.tile_count)
    if state.hint_index is not None and state.hint_index not in board.incorrect_indices:
        raise ConfigurationError("A hint must identify a currently incorrect tile.")

    original = board.original_bgr
    transformed = board.reassemble_bgr()
    if show_grid:
        transformed = draw_faint_grid(transformed, board.grid_size)
    size = board.tile_size
    if state.show_correct_ticks:
        for tile in board.tile_states:
            if not tile.is_correct:
                continue
            x, y = _origin(board, tile.current_index)
            # Clip to each tile, including valid images with extremely small tiles.
            inset = max(0, size // 12)
            roi = transformed[y : y + size, x : x + size]
            points = np.array(
                [
                    (inset, min(size - 1, inset + size // 12)),
                    (min(size - 1, inset + size // 15), min(size - 1, inset + size // 6)),
                    (min(size - 1, inset + size // 5), inset),
                ], dtype=np.int32,
            )
            cv2.polylines(roi, [points], False, (0, 180, 0), max(1, min(3, size // 40)))
    if state.selected_index is not None:
        x, y = _origin(board, state.selected_index)
        cv2.rectangle(
            transformed, (x, y), (x + size - 1, y + size - 1),
            (0, 190, 255), max(1, min(3, size // 20)),
        )
    if state.hint_index is not None:
        home_index = board.tile_states[state.hint_index].original_index
        _circle(transformed, board, state.hint_index)
        _circle(original, board, home_index)
    return bgr_to_rgb(original), bgr_to_rgb(transformed)
