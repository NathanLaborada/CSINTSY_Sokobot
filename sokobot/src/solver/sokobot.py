import heapq
import time
from collections import deque
# go to project directory and run: python -m pip install pygame-ce

class SokoState:
    # zone = smallest cell the player can reach, boxes = sorted tuple of box cells
    __slots__ = ("zone", "boxes", "_hash")

    def __init__(self, zone, boxes):
        self.zone = zone
        self.boxes = boxes
        self._hash = hash((zone, boxes))

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

    WEIGHT = 1.5        # 1.0 = normal A*, tested 1.0 to 8.0 and 1.5 was best
    TIME_LIMIT = 13.0   # seconds, gui limit is 15

    def __init__(self, width, height, mapData, itemsData):
        self.deadline = time.time() + self.TIME_LIMIT
        self.w2 = width + 2
        self.size = self.w2 * (height + 2)
        w2 = self.w2

        self.wall = bytearray(b"\x01") * self.size  # border counts as wall
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

        # for benchmark.py
        self.expanded = 0
        self.generated = 0

        self.INF = 10 ** 9
        self.tlist = sorted(self.targets)
        self.dist_tables = [self._push_distances(t) for t in self.tlist]
        self.dead = self._compute_dead_squares()
        self.h_cache = {}
        # reach[cell] = list of (target bit, distance) for targets a box on that cell can reach
        self.reach = [
            [(1 << j, t[c]) for j, t in enumerate(self.dist_tables) if t[c] < self.INF]
            for c in range(self.size)
        ]

    def _push_distances(self, target):
        wall, INF = self.wall, self.INF
        d = [INF] * self.size
        d[target] = 0
        q = deque([target])
        while q:
            p = q.popleft()
            for o in self.offsets:
                b = p - o          # Where the box was before the push
                s = p - 2 * o      # Where the player stood
                if wall[b] or wall[s]:
                    continue
                if d[b] > d[p] + 1:
                    d[b] = d[p] + 1
                    q.append(b)
        return d

    # dead square = box there can't reach any target (INF in every table)
    def _compute_dead_squares(self):
        wall, INF, tables = self.wall, self.INF, self.dist_tables
        return bytearray(
            0 if wall[c] or any(t[c] < INF for t in tables) else 1
            for c in range(self.size)
        )

    def heuristic(self, boxes):
        # same boxes = same h, so save it
        h = self.h_cache.get(boxes)
        if h is None:
            h = self.h_cache[boxes] = self._matching_cost(boxes)
        return h

    def _matching_cost(self, boxes):
        INF = self.INF
        reach = self.reach
        best = {0: 0}  # mask of used targets -> lowest cost
        # boxes with fewer reachable targets go first (faster, same answer)
        for b in sorted(boxes, key=lambda b: len(reach[b])):
            nxt = {}
            get = nxt.get
            for mask, cost in best.items():
                for bit, d in reach[b]:
                    if mask & bit:  # target already used
                        continue
                    nm = mask | bit
                    v = cost + d
                    if v < get(nm, INF):
                        nxt[nm] = v
            best = nxt
            if not best:
                return INF  # some box can't get its own target
        return min(best.values())

    USE_DEADLOCKS = True  # set to False by benchmark --no-deadlock

    def is_deadlock(self, boxes, moved):
        # only the box that just moved can cause a new deadlock
        if not self.USE_DEADLOCKS:
            return False
        if self.dead[moved]:
            return True
        frozen = set()
        if not self._frozen(moved, set(boxes), frozen):
            return False
        # frozen boxes are fine if they're all on targets
        return any(b not in self.targets for b in frozen)

    def _frozen(self, b, boxset, frozen):
        # box is frozen if it can't move horizontally or vertically.
        # b is treated as a wall while checking its neighbours so it doesn't loop forever
        before = set(frozen)
        frozen.add(b)
        if self._axis_blocked(b, 1, boxset, frozen) and self._axis_blocked(b, self.w2, boxset, frozen):
            return True
        frozen.intersection_update(before)  # undo, b isn't frozen
        return False

    def _axis_blocked(self, b, o, boxset, frozen):
        n1, n2 = b - o, b + o
        wall = self.wall
        if wall[n1] or wall[n2] or n1 in frozen or n2 in frozen:
            return True
        if self.dead[n1] and self.dead[n2]:
            return True
        if n1 in boxset and self._frozen(n1, boxset, frozen):
            return True
        if n2 in boxset and self._frozen(n2, boxset, frozen):
            return True
        return False

    def _flood(self, start, boxset):
        # returns (cells the player can reach, smallest reachable cell)
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

    def _successors(self, state):
        # every possible push from this state
        wall = self.wall
        boxes = state.boxes
        boxset = set(boxes)
        seen, _ = self._flood(state.zone, boxset)

        for b in boxes:
            for o in self.offsets:
                stand = b - o              # player stands here to push
                if not seen[stand]:
                    continue
                dest = b + o               # box moves here
                if wall[dest] or dest in boxset:
                    continue
                new_boxes = tuple(sorted([dest if x == b else x for x in boxes]))
                if self.is_deadlock(new_boxes, dest):
                    continue
                # player ends up where the box was
                _, zone = self._flood(b, set(new_boxes))
                yield SokoState(zone, new_boxes), b, o

    # weighted A*
    def solve(self):
        start_boxes = tuple(sorted(self.start_boxes))
        if self._is_goal(start_boxes):
            return ""

        _, zone0 = self._flood(self.start_player, set(start_boxes))
        start = SokoState(zone0, start_boxes)

        weight = self.WEIGHT
        deadline = self.deadline

        g_cost = {start: 0}
        parent = {start: None}   # state -> (prev state, box cell, direction)
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
            self.expanded = expansions
            if (expansions & 15) == 0 and time.time() > deadline:
                return ""

            g = g_cost[state] + 1
            for nxt, box_cell, off in self._successors(state):
                self.generated += 1
                if nxt in closed:
                    continue
                old = g_cost.get(nxt)
                if old is not None and old <= g:
                    continue
                g_cost[nxt] = g
                parent[nxt] = (state, box_cell, off)
                h = self.heuristic(nxt.boxes)
                if h >= self.INF and self.USE_DEADLOCKS:
                    continue  # boxes can't all get different targets
                counter += 1
                heapq.heappush(open_heap, (g + weight * h, h, counter, nxt))

        return ""  # no solution found

    # turn the list of pushes into u/d/l/r moves
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
            out.append(self.dir_char[off])
            boxset.discard(box_cell)
            boxset.add(box_cell + off)
            player = box_cell
        return "".join(out)

    def _walk(self, src, dst, boxset):
        # BFS walking path from src to dst, boxes block the way
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
        return ""


class SokoBot:
    def solveSokobanPuzzle(self, width, height, mapData, itemsData):
        return SokoSearch(width, height, mapData, itemsData).solve()
