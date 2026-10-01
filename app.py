"""Tkinter desktop application for HIT137 Group Assignment 3.

Contributor: Shameen Ahmed Elman
Student ID: s403447
Contribution: Tkinter GUI, interaction mapping, integration and error handling.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from game_logic import ActionResult, PuzzleGame
from image_processor import ImageLoadError, ImageProcessor


class PuzzleApp:
    """Main GUI that connects the player to the puzzle game controller."""

    CANVAS_SIZE = 464
    BACKGROUND = "#eef2f7"
    PANEL = "#ffffff"
    NAVY = "#17324d"
    BLUE = "#2563eb"
    MUTED = "#5f6f82"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.game = PuzzleGame(ImageProcessor(maximum_side=450))
        self._original_photo: ImageTk.PhotoImage | None = None
        self._board_photo: ImageTk.PhotoImage | None = None
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

    def _configure_window(self) -> None:
        self.root.title("Image Restoration Puzzle - HIT137")
        self.root.geometry("1080x730")
        self.root.minsize(1000, 690)
        self.root.configure(bg=self.BACKGROUND)

    def _configure_styles(self) -> None:
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

    def _build_interface(self) -> None:
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
        transformed_panel = ttk.Frame(image_area, style="Panel.TFrame", padding=10)
        transformed_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ttk.Label(
            original_panel,
            text="Original - reference only",
            style="PanelTitle.TLabel",
        ).pack(pady=(0, 7))
        ttk.Label(
            transformed_panel,
            text="Puzzle - interactive",
            style="PanelTitle.TLabel",
        ).pack(pady=(0, 7))

        self.original_canvas = tk.Canvas(
            original_panel,
            width=self.CANVAS_SIZE,
            height=self.CANVAS_SIZE,
            bg="#e6ebf1",
            highlightthickness=1,
            highlightbackground="#c9d3df",
            cursor="arrow",
        )
        self.original_canvas.pack(expand=True)
        self.board_canvas = tk.Canvas(
            transformed_panel,
            width=self.CANVAS_SIZE,
            height=self.CANVAS_SIZE,
            bg="#e6ebf1",
            highlightthickness=1,
            highlightbackground="#c9d3df",
            cursor="hand2",
        )
        self.board_canvas.pack(expand=True)

        self._draw_placeholder(
            self.original_canvas,
            "Original image will appear here",
        )
        self._draw_placeholder(
            self.board_canvas,
            "Transformed puzzle will appear here",
        )

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

    def _bind_controls(self) -> None:
        self.board_canvas.bind("<Button-1>", self._on_left_click)
        self.board_canvas.bind("<Shift-Button-1>", self._on_shift_left_click)
        self.board_canvas.bind("<Button-2>", self._on_right_click)
        self.board_canvas.bind("<Button-3>", self._on_right_click)
        self.board_canvas.bind("<Control-Button-1>", self._on_right_click)

    def load_image(self) -> None:
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
            self.status_text.set(
                "Image selection cancelled. The current round is unchanged."
            )
            return

        grid_size = int(self.grid_choice.get().split()[0])
        try:
            self.game.load_image(path, grid_size)
        except (ImageLoadError, OSError, ValueError) as error:
            messagebox.showerror("Unable to load image", str(error), parent=self.root)
            self.status_text.set("The selected file could not be loaded.")
            return
        except Exception as error:  # noqa: BLE001 - final defensive GUI boundary
            messagebox.showerror(
                "Unexpected image error",
                f"The image could not be prepared.\n\n{error}",
                parent=self.root,
            )
            self.status_text.set("An unexpected image error was handled safely.")
            return

        self._completion_announced = False
        self.status_text.set(
            f"Loaded {Path(path).name} as a {grid_size} x {grid_size} puzzle."
        )
        self._render_images()
        self._refresh_controls()

    def show_hint(self) -> None:
        hint = self.game.request_hint()
        if hint is None:
            if self.game.loaded and self.game.hints_remaining == 0:
                self.status_text.set("All three hints have been used for this image.")
            return
        current, home = hint
        self.status_text.set(
            f"Hint: blue circles show tile {current + 1} and home position {home + 1}."
        )
        self._render_images()
        self._refresh_controls()

    def solve_puzzle(self) -> None:
        result = self.game.solve()
        if not result.changed:
            messagebox.showinfo("Solve", result.message, parent=self.root)
            return
        self._completion_announced = True
        self.status_text.set(result.message)
        self._render_images()
        self._refresh_controls()
        messagebox.showinfo(
            "Puzzle solved",
            "The image has been restored. Load another image to continue playing.",
            parent=self.root,
        )

    def _on_left_click(self, event: tk.Event) -> str:
        board_index = self._board_index_from_event(event)
        if board_index is None:
            return "break"
        self._process_action(self.game.left_click(board_index))
        return "break"

    def _on_shift_left_click(self, event: tk.Event) -> str:
        board_index = self._board_index_from_event(event)
        if board_index is None:
            return "break"
        self._process_action(self.game.shift_left_click(board_index))
        return "break"

    def _on_right_click(self, event: tk.Event) -> str:
        board_index = self._board_index_from_event(event)
        if board_index is None:
            return "break"
        self._process_action(self.game.right_click(board_index))
        return "break"

    def _process_action(self, result: ActionResult) -> None:
        if result.message:
            self.status_text.set(result.message)
        if result.changed:
            self._render_images()
            self._refresh_controls()
        if result.completed and not self._completion_announced:
            self._completion_announced = True
            messagebox.showinfo(
                "Puzzle complete",
                (
                    "Congratulations! You restored the image in "
                    f"{self.game.moves} moves and {self._format_time(self.game.elapsed_seconds)}.\n\n"
                    "Load another image to continue playing."
                ),
                parent=self.root,
            )

    def _board_index_from_event(self, event: tk.Event) -> int | None:
        if not self.game.loaded or self.game.is_locked:
            return None
        origin_x, origin_y = self._board_origin
        local_x = int(event.x) - origin_x
        local_y = int(event.y) - origin_y
        if not (0 <= local_x < self._board_side and 0 <= local_y < self._board_side):
            # Off-image clicks are intentionally ignored.
            return None
        tile_size = self._board_side // self.game.grid_size
        column = min(local_x // tile_size, self.game.grid_size - 1)
        row = min(local_y // tile_size, self.game.grid_size - 1)
        return row * self.game.grid_size + column

    def _render_images(self) -> None:
        if not self.game.loaded:
            return
        original = self.game.original_image()
        board = self.game.board_image()
        self._original_photo, _ = self._display_image(self.original_canvas, original)
        self._board_photo, self._board_origin = self._display_image(
            self.board_canvas,
            board,
        )
        self._board_side = board.shape[0]

    def _display_image(
        self,
        canvas: tk.Canvas,
        bgr_image,
    ) -> tuple[ImageTk.PhotoImage, tuple[int, int]]:
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        origin_x = (self.CANVAS_SIZE - bgr_image.shape[1]) // 2
        origin_y = (self.CANVAS_SIZE - bgr_image.shape[0]) // 2
        canvas.delete("all")
        canvas.create_image(origin_x, origin_y, image=photo, anchor=tk.NW)
        return photo, (origin_x, origin_y)

    def _draw_placeholder(self, canvas: tk.Canvas, text: str) -> None:
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

    def _refresh_controls(self) -> None:
        if not self.game.loaded:
            self.moves_text.set("Moves: 0")
            self.tiles_text.set("Tiles left: -")
            self.hints_text.set("Hints left: 3")
            self.hint_button.configure(state=tk.DISABLED)
            self.solve_button.configure(state=tk.DISABLED)
            return

        self.moves_text.set(f"Moves: {self.game.moves}")
        self.tiles_text.set(f"Tiles left: {self.game.tiles_left}")
        self.hints_text.set(f"Hints left: {self.game.hints_remaining}")
        hint_state = (
            tk.NORMAL
            if not self.game.is_locked and self.game.hints_remaining > 0
            else tk.DISABLED
        )
        self.hint_button.configure(state=hint_state)
        self.solve_button.configure(
            state=tk.NORMAL if not self.game.is_locked else tk.DISABLED
        )

    def _update_timer(self) -> None:
        self.timer_text.set(f"Time: {self._format_time(self.game.elapsed_seconds)}")
        self.root.after(500, self._update_timer)

    @staticmethod
    def _format_time(total_seconds: int) -> str:
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


def main() -> None:
    root = tk.Tk()
    PuzzleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
