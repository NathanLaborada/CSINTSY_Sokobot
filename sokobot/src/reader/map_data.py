from dataclasses import dataclass


@dataclass
class MapData:
    tiles: list[list[str]]
    rows: int
    columns: int

    def print(self):
        for row in range(self.rows):
            print("".join(self.tiles[row][:self.columns]))