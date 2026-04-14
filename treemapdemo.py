import random
from collections import deque, defaultdict
import matplotlib.pyplot as plt

# =========================================================
# SETTINGS
# =========================================================

HOUSE_WIDTH = 41
HOUSE_HEIGHT = 25

GRID_WALL = "#"
GRID_FLOOR = " "
GRID_DOOR = "."
GRID_FRONT = "F"
GRID_BACK = "B"

MIN_ROOM_W = 4
MIN_ROOM_H = 4

ROOM_AREA_WEIGHTS = {
    "Common": 42,
    "Kitchen": 24,
    "Dining": 18,
    "Bedroom": 24,
    "Bedroom2": 22,
    "Bathroom": 10,
    "Office": 14,
    "Laundry": 10,
    "Storage": 8,
}

# =========================================================
# TREEMAP CORE
# =========================================================

def normalize_sizes(sizes, dx, dy):
    total = sum(sizes)
    return [s * dx * dy / total for s in sizes]


def worst_ratio(row, w):
    if not row:
        return float("inf")
    s = sum(row)
    return max((w * w * max(row)) / (s * s), (s * s) / (w * w * min(row)))


def layout_row(row, x, y, dx, dy):
    rects = []

    if dx >= dy:
        row_h = sum(row) / dx
        cur_x = x
        for r in row:
            row_w = r / row_h
            rects.append((cur_x, y, row_w, row_h))
            cur_x += row_w
        return rects, x, y + row_h, dx, dy - row_h
    else:
        row_w = sum(row) / dy
        cur_y = y
        for r in row:
            row_h = r / row_w
            rects.append((x, cur_y, row_w, row_h))
            cur_y += row_h
        return rects, x + row_w, y, dx - row_w, dy


def squarify(sizes, x, y, dx, dy):
    sizes = sorted(sizes, reverse=True)
    rects = []
    row = []

    while sizes:
        item = sizes[0]
        if not row or worst_ratio(row + [item], min(dx, dy)) <= worst_ratio(row, min(dx, dy)):
            row.append(item)
            sizes.pop(0)
        else:
            new_rects, x, y, dx, dy = layout_row(row, x, y, dx, dy)
            rects.extend(new_rects)
            row = []

    if row:
        new_rects, x, y, dx, dy = layout_row(row, x, y, dx, dy)
        rects.extend(new_rects)

    return rects


# =========================================================
# GRID + PATH
# =========================================================

def make_grid(width, height, fill=GRID_WALL):
    return [[fill for _ in range(width)] for _ in range(height)]


def print_grid(grid):
    for row in grid:
        print("".join(row))


def neighbors4(x, y):
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def in_bounds(x, y, width, height):
    return 0 <= x < width and 0 <= y < height


def is_walkable(cell):
    return cell != GRID_WALL


def bfs_path(grid, start, goal):
    if start is None or goal is None:
        return None

    h = len(grid)
    w = len(grid[0])

    q = deque([start])
    prev = {start: None}

    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            break

        for nx, ny in neighbors4(x, y):
            if not in_bounds(nx, ny, w, h):
                continue
            if (nx, ny) in prev:
                continue
            if not is_walkable(grid[ny][nx]):
                continue
            prev[(nx, ny)] = (x, y)
            q.append((nx, ny))

    if goal not in prev:
        return None

    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def room_center(room):
    return ((room["x1"] + room["x2"]) // 2, (room["y1"] + room["y2"]) // 2)


def find_marker(grid, marker):
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == marker:
                return (x, y)
    return None


# =========================================================
# HOUSE GENERATION
# =========================================================

def quantize_rects(raw_rects, width, height):
    """
    Convert float treemap rectangles into integer grid rooms inside outer shell.
    Uses floor/ceil style boundaries, then clamps and filters bad rooms.
    """
    rooms = []
    for i, (x, y, w, h) in enumerate(raw_rects):
        x1 = max(1, int(round(x)))
        y1 = max(1, int(round(y)))
        x2 = min(width - 2, int(round(x + w)) - 1)
        y2 = min(height - 2, int(round(y + h)) - 1)

        if x2 - x1 + 1 < MIN_ROOM_W or y2 - y1 + 1 < MIN_ROOM_H:
            continue

        rooms.append({
            "id": i,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        })
    return rooms


def assign_zones(rooms, width):
    """
    Ranch-ish:
    left = public
    middle = service
    right = private
    """
    zones = {}
    left_cut = width * 0.42
    right_cut = width * 0.70

    for room in rooms:
        cx, _ = room_center(room)
        if cx < left_cut:
            zones[room["id"]] = "public"
        elif cx > right_cut:
            zones[room["id"]] = "private"
        else:
            zones[room["id"]] = "service"

    return zones


def room_area(room):
    return (room["x2"] - room["x1"] + 1) * (room["y2"] - room["y1"] + 1)


def assign_labels(rooms, zones):
    labels = {}
    public_rooms = sorted([r for r in rooms if zones[r["id"]] == "public"], key=room_area, reverse=True)
    private_rooms = sorted([r for r in rooms if zones[r["id"]] == "private"], key=room_area, reverse=True)
    service_rooms = sorted([r for r in rooms if zones[r["id"]] == "service"], key=room_area, reverse=True)

    # Public
    if public_rooms:
        labels[public_rooms[0]["id"]] = "Common"
    if len(public_rooms) > 1:
        labels[public_rooms[1]["id"]] = "Kitchen"
    if len(public_rooms) > 2:
        labels[public_rooms[2]["id"]] = "Dining"
    for r in public_rooms[3:]:
        labels[r["id"]] = random.choice(["Dining", "Office", "Common"])

    # Private
    if private_rooms:
        labels[private_rooms[0]["id"]] = "Bedroom"
    if len(private_rooms) > 1:
        labels[private_rooms[1]["id"]] = "Bedroom"
    if len(private_rooms) > 2:
        labels[private_rooms[2]["id"]] = "Bathroom"
    for r in private_rooms[3:]:
        labels[r["id"]] = random.choice(["Bathroom", "Office", "Bedroom"])

    # Service
    service_sequence = ["Laundry", "Storage", "Office"]
    for i, r in enumerate(service_rooms):
        if i < len(service_sequence):
            labels[r["id"]] = service_sequence[i]
        else:
            labels[r["id"]] = random.choice(["Laundry", "Storage", "Office"])

    # Hard guarantees
    biggest = sorted(rooms, key=room_area, reverse=True)
    present = set(labels.values())

    needed = ["Common", "Kitchen", "Bedroom", "Bathroom"]
    for i, need in enumerate(needed):
        if need not in present and i < len(biggest):
            labels[biggest[i]["id"]] = need
            present.add(need)

    return labels


def rooms_share_wall(a, b):
    """
    Returns adjacency info if they share a wall segment:
    ('V', wall_x, y1, y2) or ('H', wall_y, x1, x2)
    """
    # vertical shared wall
    if a["x2"] + 1 == b["x1"] or b["x2"] + 1 == a["x1"]:
        wall_x = min(a["x2"], b["x2"]) + 1 if a["x2"] < b["x2"] else min(a["x1"], b["x1"])
        overlap_y1 = max(a["y1"], b["y1"])
        overlap_y2 = min(a["y2"], b["y2"])
        if overlap_y2 >= overlap_y1:
            # exact wall x between them
            if a["x2"] + 1 == b["x1"]:
                return ("V", a["x2"] + 1, overlap_y1, overlap_y2)
            else:
                return ("V", b["x2"] + 1, overlap_y1, overlap_y2)

    # horizontal shared wall
    if a["y2"] + 1 == b["y1"] or b["y2"] + 1 == a["y1"]:
        overlap_x1 = max(a["x1"], b["x1"])
        overlap_x2 = min(a["x2"], b["x2"])
        if overlap_x2 >= overlap_x1:
            if a["y2"] + 1 == b["y1"]:
                return ("H", a["y2"] + 1, overlap_x1, overlap_x2)
            else:
                return ("H", b["y2"] + 1, overlap_x1, overlap_x2)

    return None


def build_adjacency(rooms):
    adj = defaultdict(list)
    shared = {}

    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            info = rooms_share_wall(rooms[i], rooms[j])
            if info is not None:
                a = rooms[i]["id"]
                b = rooms[j]["id"]
                adj[a].append(b)
                adj[b].append(a)
                shared[(a, b)] = info
                shared[(b, a)] = info
    return adj, shared


def carve_room_floor(grid, room):
    for y in range(room["y1"], room["y2"] + 1):
        for x in range(room["x1"], room["x2"] + 1):
            grid[y][x] = GRID_FLOOR


def carve_all_rooms(grid, rooms):
    for room in rooms:
        carve_room_floor(grid, room)


def choose_door_point(shared_info):
    kind = shared_info[0]
    if kind == "V":
        _, wall_x, y1, y2 = shared_info
        return (wall_x, random.randint(y1, y2))
    else:
        _, wall_y, x1, x2 = shared_info
        return (random.randint(x1, x2), wall_y)


def make_graph_connected(room_ids, adj):
    """
    Build a spanning tree over the adjacency graph so all rooms connect.
    """
    if not room_ids:
        return []

    start = room_ids[0]
    visited = {start}
    edges = []

    frontier = [(start, nbr) for nbr in adj[start]]
    random.shuffle(frontier)

    while frontier:
        a, b = frontier.pop()
        if b in visited:
            continue
        visited.add(b)
        edges.append((a, b))
        nbrs = [(b, nxt) for nxt in adj[b] if nxt not in visited]
        random.shuffle(nbrs)
        frontier.extend(nbrs)

    # if graph somehow disconnected, connect components greedily where possible
    unvisited = [rid for rid in room_ids if rid not in visited]
    if unvisited:
        return None

    return edges


def add_extra_doors(tree_edges, adj, extra_ratio=0.25):
    tree_set = set(tuple(sorted(e)) for e in tree_edges)
    all_edges = set()

    for a, nbrs in adj.items():
        for b in nbrs:
            if a < b:
                all_edges.add((a, b))

    leftovers = list(all_edges - tree_set)
    random.shuffle(leftovers)
    extra_count = int(len(leftovers) * extra_ratio)

    return tree_edges + leftovers[:extra_count]


def place_interior_doors(grid, edges, shared_lookup):
    for a, b in edges:
        info = shared_lookup[(a, b)]
        x, y = choose_door_point(info)
        grid[y][x] = GRID_DOOR


def touches_exterior(room, width, height):
    return room["x1"] == 1 or room["x2"] == width - 2 or room["y1"] == 1 or room["y2"] == height - 2


def get_exterior_candidates(room, width, height):
    candidates = []

    if room["y1"] == 1:
        for x in range(room["x1"], room["x2"] + 1):
            candidates.append((x, room["y1"], x, 0))
    if room["y2"] == height - 2:
        for x in range(room["x1"], room["x2"] + 1):
            candidates.append((x, room["y2"], x, height - 1))
    if room["x1"] == 1:
        for y in range(room["y1"], room["y2"] + 1):
            candidates.append((room["x1"], y, 0, y))
    if room["x2"] == width - 2:
        for y in range(room["y1"], room["y2"] + 1):
            candidates.append((room["x2"], y, width - 1, y))

    return candidates


def place_exterior_marker(grid, room, marker, width, height, avoid_outer=None):
    candidates = get_exterior_candidates(room, width, height)
    if avoid_outer is not None:
        candidates = [c for c in candidates if (c[2], c[3]) != avoid_outer]
    if not candidates:
        return None

    inside_x, inside_y, outer_x, outer_y = random.choice(candidates)
    grid[inside_y][inside_x] = marker
    grid[outer_y][outer_x] = marker
    return (outer_x, outer_y), (inside_x, inside_y)


def validate_house(rooms, labels, zones, adj):
    by_label = defaultdict(list)
    for room in rooms:
        by_label[labels[room["id"]]].append(room)

    if not by_label["Common"] or not by_label["Kitchen"] or not by_label["Bedroom"] or not by_label["Bathroom"]:
        return False

    common = by_label["Common"][0]
    kitchen = by_label["Kitchen"][0]
    common_id = common["id"]
    kitchen_id = kitchen["id"]

    # kitchen should touch common or dining
    good_kitchen_neighbor = False
    for nbr in adj[kitchen_id]:
        nbr_label = labels[nbr]
        if nbr_label in ("Common", "Dining", "Laundry"):
            good_kitchen_neighbor = True
            break
    if not good_kitchen_neighbor:
        return False

    # bathroom should not be public
    bath = by_label["Bathroom"][0]
    if zones[bath["id"]] == "public":
        return False

    # at least one bedroom should be private
    if not any(zones[r["id"]] == "private" for r in by_label["Bedroom"]):
        return False

    # common should be public if possible
    if zones[common_id] != "public":
        return False

    return True


def generate_treemap_house(width=HOUSE_WIDTH, height=HOUSE_HEIGHT, max_attempts=200):
    room_names = ["Common", "Kitchen", "Dining", "Bedroom", "Bedroom2", "Bathroom", "Office", "Laundry", "Storage"]
    sizes = [ROOM_AREA_WEIGHTS[name] for name in room_names]

    for attempt in range(1, max_attempts + 1):
        norm = normalize_sizes(sizes, width - 2, height - 2)
        raw_rects = squarify(norm, 1, 1, width - 2, height - 2)

        rooms = quantize_rects(raw_rects, width, height)
        if len(rooms) < 6:
            continue

        zones = assign_zones(rooms, width)
        labels = assign_labels(rooms, zones)
        adj, shared = build_adjacency(rooms)

        room_ids = [r["id"] for r in rooms]
        tree_edges = make_graph_connected(room_ids, adj)
        if tree_edges is None:
            continue

        if not validate_house(rooms, labels, zones, adj):
            continue

        grid = make_grid(width, height, GRID_WALL)
        carve_all_rooms(grid, rooms)

        all_edges = add_extra_doors(tree_edges, adj, extra_ratio=0.22)
        place_interior_doors(grid, all_edges, shared)

        exterior_rooms = [r for r in rooms if touches_exterior(r, width, height)]
        if len(exterior_rooms) < 2:
            continue

        common_exterior = [r for r in exterior_rooms if labels[r["id"]] == "Common"]
        front_room = random.choice(common_exterior if common_exterior else exterior_rooms)

        front = place_exterior_marker(grid, front_room, GRID_FRONT, width, height)
        if front is None:
            continue
        front_outer, _ = front

        back_choices = [r for r in exterior_rooms if r["id"] != front_room["id"]]
        if not back_choices:
            continue

        kitchen_exterior = [r for r in back_choices if labels[r["id"]] == "Kitchen"]
        private_exterior = [r for r in back_choices if zones[r["id"]] == "private"]
        back_room = random.choice(kitchen_exterior or private_exterior or back_choices)

        back = place_exterior_marker(grid, back_room, GRID_BACK, width, height, avoid_outer=front_outer)
        if back is None:
            continue

        path = bfs_path(grid, find_marker(grid, GRID_FRONT), find_marker(grid, GRID_BACK))
        if path is None:
            continue

        return grid, rooms, labels, zones, width, height, attempt, path

    raise RuntimeError("Failed to generate a treemap house.")


# =========================================================
# PLOTTING
# =========================================================

def plot_house(grid, rooms, labels, width, height, path=None, title="Treemap House"):
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_facecolor("white")

    for y in range(height):
        for x in range(width):
            cell = grid[y][x]
            if cell == GRID_WALL:
                rect = plt.Rectangle((x, height - y - 1), 1, 1)
                ax.add_patch(rect)
            else:
                rect = plt.Rectangle(
                    (x, height - y - 1), 1, 1,
                    fill=False, linewidth=0.35, edgecolor="lightgray"
                )
                ax.add_patch(rect)

    if path:
        xs = [x + 0.5 for x, y in path]
        ys = [height - y - 0.5 for x, y in path]
        ax.plot(xs, ys, linewidth=2)

    for room in rooms:
        cx, cy = room_center(room)
        label = labels[room["id"]]
        if label == "Bedroom2":
            label = "Bedroom"
        ax.text(
            cx + 0.5,
            height - cy - 0.5,
            label,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.85),
        )

    for y in range(height):
        for x in range(width):
            cell = grid[y][x]
            if cell in (GRID_FRONT, GRID_BACK):
                ax.text(
                    x + 0.5,
                    height - y - 0.5,
                    cell,
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    grid, rooms, labels, zones, width, height, attempts, path = generate_treemap_house()

    print(f"Generated in {attempts} attempt(s)")
    print()
    print_grid(grid)
    print()
    for room in sorted(rooms, key=lambda r: r["id"]):
        label = labels[room["id"]]
        if label == "Bedroom2":
            label = "Bedroom"
        print(f"{label:10s} zone={zones[room['id']]:7s} bounds={room}")

    plot_house(grid, rooms, labels, width, height, path=path, title="Treemap House with F→B Path")