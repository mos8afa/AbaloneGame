
import time
import random
from copy import deepcopy

EMPTY = "."
WHITE = "W"
BLACK = "B"
WHITE_KING = "WK"   
BLACK_KING = "BK"   


class GameEngine:
    DIRECTIONS = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (1, -1),
        (-1, 1),
    ]

    def __init__(self, mode="standard"):
        self.mode = mode
        if mode == "king":
            self.board = self.initialize_board_medium()
        elif mode == "hard":
            self.board = self.initialize_board_hard()
        else:
            self.board = self.initialize_board()
        self.white_out = 0
        self.black_out = 0
        self.white_king_out = False
        self.black_king_out = False
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

    def initialize_board_hard(self):
        board = self.initialize_board()
        if (0, -2) in board: board[(0, -2)] = WHITE_KING
        if (0,  2) in board: board[(0,  2)] = BLACK_KING
        return board

    def initialize_board_medium(self):
        board = {}
        for q in range(-4, 5):
            for r in range(-4, 5):
                if -4 <= q + r <= 4:
                    board[(q, r)] = EMPTY
        for c in [(0,-4),(1,-4),(2,-4),(-1,-3),(0,-3),(1,-3)]:
            if c in board: board[c] = WHITE
        for c in [(-2,4),(-1,4),(0,4),(-1,3),(0,3),(1,3)]:
            if c in board: board[c] = BLACK
        if (0,-2) in board: board[(0,-2)] = WHITE_KING
        if (0, 2) in board: board[(0, 2)] = BLACK_KING
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
            "white_king_out": self.white_king_out,
            "black_king_out": self.black_king_out,
            "mode": self.mode,
            "current_player": self.current_player,
        }

    @classmethod
    def load_state(cls, data):
        engine = cls(mode=data.get("mode", "standard"))
        engine.board = {
            tuple(map(int, coord.split(","))): value
            for coord, value in data["board"].items()
        }
        engine.white_out = data["white_out"]
        engine.black_out = data["black_out"]
        engine.white_king_out = data.get("white_king_out", False)
        engine.black_king_out = data.get("black_king_out", False)
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

    def _belongs_to(self, piece, player):
        if player == WHITE: return piece in (WHITE, WHITE_KING)
        return piece in (BLACK, BLACK_KING)

    def is_same_player(self, coord, player):
        return self.in_bounds(coord) and self._belongs_to(self.get_piece(coord), player)

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
        if self._belongs_to(next_piece, player):
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
                last = opponents[-1]
                last_piece = self.get_piece(last)
                if last_piece == WHITE_KING: self.white_king_out = True
                elif last_piece == BLACK_KING: self.black_king_out = True
                self.set_piece(last, EMPTY)

                if player == WHITE:
                    self.black_out += 1
                else:
                    self.white_out += 1

                remaining = opponents[:-1]
                for coord in reversed(remaining):
                    self.set_piece(self.add(coord, direction), self.get_piece(coord))
                    self.set_piece(coord, EMPTY)
        sorted_grp = sorted(
            group,
            key=lambda c: c[0] * direction[0] + c[1] * direction[1],
            reverse=True
        )
        piece_map = {c: self.get_piece(c) for c in sorted_grp}
        for coord in sorted_grp:
            self.set_piece(coord, EMPTY)
            self.set_piece(self.add(coord, direction), piece_map[coord])

    # =========================
    # 6. Move Generation
    # =========================
    def get_valid_groups(self, player=None):
        player = player or self.current_player
        groups = set()
        for coord, piece in self.board.items():
            if not self._belongs_to(piece, player):
                continue
            groups.add((coord,))
            for direction in self.DIRECTIONS:
                second = self.add(coord, direction)
                if self._belongs_to(self.get_piece(second), player):
                    groups.add(tuple(sorted((coord, second))))
                    third = self.add(second, direction)
                    if self._belongs_to(self.get_piece(third), player):
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
        if self.mode == "king":
            return (
                self.white_king_out
                or self.black_king_out
                or not bool(self.get_valid_moves(self.current_player))
            )

        if self.mode == "hard":
            return (
                self.white_out >= 6
                or self.black_out >= 6
                or self.white_king_out
                or self.black_king_out
                or not bool(self.get_valid_moves(self.current_player))
            )

        return (
            self.white_out >= 6
            or self.black_out >= 6
            or not bool(self.get_valid_moves(self.current_player))
        )

    def get_winner(self):
        if self.mode == "king":
            if self.white_king_out: return BLACK
            if self.black_king_out: return WHITE
            return None

        if self.mode == "hard":
            if self.white_out >= 6 or self.white_king_out: return BLACK
            if self.black_out >= 6 or self.black_king_out: return WHITE
            return None

        if self.white_out >= 6: return BLACK
        if self.black_out >= 6: return WHITE
        return None

    def switch_player(self):
        self.current_player = BLACK if self.current_player == WHITE else WHITE

    # =========================
    # 8. AI — Evaluation & Search
    # =========================
    _CAPTURE_W   = 10_000
    _CENTER_MULT =    300
    _CENTER_W    = {0: 5, 1: 4, 2: 3, 3: 1, 4: -2}
    _ATTACK_W    =    200
    _COHESION_W  =     50

    _PHASE_MID  = 4
    _PHASE_LATE = 10

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

    def _board_hash(self):
        return (
            frozenset((k, v) for k, v in self.board.items() if v != EMPTY),
            self.white_out,
            self.black_out,
            self.white_king_out,
            self.black_king_out,
            self.current_player,
        )


    def _make_move(self, group, direction):
        old_wo  = self.white_out
        old_bo  = self.black_out
        old_wko = self.white_king_out
        old_bko = self.black_king_out
        old_player = self.current_player

        player   = self.current_player
        opponent = BLACK if player == WHITE else WHITE

        axis   = self.get_group_axis(group)
        inline = (axis is None or direction == axis or direction == self.opposite_direction(axis))

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

        self.apply_group_move(group, direction, switch=True)

        return (changed, old_wo, old_bo, old_wko, old_bko, old_player)

    def _undo_move(self, undo_record):
        changed, old_wo, old_bo, old_wko, old_bko, old_player = undo_record
        for coord, value in changed:
            self.board[coord] = value
        self.white_out      = old_wo
        self.black_out      = old_bo
        self.white_king_out = old_wko
        self.black_king_out = old_bko
        self.current_player = old_player


    def evaluate_board(self, player=None):
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

        my_caps  = self.black_out if player == BLACK else self.white_out
        opp_caps = self.white_out if player == BLACK else self.black_out
        score += (my_caps - opp_caps) * self._CAPTURE_W

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

        score += int(self._attack_score(player, opponent) * attack_scale)
        score -= int(self._attack_score(opponent, player) * attack_scale)

        score += self._cohesion_score(player)
        score -= self._cohesion_score(opponent)

        return score

    def evaluate_board_easy(self, player=None):
        player   = player or self.current_player
        my_caps  = self.black_out if player == BLACK else self.white_out
        opp_caps = self.white_out if player == BLACK else self.black_out
        score = (my_caps - opp_caps) * self._CAPTURE_W
        score += random.randint(-800, 800)
        return score

    def evaluate_board_medium(self, player=None):
        player      = player or self.current_player
        player_king = WHITE_KING if player == WHITE else BLACK_KING
        opp_king    = BLACK_KING if player == WHITE else WHITE_KING

        if self.white_king_out:
            return -1_000_000 if player == WHITE else 1_000_000
        if self.black_king_out:
            return  1_000_000 if player == WHITE else -1_000_000

        my_king_pos = opp_king_pos = None
        for coord, piece in self.board.items():
            if piece == player_king: my_king_pos  = coord
            elif piece == opp_king:  opp_king_pos = coord

        score = 0

        if my_king_pos:
            score -= self._hex_dist(my_king_pos) * 600

        if opp_king_pos:
            score += self._hex_dist(opp_king_pos) * 700

        if opp_king_pos:
            oq, orr = opp_king_pos
            for coord, piece in self.board.items():
                if piece == EMPTY or not self._belongs_to(piece, player):
                    continue
                d = max(abs(coord[0]-oq), abs(coord[1]-orr),
                        abs((-coord[0]-coord[1])-(-oq-orr)))
                if d <= 3:
                    score += 150 // max(d, 1)

        for coord, piece in self.board.items():
            if piece == EMPTY: continue
            d = self._hex_dist(coord)
            if self._belongs_to(piece, player): score += (4 - d) * 30
            else:                               score -= (4 - d) * 30

        score += random.randint(-200, 200)
        return score

    def _edge_kill_bonus(self, move):
        group, direction = move
        player = self.current_player
        opponent = BLACK if player == WHITE else WHITE

        head = self.get_group_head(group, direction)
        next_cell = self.add(head, direction)

        if self.get_piece(next_cell) != opponent:
            return 0

        opp_line = self.get_line_from(head, direction)
        if not opp_line:
            return 0

        score = 0

        for c in opp_line:
            dist = max(abs(c[0]), abs(c[1]), abs(-c[0]-c[1]))

            if dist == 4:
                score += 200_000
            elif dist == 3:
                score += 80_000

            empty_neighbors = 0
            for d in self.DIRECTIONS:
                n = self.add(c, d)
                if self.in_bounds(n) and self.get_piece(n) == EMPTY:
                    empty_neighbors += 1

            if empty_neighbors <= 2:
                score += 100_000

        return score
    def _attack_score(self, attacker, defender):
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


    def _move_priority(self, move):
        group, direction = move
        player   = self.current_player
        opponent = BLACK if player == WHITE else WHITE
        board    = self.board

        axis   = self.get_group_axis(group)
        inline = (axis is None or direction == axis or direction == self.opposite_direction(axis))

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
        edge_bonus = self._edge_kill_bonus(move)
        return push_score + edge_bonus + size_bonus + center_bonus + inline_bonus

    def get_ai_move(self, difficulty="hard"):
        import time

        valid_moves = self.get_valid_moves(self.current_player)
        if not valid_moves:
            return None

        if difficulty == "hard":
            for move in valid_moves:
                group, direction = move
                player   = self.current_player
                opponent = BLACK if player == WHITE else WHITE
                axis   = self.get_group_axis(group)
                inline = (axis is None
                        or direction == axis
                        or direction == self.opposite_direction(axis))
                if not inline or len(group) < 2:
                    continue
                head      = self.get_group_head(group, direction)
                next_cell = self.add(head, direction)
                if self.get_piece(next_cell) != opponent:
                    continue
                opp_line = self.get_line_from(head, direction)
                if not opp_line:
                    continue
                after = self.add(opp_line[-1], direction)
                if after not in self.board:
                    return move

            time_limit = 1.5
            max_depth  = 4
            branch_cap = 18
            eval_fn    = self.evaluate_board

        elif difficulty == "easy":
            time_limit = 0.4
            max_depth  = 2
            branch_cap = 8
            eval_fn    = self.evaluate_board_easy

        elif difficulty == "medium":
            time_limit = 0.8
            max_depth  = 3
            branch_cap = 14
            eval_fn    = self.evaluate_board_medium

        if difficulty == "hard":
            ordered = sorted(valid_moves, key=self._move_priority, reverse=True)
        else:
            ordered = list(valid_moves)
            random.shuffle(ordered)
        ordered = ordered[:branch_cap]

        best_move  = ordered[0]
        deadline   = time.time() + time_limit
        tt         = {}

        for depth in range(1, max_depth + 1):
            if time.time() >= deadline:
                break

            iter_best_score  = float("-inf")
            iter_best_move   = best_move
            iter_move_scores = []
            alpha            = float("-inf")
            beta             = float("inf")
            opponent         = BLACK if self.current_player == WHITE else WHITE

            for move in ordered:
                if time.time() >= deadline:
                    break
                undo = self._make_move(move[0], move[1])
                score = self._alphabeta(
                    depth - 1, opponent, alpha, beta, False,
                    deadline, tt, branch_cap, eval_fn    # ← eval_fn passed here
                )
                self._undo_move(undo)

                iter_move_scores.append((move, score))
                if score > iter_best_score:
                    iter_best_score = score
                    iter_best_move  = move
                alpha = max(alpha, iter_best_score)
                if beta <= alpha:
                    break

            if time.time() < deadline or depth == 1:
                if difficulty in ("easy", "medium") and iter_move_scores:
                    threshold   = 800 if difficulty == "medium" else 1500
                    close_moves = [m for m, s in iter_move_scores
                                   if s >= iter_best_score - threshold]
                    best_move = random.choice(close_moves) if close_moves else iter_best_move
                else:
                    best_move = iter_best_move

            if difficulty == "hard" and iter_best_move in ordered:
                ordered.remove(iter_best_move)
                ordered.insert(0, iter_best_move)

        return best_move

    def _alphabeta(self, depth, player, alpha, beta, maximizing,
                   deadline, tt, branch_cap, eval_fn=None):
        if eval_fn is None:
            eval_fn = self.evaluate_board

        if self.is_game_over():
            return eval_fn(player)
        if depth == 0:
            return eval_fn(player)

        if time.time() >= deadline:
            return eval_fn(player)

        key = self._board_hash()
        if key in tt:
            cached_depth, cached_score = tt[key]
            if cached_depth >= depth:
                return cached_score

        valid_moves = self.get_valid_moves(player)
        if not valid_moves:
            return eval_fn(player)

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
                                    deadline, tt, branch_cap, eval_fn)
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
                                    deadline, tt, branch_cap, eval_fn)
                )
                self._undo_move(undo)
                beta = min(beta, value)
                if beta <= alpha:
                    break

        tt[key] = (depth, value)
        return value


GameEngine._build_dist_cache()
