from pathlib import Path

from src.reader.map_data import MapData


class FileReader:
    def read_file(self, keyword):
        path = Path("maps") / f"{keyword}.txt"

        try:
            lines = path.read_text().splitlines()
        except FileNotFoundError:
            return None
        except Exception as ex:
            print(ex)
            return None

        rows = len(lines)
        columns = max((len(line) for line in lines), default=0)
        tiles = []

        for line in lines:
            tiles.append(list(line.ljust(columns)))

        return MapData(tiles, rows, columns)