# Benchmark for all maps (Nathan)
# run from the sokobot folder:
#   python -m src.solver.benchmark
#   python -m src.solver.benchmark 1 5 original1
#   python -m src.solver.benchmark --no-deadlock
# results also saved to benchmark_results.csv
import csv
import sys
import time
from pathlib import Path

from src.main.driver import split_map
from src.reader.file_reader import FileReader
from src.solver.sokobot import SokoSearch

TIME_LIMIT = 15.0
STEP = {"u": (-1, 0), "d": (1, 0), "l": (0, -1), "r": (0, 1)}


def replay(static_map, items, moves):
    # plays the moves to check the solution actually works, returns (solved, pushes)
    boxes = {(y, x) for y, row in enumerate(items) for x, it in enumerate(row) if it == "$"}
    player = next((y, x) for y, row in enumerate(items) for x, it in enumerate(row) if it == "@")

    def free(p):
        y, x = p
        return 0 <= y < len(static_map) and 0 <= x < len(static_map[y]) and static_map[y][x] != "#"

    pushes = 0
    for m in moves:
        dy, dx = STEP[m]
        nxt = (player[0] + dy, player[1] + dx)
        if not free(nxt):
            return False, pushes
        if nxt in boxes:
            beyond = (nxt[0] + dy, nxt[1] + dx)
            if not free(beyond) or beyond in boxes:
                return False, pushes
            boxes.remove(nxt)
            boxes.add(beyond)
            pushes += 1
        player = nxt
    return all(static_map[y][x] == "." for y, x in boxes), pushes


def run_map(name):
    map_data = FileReader().read_file(name)
    static_map, items = split_map(map_data)

    search = SokoSearch(map_data.columns, map_data.rows, static_map, items)
    start = time.perf_counter()
    try:
        moves, status = search.solve(), None
    except MemoryError:
        moves, status = "", "Memory Out"
    elapsed = time.perf_counter() - start

    ok, pushes = replay(static_map, items, moves)
    if status:
        pass
    elif moves and ok:
        status = "Solved" if elapsed <= TIME_LIMIT else "Too slow"
    elif moves:
        status = "Invalid"
    elif elapsed >= search.TIME_LIMIT:
        status = "Timeout"
    else:
        status = "No solution"

    return {
        "map": name,
        "crates": len(search.start_boxes),
        "status": status,
        "time_s": round(elapsed, 3),
        "expanded": search.expanded,
        "generated": search.generated,
        "moves": len(moves),
        "pushes": pushes,
    }


def map_order(path):
    return (0, int(path.stem), "") if path.stem.isdigit() else (1, 0, path.stem)


def main():
    args = sys.argv[1:]
    if "--no-deadlock" in args:
        SokoSearch.USE_DEADLOCKS = False
        args.remove("--no-deadlock")
    names = args or [p.stem for p in sorted(Path("maps").glob("*.txt"), key=map_order)]

    rows = []
    for name in names:
        rows.append(run_map(name))
        print(f"  {name}: {rows[-1]['status']} in {rows[-1]['time_s']}s", file=sys.stderr)

    cols = list(rows[0])
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")
    solved = sum(r["status"] == "Solved" for r in rows)
    print(f"\nSolved {solved}/{len(rows)} ({100 * solved / len(rows):.0f}%), target is 80%")

    with open("benchmark_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
