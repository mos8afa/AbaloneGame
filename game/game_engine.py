# game_engine.py

import random
from copy import deepcopy

EMPTY = "."
WHITE = "W"
BLACK = "B"


class GameEngine:
    DIRECTIONS = [
        (1, 0), #Right
        (-1, 0), #Left
        (0, 1), #Down-Right
        (0, -1), #Up-Left
        (1, -1), #Down-Left
        (-1, 1), #Up-Right
    ]

    def __init__(self):
        self.board = self.initialize_board()
        self.white_out = 0
        self.black_out = 0
        self.current_player = WHITE

    # =========================
    # 1. Initialize Board
    # =========================
    def initialize_board(self):
        board = {}

        for q in range(-4, 5):
            for r in range(-4, 5):
                if -4 <= q + r <= 4:
                    board[(q, r)] = EMPTY

        white_positions = [
            *((q, -4) for q in range(0, 5)),
            *((q, -3) for q in range(-1, 5)),
            (0, -2), (1, -2), (2, -2),
        ]

        black_positions = [
            *((q, 4) for q in range(-4, 1)),
            *((q, 3) for q in range(-4, 2)),
            (-2, 2), (-1, 2), (0, 2),
        ]

        for coord in white_positions:
            if coord in board:
                board[coord] = WHITE

        for coord in black_positions:
            if coord in board:
                board[coord] = BLACK

        return board

    # =========================
    # 2. Serialization
    # =========================
    def clone(self):
        return deepcopy(self)

    def serialize_state(self):
        return {
            "board": {f"{q},{r}": value for (q, r), value in self.board.items()},
            "white_out": self.white_out,
            "black_out": self.black_out,
            "current_player": self.current_player,
        }

    @classmethod
    def load_state(cls, data):
        engine = cls()
        engine.board = {
            tuple(map(int, coord.split(","))): value
            for coord, value in data["board"].items()
        }
        engine.white_out = data["white_out"]
        engine.black_out = data["black_out"]
        engine.current_player = data["current_player"]
        return engine

    # =========================
    # 3. Board Utilities
    # =========================
    def in_bounds(self, coord):
        return coord in self.board

    def get_piece(self, coord):
        return self.board.get(coord, None)

    def set_piece(self, coord, value):
        self.board[coord] = value

    def add(self, coord, direction):
        return coord[0] + direction[0], coord[1] + direction[1]

    def opposite_direction(self, direction):
        return -direction[0], -direction[1]

    def direction_between(self, source, target):
        delta = (target[0] - source[0], target[1] - source[1])
        if delta in self.DIRECTIONS:
            return delta
        return None

    def is_same_player(self, coord, player):
        return self.in_bounds(coord) and self.get_piece(coord) == player

    def get_group_axis(self, group):
        if len(group) < 2:
            return None
        for direction in self.DIRECTIONS:
            candidate = sorted(
                group,
                key=lambda c: (c[0] * direction[0] + c[1] * direction[1], c[0], c[1])
            )
            if all(
                self.add(candidate[i], direction) == candidate[i + 1]
                for i in range(len(candidate) - 1)
            ):
                return direction
        return None

    def get_group_head(self, group, direction):
        return max(group, key=lambda c: c[0] * direction[0] + c[1] * direction[1])

    def get_line_from(self, coord, direction):
        line = []
        pointer = self.add(coord, direction)
        while self.in_bounds(pointer) and self.get_piece(pointer) != EMPTY:
            line.append(pointer)
            pointer = self.add(pointer, direction)
        return line

    # =========================
    # 4. Move Validation
    # =========================
    def is_valid_group_move(self, group, direction, player=None):
        player = player or self.current_player
        group = tuple(sorted(tuple(coord) for coord in group))
        if not (1 <= len(group) <= 3):
            return False
        if any(not self.is_same_player(coord, player) for coord in group):
            return False
        axis = self.get_group_axis(group)
        if len(group) > 1 and axis is None:
            return False
        if direction not in self.DIRECTIONS:
            return False
        inline = axis is None or direction == axis or direction == self.opposite_direction(axis)
        if inline:
            return self._can_inline_move(group, direction, player)
        return self._can_lateral_move(group, direction)

    def _can_lateral_move(self, group, direction):
        for coord in group:
            target = self.add(coord, direction)
            if not self.in_bounds(target) or self.get_piece(target) != EMPTY:
                return False
        return True

    def _can_inline_move(self, group, direction, player):
        head = self.get_group_head(group, direction)
        next_coord = self.add(head, direction)
        if not self.in_bounds(next_coord):
            return False
        next_piece = self.get_piece(next_coord)
        if next_piece == EMPTY:
            return True
        if next_piece == player:
            return False
        opponents = self.get_line_from(head, direction)
        if len(opponents) > 3 or len(opponents) >= len(group):
            return False
        after_line = self.add(opponents[-1], direction)
        return not self.in_bounds(after_line) or self.get_piece(after_line) == EMPTY

    # =========================
    # 5. Move Application
    # =========================
    def apply_group_move(self, group, direction, player=None, switch=True):
        player = player or self.current_player
        if not self.is_valid_group_move(group, direction, player):
            return False
        group = tuple(sorted(tuple(coord) for coord in group))
        axis = self.get_group_axis(group)
        inline = axis is None or direction == axis or direction == self.opposite_direction(axis)
        if inline:
            self._apply_inline_move(group, direction, player)
        else:
            self._apply_lateral_move(group, direction)
        if switch:
            self.switch_player()
        return True

    def _apply_lateral_move(self, group, direction):
        pieces = [self.get_piece(coord) for coord in group]
        for coord in group:
            self.set_piece(coord, EMPTY)
        for coord, piece in zip(group, pieces):
            self.set_piece(self.add(coord, direction), piece)

    def _apply_inline_move(self, group, direction, player):
        head = self.get_group_head(group, direction)
        opponents = self.get_line_from(head, direction)
        if opponents:
            after_line = self.add(opponents[-1], direction)
            if self.in_bounds(after_line):
                for coord in reversed(opponents):
                    self.set_piece(self.add(coord, direction), self.get_piece(coord))
            else:
                removed = len(opponents)
                for coord in opponents:
                    self.set_piece(coord, EMPTY)
                if player == WHITE:
                    self.black_out += removed
                else:
                    self.white_out += removed
        for coord in sorted(
            group,
            key=lambda c: c[0] * direction[0] + c[1] * direction[1],
            reverse=True
        ):
            self.set_piece(coord, EMPTY)
            self.set_piece(self.add(coord, direction), player)

    # =========================
    # 6. Move Generation
    # =========================
    def get_valid_groups(self, player=None):
        player = player or self.current_player
        groups = set()
        for coord, piece in self.board.items():
            if piece != player:
                continue
            groups.add((coord,))
            for direction in self.DIRECTIONS:
                second = self.add(coord, direction)
                if self.get_piece(second) == player:
                    groups.add(tuple(sorted((coord, second))))
                    third = self.add(second, direction)
                    if self.get_piece(third) == player:
                        groups.add(tuple(sorted((coord, second, third))))
        return [tuple(group) for group in groups]

    def get_valid_moves(self, player=None):
        player = player or self.current_player
        moves = []
        for group in self.get_valid_groups(player):
            for direction in self.DIRECTIONS:
                if self.is_valid_group_move(group, direction, player):
                    moves.append((group, direction))
        return moves

    # =========================
    # 7. Game Over / Winner
    # =========================
    def is_game_over(self):
        return (
            self.white_out >= 6
            or self.black_out >= 6
            or not bool(self.get_valid_moves(self.current_player))
        )

    def get_winner(self):
        if self.white_out >= 6:
            return BLACK
        if self.black_out >= 6:
            return WHITE
        return None

    def switch_player(self):
        self.current_player = BLACK if self.current_player == WHITE else WHITE

    # =========================
    # 8. AI — Evaluation & Search
    # =========================

    # ── Evaluation weight constants ───────────────────────────
    _CAPTURE_W   = 10_000
    _CENTER_MULT =    300
    _CENTER_W    = {0: 5, 1: 4, 2: 3, 3: 1, 4: -2}
    _ATTACK_W    =    200
    _COHESION_W  =     50

    # ── Phase thresholds ──────────────────────────────────────
    _PHASE_MID  = 4
    _PHASE_LATE = 10

    # ── Pre-computed hex distances for all 61 board cells ─────
    # Built once at class definition; avoids repeated max(abs…) calls.
    _DIST_CACHE: dict = {}

    @classmethod
    def _build_dist_cache(cls):
        for q in range(-4, 5):
            for r in range(-4, 5):
                if -4 <= q + r <= 4:
                    cls._DIST_CACHE[(q, r)] = max(abs(q), abs(r), abs(-q - r))
    @staticmethod
    def _hex_dist(coord):
        return GameEngine._DIST_CACHE.get(
            coord, max(abs(coord[0]), abs(coord[1]), abs(-coord[0] - coord[1]))
        )

    def _game_phase(self):
        total_out = self.white_out + self.black_out
        if total_out < self._PHASE_MID:
            return "early"
        if total_out < self._PHASE_LATE:
            return "mid"
        return "late"

    # ── Board hash for transposition table ────────────────────
    def _board_hash(self):
        """
        Fast position key: only non-empty cells + capture counts + player.
        Uses frozenset so order doesn't matter.
        """
        return (
            frozenset((k, v) for k, v in self.board.items() if v != EMPTY),
            self.white_out,
            self.black_out,
            self.current_player,
        )

    # ── Apply / Undo (replaces deepcopy) ──────────────────────
    def _make_move(self, group, direction):
        """
        Apply a move and return an undo record.
        The undo record is a tuple:
          (changed_cells, old_white_out, old_black_out, old_player)
        where changed_cells is a list of (coord, old_value).
        """
        old_wo     = self.white_out
        old_bo     = self.black_out
        old_player = self.current_player

        # Snapshot only the cells that will change
        player   = self.current_player
        opponent = BLACK if player == WHITE else WHITE

        axis   = self.get_group_axis(group)
        inline = (axis is None
                  or direction == axis
                  or direction == self.opposite_direction(axis))

        # Collect coords that will be touched
        touched = set(group)
        for coord in group:
            touched.add(self.add(coord, direction))
        if inline:
            head = self.get_group_head(group, direction)
            ptr  = self.add(head, direction)
            while ptr in self.board and self.board.get(ptr) not in (EMPTY, None):
                touched.add(ptr)
                touched.add(self.add(ptr, direction))
                ptr = self.add(ptr, direction)

        changed = [(c, self.board.get(c, EMPTY)) for c in touched if c in self.board]

        # Apply the move (switch=True so current_player flips)
        self.apply_group_move(group, direction, switch=True)

        return (changed, old_wo, old_bo, old_player)

    def _undo_move(self, undo_record):
        """Restore the board to the state before _make_move was called."""
        changed, old_wo, old_bo, old_player = undo_record
        for coord, value in changed:
            self.board[coord] = value
        self.white_out     = old_wo
        self.black_out     = old_bo
        self.current_player = old_player

    # ── Core evaluation ───────────────────────────────────────
    def evaluate_board(self, player=None):
        """
        Multi-factor static evaluation from `player`'s perspective.
        Factors: captures (dominant) > center control > attack > cohesion.
        Phase scaling adjusts center vs attack emphasis over the game.
        """
        player   = player or self.current_player
        opponent = BLACK if player == WHITE else WHITE
        phase    = self._game_phase()

        if phase == "early":
            center_scale, attack_scale = 1.4, 0.8
        elif phase == "mid":
            center_scale, attack_scale = 1.0, 1.0
        else:
            center_scale, attack_scale = 0.6, 1.4

        score = 0

        # 1. Captures
        my_caps  = self.black_out if player == BLACK else self.white_out
        opp_caps = self.white_out if player == BLACK else self.black_out
        score += (my_caps - opp_caps) * self._CAPTURE_W

        # 2. Center control (single pass over board)
        board    = self.board
        dist_c   = self._DIST_CACHE
        cw       = self._CENTER_W
        cm       = self._CENTER_MULT
        center_score = 0
        for coord, piece in board.items():
            if piece == EMPTY:
                continue
            w = cw.get(dist_c.get(coord, 4), -2) * cm
            if piece == player:
                center_score += w
            else:
                center_score -= w
        score += int(center_score * center_scale)

        # 3. Attack bonus
        score += int(self._attack_score(player, opponent) * attack_scale)
        score -= int(self._attack_score(opponent, player) * attack_scale)

        # 4. Cohesion
        score += self._cohesion_score(player)
        score -= self._cohesion_score(opponent)

        return score

    def _attack_score(self, attacker, defender):
        """O(pieces × 6) attack threat score — no sorting, no cloning."""
        score = 0
        board = self.board
        add   = self.add
        for coord, piece in board.items():
            if piece != attacker:
                continue
            for direction in self.DIRECTIONS:
                n1 = add(coord, direction)
                p1 = board.get(n1)
                if p1 == attacker:
                    n2 = add(n1, direction)
                    p2 = board.get(n2)
                    if p2 == defender:
                        score += self._ATTACK_W
                    elif p2 == attacker:
                        n3 = add(n2, direction)
                        if board.get(n3) == defender:
                            score += self._ATTACK_W * 2
        return score // 2

    def _cohesion_score(self, player):
        """O(pieces × 3) — each pair counted once via half-directions."""
        score     = 0
        board     = self.board
        add       = self.add
        half_dirs = self.DIRECTIONS[:3]
        for coord, piece in board.items():
            if piece != player:
                continue
            for direction in half_dirs:
                if board.get(add(coord, direction)) == player:
                    score += self._COHESION_W
        return score

    # ── Move ordering ─────────────────────────────────────────
    def _move_priority(self, move):
        """
        Fast heuristic score for move ordering (no cloning).
        Tiers: capture(10M) > push(500K) > 3-inline(50K) >
               2-inline(10K) > center-gain(1K×Δ) > inline(100) > lateral(0)
        """
        group, direction = move
        player   = self.current_player
        opponent = BLACK if player == WHITE else WHITE
        board    = self.board

        axis   = self.get_group_axis(group)
        inline = (axis is None
                  or direction == axis
                  or direction == self.opposite_direction(axis))

        push_score = 0
        if inline and len(group) >= 2:
            head      = self.get_group_head(group, direction)
            next_cell = self.add(head, direction)
            if board.get(next_cell) == opponent:
                opp_line = self.get_line_from(head, direction)
                after    = self.add(opp_line[-1], direction) if opp_line else None
                if after is not None and after not in board:
                    push_score = 10_000_000
                else:
                    push_score = 500_000

        size_bonus = (50_000 if len(group) == 3 else 10_000) if inline else 0

        dist_c = self._DIST_CACHE
        cw     = self._CENTER_W
        center_delta = 0
        for coord in group:
            dest = self.add(coord, direction)
            if dest in board:
                center_delta += cw.get(dist_c.get(dest, 4), -2) - cw.get(dist_c.get(coord, 4), -2)
        center_bonus = max(center_delta, 0) * 1_000

        inline_bonus = 100 if inline else 0
        return push_score + size_bonus + center_bonus + inline_bonus

    # ── Root search: iterative deepening + time limit ─────────
    def get_ai_move(self, difficulty="medium"):
        """
        Iterative deepening minimax with alpha-beta pruning.

        Optimisations applied:
          • Iterative deepening — returns best move found within time limit
          • Time limit — hard cutoff (1.5 s for hard, 0.8 s for medium)
          • Transposition table — skip re-evaluating identical positions
          • Branch cap — only top-N moves explored per node (reduces branching)
          • Apply/undo — no deepcopy; board mutated in-place and restored
          • Move ordering — captures first for maximum alpha-beta pruning
        """
        import time

        valid_moves = self.get_valid_moves(self.current_player)
        if not valid_moves:
            return None
        if difficulty == "easy":
            return random.choice(valid_moves)

        time_limit = 0.8 if difficulty == "medium" else 1.5
        max_depth  = 2   if difficulty == "medium" else 4
        branch_cap = 14  if difficulty == "medium" else 18

        # Order and cap moves at root
        ordered = sorted(valid_moves, key=self._move_priority, reverse=True)
        ordered = ordered[:branch_cap]

        best_move  = ordered[0]
        deadline   = time.time() + time_limit
        tt         = {}          # transposition table: hash → (depth, score)

        for depth in range(1, max_depth + 1):
            if time.time() >= deadline:
                break

            iter_best_score = float("-inf")
            iter_best_move  = best_move
            alpha           = float("-inf")
            beta            = float("inf")
            opponent        = BLACK if self.current_player == WHITE else WHITE

            for move in ordered:
                if time.time() >= deadline:
                    break
                undo = self._make_move(move[0], move[1])
                score = self._alphabeta(
                    depth - 1, opponent, alpha, beta, False,
                    deadline, tt, branch_cap
                )
                self._undo_move(undo)

                if score > iter_best_score:
                    iter_best_score = score
                    iter_best_move  = move
                alpha = max(alpha, iter_best_score)
                if beta <= alpha:
                    break

            # Only update best_move if this iteration completed fully
            if time.time() < deadline or depth == 1:
                best_move = iter_best_move

            # Re-order for next iteration using scores from this one
            # (simple: put the best move first)
            if iter_best_move in ordered:
                ordered.remove(iter_best_move)
                ordered.insert(0, iter_best_move)

        return best_move

    # ── Recursive alpha-beta with apply/undo ──────────────────
    def _alphabeta(self, depth, player, alpha, beta, maximizing,
                   deadline, tt, branch_cap):
        import time

        # Terminal / leaf
        if self.is_game_over():
            return self.evaluate_board(player)
        if depth == 0:
            return self.evaluate_board(player)

        # Time cutoff — return a neutral score so the caller ignores this branch
        if time.time() >= deadline:
            return self.evaluate_board(player)

        # Transposition table lookup
        key = self._board_hash()
        if key in tt:
            cached_depth, cached_score = tt[key]
            if cached_depth >= depth:
                return cached_score

        valid_moves = self.get_valid_moves(player)
        if not valid_moves:
            return self.evaluate_board(player)

        # Order and cap moves
        if depth >= 2:
            ordered = sorted(valid_moves, key=self._move_priority, reverse=True)
        else:
            ordered = valid_moves
        ordered = ordered[:branch_cap]

        opponent = BLACK if player == WHITE else WHITE

        if maximizing:
            value = float("-inf")
            for move in ordered:
                undo  = self._make_move(move[0], move[1])
                value = max(
                    value,
                    self._alphabeta(depth - 1, opponent, alpha, beta, False,
                                    deadline, tt, branch_cap)
                )
                self._undo_move(undo)
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
        else:
            value = float("inf")
            for move in ordered:
                undo  = self._make_move(move[0], move[1])
                value = min(
                    value,
                    self._alphabeta(depth - 1, opponent, alpha, beta, True,
                                    deadline, tt, branch_cap)
                )
                self._undo_move(undo)
                beta = min(beta, value)
                if beta <= alpha:
                    break

        # Store in transposition table
        tt[key] = (depth, value)
        return value


# Build the hex-distance cache once at import time
GameEngine._build_dist_cache()
