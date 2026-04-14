import random
from collections import deque

MIN_WIDTH = 25
MAX_WIDTH = 49   # odd only
MIN_HEIGHT = 19
MAX_HEIGHT = 37  # odd only

MIN_LEAF_WIDTH = 9
MIN_LEAF_HEIGHT = 9
MAX_SPLIT_DEPTH = 4

MIN_ROOM_WIDTH = 5
MIN_ROOM_HEIGHT = 5


def odd_rand(a, b):
    vals = [n for n in range(a, b + 1) if n % 2 == 1]
    return random.choice(vals)


def make_grid(width, height, fill="#"):
    return [[fill for _ in range(width)] for _ in range(height)]


def print_grid(grid):
    for row in grid:
        print("".join(row))


def room_center(room):
    cx = (room["x1"] + room["x2"]) // 2
    cy = (room["y1"] + room["y2"]) // 2
    return cx, cy


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
        if min_split > max_split:
            return False
        split_x = random.randint(min_split, max_split)

        node.left = BSPNode(node.x1, node.y1, split_x - 1, node.y2, node.depth + 1)
        node.right = BSPNode(split_x + 1, node.y1, node.x2, node.y2, node.depth + 1)
        return True

    min_split = node.y1 + MIN_LEAF_HEIGHT
    max_split = node.y2 - MIN_LEAF_HEIGHT
    if min_split > max_split:
        return False
    split_y = random.randint(min_split, max_split)

    node.left = BSPNode(node.x1, node.y1, node.x2, split_y - 1, node.depth + 1)
    node.right = BSPNode(node.x1, split_y + 1, node.x2, node.y2, node.depth + 1)
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
    for y in range(room["y1"], room["y2"] + 1):
        for x in range(room["x1"], room["x2"] + 1):
            grid[y][x] = " "


def carve_h_tunnel(grid, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        grid[y][x] = " "


def carve_v_tunnel(grid, y1, y2, x):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        grid[y][x] = " "


def carve_corridor(grid, a, b):
    ax, ay = a
    bx, by = b

    if random.random() < 0.5:
        carve_h_tunnel(grid, ax, bx, ay)
        carve_v_tunnel(grid, ay, by, bx)
    else:
        carve_v_tunnel(grid, ay, by, ax)
        carve_h_tunnel(grid, ax, bx, by)


def make_room_in_leaf(leaf, house_width, house_height):
    # If the leaf touches the outer shell, allow zero margin on that side
    min_left = 0 if leaf.x1 == 1 else 1
    min_right = 0 if leaf.x2 == house_width - 2 else 1
    min_top = 0 if leaf.y1 == 1 else 1
    min_bottom = 0 if leaf.y2 == house_height - 2 else 1

    max_left = max(min_left, leaf.width - MIN_ROOM_WIDTH - min_right)
    max_right = max(min_right, leaf.width - MIN_ROOM_WIDTH - min_left)
    max_top = max(min_top, leaf.height - MIN_ROOM_HEIGHT - min_bottom)
    max_bottom = max(min_bottom, leaf.height - MIN_ROOM_HEIGHT - min_top)

    if max_left < min_left or max_right < min_right or max_top < min_top or max_bottom < min_bottom:
        return None

    left_margin = random.randint(min_left, max_left)
    right_margin = random.randint(min_right, max_right)
    top_margin = random.randint(min_top, max_top)
    bottom_margin = random.randint(min_bottom, max_bottom)

    x1 = leaf.x1 + left_margin
    x2 = leaf.x2 - right_margin
    y1 = leaf.y1 + top_margin
    y2 = leaf.y2 - bottom_margin

    # tighten if randomness made it too small
    if x2 - x1 + 1 < MIN_ROOM_WIDTH:
        x1 = leaf.x1 + min_left
        x2 = x1 + MIN_ROOM_WIDTH - 1
        if x2 > leaf.x2 - min_right:
            x2 = leaf.x2 - min_right
            x1 = x2 - MIN_ROOM_WIDTH + 1

    if y2 - y1 + 1 < MIN_ROOM_HEIGHT:
        y1 = leaf.y1 + min_top
        y2 = y1 + MIN_ROOM_HEIGHT - 1
        if y2 > leaf.y2 - min_bottom:
            y2 = leaf.y2 - min_bottom
            y1 = y2 - MIN_ROOM_HEIGHT + 1

    if x2 - x1 + 1 < MIN_ROOM_WIDTH or y2 - y1 + 1 < MIN_ROOM_HEIGHT:
        return None

    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def assign_rooms_to_leaves(leaves, grid, house_width, house_height):
    rooms = []

    for leaf in leaves:
        room = make_room_in_leaf(leaf, house_width, house_height)
        if room is None:
            continue
        leaf.room = room
        carve_room(grid, room)
        rooms.append(room)

    return rooms


def get_subtree_room(node):
    if node is None:
        return None
    if node.room is not None:
        return node.room

    left_room = get_subtree_room(node.left)
    right_room = get_subtree_room(node.right)

    if left_room is not None and right_room is not None:
        return random.choice([left_room, right_room])
    return left_room if left_room is not None else right_room


def connect_tree(grid, node):
    if node is None or node.is_leaf():
        return

    connect_tree(grid, node.left)
    connect_tree(grid, node.right)

    left_room = get_subtree_room(node.left)
    right_room = get_subtree_room(node.right)

    if left_room is None or right_room is None:
        return

    a = room_center(left_room)
    b = room_center(right_room)
    carve_corridor(grid, a, b)


def assign_room_labels(rooms):
    labels = {}

    rooms_sorted = sorted(
        rooms,
        key=lambda r: (r["x2"] - r["x1"] + 1) * (r["y2"] - r["y1"] + 1),
        reverse=True,
    )

    required = ["Common", "Kitchen", "Bedroom", "Bathroom"]
    extras = ["Dining", "Office", "Storage", "Laundry", "Garage", "Bedroom", "Bedroom"]

    chosen = required[:]
    while len(chosen) < len(rooms_sorted):
        chosen.append(random.choice(extras))

    if len(rooms_sorted) >= 2:
        labels[id(rooms_sorted[0])] = "Common"
        labels[id(rooms_sorted[1])] = "Kitchen"

        used_common = False
        used_kitchen = False
        remaining = []

        for lab in chosen:
            if lab == "Common" and not used_common:
                used_common = True
                continue
            if lab == "Kitchen" and not used_kitchen:
                used_kitchen = True
                continue
            remaining.append(lab)

        for i, room in enumerate(rooms_sorted[2:]):
            labels[id(room)] = remaining[i]
    elif len(rooms_sorted) == 1:
        labels[id(rooms_sorted[0])] = "Common"

    return labels


def find_room_by_label(rooms, labels, label):
    for room in rooms:
        if labels[id(room)] == label:
            return room
    return None


def room_touches_exterior(room, width, height):
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


def place_marker_on_exterior(grid, room, marker, width, height, avoid_outer=None):
    candidates = get_exterior_candidates(room, width, height)

    if avoid_outer is not None:
        candidates = [c for c in candidates if (c[2], c[3]) != avoid_outer]

    if not candidates:
        return None

    inside_x, inside_y, outer_x, outer_y = random.choice(candidates)
    grid[inside_y][inside_x] = marker
    grid[outer_y][outer_x] = marker
    return (outer_x, outer_y), (inside_x, inside_y)


def score_rooms(rooms, labels):
    score = 0.0
    for room in rooms:
        w = room["x2"] - room["x1"] + 1
        h = room["y2"] - room["y1"] + 1
        ratio = max(w / h, h / w)
        score -= (ratio - 1.0) * 4.0
        score += w * h * 0.03

        label = labels[id(room)]
        if label == "Bathroom" and w * h > 80:
            score -= 5
        if label == "Storage" and w * h > 90:
            score -= 5

    score += len(set(labels.values())) * 2.0
    return score


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
            print("Rejected: too few leaves")
        return None

    rooms = assign_rooms_to_leaves(leaves, grid, width, height)
    if len(rooms) < 4:
        if debug:
            print("Rejected: too few usable rooms")
        return None

    connect_tree(grid, root)
    labels = assign_room_labels(rooms)

    exterior_rooms = [r for r in rooms if room_touches_exterior(r, width, height)]
    if len(exterior_rooms) < 2:
        if debug:
            print("Rejected: fewer than 2 exterior rooms")
        return None

    # Prefer Common for F if possible
    common_exterior = [r for r in exterior_rooms if labels[id(r)] == "Common"]
    if common_exterior:
        front_room = random.choice(common_exterior)
    else:
        front_room = random.choice(exterior_rooms)

    front = place_marker_on_exterior(grid, front_room, "F", width, height)
    if front is None:
        if debug:
            print("Rejected: failed placing F")
        return None

    front_outer, _ = front

    back_candidates = [r for r in exterior_rooms if r is not front_room]
    if not back_candidates:
        if debug:
            print("Rejected: no exterior room left for B")
        return None

    kitchen_exterior = [r for r in back_candidates if labels[id(r)] == "Kitchen"]
    if kitchen_exterior:
        back_room = random.choice(kitchen_exterior)
    else:
        back_room = random.choice(back_candidates)

    back = place_marker_on_exterior(grid, back_room, "B", width, height, avoid_outer=front_outer)
    if back is None:
        if debug:
            print("Rejected: failed placing B")
        return None

    back_outer, _ = back

    path = bfs_path(grid, front_outer, back_outer)
    if path is None:
        if debug:
            print("Rejected: no F->B path")
        return None

    score = score_rooms(rooms, labels) + len(path) * 0.02
    return grid, rooms, labels, width, height, score


def generate_valid_house(max_attempts=300, debug=False):
    best = None
    best_score = -10**9

    for attempt in range(1, max_attempts + 1):
        result = generate_once(debug=debug)
        if result is None:
            continue

        grid, rooms, labels, width, height, score = result

        if score > best_score:
            best = (grid, rooms, labels, width, height, attempt)
            best_score = score

        if score > 0:
            if debug:
                print(f"Accepted on attempt {attempt}, score={score:.2f}")
            return grid, rooms, labels, width, height, attempt

    if best is not None:
        if debug:
            print(f"Returning best after {max_attempts} attempts, score={best_score:.2f}")
        return best

    raise RuntimeError("Failed to generate a valid house.")


if __name__ == "__main__":
    grid, rooms, labels, width, height, attempts = generate_valid_house(debug=True)

    print(f"\nHouse size: {width} x {height}")
    print(f"Attempts: {attempts}\n")
    print_grid(grid)

    print("\nRooms:")
    for room in rooms:
        print(labels[id(room)], room)