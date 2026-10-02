# HIT137 Group Assignment 3 | Semester 2, 2026
# Allocated student: Redwan Rahman Rupom | Student ID: 397409
# Component: OpenCV Image Processing
# AI-assisted preparation; see docs/AI_ASSISTANCE.md.

"""Exceptions the GUI can catch and show in a message box."""


class ImageProcessingError(ValueError):
    """Base exception for an invalid image-processing request."""


class ImageLoadError(ImageProcessingError):
    """The selected file could not be read as a supported image."""


class ConfigurationError(ImageProcessingError):
    """A grid size, image shape, or display bound is invalid."""


class TileOperationError(ImageProcessingError):
    """A tile index or transformation argument is invalid."""
