import random
from collections import deque, defaultdict
from dataclasses import dataclass, field

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


# ============================================================
# Room definitions inspired by the repo
# - diningroom wants bedroom, toilet, kitchen, bathroom
# - bedroom wants diningroom
# - bathroom wants diningroom, kitchen
# - toilet wants bedroom, diningroom
# - kitchen wants diningroom, pantry, bathroom
# - pantry wants kitchen
# - diningroom and kitchen want outside connection
# ============================================================

ROOM_LIBRARY = {
    "diningroom": {
        "size": 7,
        "wanted_neighbors": ["bedroom", "toilet", "kitchen", "bathroom"],
        "outside_connection": True,
    },
    "bedroom": {
        "size": 3,
        "wanted_neighbors": ["diningroom"],
        "outside_connection": False,
    },
    "bathroom": {
        "size": 3,
        "wanted_neighbors": ["diningroom", "kitchen"],
        "outside_connection": False,
    },
    "toilet": {
        "size": 2,
        "wanted_neighbors": ["bedroom", "diningroom"],
        "outside_connection": False,
    },
    "kitchen": {
        "size": 3,
        "wanted_neighbors": ["diningroom", "pantry", "bathroom"],
        "outside_connection": True,
    },
    "pantry": {
        "size": 1,
        "wanted_neighbors": ["kitchen"],
        "outside_connection": False,
    },
    # Extra practical types for your experiments
    "common": {
        "size": 8,
        "wanted_neighbors": ["kitchen", "diningroom", "office", "bathroom"],
        "outside_connection": True,
    },
    "office": {
        "size": 2,
        "wanted_neighbors": ["common", "bathroom"],
        "outside_connection": False,
    },
    "garage": {
        "size": 5,
        "wanted_neighbors": ["kitchen", "common"],
        "outside_connection": True,
    },
}


@dataclass
class RoomSpec:
    name: str
    room_type: str
    size: int
    wanted_neighbors: list[str]
    outside_connection: bool
    target_area: int = 0
    cells: set[tuple[int, int]] = field(default_factory=set)
    seed: tuple[int, int] | None = None

    @property
    def area(self) -> int:
        return len(self.cells)


def make_room(name: str, room_type: str) -> RoomSpec:
    cfg = ROOM_LIBRARY[room_type]
    return RoomSpec(
        name=name,
        room_type=room_type,
        size=cfg["size"],
        wanted_neighbors=cfg["wanted_neighbors"][:],
        outside_connection=cfg["outside_connection"],
    )


# ============================================================
# Utility functions
# ============================================================

DIR4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def neighbors4(x: int, y: int, w: int, h: int):
    for dx, dy in DIR4:
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny


def is_edge(x: int, y: int, w: int, h: int) -> bool:
    return x == 0 or y == 0 or x == w - 1 or y == h - 1


def distance_to_edge(x: int, y: int, w: int, h: int) -> int:
    return min(x, y, w - 1 - x, h - 1 - y)


def bfs_fill_component(grid: np.ndarray, start: tuple[int, int], value: int) -> list[tuple[int, int]]:
    w, h = grid.shape
    q = deque([start])
    seen = {start}
    comp = []

    while q:
        x, y = q.popleft()
        comp.append((x, y))
        for nx, ny in neighbors4(x, y, w, h):
            if (nx, ny) not in seen and grid[nx, ny] == value:
                seen.add((nx, ny))
                q.append((nx, ny))
    return comp


# ============================================================
# Generator
# ============================================================

class FloorPlanGenerator:
    def __init__(self, width: int, height: int, room_specs: list[RoomSpec], seed: int | None = None):
        self.width = width
        self.height = height
        self.rooms = room_specs
        self.grid = np.full((width, height), -1, dtype=int)
        self.rng = random.Random(seed)

        self._assign_target_areas()

    def _assign_target_areas(self):
        total_weight = sum(r.size ** 2 for r in self.rooms)
        total_area = self.width * self.height

        allocated = 0
        for room in self.rooms:
            room.target_area = max(3, round(total_area * (room.size ** 2) / total_weight))
            allocated += room.target_area

        # Fix rounding drift
        while allocated > total_area:
            candidate = max(self.rooms, key=lambda r: r.target_area)
            if candidate.target_area > 3:
                candidate.target_area -= 1
                allocated -= 1
            else:
                break

        while allocated < total_area:
            candidate = max(self.rooms, key=lambda r: r.size)
            candidate.target_area += 1
            allocated += 1

    def _seed_score(self, room: RoomSpec, x: int, y: int, placed_rooms: list[int]) -> float:
        if self.grid[x, y] != -1:
            return -1e9

        score = 0.0

        # Outside preference
        dist_edge = distance_to_edge(x, y, self.width, self.height)
        if room.outside_connection:
            score += max(0, 6 - 2.0 * dist_edge)
        else:
            score += min(dist_edge * 1.2, 4.0)

        # Mild penalty if boxed in by existing rooms too early
        occupied_adj = 0
        for nx, ny in neighbors4(x, y, self.width, self.height):
            if self.grid[nx, ny] != -1:
                occupied_adj += 1
        score -= occupied_adj * 0.75

        # Wanted-neighbor attraction
        for idx in placed_rooms:
            other = self.rooms[idx]
            if other.room_type in room.wanted_neighbors:
                ox, oy = other.seed
                manhattan = abs(x - ox) + abs(y - oy)
                score += max(0, 8 - manhattan) * 1.6

        # Tiny noise so it doesn't always produce same robot house
        score += self.rng.uniform(-0.25, 0.25)
        return score

    def place_seeds(self):
        order = sorted(range(len(self.rooms)), key=lambda i: self.rooms[i].target_area, reverse=True)
        placed = []

        for idx in order:
            room = self.rooms[idx]
            best_score = -1e9
            best_pos = None

            for x in range(self.width):
                for y in range(self.height):
                    s = self._seed_score(room, x, y, placed)
                    if s > best_score:
                        best_score = s
                        best_pos = (x, y)

            if best_pos is None:
                raise RuntimeError(f"Could not place seed for {room.name}")

            room.seed = best_pos
            room.cells.add(best_pos)
            self.grid[best_pos] = idx
            placed.append(idx)

    def _growth_priority(self, room_idx: int, cell: tuple[int, int]) -> float:
        room = self.rooms[room_idx]
        x, y = cell
        score = 0.0

        # Outside preference
        dist_edge = distance_to_edge(x, y, self.width, self.height)
        if room.outside_connection:
            score += max(0, 5 - 1.5 * dist_edge)
        else:
            score += min(dist_edge, 3)

        # Neighbor preference based on adjacent cells
        for nx, ny in neighbors4(x, y, self.width, self.height):
            other_idx = self.grid[nx, ny]
            if other_idx != -1 and other_idx != room_idx:
                other_type = self.rooms[other_idx].room_type
                if other_type in room.wanted_neighbors:
                    score += 3.0
                else:
                    score -= 0.25

        # Prefer compact growth around seed
        sx, sy = room.seed
        score -= 0.15 * (abs(x - sx) + abs(y - sy))

        # Small randomness
        score += self.rng.uniform(-0.1, 0.1)
        return score

    def grow_rooms(self):
        active = {i for i in range(len(self.rooms))}

        while active:
            progressed = False
            order = list(active)
            self.rng.shuffle(order)

            for idx in order:
                room = self.rooms[idx]

                if room.area >= room.target_area:
                    active.discard(idx)
                    continue

                frontier = []
                for x, y in room.cells:
                    for nx, ny in neighbors4(x, y, self.width, self.height):
                        if self.grid[nx, ny] == -1:
                            frontier.append((nx, ny))

                if not frontier:
                    active.discard(idx)
                    continue

                frontier = list(set(frontier))
                frontier.sort(key=lambda c: self._growth_priority(idx, c), reverse=True)

                chosen = frontier[0]
                room.cells.add(chosen)
                self.grid[chosen] = idx
                progressed = True

                if room.area >= room.target_area:
                    active.discard(idx)

            if not progressed:
                break

    def fill_empty(self):
        empties = list(zip(*np.where(self.grid == -1)))
        seen = set()

        for start in empties:
            if start in seen:
                continue
            comp = bfs_fill_component(self.grid, start, -1)
            seen.update(comp)

            boundary_counts = defaultdict(int)
            for x, y in comp:
                for nx, ny in neighbors4(x, y, self.width, self.height):
                    room_idx = self.grid[nx, ny]
                    if room_idx != -1:
                        boundary_counts[room_idx] += 1

            if not boundary_counts:
                continue

            best_room = max(boundary_counts, key=boundary_counts.get)
            for cell in comp:
                self.grid[cell] = best_room
                self.rooms[best_room].cells.add(cell)

    def adjacency_report(self) -> dict[str, set[str]]:
        report = {room.name: set() for room in self.rooms}
        for x in range(self.width):
            for y in range(self.height):
                a = self.grid[x, y]
                for nx, ny in neighbors4(x, y, self.width, self.height):
                    b = self.grid[nx, ny]
                    if a != b and a != -1 and b != -1:
                        report[self.rooms[a].name].add(self.rooms[b].name)
        return report

    def score_layout(self) -> tuple[int, int]:
        """Returns (wanted_adjacencies_hit, outside_rooms_touching_edge)."""
        adj = self.adjacency_report()

        wanted_hits = 0
        outside_hits = 0

        for room in self.rooms:
            for other_name in adj[room.name]:
                other_room = next(r for r in self.rooms if r.name == other_name)
                if other_room.room_type in room.wanted_neighbors:
                    wanted_hits += 1

            if room.outside_connection:
                if any(is_edge(x, y, self.width, self.height) for x, y in room.cells):
                    outside_hits += 1

        return wanted_hits, outside_hits

    def generate(self):
        self.place_seeds()
        self.grow_rooms()
        self.fill_empty()
        return self.grid, self.rooms


# ============================================================
# Plotting
# ============================================================

def plot_floorplan(grid: np.ndarray, rooms: list[RoomSpec], title: str = "Neighbor-Aware Floor Plan"):
    fig, ax = plt.subplots(figsize=(10, 8))

    cmap = plt.cm.get_cmap("tab20", len(rooms))
    width, height = grid.shape

    # Draw cells
    for x in range(width):
        for y in range(height):
            idx = grid[x, y]
            if idx >= 0:
                rect = Rectangle((x, y), 1, 1, facecolor=cmap(idx), edgecolor="black", linewidth=0.8)
                ax.add_patch(rect)

    # Label rooms at centroid
    for idx, room in enumerate(rooms):
        xs = [c[0] + 0.5 for c in room.cells]
        ys = [c[1] + 0.5 for c in room.cells]
        if xs and ys:
            ax.text(
                sum(xs) / len(xs),
                sum(ys) / len(ys),
                f"{room.name}\n{room.area}",
                ha="center",
                va="center",
                fontsize=9,
                color="black",
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=1.5),
            )

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xticks(range(width + 1))
    ax.set_yticks(range(height + 1))
    ax.grid(True, linewidth=0.5, alpha=0.4)
    plt.tight_layout()
    plt.show()


# ============================================================
# Example usage
# ============================================================

def build_example_rooms():
    return [
        make_room("Common", "common"),
        make_room("Kitchen", "kitchen"),
        make_room("Dining", "diningroom"),
        make_room("Bedroom 1", "bedroom"),
        make_room("Bedroom 2", "bedroom"),
        make_room("Bathroom", "bathroom"),
        make_room("Office", "office"),
        make_room("Garage", "garage"),
        make_room("Pantry", "pantry"),
    ]


if __name__ == "__main__":
    best = None
    best_score = (-1, -1)

    # Try several seeds and keep the best layout
    for trial_seed in range(40):
        rooms = build_example_rooms()
        gen = FloorPlanGenerator(width=16, height=12, room_specs=rooms, seed=trial_seed)
        grid, rooms_out = gen.generate()
        score = gen.score_layout()

        if score > best_score:
            best_score = score
            best = (grid.copy(), rooms_out, trial_seed)

    grid, rooms_out, trial_seed = best
    print(f"Best seed: {trial_seed}")
    print(f"Wanted-adjacency hits / outside hits: {best_score}")

    adj = FloorPlanGenerator(16, 12, build_example_rooms(), seed=trial_seed)
    adj.grid = grid.copy()
    adj.rooms = rooms_out
    report = adj.adjacency_report()

    print("\nAdjacency report:")
    for room_name, neighbors in report.items():
        print(f"  {room_name}: {sorted(neighbors)}")

    plot_floorplan(grid, rooms_out, title=f"Neighbor-Aware Floor Plan (seed={trial_seed})")