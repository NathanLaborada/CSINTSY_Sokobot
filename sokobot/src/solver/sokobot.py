import heapq
import time
# go to project directory and run: python -m pip install pygame-ce

# Design summary
#   * The grid is flattened into a 1-D array with a 1-cell wall border, so a
#     neighbour of any cell is simply (cell + offset) and never out of range.
#   * A search state is (zone_id, sorted tuple of box cells). zone_id is the
#     smallest cell index the player can reach without pushing anything, so two
#     positions of the player inside the same region map to the same state.
#   * Actions are crate PUSHES (macro-moves), not single player steps.
#   * The search is weighted A* on a heapq priority queue. g(n) = number of
#     pushes so far, f(n) = g(n) + WEIGHT * h(n).
#   * Only at the very end are the pushes expanded into 'u','d','l','r' steps.
#
# Hooks for the other members (clearly marked below):
#   * SokoSearch.heuristic(boxes)   -> estimated pushes remaining
#   * SokoSearch.is_deadlock(boxes) -> True if the position can never be solved
# The defaults are only simple placeholders so that the search runs end to end.


class SokoState:
    """Immutable, lightweight, hashable search state.

    zone  : int   - normalized player position (min reachable cell index)
    boxes : tuple - sorted tuple of box cell indices
    """

    __slots__ = ("zone", "boxes", "_hash")

    def __init__(self, zone, boxes):
        self.zone = zone
        self.boxes = boxes
        self._hash = hash((zone, boxes))  # computed once, reused for every lookup

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return (
            self._hash == other._hash
            and self.zone == other.zone
            and self.boxes == other.boxes
        )


class SokoSearch:
    # u, d, l, r as (char, row delta, col delta)
    _DIR_DEFS = (("u", -1, 0), ("d", 1, 0), ("l", 0, -1), ("r", 0, 1))

    WEIGHT = 3.0        # 1.0 = plain A*; larger = greedier and faster, less optimal
    TIME_LIMIT = 13.0   # seconds; the program's hard limit is 15

    def __init__(self, width, height, mapData, itemsData):
        self.w2 = width + 2
        self.size = self.w2 * (height + 2)
        w2 = self.w2

        self.wall = bytearray(b"\x01") * self.size  # border (and outside) = wall
        self.targets = set()
        boxes = []
        player = -1

        for y in range(height):
            for x in range(width):
                c = (y + 1) * w2 + (x + 1)
                m = mapData[y][x]
                it = itemsData[y][x]
                self.wall[c] = 1 if m == "#" else 0
                if m == ".":
                    self.targets.add(c)
                if it == "$":
                    boxes.append(c)
                elif it == "@":
                    player = c

        self.start_player = player
        self.start_boxes = boxes
        self.dirs = tuple((ch, dy * w2 + dx) for ch, dy, dx in self._DIR_DEFS)
        self.offsets = tuple(o for _, o in self.dirs)
        self.dir_char = {o: ch for ch, o in self.dirs}

    # Hooks (to be replaced / improved by the heuristic & deadlock members)
    def heuristic(self, boxes):
        """Placeholder: sum of each box's Manhattan distance to its nearest target."""
        w2 = self.w2
        total = 0
        for b in boxes:
            if b in self.targets:
                continue
            by, bx = divmod(b, w2)
            best = 10 ** 9
            for t in self.targets:
                ty, tx = divmod(t, w2)
                d = abs(by - ty) + abs(bx - tx)
                if d < best:
                    best = d
            total += best
        return total

    def is_deadlock(self, boxes):
        """Placeholder: no deadlock pruning yet."""
        return False

    # State helpers
    def _flood(self, start, boxset):
        """Flood fill from `start` with boxes as obstacles.

        Returns (seen bytearray, min reachable cell index)."""
        wall = self.wall
        offsets = self.offsets
        seen = bytearray(self.size)
        seen[start] = 1
        stack = [start]
        lowest = start
        while stack:
            p = stack.pop()
            if p < lowest:
                lowest = p
            for o in offsets:
                q = p + o
                if not seen[q] and not wall[q] and q not in boxset:
                    seen[q] = 1
                    stack.append(q)
        return seen, lowest

    def _is_goal(self, boxes):
        targets = self.targets
        for b in boxes:
            if b not in targets:
                return False
        return True

    # Push-based action generation
    def _successors(self, state):
        """Yield (new_state, box_from_cell, direction_offset) for every legal push."""
        wall = self.wall
        boxes = state.boxes
        boxset = set(boxes)
        seen, _ = self._flood(state.zone, boxset)

        for b in boxes:
            for o in self.offsets:
                stand = b - o              # cell the player must stand on to push
                if not seen[stand]:
                    continue
                dest = b + o               # cell the crate moves into
                if wall[dest] or dest in boxset:
                    continue
                new_boxes = tuple(sorted([dest if x == b else x for x in boxes]))
                if self.is_deadlock(new_boxes):
                    continue
                # After the push the player stands where the crate used to be.
                _, zone = self._flood(b, set(new_boxes))
                yield SokoState(zone, new_boxes), b, o

    # Search framework: weighted A* on heapq
    def solve(self):
        start_boxes = tuple(sorted(self.start_boxes))
        if self._is_goal(start_boxes):
            return ""

        _, zone0 = self._flood(self.start_player, set(start_boxes))
        start = SokoState(zone0, start_boxes)

        weight = self.WEIGHT
        deadline = time.time() + self.TIME_LIMIT

        g_cost = {start: 0}
        parent = {start: None}   # state -> (prev_state, box_cell_before_push, direction_offset)
        counter = 0
        h0 = self.heuristic(start_boxes)
        open_heap = [(weight * h0, h0, counter, start)]
        closed = set()
        expansions = 0

        while open_heap:
            _, _, _, state = heapq.heappop(open_heap)
            if state in closed:
                continue
            closed.add(state)

            if self._is_goal(state.boxes):
                return self._build_solution(state, parent)

            expansions += 1
            if (expansions & 255) == 0 and time.time() > deadline:
                return ""

            g = g_cost[state] + 1
            for nxt, box_cell, off in self._successors(state):
                if nxt in closed:
                    continue
                old = g_cost.get(nxt)
                if old is not None and old <= g:
                    continue
                g_cost[nxt] = g
                parent[nxt] = (state, box_cell, off)
                h = self.heuristic(nxt.boxes)
                counter += 1
                heapq.heappush(open_heap, (g + weight * h, h, counter, nxt))

        return ""  # if no solution is found

    # Path reconstruction: pushes -> exact walking steps
    def _build_solution(self, goal_state, parent):
        pushes = []
        s = goal_state
        while parent[s] is not None:
            prev, box_cell, off = parent[s]
            pushes.append((box_cell, off))
            s = prev
        pushes.reverse()

        player = self.start_player
        boxset = set(self.start_boxes)
        out = []
        for box_cell, off in pushes:
            stand = box_cell - off
            out.append(self._walk(player, stand, boxset))
            out.append(self.dir_char[off])       # the push itself moves the player 1 step
            boxset.discard(box_cell)
            boxset.add(box_cell + off)
            player = box_cell
        return "".join(out)

    def _walk(self, src, dst, boxset):
        """Shortest walking path (BFS, boxes are obstacles) from src to dst."""
        if src == dst:
            return ""
        wall = self.wall
        prev = {src: None}
        frontier = [src]
        while frontier:
            nxt_frontier = []
            for p in frontier:
                for ch, o in self.dirs:
                    q = p + o
                    if q in prev or wall[q] or q in boxset:
                        continue
                    prev[q] = (p, ch)
                    if q == dst:
                        steps = []
                        cur = q
                        while prev[cur] is not None:
                            cur, c = prev[cur][0], prev[cur][1]
                            steps.append(c)
                        steps.reverse()
                        return "".join(steps)
                    nxt_frontier.append(q)
            frontier = nxt_frontier
        return ""  # should never happen for a state the search generated


class SokoBot:
    def solveSokobanPuzzle(self, width, height, mapData, itemsData):
        return SokoSearch(width, height, mapData, itemsData).solve()
