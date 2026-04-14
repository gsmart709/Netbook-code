import random
from collections import deque

MIN_WIDTH = 25
MAX_WIDTH = 49   # odd only
MIN_HEIGHT = 19
MAX_HEIGHT = 37  # odd only

MIN_LEAF_WIDTH = 7
MIN_LEAF_HEIGHT = 7
MAX_SPLIT_DEPTH = 4

ROOM_LABELS = [
    "Kitchen",
    "Common",
    "Bedroom",
    "Bathroom",
    "Office",
    "Dining",
    "Storage",
    "Garage",
    "Laundry",
]


def odd_rand(a, b):
    vals = [n for n in range(a, b + 1) if n % 2 == 1]
    return random.choice(vals)


def room_center(room):
    cx = (room["x1"] + room["x2"]) // 2
    cy = (room["y1"] + room["y2"]) // 2
    return cx, cy


def make_grid(width, height, fill="#"):
    return [[fill for _ in range(width)] for _ in range(height)]


def in_bounds(x, y, width, height):
    return 0 <= x < width and 0 <= y < height


def neighbors4(x, y):
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def is_walkable(cell):
    return cell != "#"


def bfs_path(grid, start, goal):
    if start is None or goal is None:
        return None

    height = len(grid)
    width = len(grid[0])

    q = deque([start])
    prev = {start: None}

    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            break

        for nx, ny in neighbors4(x, y):
            if not in_bounds(nx, ny, width, height):
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


class BSPNode:
    def __init__(self, x1, y1, x2, y2, depth=0):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.depth = depth
        self.left = None
        self.right = None
        self.split_orientation = None
        self.room = None

    @property
    def width(self):
        return self.x2 - self.x1 + 1

    @property
    def height(self):
        return self.y2 - self.y1 + 1

    def is_leaf(self):
        return self.left is None and self.right is None


def can_split_vert(node):
    return node.width >= (MIN_LEAF_WIDTH * 2 + 1)


def can_split_horiz(node):
    return node.height >= (MIN_LEAF_HEIGHT * 2 + 1)


def split_node(node):
    if node.depth >= MAX_SPLIT_DEPTH:
        return False

    vert_ok = can_split_vert(node)
    horiz_ok = can_split_horiz(node)

    if not vert_ok and not horiz_ok:
        return False

    if vert_ok and horiz_ok:
        if node.width > node.height:
            orientation = random.choice(["V", "V", "H"])
        elif node.height > node.width:
            orientation = random.choice(["H", "H", "V"])
        else:
            orientation = random.choice(["V", "H"])
    elif vert_ok:
        orientation = "V"
    else:
        orientation = "H"

    if orientation == "V":
        min_split = node.x1 + MIN_LEAF_WIDTH
        max_split = node.x2 - MIN_LEAF_WIDTH
        candidates = [x for x in range(min_split, max_split + 1)]
        if not candidates:
            return False

        split_x = random.choice(candidates)

        node.left = BSPNode(node.x1, node.y1, split_x - 1, node.y2, node.depth + 1)
        node.right = BSPNode(split_x + 1, node.y1, node.x2, node.y2, node.depth + 1)
        node.split_orientation = "V"
        return True

    min_split = node.y1 + MIN_LEAF_HEIGHT
    max_split = node.y2 - MIN_LEAF_HEIGHT
    candidates = [y for y in range(min_split, max_split + 1)]
    if not candidates:
        return False

    split_y = random.choice(candidates)

    node.left = BSPNode(node.x1, node.y1, node.x2, split_y - 1, node.depth + 1)
    node.right = BSPNode(node.x1, split_y + 1, node.x2, node.y2, node.depth + 1)
    node.split_orientation = "H"
    return True


def grow_tree(node):
    if split_node(node):
        grow_tree(node.left)
        grow_tree(node.right)


def collect_leaves(node, out):
    if node.is_leaf():
        out.append(node)
        return
    collect_leaves(node.left, out)
    collect_leaves(node.right, out)


def carve_room(grid, room):
    for y in range(room["y1"] + 1, room["y2"]):
        for x in range(room["x1"] + 1, room["x2"]):
            grid[y][x] = " "


def make_leaf_rooms(leaves, grid):
    rooms = []
    for leaf in leaves:
        room = {
            "x1": leaf.x1,
            "y1": leaf.y1,
            "x2": leaf.x2,
            "y2": leaf.y2,
        }
        leaf.room = room
        rooms.append(room)
        carve_room(grid, room)
    return rooms


def assign_room_types(leaves):
    leaves_sorted = sorted(
        leaves,
        key=lambda n: n.width * n.height,
        reverse=True
    )

    labels = {}

    required = ["Kitchen", "Common", "Bedroom", "Bathroom"]
    remaining_pool = [
        "Dining", "Office", "Bedroom", "Storage",
        "Laundry", "Garage", "Bedroom", "Common"
    ]

    chosen = required[:]
    while len(chosen) < len(leaves_sorted):
        chosen.append(random.choice(remaining_pool))

    random.shuffle(chosen)

    if len(leaves_sorted) >= 2:
        big_labels = ["Common", "Kitchen"]
        random.shuffle(big_labels)
        labels[id(leaves_sorted[0].room)] = big_labels[0]
        labels[id(leaves_sorted[1].room)] = big_labels[1]

        skip_common = False
        skip_kitchen = False
        chosen_remaining = []

        for lab in chosen:
            if lab == "Common" and not skip_common:
                skip_common = True
                continue
            if lab == "Kitchen" and not skip_kitchen:
                skip_kitchen = True
                continue
            chosen_remaining.append(lab)

        for i, leaf in enumerate(leaves_sorted[2:]):
            labels[id(leaf.room)] = chosen_remaining[i]
    elif len(leaves_sorted) == 1:
        labels[id(leaves_sorted[0].room)] = "Common"

    return labels


def carve_door_between(grid, a, b, orientation):
    if orientation == "V":
        wall_x = a.x2 + 1
        overlap_y1 = max(a.y1 + 1, b.y1 + 1)
        overlap_y2 = min(a.y2 - 1, b.y2 - 1)
        candidates = [y for y in range(overlap_y1, overlap_y2 + 1)]

        if candidates:
            door_y = random.choice(candidates)
            grid[door_y][wall_x] = "."
            return True

        # fallback
        y = max(a.y1 + 1, min((a.y1 + a.y2) // 2, a.y2 - 1))
        if 0 <= wall_x < len(grid[0]) and 0 <= y < len(grid):
            grid[y][wall_x] = "."
            return True

        return False

    wall_y = a.y2 + 1
    overlap_x1 = max(a.x1 + 1, b.x1 + 1)
    overlap_x2 = min(a.x2 - 1, b.x2 - 1)
    candidates = [x for x in range(overlap_x1, overlap_x2 + 1)]

    if candidates:
        door_x = random.choice(candidates)
        grid[wall_y][door_x] = "."
        return True

    # fallback
    x = max(a.x1 + 1, min((a.x1 + a.x2) // 2, a.x2 - 1))
    if 0 <= x < len(grid[0]) and 0 <= wall_y < len(grid):
        grid[wall_y][x] = "."
        return True

    return False


def connect_tree(grid, node):
    if node.is_leaf():
        return

    connect_tree(grid, node.left)
    connect_tree(grid, node.right)
    carve_door_between(grid, node.left, node.right, node.split_orientation)


def get_exterior_candidates(room, width, height):
    candidates = []

    # top wall
    if room["y1"] == 1:
        for x in range(room["x1"] + 1, room["x2"]):
            candidates.append((x, room["y1"], x, 0))

    # bottom wall
    if room["y2"] == height - 2:
        for x in range(room["x1"] + 1, room["x2"]):
            candidates.append((x, room["y2"], x, height - 1))

    # left wall
    if room["x1"] == 1:
        for y in range(room["y1"] + 1, room["y2"]):
            candidates.append((room["x1"], y, 0, y))

    # right wall
    if room["x2"] == width - 2:
        for y in range(room["y1"] + 1, room["y2"]):
            candidates.append((room["x2"], y, width - 1, y))

    return candidates


def place_marker_on_exterior(grid, room, marker, width, height, avoid_wall=None):
    candidates = get_exterior_candidates(room, width, height)

    if avoid_wall is not None:
        candidates = [c for c in candidates if c[2:] != avoid_wall]

    if not candidates:
        return None

    inside_x, inside_y, outer_x, outer_y = random.choice(candidates)
    grid[inside_y][inside_x] = marker
    grid[outer_y][outer_x] = marker
    return (outer_x, outer_y), (inside_x, inside_y)


def find_room_by_label(rooms, labels, label):
    for room in rooms:
        if labels[id(room)] == label:
            return room
    return None


def score_room_shapes(rooms):
    score = 0.0
    for room in rooms:
        w = room["x2"] - room["x1"] - 1
        h = room["y2"] - room["y1"] - 1

        if w < 3 or h < 3:
            return -9999

        ratio = max(w / h, h / w)
        score -= (ratio - 1.0) * 5.0
        score += w * h * 0.05

    return score


def count_unique_labels(labels):
    return len(set(labels.values()))


def generate_once(debug=False):
    width = odd_rand(MIN_WIDTH, MAX_WIDTH)
    height = odd_rand(MIN_HEIGHT, MAX_HEIGHT)

    grid = make_grid(width, height, "#")

    root = BSPNode(1, 1, width - 2, height - 2)
    grow_tree(root)

    leaves = []
    collect_leaves(root, leaves)

    if len(leaves) < 4:
        if debug:
            print("Rejected: fewer than 4 leaves")
        return None

    rooms = make_leaf_rooms(leaves, grid)
    connect_tree(grid, root)
    labels = assign_room_types(leaves)

    kitchen = find_room_by_label(rooms, labels, "Kitchen")
    common = find_room_by_label(rooms, labels, "Common")

    if kitchen is None or common is None:
        if debug:
            print("Rejected: missing Kitchen or Common")
        return None

    front = place_marker_on_exterior(grid, common, "F", width, height)
    if front is None:
        if debug:
            print("Rejected: could not place F on Common")
        return None

    front_outer, _ = front

    back = place_marker_on_exterior(
        grid,
        kitchen,
        "B",
        width,
        height,
        avoid_wall=front_outer
    )

    if back is None:
        other_rooms = [r for r in rooms if r is not common]
        random.shuffle(other_rooms)

        placed = None
        for room in other_rooms:
            placed = place_marker_on_exterior(
                grid,
                room,
                "B",
                width,
                height,
                avoid_wall=front_outer
            )
            if placed is not None:
                break

        if placed is None:
            if debug:
                print("Rejected: could not place B")
            return None

        back_outer, _ = placed
    else:
        back_outer, _ = back

    path = bfs_path(grid, front_outer, back_outer)
    if path is None:
        if debug:
            print("Rejected: no F->B path")
        return None

    variety_score = count_unique_labels(labels) * 4.0
    shape_score = score_room_shapes(rooms)
    path_score = len(path) * 0.02
    total_score = variety_score + shape_score + path_score

    return grid, rooms, labels, width, height, total_score


def generate_valid_house(max_attempts=1000, debug=False):
    best = None
    best_score = -10**9
    last_non_none = None

    for attempt in range(1, max_attempts + 1):
        result = generate_once(debug=debug)

        if result is None:
            continue

        last_non_none = result
        grid, rooms, labels, width, height, score = result

        if score > best_score:
            best = (grid, rooms, labels, width, height, attempt)
            best_score = score

        if score > 2:
            if debug:
                print(f"Accepted on attempt {attempt} with score {score:.2f}")
            return grid, rooms, labels, width, height, attempt

    if best is not None:
        if debug:
            print(f"Returning best result after {max_attempts} attempts, score {best_score:.2f}")
        return best

    if last_non_none is not None:
        grid, rooms, labels, width, height, _ = last_non_none
        if debug:
            print("WARNING: Returning last non-none result")
        return grid, rooms, labels, width, height, max_attempts

    raise RuntimeError("Failed to generate a valid house.")


def print_grid(grid):
    for row in grid:
        print("".join(row))


if __name__ == "__main__":
    grid, rooms, labels, width, height, attempts = generate_valid_house(debug=True)

    print(f"\nHouse size: {width} x {height}")
    print(f"Attempts: {attempts}\n")

    print_grid(grid)

    print("\nRooms:")
    for room in rooms:
        print(labels[id(room)], room)