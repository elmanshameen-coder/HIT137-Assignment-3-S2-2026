MD RIJUAN - GAMEPLAY CONTROLLER
Student ID: s405120
HIT137 GROUP ASSIGNMENT 3, SEMESTER 2, 2026

1. CONTRIBUTION

I implemented the gameplay controller that connects Tkinter actions to the
group's shared PuzzleState.

The controller handles:
- left-click selection, deselection and swapping
- right-click 90-degree clockwise rotation
- Shift + left-click horizontal flipping
- GUI status values for moves and incorrect tiles
- selection, correct-tile and completion information
- a maximum of three hints per image
- clearing the active hint through the next move
- Solve behaviour and input locking after completion
- both linear tile numbers and (row, column) positions
- invalid and off-image positions without crashing

2. INTEGRATION DESIGN

The application uses ONE central PuzzleState from puzzle_models.py.

GameplayLogic does not duplicate tile order, orientation, moves, hints or
completion values. It delegates all state changes to these existing methods:

    state.select_tile(position)
    state.rotate_tile(position, 90)
    state.flip_tile(position, "horizontal")
    state.request_hint()
    state.solve()

It reads the existing PuzzleState properties to prepare simple result
dictionaries for the Tkinter GUI. Therefore there is no double move count and
no attempt to write to PuzzleState's read-only properties.

3. REQUIRED GROUP FILE

The repository must contain Arshad's file with this exact name:

    puzzle_models.py

The tests intentionally use the real PuzzleState, Tile and Transformation
classes from that file instead of a separate dummy state.

4. RIJUAN FILES TO UPLOAD

Upload these three files without changing their names:

    rijuan_gameplay_logic.py
    test_rijuan_gameplay_logic.py
    RIJUAN_GAMEPLAY_README.txt

Do not upload files containing names such as "(1)" or "(1) (1)" because the
Python import in the test file expects rijuan_gameplay_logic.py exactly.

5. TESTING

Place puzzle_models.py and the two Python files in the same repository folder.

Direct test:

    python test_rijuan_gameplay_logic.py

Expected output:

    All Rijuan gameplay tests passed with the real PuzzleState for 3x3, 4x4 and 5x5.

Pytest:

    pytest -q test_rijuan_gameplay_logic.py

The test suite checks all three grid sizes, selection/deselection/swap,
rotation, horizontal flip, move counting, completion and locking, hints, Solve,
linear/tuple positions, and ignored off-image clicks.

6. GUI CONNECTION EXAMPLE

Create the central state and then connect the controller:

    state = PuzzleState(tiles, grid_size)
    state.scramble(transformations)
    game = GameplayLogic(state)

Call from Tkinter events:

    result = game.left_click((row, column))
    result = game.right_click((row, column))
    result = game.shift_left_click((row, column))
    hint = game.request_hint()
    result = game.solve()

Use game.status() for:
- moves
- tiles_left
- selected_position
- hints_used and hints_remaining
- active_hint
- can_hint
- game_complete
- input_locked

Use game.is_position_correct((row, column)) when drawing green ticks.

7. GITHUB COMMIT

Suggested commit message:

    Add Rijuan gameplay controller and integration tests - s405120

Suggested contribution description:

    Implemented the gameplay controller for selection, swapping, clockwise
    rotation, horizontal flipping, counters, hints, completion locking and
    Solve. Integrated the controller with the group's shared PuzzleState and
    added tests using the real model for 3x3, 4x4 and 5x5 grids.
