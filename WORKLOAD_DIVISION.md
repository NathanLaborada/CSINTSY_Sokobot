# SokoBot Project: Workload Division & Execution Plan (3 Members)

This document outlines the workload breakdown, modular code architecture, report section assignments, and milestones for Major Course Output 1 (SokoBot), based on the requirements defined in [`specifications.pdf`]

---

## 1. Project Constraints & Target Goals

* **Target Problem**: Autonomous Sokoban solver in Python (2 to 8 crates).
* **Success Criterion**: Solve **≥ 80%** of test levels within the **15-second thinking limit** per puzzle.
* **Code Scope Constraint**: All custom bot code must reside exclusively in the `src/solver` directory modifying or importing into [`src/solver/sokobot.py`]
* **Library Restrictions**: Built-in data structures and generic graph/tree structures are allowed; external AI or search libraries are strictly prohibited.
* **Deliverables**:
  1. Complete project directory `.zip` (including working bot code and map files).
  2. Max 4-page A4 PDF Report (written entirely by students without Generative AI).
  3. Oral Examination (individual understanding tested; poor understanding can risk a grade of 0 for the group).

---

## 2. High-Level Architecture & Member Roles

To prevent team members from blocking each other and to avoid single points of failure during the oral exam, the technical work is divided into three distinct modules:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SokoBot Architecture                                  │
│                                                                                        │
│   ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐   │
│   │        Member 1        │  │        Member 2        │  │        Member 3        │   │
│   │  Core Search & State   │  │  Heuristics & Target   │  │  Deadlocks & Testing   │   │
│   │     Representation     │  │      Assignments       │  │      Benchmarking      │   │
│   └───────────┬────────────┘  └───────────┬────────────┘  └───────────┬────────────┘   │
│               │                           │                           │                │
│               ▼                           ▼                           ▼                │
│   • A* / Search Framework      • True Distance Matrix      • Static Deadlock Pruning   │
│   • Push-based abstraction     • Bipartite Matching        • Freeze Deadlock Pruning   │
│   • Path reconstruction (udlr) • Crate-to-target assignment• Test harness & metrics    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Workload Breakdown

### Member 1: Core Search Architecture & State Representation
> **Focus**: Building a fast search engine and translating abstract crate-push paths into valid move sequences.

#### Coding Responsibilities (`src/solver/`)
1. **State Representation**:
   * Design an immutable, lightweight, hashable state structure: `(player_reachable_zone_id, tuple_of_sorted_box_coords)`.
   * Implement custom equality (`__eq__`) and hash (`__hash__`) methods for fast lookups in `visited` sets and transposition tables.
2. **Search Algorithm Framework**:
   * Implement priority-queue-based search (A*, Weighted A*, or Greedy Best-First Search) using Python's standard `heapq`.
   * Track state history and cumulative $g(n)$ cost.
3. **Push-Based Action Generation (Macro-Moves)**:
   * Instead of step-by-step player walking (which drastically inflates branching factor and depth), evaluate candidate moves as **crate pushes**.
   * Run a quick flood-fill / BFS to determine all crate push directions reachable by the player from their current position.
4. **Path Reconstruction**:
   * Map search transitions back to exact player walking steps.
   * Return the solution string using characters `'u'`, `'d'`, `'l'`, and `'r'` as expected by [SokoBot.solveSokobanPuzzle].

#### Report Responsibilities
* **Section 1(a)**: Search algorithm formulation (A* variants, node expansion logic).
* **Section 1(b)**: State representation, normalization, and memory efficiency.
* **Section 1(c)**: Action generation and push-based search abstraction.

---

### Member 2: Heuristics & Distance Precomputations
> **Focus**: Minimizing explored search nodes so 2–8 crate maps resolve within the 15-second budget.

#### Coding Responsibilities (`src/solver/`)
1. **True Distance Matrix (Grid-Aware BFS)**:
   * Replace naive Manhattan distance with precomputed floor distances from every target to all navigable tiles (ignoring crates initially).
   * Account for static walls so crates do not receive misleadingly low heuristic costs across impassable barriers.
2. **Goal Assignment & Heuristic Functions**:
   * **Baseline Heuristic**: Sum of shortest grid distances from each crate to its closest target.
   * **Advanced Heuristic (Minimum-Cost Bipartite Matching)**: Implement an assignment algorithm (e.g., Hungarian algorithm / Kuhn-Munkres or greedy matching) to ensure each crate is mapped to a distinct target, preventing convergence on the same slot.
3. **Tie-Breaking & Player-Distance Penalties**:
   * Add a secondary heuristic component representing the distance from the player to the next push position to avoid zigzagging and reduce node ties in the priority queue.
4. **Admissibility & Performance Tuning**:
   * Benchmark the calculation time of complex heuristics vs. node reduction benefit to keep per-node overhead low.

#### Report Responsibilities
* **Section 1(d)**: Rationale behind search strategies and tie-breaking policies.
* **Section 1(e)**: Mathematical description and evaluation of heuristic functions (Manhattan vs. true distance vs. bipartite matching).

---

### Member 3: Deadlock Detection, Pruning & Benchmark Evaluation
> **Focus**: Pruning unwinnable puzzle branches early and conducting empirical performance experiments.

#### Coding Responsibilities (`src/solver/`)
1. **Static Deadlock Precomputation**:
   * Identify all non-goal corner tiles where a crate can never be pushed out.
   * Identify dead wall lines (perimeter or internal walls without targets where a pushed crate becomes trapped).
2. **Dynamic / Freeze Deadlock Detection**:
   * Detect 2×2 blocks of immobile objects (e.g., crate-crate, crate-wall configurations where neither can move).
   * Detect corridor blockages where a crate blocks the only path to open targets.
3. **Automated Testing Harness**:
   * Create an automated evaluation script that runs [SokoBot.solveSokobanPuzzle] or solver on all levels in [`sokobot/maps/`] (1–15, original1–3, testlevel).
   * Record metrics per level:
     * Status (Solved / Timeout / Memory Out)
     * Execution time (seconds, ensuring $\le 15$s)
     * Generated and expanded node counts
     * Solution length (move count)
4. **Data Compilation**:
   * Summarize test runs into structured tables and charts for the report.

#### Report Responsibilities
* **Section 2**: Evaluation and Performance (tables of results, strengths/weaknesses across crate counts and corridor layouts, failure analysis).
* **Section 3**: Reflections and Challenges (NP-hardness of Sokoban, branching factor challenges, state explosion).

---

## 4. Shared Responsibilities & Oral Exam Strategy

| Task | Assigned To | Details |
| :--- | :--- | :--- |
| **Section 4: Table of Contributions** | All Members | Fill in precise task contributions per student as required by report guidelines. |
| **Code Review & Internal Walkthrough** | All Members | Regularly review pull requests or code commits. **Every member must be able to explain all modules** during the oral exam. |
| **Report Synthesis & Page Budget Check** | All Members | Ensure the final document does not exceed the strict **4-page A4 limit**, avoids textbook definitions, and uses the team's own writing. |
| **Final Packaging Validation** | Members 1 & 3 | Verify that `freeplay.bat`, `sokobot.bat`, and `sokobot.bat <map> --gui` run cleanly on a clean clone before submission. |

---

## 5. Suggested 3-Phase Roadmap

### Phase 1: Baseline Working Solver (Days 1–7)
* [ ] **Member 1**: Implement basic A* algorithm with standard state tuples and step-by-step move generation.
* [ ] **Member 2**: Implement basic Manhattan distance heuristic.
* [ ] **Member 3**: Set up the automated batch test script and run baseline on maps 1 to 5.
* **Milestone**: The bot solves trivial maps (1–3 crates) end-to-end.

### Phase 2: Optimization, Heuristics & Pruning (Days 8–15)
* [ ] **Member 1**: Upgrade to push-based macro actions with reachability flood-fill and path reconstruction.
* [ ] **Member 2**: Implement precomputed target-to-tile distance matrix and bipartite matching assignment.
* [ ] **Member 3**: Integrate static corner/wall deadlock tables and 2×2 freeze deadlock checks.
* **Milestone**: Solve rate improves significantly; complex maps (4–8 crates) finish well under 15 seconds.

### Phase 3: Benchmarking, Report Writing & Oral Prep (Days 16–Final)
* [ ] **Member 3**: Execute full benchmark suite across all maps; compile execution tables and analysis.
* [ ] **All Members**: Draft assigned sections of the 4-page report (adhering strictly to no-AI writing rules).
* [ ] **All Members**: Conduct mock oral defense sessions asking each other about state representation, heuristic admissibility, deadlock criteria, and algorithm complexity.
* [ ] **Members 1 & 3**: Package the final `.zip` archive and verify against starter requirements.
