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
    Loose zoning only. Used mostly for scoring.
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
    """
    Much looser labeling than before. Less likely to reject everything.
    """
    labels = {}

    rooms_sorted = sorted(rooms, key=room_area, reverse=True)

    public_rooms = [r for r in rooms_sorted if zones[r["id"]] == "public"]
    private_rooms = [r for r in rooms_sorted if zones[r["id"]] == "private"]
    service_rooms = [r for r in rooms_sorted if zones[r["id"]] == "service"]

    # Try to place sensible labels first
    if public_rooms:
        labels[public_rooms[0]["id"]] = "Common"
    if len(public_rooms) > 1:
        labels[public_rooms[1]["id"]] = "Kitchen"
    if len(public_rooms) > 2:
        labels[public_rooms[2]["id"]] = "Dining"

    if private_rooms:
        labels[private_rooms[0]["id"]] = "Bedroom"
    if len(private_rooms) > 1:
        labels[private_rooms[1]["id"]] = "Bedroom"
    if len(private_rooms) > 2:
        labels[private_rooms[2]["id"]] = "Bathroom"

    service_defaults = ["Laundry", "Storage", "Office"]
    for i, room in enumerate(service_rooms):
        if room["id"] in labels:
            continue
        if i < len(service_defaults):
            labels[room["id"]] = service_defaults[i]
        else:
            labels[room["id"]] = random.choice(["Office", "Storage", "Laundry"])

    # Fill unlabeled rooms
    fallback_pool = [
        "Office", "Dining", "Storage", "Laundry",
        "Bedroom", "Bathroom", "Common", "Kitchen"
    ]
    for room in rooms_sorted:
        if room["id"] not in labels:
            labels[room["id"]] = random.choice(fallback_pool)

    # Hard guarantees only
    values = set(labels.values())
    required = ["Common", "Kitchen", "Bedroom", "Bathroom"]
    for i, need in enumerate(required):
        if need not in values and i < len(rooms_sorted):
            labels[rooms_sorted[i]["id"]] = need
            values.add(need)

    return labels


def rooms_share_wall(a, b):
    """
    Returns:
      ("V", wall_x, y1, y2) for vertical wall
      ("H", wall_y, x1, x2) for horizontal wall
    """
    if a["x2"] + 1 == b["x1"]:
        overlap_y1 = max(a["y1"], b["y1"])
        overlap_y2 = min(a["y2"], b["y2"])
        if overlap_y2 >= overlap_y1:
            return ("V", a["x2"] + 1, overlap_y1, overlap_y2)

    if b["x2"] + 1 == a["x1"]:
        overlap_y1 = max(a["y1"], b["y1"])
        overlap_y2 = min(a["y2"], b["y2"])
        if overlap_y2 >= overlap_y1:
            return ("V", b["x2"] + 1, overlap_y1, overlap_y2)

    if a["y2"] + 1 == b["y1"]:
        overlap_x1 = max(a["x1"], b["x1"])
        overlap_x2 = min(a["x2"], b["x2"])
        if overlap_x2 >= overlap_x1:
            return ("H", a["y2"] + 1, overlap_x1, overlap_x2)

    if b["y2"] + 1 == a["y1"]:
        overlap_x1 = max(a["x1"], b["x1"])
        overlap_x2 = min(a["x2"], b["x2"])
        if overlap_x2 >= overlap_x1:
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

    _, wall_y, x1, x2 = shared_info
    return (random.randint(x1, x2), wall_y)


def make_graph_connected(room_ids, adj):
    """
    Build a spanning tree over adjacency graph.
    """
    if not room_ids:
        return None

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

    if len(visited) != len(room_ids):
        return None

    return edges


def add_extra_doors(tree_edges, adj, extra_ratio=0.25):
    tree_set = {tuple(sorted(e)) for e in tree_edges}
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
        info = shared_lookup.get((a, b))
        if info is None:
            continue
        x, y = choose_door_point(info)
        grid[y][x] = GRID_DOOR


def touches_exterior(room, width, height):
    return (
        room["x1"] == 1
        or room["x2"] == width - 2
        or room["y1"] == 1
        or room["y2"] == height - 2
    )


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
    """
    Soft validation. Only reject layouts that are truly busted.
    """
    by_label = defaultdict(list)
    for room in rooms:
        by_label[labels[room["id"]]].append(room)

    required = ["Common", "Kitchen", "Bedroom", "Bathroom"]
    for label in required:
        if not by_label[label]:
            return False

    kitchen = by_label["Kitchen"][0]
    kitchen_ok = False
    for nbr in adj[kitchen["id"]]:
        if labels[nbr] in ("Common", "Dining", "Laundry", "Office"):
            kitchen_ok = True
            break

    bedroom_ok = any(zones[r["id"]] == "private" for r in by_label["Bedroom"])

    # only truly hard fail if both are garbage
    if not kitchen_ok and not bedroom_ok:
        return False

    return True


def score_layout(rooms, labels, zones, adj, path_len):
    score = 0.0

    for room in rooms:
        area = room_area(room)
        w = room["x2"] - room["x1"] + 1
        h = room["y2"] - room["y1"] + 1
        ratio = max(w / h, h / w)

        score += area * 0.03
        score -= (ratio - 1.0) * 3.0

        label = labels[room["id"]]
        zone = zones[room["id"]]

        if label == "Common":
            score += 3
        if label == "Kitchen":
            score += 2
        if label == "Bedroom":
            score += 1.5

        if label in ("Common", "Kitchen", "Dining") and zone == "public":
            score += 1.5
        if label in ("Bedroom", "Bathroom") and zone == "private":
            score += 1.5
        if label in ("Laundry", "Storage", "Office") and zone == "service":
            score += 1.0

        if label == "Bathroom" and area > 80:
            score -= 4
        if label == "Storage" and area > 90:
            score -= 4

    # reward useful kitchen adjacency
    kitchen_ids = [rid for rid, lab in labels.items() if lab == "Kitchen"]
    if kitchen_ids:
        k = kitchen_ids[0]
        useful = 0
        for nbr in adj[k]:
            if labels[nbr] in ("Common", "Dining", "Laundry"):
                useful += 1
        score += useful * 2.0

    score += len(set(labels.values())) * 0.8
    score += path_len * 0.03

    return score


def generate_treemap_house(width=HOUSE_WIDTH, height=HOUSE_HEIGHT, max_attempts=600, debug=False):
    room_names = [
        "Common", "Kitchen", "Dining",
        "Bedroom", "Bedroom2", "Bathroom",
        "Office", "Laundry", "Storage"
    ]
    sizes = [ROOM_AREA_WEIGHTS[name] for name in room_names]

    best_result = None
    best_score = float("-inf")

    for attempt in range(1, max_attempts + 1):
        norm = normalize_sizes(sizes, width - 2, height - 2)
        raw_rects = squarify(norm, 1, 1, width - 2, height - 2)

        rooms = quantize_rects(raw_rects, width, height)
        if len(rooms) < 6:
            if debug:
                print("Rejected: too few quantized rooms")
            continue

        zones = assign_zones(rooms, width)
        labels = assign_labels(rooms, zones)
        adj, shared = build_adjacency(rooms)

        room_ids = [r["id"] for r in rooms]
        tree_edges = make_graph_connected(room_ids, adj)
        if tree_edges is None:
            if debug:
                print("Rejected: adjacency graph disconnected")
            continue

        if not validate_house(rooms, labels, zones, adj):
            if debug:
                print("Rejected: soft validation failed")
            continue

        grid = make_grid(width, height, GRID_WALL)
        carve_all_rooms(grid, rooms)

        all_edges = add_extra_doors(tree_edges, adj, extra_ratio=0.22)
        place_interior_doors(grid, all_edges, shared)

        exterior_rooms = [r for r in rooms if touches_exterior(r, width, height)]
        if len(exterior_rooms) < 2:
            if debug:
                print("Rejected: fewer than 2 exterior rooms")
            continue

        common_exterior = [r for r in exterior_rooms if labels[r["id"]] == "Common"]
        front_room = random.choice(common_exterior if common_exterior else exterior_rooms)

        front = place_exterior_marker(grid, front_room, GRID_FRONT, width, height)
        if front is None:
            if debug:
                print("Rejected: failed placing F")
            continue

        front_outer, _ = front

        back_choices = [r for r in exterior_rooms if r["id"] != front_room["id"]]
        if not back_choices:
            if debug:
                print("Rejected: no back choices")
            continue

        kitchen_exterior = [r for r in back_choices if labels[r["id"]] == "Kitchen"]
        private_exterior = [r for r in back_choices if zones[r["id"]] == "private"]
        back_room = random.choice(kitchen_exterior or private_exterior or back_choices)

        back = place_exterior_marker(grid, back_room, GRID_BACK, width, height, avoid_outer=front_outer)
        if back is None:
            if debug:
                print("Rejected: failed placing B")
            continue

        path = bfs_path(grid, find_marker(grid, GRID_FRONT), find_marker(grid, GRID_BACK))
        if path is None:
            if debug:
                print("Rejected: no F->B path")
            continue

        score = score_layout(rooms, labels, zones, adj, len(path))

        if score > best_score:
            best_score = score
            best_result = (grid, rooms, labels, zones, width, height, attempt, path)

        if score > 8:
            if debug:
                print(f"Accepted on attempt {attempt}, score={score:.2f}")
            return grid, rooms, labels, zones, width, height, attempt, path

    if best_result is not None:
        if debug:
            print(f"Returning best result after {max_attempts} attempts, score={best_score:.2f}")
        return best_result

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
    grid, rooms, labels, zones, width, height, attempts, path = generate_treemap_house(debug=True)

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