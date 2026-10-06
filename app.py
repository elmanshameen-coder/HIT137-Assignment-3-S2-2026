"""Final Tkinter application for HIT137 Group Assignment 3.

Contributor: Shameen Ahmed Elman
Student ID: s403447
Contribution: Tkinter GUI, event mapping, integration and error handling.

This file integrates:
- Arshad's PuzzleState/Tile OOP model from puzzle_models.py
- Rupom's OpenCV preparation and scramble planner from image_processing/
- Rijuan's gameplay controller from rijuan_gameplay_logic.py
"""

from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from image_processing import (
    Flip,
    ImageProcessingError,
    ImageProcessor,
    Rotate,
    ScramblePlanner,
    Swap,
    bgr_to_rgb,
    draw_faint_grid,
)
from puzzle_models import (
    FlipTransformation,
    PuzzleState,
    RotateTransformation,
    SwapTransformation,
    Tile,
)
from rijuan_gameplay_logic import GameplayLogic


def create_puzzle_state(prepared_bgr, grid_size, scramble_plan):
    """Create Arshad's PuzzleState from Rupom's prepared image and plan."""
    height, width = prepared_bgr.shape[:2]
    if height != width or width % grid_size:
        raise ValueError("Prepared image must be square and grid-divisible.")

    tile_size = width // grid_size
    tiles = []
    for row in range(grid_size):
        for column in range(grid_size):
            y1, y2 = row * tile_size, (row + 1) * tile_size
            x1, x2 = column * tile_size, (column + 1) * tile_size
            tiles.append(
                Tile(
                    (row, column),
                    prepared_bgr[y1:y2, x1:x2].copy(),
                )
            )

    state = PuzzleState(tiles, grid_size)
    model_transformations = []

    for action in scramble_plan:
        if isinstance(action, Swap):
            model_transformations.append(
                SwapTransformation(tiles[action.first], tiles[action.second])
            )
        elif isinstance(action, Rotate):
            model_transformations.append(
                RotateTransformation(tiles[action.target], action.degrees)
            )
        elif isinstance(action, Flip):
            model_transformations.append(
                FlipTransformation(tiles[action.target], action.direction)
            )
        else:
            raise TypeError("Unsupported scramble transformation.")

    state.scramble(model_transformations)
    return state


def reassemble_state_bgr(state):
    """Reassemble the central PuzzleState into one clean OpenCV BGR image."""
    rows = []
    for row in range(state.grid_size):
        row_images = []
        for column in range(state.grid_size):
            tile = state.get_tile_at((row, column))
            if tile is None:
                raise RuntimeError("PuzzleState is missing a grid tile.")
            row_images.append(tile.get_display_image())
        rows.append(cv2.hconcat(row_images))
    return cv2.vconcat(rows)


def _tile_origin(position, tile_size):
    row, column = position
    return column * tile_size, row * tile_size


def _draw_hint_circle(image, position, tile_size):
    x, y = _tile_origin(position, tile_size)
    centre = (x + tile_size // 2, y + tile_size // 2)
    radius = max(4, tile_size // 5)
    thickness = max(2, min(5, tile_size // 20))
    cv2.circle(image, centre, radius + 2, (255, 255, 255), thickness + 2)
    cv2.circle(image, centre, radius, (255, 80, 20), thickness)


def render_state_rgb(original_bgr, state):
    """Return reference/puzzle RGB arrays with all required overlays."""
    original = original_bgr.copy()
    transformed = draw_faint_grid(reassemble_state_bgr(state), state.grid_size)
    tile_size = transformed.shape[0] // state.grid_size

    for tile in state.tiles:
        if not tile.is_correct():
            continue
        x, y = _tile_origin(tile.current_position, tile_size)
        scale = max(8, tile_size // 7)
        end = (x + tile_size - 7, y + 7)
        middle = (end[0] - scale // 2, end[1] + scale)
        start = (middle[0] - scale // 2, middle[1] - scale // 3)
        cv2.line(transformed, start, middle, (20, 55, 20), 6, cv2.LINE_AA)
        cv2.line(transformed, middle, end, (20, 55, 20), 6, cv2.LINE_AA)
        cv2.line(transformed, start, middle, (45, 225, 75), 3, cv2.LINE_AA)
        cv2.line(transformed, middle, end, (45, 225, 75), 3, cv2.LINE_AA)

    if state.selected_tile is not None:
        x, y = _tile_origin(state.selected_tile.current_position, tile_size)
        cv2.rectangle(
            transformed,
            (x + 2, y + 2),
            (x + tile_size - 3, y + tile_size - 3),
            (0, 145, 255),
            max(2, min(5, tile_size // 18)),
        )

    if state.active_hint is not None:
        current_position, home_position = state.active_hint
        _draw_hint_circle(transformed, current_position, tile_size)
        _draw_hint_circle(original, home_position, tile_size)

    return bgr_to_rgb(original), bgr_to_rgb(transformed)


class PuzzleSession:
    """Own one application round while keeping PuzzleState authoritative."""

    def __init__(self, max_size=(450, 450), fit_mode="pad", seed=None):
        self.processor = ImageProcessor(max_size=max_size, fit_mode=fit_mode)
        self.planner = ScramblePlanner(seed)
        self.state = None
        self.game = None
        self.original_bgr = None
        self.preparation_info = None
        self.scramble_plan = ()
        self.started_at = None
        self.finished_at = None

    @property
    def loaded(self):
        return self.state is not None and self.game is not None

    @property
    def elapsed_seconds(self):
        if self.started_at is None:
            return 0
        end = self.finished_at if self.finished_at is not None else time.monotonic()
        return max(0, int(end - self.started_at))

    def load_image(self, path, grid_size):
        """Safely load a supported image; commit only after full preparation."""
        image_bgr = self.processor.read_bgr(path)
        self.load_array(image_bgr, grid_size)

    def load_array(self, image_bgr, grid_size):
        """Start a new round from an in-memory BGR image."""
        prepared, info = self.processor.prepare(image_bgr, grid_size)
        plan = self.planner.generate(grid_size)
        state = create_puzzle_state(prepared, grid_size, plan)
        game = GameplayLogic(state)

        self.original_bgr = prepared.copy()
        self.preparation_info = info
        self.scramble_plan = plan
        self.state = state
        self.game = game
        self.started_at = time.monotonic()
        self.finished_at = None

    def left_click(self, position):
        return self._complete_if_needed(self.game.left_click(position))

    def right_click(self, position):
        return self._complete_if_needed(self.game.right_click(position))

    def shift_left_click(self, position):
        return self._complete_if_needed(self.game.shift_left_click(position))

    def request_hint(self):
        return self.game.request_hint()

    def solve(self):
        result = self.game.solve()
        self.finished_at = time.monotonic()
        return result

    def status(self):
        if not self.loaded:
            return {
                "moves": 0,
                "tiles_left": None,
                "hints_remaining": 3,
                "can_hint": False,
                "game_complete": False,
                "input_locked": True,
            }
        return self.game.status()

    def render_rgb(self):
        if not self.loaded:
            raise RuntimeError("Load an image before rendering.")
        return render_state_rgb(self.original_bgr, self.state)

    def _complete_if_needed(self, result):
        if result["game_complete"] and self.finished_at is None:
            self.finished_at = time.monotonic()
        return result


class PuzzleApp:
    """Tkinter interface for the fully integrated image puzzle."""

    CANVAS_SIZE = 464
    BACKGROUND = "#eef2f7"
    PANEL = "#ffffff"
    NAVY = "#17324d"
    BLUE = "#2563eb"
    MUTED = "#5f6f82"

    def __init__(self, root):
        self.root = root
        self.session = PuzzleSession(max_size=(450, 450), fit_mode="pad")
        self._original_photo = None
        self._board_photo = None
        self._board_origin = (0, 0)
        self._board_side = 0
        self._completion_announced = False

        self.grid_choice = tk.StringVar(value="3 x 3")
        self.moves_text = tk.StringVar(value="Moves: 0")
        self.tiles_text = tk.StringVar(value="Tiles left: -")
        self.hints_text = tk.StringVar(value="Hints left: 3")
        self.timer_text = tk.StringVar(value="Time: 00:00")
        self.status_text = tk.StringVar(
            value="Choose a grid size, then load a JPG, PNG or BMP image."
        )

        self._configure_window()
        self._configure_styles()
        self._build_interface()
        self._bind_controls()
        self._refresh_controls()
        self._update_timer()

    def _configure_window(self):
        self.root.title("Image Restoration Puzzle - HIT137")
        self.root.geometry("1080x730")
        self.root.minsize(1000, 690)
        self.root.configure(bg=self.BACKGROUND)

    def _configure_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=self.BACKGROUND)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure(
            "Title.TLabel",
            background=self.BACKGROUND,
            foreground=self.NAVY,
            font=("Helvetica", 23, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.BACKGROUND,
            foreground=self.MUTED,
            font=("Helvetica", 10),
        )
        style.configure(
            "PanelTitle.TLabel",
            background=self.PANEL,
            foreground=self.NAVY,
            font=("Helvetica", 12, "bold"),
        )
        style.configure(
            "Stat.TLabel",
            background=self.PANEL,
            foreground=self.NAVY,
            font=("Helvetica", 11, "bold"),
            padding=(12, 7),
        )
        style.configure(
            "Primary.TButton",
            background=self.BLUE,
            foreground="white",
            font=("Helvetica", 10, "bold"),
            padding=(14, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1d4ed8"), ("disabled", "#9ab4e6")],
        )
        style.configure("Action.TButton", font=("Helvetica", 10), padding=(13, 8))
        style.configure(
            "Status.TLabel",
            background="#dfe8f5",
            foreground=self.NAVY,
            font=("Helvetica", 10),
            padding=(12, 9),
        )

    def _build_interface(self):
        outer = ttk.Frame(self.root, padding=(18, 14))
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Image Restoration Puzzle", style="Title.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            header,
            text="Restore every tile using swaps, rotations and flips.",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        controls = ttk.Frame(outer, style="Panel.TFrame", padding=(14, 10))
        controls.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(controls, text="Grid size", style="PanelTitle.TLabel").pack(
            side=tk.LEFT, padx=(0, 8)
        )
        self.grid_box = ttk.Combobox(
            controls,
            textvariable=self.grid_choice,
            values=("3 x 3", "4 x 4", "5 x 5"),
            state="readonly",
            width=8,
        )
        self.grid_box.pack(side=tk.LEFT, padx=(0, 12))
        self.load_button = ttk.Button(
            controls,
            text="Load Image",
            command=self.load_image,
            style="Primary.TButton",
        )
        self.load_button.pack(side=tk.LEFT, padx=(0, 8))
        self.hint_button = ttk.Button(
            controls,
            text="Hint",
            command=self.show_hint,
            style="Action.TButton",
        )
        self.hint_button.pack(side=tk.LEFT, padx=4)
        self.solve_button = ttk.Button(
            controls,
            text="Solve",
            command=self.solve_puzzle,
            style="Action.TButton",
        )
        self.solve_button.pack(side=tk.LEFT, padx=4)

        stat_frame = ttk.Frame(controls, style="Panel.TFrame")
        stat_frame.pack(side=tk.RIGHT)
        for variable in (
            self.moves_text,
            self.tiles_text,
            self.hints_text,
            self.timer_text,
        ):
            ttk.Label(stat_frame, textvariable=variable, style="Stat.TLabel").pack(
                side=tk.LEFT, padx=2
            )

        image_area = ttk.Frame(outer)
        image_area.pack(fill=tk.BOTH, expand=True)
        image_area.columnconfigure(0, weight=1)
        image_area.columnconfigure(1, weight=1)

        original_panel = ttk.Frame(image_area, style="Panel.TFrame", padding=10)
        original_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        puzzle_panel = ttk.Frame(image_area, style="Panel.TFrame", padding=10)
        puzzle_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ttk.Label(
            original_panel,
            text="Original - reference only",
            style="PanelTitle.TLabel",
        ).pack(pady=(0, 7))
        ttk.Label(
            puzzle_panel,
            text="Puzzle - interactive",
            style="PanelTitle.TLabel",
        ).pack(pady=(0, 7))

        self.original_canvas = self._make_canvas(original_panel, "arrow")
        self.board_canvas = self._make_canvas(puzzle_panel, "hand2")
        self._draw_placeholder(self.original_canvas, "Original image will appear here")
        self._draw_placeholder(self.board_canvas, "Transformed puzzle will appear here")

        ttk.Label(outer, textvariable=self.status_text, style="Status.TLabel").pack(
            fill=tk.X, pady=(10, 0)
        )
        ttk.Label(
            outer,
            text=(
                "Controls: left-click selects/swaps | right-click rotates | "
                "Shift + left-click flips horizontally"
            ),
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(7, 0))

    def _make_canvas(self, parent, cursor):
        canvas = tk.Canvas(
            parent,
            width=self.CANVAS_SIZE,
            height=self.CANVAS_SIZE,
            bg="#e6ebf1",
            highlightthickness=1,
            highlightbackground="#c9d3df",
            cursor=cursor,
        )
        canvas.pack(expand=True)
        return canvas

    def _bind_controls(self):
        self.board_canvas.bind("<Button-1>", self._on_left_click)
        self.board_canvas.bind("<Shift-Button-1>", self._on_shift_left_click)
        self.board_canvas.bind("<Button-2>", self._on_right_click)
        self.board_canvas.bind("<Button-3>", self._on_right_click)
        self.board_canvas.bind("<Control-Button-1>", self._on_right_click)

    def load_image(self):
        path = filedialog.askopenfilename(
            title="Choose a puzzle image",
            filetypes=(
                ("Supported images", "*.jpg *.jpeg *.png *.bmp"),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("Bitmap", "*.bmp"),
                ("All files", "*.*"),
            ),
        )
        if not path:
            self.status_text.set("Selection cancelled. The current round is unchanged.")
            return

        grid_size = int(self.grid_choice.get().split()[0])
        try:
            self.session.load_image(path, grid_size)
        except (ImageProcessingError, OSError, ValueError, TypeError) as error:
            messagebox.showerror("Unable to load image", str(error), parent=self.root)
            self.status_text.set("The selected file could not be loaded.")
            return

        self._completion_announced = False
        self.status_text.set(
            f"Loaded {Path(path).name} as a {grid_size} x {grid_size} puzzle."
        )
        self._render_images()
        self._refresh_controls()

    def show_hint(self):
        if not self.session.loaded:
            return
        result = self.session.request_hint()
        if result["action"] != "hint":
            if result.get("reason") == "limit":
                self.status_text.set("All three hints have been used for this image.")
            return

        current = result["current_position"]
        home = result["home_position"]
        self.status_text.set(
            "Hint: blue circles mark puzzle tile "
            f"({current[0] + 1}, {current[1] + 1}) and home "
            f"({home[0] + 1}, {home[1] + 1})."
        )
        self._render_images()
        self._refresh_controls()

    def solve_puzzle(self):
        if not self.session.loaded:
            return
        self.session.solve()
        self._completion_announced = True
        self.status_text.set("Puzzle solved automatically. Load another image to play again.")
        self._render_images()
        self._refresh_controls()
        messagebox.showinfo(
            "Puzzle solved",
            "The image has been restored and the move score cleared.",
            parent=self.root,
        )

    def _on_left_click(self, event):
        position = self._position_from_event(event)
        if position is not None:
            self._process_action(self.session.left_click(position))
        return "break"

    def _on_shift_left_click(self, event):
        position = self._position_from_event(event)
        if position is not None:
            self._process_action(self.session.shift_left_click(position))
        return "break"

    def _on_right_click(self, event):
        position = self._position_from_event(event)
        if position is not None:
            self._process_action(self.session.right_click(position))
        return "break"

    def _position_from_event(self, event):
        if not self.session.loaded or self.session.status()["input_locked"]:
            return None
        origin_x, origin_y = self._board_origin
        local_x = int(event.x) - origin_x
        local_y = int(event.y) - origin_y
        if not (0 <= local_x < self._board_side and 0 <= local_y < self._board_side):
            return None
        grid_size = self.session.state.grid_size
        tile_size = self._board_side // grid_size
        return (local_y // tile_size, local_x // tile_size)

    def _process_action(self, result):
        messages = {
            "select": "Tile selected. Choose another tile to swap.",
            "deselect": "Tile deselected.",
            "swap": "Tiles swapped.",
            "rotate": "Tile rotated 90 degrees clockwise.",
            "flip": "Tile flipped horizontally.",
            "locked": "Puzzle input is locked. Load another image to continue.",
        }
        self.status_text.set(messages.get(result["action"], "Action completed."))
        if result["action"] not in ("ignored", "locked"):
            self._render_images()
            self._refresh_controls()

        if result["game_complete"] and not self._completion_announced:
            self._completion_announced = True
            messagebox.showinfo(
                "Puzzle complete",
                (
                    "Congratulations! You restored the image in "
                    f"{result['moves']} moves and "
                    f"{self._format_time(self.session.elapsed_seconds)}.\n\n"
                    "Load another image to continue playing."
                ),
                parent=self.root,
            )

    def _render_images(self):
        original_rgb, board_rgb = self.session.render_rgb()
        self._original_photo, _ = self._display_rgb(self.original_canvas, original_rgb)
        self._board_photo, self._board_origin = self._display_rgb(
            self.board_canvas, board_rgb
        )
        self._board_side = board_rgb.shape[0]

    def _display_rgb(self, canvas, rgb_image):
        photo = ImageTk.PhotoImage(Image.fromarray(rgb_image))
        origin_x = (self.CANVAS_SIZE - rgb_image.shape[1]) // 2
        origin_y = (self.CANVAS_SIZE - rgb_image.shape[0]) // 2
        canvas.delete("all")
        canvas.create_image(origin_x, origin_y, image=photo, anchor=tk.NW)
        return photo, (origin_x, origin_y)

    def _draw_placeholder(self, canvas, text):
        canvas.delete("all")
        canvas.create_text(
            self.CANVAS_SIZE // 2,
            self.CANVAS_SIZE // 2,
            text=text,
            fill=self.MUTED,
            font=("Helvetica", 11),
            width=250,
            justify=tk.CENTER,
        )

    def _refresh_controls(self):
        status = self.session.status()
        self.moves_text.set(f"Moves: {status['moves']}")
        tiles = "-" if status["tiles_left"] is None else status["tiles_left"]
        self.tiles_text.set(f"Tiles left: {tiles}")
        self.hints_text.set(f"Hints left: {status['hints_remaining']}")
        self.hint_button.configure(
            state=tk.NORMAL if status["can_hint"] else tk.DISABLED
        )
        self.solve_button.configure(
            state=(
                tk.NORMAL
                if self.session.loaded and not status["input_locked"]
                else tk.DISABLED
            )
        )

    def _update_timer(self):
        self.timer_text.set(f"Time: {self._format_time(self.session.elapsed_seconds)}")
        self.root.after(500, self._update_timer)

    @staticmethod
    def _format_time(total_seconds):
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


def main():
    root = tk.Tk()
    PuzzleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
