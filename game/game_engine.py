# game_engine.py

import random
from copy import deepcopy

EMPTY = "."
WHITE = "W"
BLACK = "B"


class GameEngine:
    DIRECTIONS = [
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (1, -1),
        (-1, 1),
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
            (-1, -2), (0, -2), (1, -2),
        ]

        black_positions = [
            *((q, 4) for q in range(-4, 1)),
            *((q, 3) for q in range(-4, 2)),
            (-1, 2), (0, 2), (1, 2),
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
    # 8. AI
    # =========================
    def evaluate_board(self, player=None):
        player = player or self.current_player
        opponent = BLACK if player == WHITE else WHITE
        score = (self.black_out - self.white_out) if player == BLACK else (self.white_out - self.black_out)
        score *= 1000
        score += self._piece_count(player) * 10
        score -= self._piece_count(opponent) * 10
        score += self._position_score(player) - self._position_score(opponent)
        return score

    def _piece_count(self, player):
        return sum(1 for piece in self.board.values() if piece == player)

    def _position_score(self, player):
        score = 0
        for coord, piece in self.board.items():
            if piece != player:
                continue
            distance = max(abs(coord[0]), abs(coord[1]), abs(-coord[0] - coord[1]))
            score += 4 - distance
        return score

    def get_ai_move(self, difficulty="medium"):
        valid_moves = self.get_valid_moves(self.current_player)
        if not valid_moves:
            return None
        if difficulty == "easy":
            return random.choice(valid_moves)

        depth = 2 if difficulty == "medium" else 3
        best_score = float("-inf")
        best_move = None
        alpha = float("-inf")
        beta = float("inf")
        opponent = BLACK if self.current_player == WHITE else WHITE

        for move in valid_moves:
            clone = self.clone()
            clone.apply_group_move(move[0], move[1], switch=True)
            score = clone._alphabeta(depth - 1, opponent, alpha, beta, False)
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break

        return best_move or random.choice(valid_moves)

    def _alphabeta(self, depth, player, alpha, beta, maximizing):
        if depth == 0 or self.is_game_over():
            return self.evaluate_board(player)

        valid_moves = self.get_valid_moves(player)
        if not valid_moves:
            return self.evaluate_board(player)

        opponent = BLACK if player == WHITE else WHITE
        if maximizing:
            value = float("-inf")
            for move in valid_moves:
                clone = self.clone()
                clone.apply_group_move(move[0], move[1], switch=True)
                value = max(value, clone._alphabeta(depth - 1, opponent, alpha, beta, False))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value

        value = float("inf")
        for move in valid_moves:
            clone = self.clone()
            clone.apply_group_move(move[0], move[1], switch=True)
            value = min(value, clone._alphabeta(depth - 1, opponent, alpha, beta, True))
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value
