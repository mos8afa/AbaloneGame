import json
import traceback

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .game_engine import GameEngine

# ── Difficulty mapping ────────────────────────────────────────
DIFFICULTY_MAP = {1: "easy", 2: "medium", 3: "hard"}

# ── Coordinate conversion constants ──────────────────────────
# Frontend row = r + 4,  col = q - Q_MIN[r]
# Q_MIN maps axial r (-4..+4) to the minimum q value in that row.
_Q_MIN = {
        -4:  0, -3: -1, -2: -2, -1: -3,
        0: -4,
        1: -4,  2: -4,  3: -4,  4: -4,
}
_ROW_COUNTS = [5, 6, 7, 8, 9, 8, 7, 6, 5]


# ── Coordinate helpers ────────────────────────────────────────

def _frontend_to_backend(cell):
    """Convert frontend {row, col} → backend axial (q, r)."""
    r = cell["row"] - 4
    q = cell["col"] + _Q_MIN[r]
    return (q, r)


def _backend_to_frontend(coord):
    """Convert backend axial (q, r) → frontend {row, col}."""
    q, r = coord
    return {"row": r + 4, "col": q - _Q_MIN[r]}


def _serialize_for_frontend(engine):
    """
    Convert the backend board dict to a jagged 2-D list indexed as
    board[frontend_row][frontend_col], plus captured counts and turn.
    """
    board = [[""] * count for count in _ROW_COUNTS]
    for (q, r), value in engine.board.items():
        row = r + 4
        col = q - _Q_MIN[r]
        if 0 <= row < 9 and 0 <= col < _ROW_COUNTS[row]:
            board[row][col] = "" if value == "." else value

    return {
        "state": {
            "board": board,
            "captured": {"B": engine.black_out, "W": engine.white_out},
            "turn": "player" if engine.current_player == "W" else "ai",
        }
    }


def _compute_direction(backend_group, backend_target, engine):
    """
    Derive the hex direction from a group of backend coords to a target.
    First tries direct adjacency; falls back to nearest-valid-direction.
    """
    directions = engine.DIRECTIONS

    for coord in backend_group:
        delta = (backend_target[0] - coord[0], backend_target[1] - coord[1])
        if delta in directions:
            return delta

    def hex_dist(a, b):
        return max(
            abs(a[0] - b[0]),
            abs(a[1] - b[1]),
            abs((-a[0] - a[1]) - (-b[0] - b[1])),
        )

    nearest = min(backend_group, key=lambda c: hex_dist(c, backend_target))
    return min(
        directions,
        key=lambda d: hex_dist(
            (nearest[0] + d[0], nearest[1] + d[1]),
            backend_target,
        ),
    )


# ── Session helpers ───────────────────────────────────────────

def _get_engine(request):
    """Load the game engine from the session, or return None."""
    state = request.session.get("game_state")
    return GameEngine.load_state(state) if state else None


def _save_engine(request, engine):
    request.session["game_state"] = engine.serialize_state()
    request.session.modified = True


# ── Views ─────────────────────────────────────────────────────

def game(request):
    return render(request, "game/game.html")


def get_state(request):
    engine = _get_engine(request)
    if not engine:
        return JsonResponse({"status": "no_game"})
    return JsonResponse({"status": "ok", **_serialize_for_frontend(engine)})


@csrf_exempt
def start_game(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body or "{}")
            level = int(data.get("difficulty", 3))
        except (ValueError, TypeError):
            level = 3
        request.session["difficulty"] = DIFFICULTY_MAP.get(level, "hard")

    if request.session.get("difficulty") == "medium":
        engine = GameEngine(mode="king")
    elif request.session.get("difficulty") == "hard":
        # ===== MODIFICATION: FINAL LEVEL WIN CONDITION ONLY =====
        # mode="hard" activates dual win: 6 marbles OR king elimination
        engine = GameEngine(mode="hard")
    else:
        engine = GameEngine()   # easy / standard: 6-marble rule only
    _save_engine(request, engine)
    return JsonResponse({"status": "started", **_serialize_for_frontend(engine)})


@csrf_exempt
def make_move(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    engine = _get_engine(request)
    if not engine:
        return JsonResponse({"error": "No active game"}, status=400)

    try:
        data   = json.loads(request.body)
        group  = data.get("group")
        target = data.get("target")

        if not group or not target:
            return JsonResponse({"error": "Missing group or target"}, status=400)

        backend_group  = [_frontend_to_backend(g) for g in group]
        backend_target = _frontend_to_backend(target)
        direction      = _compute_direction(backend_group, backend_target, engine)

        black_before = engine.black_out
        white_before = engine.white_out

        if not engine.apply_group_move(backend_group, direction):
            return JsonResponse(
                {"error": "Invalid move", **_serialize_for_frontend(engine)},
                status=400,
            )

        captured = (engine.black_out - black_before) + (engine.white_out - white_before)
        _save_engine(request, engine)

        return JsonResponse({
            "status": "ok",
            "captured": captured > 0,
            "game_over": engine.is_game_over(),
            "winner": engine.get_winner(),
            **_serialize_for_frontend(engine),
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def ai_move(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    engine = _get_engine(request)
    if not engine:
        return JsonResponse({"error": "No active game"}, status=400)

    if engine.is_game_over():
        return JsonResponse({
            "status": "ok",
            "game_over": True,
            "winner": engine.get_winner(),
            **_serialize_for_frontend(engine),
        })

    try:
        black_before = engine.black_out
        white_before = engine.white_out

        difficulty       = request.session.get("difficulty", "hard")
        move             = engine.get_ai_move(difficulty)
        captured         = False
        ai_move_frontend = None

        if move:
            ai_move_frontend = [_backend_to_frontend(c) for c in move[0]]
            engine.apply_group_move(move[0], move[1])
            captured = (engine.black_out - black_before) + (engine.white_out - white_before) > 0

        _save_engine(request, engine)

        return JsonResponse({
            "status": "ok",
            "captured": captured,
            "ai_move": ai_move_frontend,
            "game_over": engine.is_game_over(),
            "winner": engine.get_winner(),
            **_serialize_for_frontend(engine),
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
