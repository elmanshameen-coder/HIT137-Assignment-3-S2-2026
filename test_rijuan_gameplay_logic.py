"""
Tests for MD Rijuan's GameplayLogic.
Student ID: s405120

Run either:
    python test_rijuan_gameplay_logic.py
or:
    pytest -q test_rijuan_gameplay_logic.py
"""

from puzzle_models import (
    FlipTransformation,
    PuzzleState,
    RotateTransformation,
    SwapTransformation,
    Tile,
)
from rijuan_gameplay_logic import GameplayLogic


def make_tiles(grid_size):
    """Create one solved set of tiles for a selected grid size."""
    return [
        Tile((row, column))
        for row in range(grid_size)
        for column in range(grid_size)
    ]


def make_swapped_game(grid_size):
    """Create a puzzle with the first two tiles swapped."""
    tiles = make_tiles(grid_size)
    state = PuzzleState(tiles, grid_size)
    state.scramble([SwapTransformation(tiles[0], tiles[1])])
    return state, GameplayLogic(state)


def run_selection_swap_and_completion(grid_size):
    state, game = make_swapped_game(grid_size)

    result = game.left_click((0, 0))
    assert result["action"] == "select"
    assert result["selected_position"] == (0, 0)
    assert state.moves == 0

    result = game.left_click((0, 0))
    assert result["action"] == "deselect"
    assert result["selected_position"] is None
    assert state.moves == 0

    game.left_click((0, 0))
    result = game.left_click((0, 1))

    assert result["action"] == "swap"
    assert result["moves"] == 1
    assert result["tiles_left"] == 0
    assert result["selected_position"] is None
    assert result["game_complete"] is True
    assert result["input_locked"] is True

    assert game.left_click((0, 0))["action"] == "locked"


def run_rotation(grid_size):
    tiles = make_tiles(grid_size)
    state = PuzzleState(tiles, grid_size)
    state.scramble([RotateTransformation(tiles[0], 90)])
    game = GameplayLogic(state)

    assert game.status()["tiles_left"] == 1

    game.right_click((0, 0))
    game.right_click((0, 0))
    result = game.right_click((0, 0))

    assert result["action"] == "rotate"
    assert result["moves"] == 3
    assert result["tiles_left"] == 0
    assert result["game_complete"] is True


def run_horizontal_flip(grid_size):
    tiles = make_tiles(grid_size)
    state = PuzzleState(tiles, grid_size)
    state.scramble([FlipTransformation(tiles[0], "horizontal")])
    game = GameplayLogic(state)

    assert game.status()["tiles_left"] == 1
    result = game.shift_left_click((0, 0))

    assert result["action"] == "flip"
    assert result["moves"] == 1
    assert result["tiles_left"] == 0
    assert result["game_complete"] is True


def run_hint_system(grid_size):
    state, game = make_swapped_game(grid_size)

    first_hint = game.request_hint()
    assert first_hint["action"] == "hint"
    assert first_hint["current_position"] in ((0, 0), (0, 1))
    assert first_hint["home_position"] in ((0, 0), (0, 1))
    assert game.status()["active_hint"] is not None

    game.right_click(first_hint["current_position"])
    assert game.status()["active_hint"] is None

    assert game.request_hint()["action"] == "hint"
    assert game.request_hint()["action"] == "hint"

    fourth_hint = game.request_hint()
    assert fourth_hint["action"] == "hint_unavailable"
    assert fourth_hint["reason"] == "limit"
    assert fourth_hint["hints_remaining"] == 0


def run_solve(grid_size):
    tiles = make_tiles(grid_size)
    state = PuzzleState(tiles, grid_size)
    state.scramble([
        SwapTransformation(tiles[0], tiles[-1]),
        RotateTransformation(tiles[1], 270),
    ])
    game = GameplayLogic(state)

    game.left_click((0, 0))
    game.request_hint()
    result = game.solve()

    assert result["action"] == "solve"
    assert result["moves"] == 0
    assert result["tiles_left"] == 0
    assert result["selected_position"] is None
    assert result["active_hint"] is None
    assert result["hints_used"] == 0
    assert result["game_complete"] is True
    assert result["input_locked"] is True
    assert game.right_click((0, 0))["action"] == "locked"


def run_position_and_error_handling(grid_size):
    state, game = make_swapped_game(grid_size)

    # A linear tile number is converted to (row, column).
    assert game.left_click(0)["action"] == "select"
    assert game.left_click(1)["action"] == "swap"
    assert state.completed is True

    # A fresh unsolved game ignores clicks outside the puzzle.
    state, game = make_swapped_game(grid_size)
    moves_before = state.moves

    assert game.left_click((-1, 0))["action"] == "ignored"
    assert game.right_click(grid_size * grid_size)["action"] == "ignored"
    assert game.shift_left_click("not a position")["action"] == "ignored"
    assert state.moves == moves_before


def test_all_gameplay_logic():
    """Pytest entry point with no fixture parameters."""
    for grid_size in (3, 4, 5):
        run_selection_swap_and_completion(grid_size)
        run_rotation(grid_size)
        run_horizontal_flip(grid_size)
        run_hint_system(grid_size)
        run_solve(grid_size)
        run_position_and_error_handling(grid_size)


def main():
    test_all_gameplay_logic()
    print("All Rijuan gameplay tests passed with the real PuzzleState for 3x3, 4x4 and 5x5.")


if __name__ == "__main__":
    main()
