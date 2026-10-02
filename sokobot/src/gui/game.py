import sys
import threading
import time
from pathlib import Path

import pygame


class Game:
    UPPER_LEFT_X = 10
    UPPER_LEFT_Y = 10
    TILE_SIZE = 32
    STATUS_BAR_HEIGHT = 24
    SOLUTION_TIME_LIMIT = 15.0
    SOLUTION_DELAY = 0.1

    STATUS_WAITING_FOR_SPACE = "Push SPACE to start Bot..."
    STATUS_WAITING_FOR_SOLUTION = "Waiting for solution..."
    STATUS_SOLUTION_TIMEOUT = "TIME'S UP! Bot took too long thinking..."
    STATUS_PLAYING_SOLUTION = "Playing solution..."
    STATUS_FINISHED_PLAYING_SOLUTION = "SOLUTION FINISHED!"
    STATUS_FREE_PLAY = "FREE PLAY MODE!"

    def __init__(self, map_data):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Sokoban")
        self.clock = pygame.time.Clock()
        self.status_font = pygame.font.SysFont("arial", 16, bold=True)
        self.status_value_font = pygame.font.SysFont("arial", 16)
        self.images = self.load_images()

        self.map_loaded = False
        self.free_play = False
        self.waiting_for_space = False
        self.status_string = ""
        self.solution_time_string = ""
        self.solution_string = ""
        self.solution_ctr = 0
        self.solution_thread = None
        self.solution_result = None
        self.solution_error = None
        self.solution_finished = False
        self.solution_start_time = 0.0
        self.last_solution_step = 0.0
        self.state = "idle"

        self.player_row = -1
        self.player_column = -1
        self.rows = 0
        self.columns = 0
        self.static_map = []
        self.items = []
        self.progress = 0
        self.moves = 0
        self.box_count = 0
        self.goal_count = 0
        self.player_count = 0
        self.history = []
        self.initial_map_data = map_data

        self.load_map(map_data)

    def load_images(self):
        result = {}
        graphics_path = Path("src") / "graphics"
        names = {
            "brick": "brick.png",
            "goal": "goal.png",
            "crate": "crate.png",
            "crategoal": "crategoal.png",
            "robot": "robot.png",
        }
        for key, filename in names.items():
            path = graphics_path / filename
            if path.exists():
                image = pygame.image.load(path).convert_alpha()
                result[key] = pygame.transform.scale(image, (self.TILE_SIZE, self.TILE_SIZE))
        return result

    def load_map(self, map_data):
        self.progress = 0
        self.moves = 0
        self.player_count = 0
        self.box_count = 0
        self.goal_count = 0
        self.static_map = [[" " for _ in range(map_data.columns)] for _ in range(map_data.rows)]
        self.items = [[" " for _ in range(map_data.columns)] for _ in range(map_data.rows)]

        for row in range(map_data.rows):
            for column in range(map_data.columns):
                tile = map_data.tiles[row][column]
                if tile == "#":
                    self.static_map[row][column] = "#"
                elif tile == "@":
                    self.items[row][column] = "@"
                    self.player_count += 1
                    self.player_row = row
                    self.player_column = column
                elif tile == "$":
                    self.items[row][column] = "$"
                    self.box_count += 1
                elif tile == ".":
                    self.static_map[row][column] = "."
                    self.goal_count += 1
                elif tile == "+":
                    self.static_map[row][column] = "."
                    self.items[row][column] = "@"
                    self.player_count += 1
                    self.goal_count += 1
                    self.player_row = row
                    self.player_column = column
                elif tile == "*":
                    self.static_map[row][column] = "."
                    self.items[row][column] = "$"
                    self.box_count += 1
                    self.goal_count += 1
                    self.progress += 1

        self.rows = map_data.rows
        self.columns = map_data.columns

        if self.player_count == 1 and self.box_count == self.goal_count and self.box_count > 0:
            self.free_play = False
            self.map_loaded = True

    def run(self, mode):
        if mode == "fp":
            self.initiate_free_play()
        elif mode == "bot":
            self.initiate_solution()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)

            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        raise SystemExit(0)

    def initiate_free_play(self):
        self.status_string = self.STATUS_FREE_PLAY
        self.waiting_for_space = False
        self.free_play = True

    def initiate_solution(self):
        self.status_string = self.STATUS_WAITING_FOR_SPACE
        self.waiting_for_space = True
        self.free_play = False

    def handle_key(self, key):
        if self.free_play:
            if key == pygame.K_UP:
                self.execute_move(0)
            elif key == pygame.K_DOWN:
                self.execute_move(1)
            elif key == pygame.K_LEFT:
                self.execute_move(2)
            elif key == pygame.K_RIGHT:
                self.execute_move(3)
            elif key == pygame.K_u:
                self.undo_move()
            elif key == pygame.K_r:
                self.restart_level()
        elif self.waiting_for_space and key == pygame.K_SPACE:
            self.start_thinking()

    def execute_move(self, direction):
        point_row = -1
        point_column = -1
        box_row = -1
        box_column = -1

        if direction == 0:
            point_row = self.player_row - 1
            point_column = self.player_column
            box_row = self.player_row - 2
            box_column = self.player_column
        elif direction == 1:
            point_row = self.player_row + 1
            point_column = self.player_column
            box_row = self.player_row + 2
            box_column = self.player_column
        elif direction == 2:
            point_row = self.player_row
            point_column = self.player_column - 1
            box_row = self.player_row
            box_column = self.player_column - 2
        elif direction == 3:
            point_row = self.player_row
            point_column = self.player_column + 1
            box_row = self.player_row
            box_column = self.player_column + 2

        if self.free_play:
            self.push_history()
            if not self.handle_movement(point_row, point_column, box_row, box_column):
                self.history.pop()
        else:
            self.handle_movement(point_row, point_column, box_row, box_column)

    def push_history(self):
        self.history.append((
            [row[:] for row in self.items],
            self.player_row,
            self.player_column,
            self.progress,
            self.moves,
        ))

    def undo_move(self):
        if not self.history:
            return
        items, player_row, player_column, progress, moves = self.history.pop()
        self.items = items
        self.player_row = player_row
        self.player_column = player_column
        self.progress = progress
        self.moves = moves

    def restart_level(self):
        self.load_map(self.initial_map_data)
        self.history = []
        self.initiate_free_play()

    def handle_movement(self, point_row, point_column, box_row, box_column):
        if point_row < 0 or point_row >= self.rows or point_column < 0 or point_column >= self.columns:
            return False
        if self.static_map[point_row][point_column] == "#":
            return False
        if self.items[point_row][point_column] != "$":
            self.items[self.player_row][self.player_column] = " "
            self.items[point_row][point_column] = "@"
            self.player_row = point_row
            self.player_column = point_column
        elif self.items[point_row][point_column] == "$":
            if box_row < 0 or box_row >= self.rows or box_column < 0 or box_column >= self.columns:
                return False
            if self.static_map[box_row][box_column] == "#" or self.items[box_row][box_column] == "$":
                return False
            if self.static_map[box_row][box_column] == ".":
                self.progress += 1
            if self.static_map[point_row][point_column] == ".":
                self.progress -= 1
            self.items[box_row][box_column] = "$"
            self.items[self.player_row][self.player_column] = " "
            self.items[point_row][point_column] = "@"
            self.player_row = point_row
            self.player_column = point_column

        self.moves += 1
        return True

    def start_thinking(self):
        from src.solver.sokobot import SokoBot

        self.waiting_for_space = False
        self.status_string = self.STATUS_WAITING_FOR_SOLUTION
        self.state = "thinking"
        self.solution_result = None
        self.solution_error = None
        self.solution_finished = False
        self.solution_start_time = time.perf_counter()
        static_map_copy = [row[:] for row in self.static_map]
        items_copy = [row[:] for row in self.items]

        def solve():
            try:
                soko_bot = SokoBot()
                self.solution_result = soko_bot.solveSokobanPuzzle(
                    self.columns, self.rows, static_map_copy, items_copy
                )
            except BaseException as ex:
                self.solution_error = ex
            finally:
                self.solution_finished = True

        self.solution_thread = threading.Thread(target=solve, daemon=True)
        self.solution_thread.start()

    def play_solution(self, solution_string):
        self.free_play = False
        self.status_string = self.STATUS_PLAYING_SOLUTION
        self.solution_string = solution_string
        self.solution_ctr = 0
        self.last_solution_step = time.perf_counter()
        self.state = "playing"

    def update(self):
        now = time.perf_counter()
        if self.state == "thinking":
            elapsed = now - self.solution_start_time
            self.solution_time_string = f"{elapsed:.2f}s"
            if self.solution_finished:
                if self.solution_error is not None:
                    raise self.solution_error
                self.play_solution(self.solution_result or "")
            elif elapsed >= self.SOLUTION_TIME_LIMIT:
                self.status_string = self.STATUS_SOLUTION_TIMEOUT
                self.solution_time_string = f"{elapsed:.2f}"
                self.state = "timeout"
        elif self.state == "playing" and now - self.last_solution_step >= self.SOLUTION_DELAY:
            if self.solution_ctr >= len(self.solution_string):
                self.status_string = self.STATUS_FINISHED_PLAYING_SOLUTION
                self.state = "finished"
                return
            next_move = self.solution_string[self.solution_ctr]
            self.solution_ctr += 1
            if next_move == "u":
                self.execute_move(0)
            elif next_move == "d":
                self.execute_move(1)
            elif next_move == "l":
                self.execute_move(2)
            elif next_move == "r":
                self.execute_move(3)
            self.last_solution_step = now

    def draw(self):
        self.screen.fill((10, 10, 10))
        if not self.map_loaded:
            return

        for row in range(self.rows):
            for column in range(self.columns):
                x = self.UPPER_LEFT_X + column * self.TILE_SIZE
                y = self.UPPER_LEFT_Y + self.STATUS_BAR_HEIGHT + row * self.TILE_SIZE
                if self.static_map[row][column] == "#":
                    self.draw_tile("brick", x, y, (100, 100, 100))
                elif self.static_map[row][column] == ".":
                    self.draw_tile("goal", x, y, (150, 214, 124))

                if self.items[row][column] == "$" and self.static_map[row][column] == ".":
                    self.draw_tile("crategoal", x, y, (210, 160, 70))
                elif self.items[row][column] == "$":
                    self.draw_tile("crate", x, y, (190, 120, 50))
                elif self.items[row][column] == "@":
                    self.draw_tile("robot", x, y, (80, 160, 220))

        footer_rect = pygame.Rect(0, 0, self.screen.get_width(), self.STATUS_BAR_HEIGHT)
        pygame.draw.rect(self.screen, (0, 0, 0), footer_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), footer_rect, 2)
        text_y = footer_rect.centery
        moves_label = "MOVES:"
        self.draw_text(moves_label, self.status_font, (255, 255, 255), 12, text_y, "midleft")
        moves_value_x = 12 + self.status_font.size(moves_label)[0] + 8
        self.draw_text(str(self.moves), self.status_value_font, (255, 255, 255), moves_value_x, text_y, "midleft")
        progress_label = "PROGRESS:"
        progress_label_x = 250
        self.draw_text(progress_label, self.status_font, (255, 255, 255), progress_label_x, text_y, "midleft")
        progress_value_x = progress_label_x + self.status_font.size(progress_label)[0] + 8
        self.draw_text(f"{self.progress} / {self.box_count}", self.status_value_font, (255, 255, 255), progress_value_x, text_y, "midleft")
        time_width = self.status_value_font.size(self.solution_time_string)[0] if self.solution_time_string else 0
        status_right = self.screen.get_width() - time_width - 48
        self.draw_text(self.status_string, self.status_font, (255, 100, 100), status_right, text_y, "midright")
        self.draw_text(self.solution_time_string, self.status_value_font, (255, 255, 255), self.screen.get_width() - 24, text_y, "midright")

    def draw_tile(self, image_key, x, y, color):
        image = self.images.get(image_key)
        if image is not None:
            self.screen.blit(image, (x, y))
        else:
            pygame.draw.rect(self.screen, color, (x, y, self.TILE_SIZE, self.TILE_SIZE))
            pygame.draw.rect(self.screen, (0, 0, 0), (x, y, self.TILE_SIZE, self.TILE_SIZE), 1)

    def draw_text(self, text, font, color, x, y, anchor="topleft"):
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        setattr(rect, anchor, (x, y))
        self.screen.blit(surface, rect)
        return rect
