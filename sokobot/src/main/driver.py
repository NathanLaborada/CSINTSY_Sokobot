import os
import sys

from src.reader.file_reader import FileReader
from src.solver.sokobot import SokoBot


def split_map(map_data):
    static_map = [[" " for _ in range(map_data.columns)] for _ in range(map_data.rows)]
    items = [[" " for _ in range(map_data.columns)] for _ in range(map_data.rows)]

    for row in range(map_data.rows):
        for column in range(map_data.columns):
            tile = map_data.tiles[row][column]
            if tile == "#":
                static_map[row][column] = "#"
            elif tile == "@":
                items[row][column] = "@"
            elif tile == "$":
                items[row][column] = "$"
            elif tile == ".":
                static_map[row][column] = "."
            elif tile == "+":
                static_map[row][column] = "."
                items[row][column] = "@"
            elif tile == "*":
                static_map[row][column] = "."
                items[row][column] = "$"

    return static_map, items


def main():
    if len(sys.argv) < 3:
        map_name = os.environ.get("MAP_NAME")
        mode = os.environ.get("MODE")
        if map_name is None or mode is None:
            print("Usage: driver.py <map name> <mode>", file=sys.stderr)
            raise SystemExit(1)
    else:
        map_name = sys.argv[1]
        mode = sys.argv[2]

    file_reader = FileReader()
    map_data = file_reader.read_file(map_name)

    if map_data is None:
        print(f"Error: Map '{map_name}' could not be loaded.", file=sys.stderr)
        raise SystemExit(1)

    if mode == "raw":
        static_map, items = split_map(map_data)
        soko_bot = SokoBot()
        solution = soko_bot.solveSokobanPuzzle(map_data.columns, map_data.rows, static_map, items)
        print(solution)
    elif mode in {"fp", "bot"}:
        from src.gui.game import Game

        game = Game(map_data)
        game.run(mode)
    else:
        print(f"Error: Unknown mode '{mode}'.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
