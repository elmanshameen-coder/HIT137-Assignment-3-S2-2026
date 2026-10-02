"""
MD Rijuan - Gameplay Controller
Student ID: s405120
HIT137 Group Assignment 3, Semester 2, 2026

This module connects Tkinter mouse/button events to the group's central
PuzzleState from puzzle_models.py.  PuzzleState remains the single source of
truth for tile positions, orientations, moves, hints and completion.
"""


class GameplayLogic:
    """Translate GUI actions into operations on one shared PuzzleState."""

    def __init__(self, puzzle_state):
        self._check_state_interface(puzzle_state)
        self.state = puzzle_state

    def set_puzzle_state(self, puzzle_state):
        """Connect the controller to a newly loaded and scrambled puzzle."""
        self._check_state_interface(puzzle_state)
        self.state = puzzle_state
        return self.status()

    def left_click(self, position):
        """Select, deselect or swap a tile after a normal left-click."""
        position = self._normalise_position(position)
        if position is None:
            return self._result("ignored")
        if self.state.locked:
            return self._result("locked")

        clicked_tile = self.state.get_tile_at(position)
        selected_tile = self.state.selected_tile

        if clicked_tile is None:
            return self._result("ignored")
        if selected_tile is None:
            action = "select"
        elif clicked_tile is selected_tile:
            action = "deselect"
        else:
            action = "swap"

        if not self.state.select_tile(position):
            return self._result("ignored")
        return self._result(action)

    def right_click(self, position):
        """Rotate the clicked tile 90 degrees clockwise."""
        position = self._normalise_position(position)
        if position is None:
            return self._result("ignored")
        if self.state.locked:
            return self._result("locked")

        changed = self.state.rotate_tile(position, 90)
        return self._result("rotate" if changed else "ignored")

    def shift_left_click(self, position):
        """Flip the clicked tile horizontally."""
        position = self._normalise_position(position)
        if position is None:
            return self._result("ignored")
        if self.state.locked:
            return self._result("locked")

        changed = self.state.flip_tile(position, "horizontal")
        return self._result("flip" if changed else "ignored")

    def request_hint(self):
        """Request one of the maximum three hints for the current image."""
        if self.state.completed:
            return self._hint_unavailable("complete")
        if self.state.hints_used >= self.state.MAX_HINTS:
            return self._hint_unavailable("limit")

        hint = self.state.request_hint()
        if hint is None:
            return self._hint_unavailable("unavailable")

        current_position, home_position = hint
        return {
            "action": "hint",
            "current_position": current_position,
            "home_position": home_position,
            "hints_used": self.state.hints_used,
            "hints_remaining": self._hints_remaining(),
        }

    def solve(self):
        """Solve the puzzle and clear moves, selection, hint and score."""
        self.state.solve()
        return self._result("solve")

    def is_position_correct(self, position):
        """Return True when a position contains a correctly oriented tile."""
        position = self._normalise_position(position)
        if position is None:
            return False
        tile = self.state.get_tile_at(position)
        return tile is not None and tile.is_correct()

    def incorrect_positions(self):
        """Return the current positions of all unfinished tiles."""
        return tuple(tile.current_position for tile in self.state.incorrect_tiles)

    def status(self):
        """Return all values normally needed by the Tkinter GUI."""
        selected_tile = self.state.selected_tile
        selected_position = None
        if selected_tile is not None:
            selected_position = selected_tile.current_position

        return {
            "moves": self.state.moves,
            "tiles_left": self.state.incorrect_count,
            "selected_position": selected_position,
            "hints_used": self.state.hints_used,
            "hints_remaining": self._hints_remaining(),
            "active_hint": self.state.active_hint,
            "can_hint": self.state.can_hint,
            "game_complete": self.state.completed,
            "input_locked": self.state.locked,
        }

    def _result(self, action):
        """Build one consistent result dictionary for the GUI."""
        result = self.status()
        result["action"] = action
        return result

    def _hint_unavailable(self, reason):
        return {
            "action": "hint_unavailable",
            "reason": reason,
            "hints_used": self.state.hints_used,
            "hints_remaining": self._hints_remaining(),
        }

    def _hints_remaining(self):
        return max(0, self.state.MAX_HINTS - self.state.hints_used)

    def _normalise_position(self, position):
        """Accept a linear tile number or a (row, column) GUI position."""
        grid_size = self.state.grid_size

        if type(position) is int:
            if position < 0 or position >= grid_size * grid_size:
                return None
            return divmod(position, grid_size)

        if (not isinstance(position, (tuple, list)) or len(position) != 2
                or any(type(number) is not int for number in position)):
            return None

        row, column = position
        if row < 0 or column < 0 or row >= grid_size or column >= grid_size:
            return None
        return (row, column)

    @staticmethod
    def _check_state_interface(puzzle_state):
        """Fail early if the wrong model object is supplied."""
        required_methods = (
            "get_tile_at",
            "select_tile",
            "rotate_tile",
            "flip_tile",
            "request_hint",
            "solve",
        )
        required_values = (
            "grid_size",
            "selected_tile",
            "moves",
            "hints_used",
            "active_hint",
            "completed",
            "locked",
            "incorrect_tiles",
            "incorrect_count",
            "can_hint",
            "MAX_HINTS",
        )

        for name in required_methods:
            if not callable(getattr(puzzle_state, name, None)):
                raise TypeError("PuzzleState is missing method: " + name)
        for name in required_values:
            if not hasattr(puzzle_state, name):
                raise TypeError("PuzzleState is missing value: " + name)
