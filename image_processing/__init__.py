# HIT137 Group Assignment 3 | Semester 2, 2026
# Allocated student: Redwan Rahman Rupom | Student ID: 397409
# Component: OpenCV Image Processing
# AI-assisted preparation; see docs/AI_ASSISTANCE.md.

"""Public API for Redwan Rahman Rupom (397409): HIT137 A3 image processing."""

from .errors import ConfigurationError, ImageLoadError, ImageProcessingError, TileOperationError
from .model import PreparationInfo, PuzzleBoard, SUPPORTED_GRIDS, TileState
from .processor import ImageProcessor
from .rendering import OverlayState, bgr_to_rgb, draw_faint_grid, render_pair
from .transformations import (
    TRANSFORMATION_COUNTS,
    Flip,
    Rotate,
    ScramblePlanner,
    Swap,
    Transformation,
)

__all__ = [
    "ConfigurationError", "Flip", "ImageLoadError", "ImageProcessingError",
    "ImageProcessor", "OverlayState", "PreparationInfo", "PuzzleBoard", "Rotate",
    "SUPPORTED_GRIDS", "ScramblePlanner", "Swap", "TRANSFORMATION_COUNTS",
    "TileOperationError", "TileState", "Transformation", "bgr_to_rgb",
    "draw_faint_grid", "render_pair",
]
