# HIT137 Group Assignment 3 | Semester 2, 2026
# Allocated student: Redwan Rahman Rupom | Student ID: 397409
# Component: OpenCV Image Processing
# AI-assisted preparation; see docs/AI_ASSISTANCE.md.

"""OpenCV file loading and aspect-preserving preparation of square tiles."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from .errors import ConfigurationError, ImageLoadError
from .model import ImageArray, PreparationInfo, PuzzleBoard, validate_bgr, validate_grid
from .transformations import ScramblePlanner

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp"})


class ImageProcessor:
    """Create independent puzzle rounds. Failed loads do not alter older boards.

    max_size is the space available for ONE image, not the whole application.
    'pad' preserves all visible content; 'crop' takes a centred square after an
    aspect-preserving resize. Square tiles make 90-degree rotation lossless.
    """

    def __init__(
        self,
        max_size: tuple[int, int] = (500, 500),
        fit_mode: str = "pad",
        seed: int | None = None,
    ) -> None:
        if (
            not isinstance(max_size, tuple)
            or len(max_size) != 2
            or any(type(value) is not int or value < 5 for value in max_size)
        ):
            raise ConfigurationError("max_size must contain two integers of at least 5 pixels.")
        if fit_mode not in ("pad", "crop"):
            raise ConfigurationError("fit_mode must be 'pad' or 'crop'.")
        self._max_size = max_size
        self._fit_mode = fit_mode
        self._planner = ScramblePlanner(seed)

    @staticmethod
    def read_bgr(path: str | Path) -> ImageArray:
        """Decode using OpenCV; reading bytes first supports Unicode filenames.

        IMREAD_COLOR produces eight-bit BGR for colour or greyscale input.
        Transparency is discarded by this documented colour-load policy.
        A cancelled Tk file dialog should be handled by the GUI before calling.
        """
        if not isinstance(path, (str, Path)) or not str(path).strip():
            raise ImageLoadError("No image file was selected.")
        image_path = Path(path).expanduser()
        if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ImageLoadError("Choose a JPG, JPEG, PNG, or BMP image.")
        try:
            content = image_path.read_bytes()
        except (OSError, ValueError) as error:
            raise ImageLoadError(f"Cannot read image: {image_path.name}") from error
        if not content:
            raise ImageLoadError("The selected image file is empty.")
        try:
            image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        except cv2.error as error:
            raise ImageLoadError("The image is damaged or cannot be decoded.") from error
        if image is None or image.size == 0:
            raise ImageLoadError("The file does not contain a readable image.")
        return image

    def prepare(
        self, image_bgr: ImageArray, grid_size: int = 3
    ) -> tuple[ImageArray, PreparationInfo]:
        """Resize uniformly, then pad/crop to a grid-divisible square.

        Rounding to integer pixel sizes can introduce at most half a pixel of
        error in each resized dimension. No independent horizontal/vertical
        stretch is used. Tiny inputs are padded rather than enlarged.
        """
        validate_grid(grid_size)
        validate_bgr(image_bgr)
        source_height, source_width = image_bgr.shape[:2]
        max_side = (min(self._max_size) // grid_size) * grid_size
        scale = min(1.0, max_side / max(source_width, source_height))
        width = max(1, min(max_side, round(source_width * scale)))
        height = max(1, min(max_side, round(source_height * scale)))
        if (width, height) == (source_width, source_height):
            resized = image_bgr.copy()
        else:
            resized = cv2.resize(image_bgr, (width, height), interpolation=cv2.INTER_AREA)

        if self._fit_mode == "pad":
            side = math.ceil(max(width, height) / grid_size) * grid_size
            left, top = (side - width) // 2, (side - height) // 2
            prepared = cv2.copyMakeBorder(
                resized,
                top,
                side - height - top,
                left,
                side - width - left,
                cv2.BORDER_CONSTANT,
                value=(240, 240, 240),
            )
        else:
            side = (min(width, height) // grid_size) * grid_size
            if side == 0:
                # A tiny dimension has no non-empty grid-divisible crop.
                side = grid_size
                left, top = max(0, (width - side) // 2), max(0, (height - side) // 2)
                cropped = resized[top : top + side, left : left + side]
                h, w = cropped.shape[:2]
                dx, dy = (side - w) // 2, (side - h) // 2
                prepared = cv2.copyMakeBorder(
                    cropped, dy, side - h - dy, dx, side - w - dx,
                    cv2.BORDER_CONSTANT, value=(240, 240, 240),
                )
            else:
                left, top = (width - side) // 2, (height - side) // 2
                prepared = resized[top : top + side, left : left + side].copy()
        info = PreparationInfo(
            source_size=(source_width, source_height),
            resized_size=(width, height),
            output_size=(side, side),
            fit_mode=self._fit_mode,
        )
        return np.ascontiguousarray(prepared), info

    def from_bgr(
        self, image_bgr: ImageArray, grid_size: int = 3, *, scramble: bool = True
    ) -> PuzzleBoard:
        """Prepare an already decoded BGR array and optionally scramble it."""
        prepared, info = self.prepare(image_bgr, grid_size)
        board = PuzzleBoard(prepared, grid_size, info)
        if scramble:
            plan = self._planner.generate(grid_size)
            board.apply_initial_scramble(plan)
        return board

    def load_image(
        self, path: str | Path, grid_size: int = 3, *, scramble: bool = True
    ) -> PuzzleBoard:
        """Load a fresh image round; default grid is 3 x 3."""
        validate_grid(grid_size)
        return self.from_bgr(self.read_bgr(path), grid_size, scramble=scramble)
