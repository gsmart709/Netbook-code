import random
import time
from collections import deque
import matplotlib.pyplot as plt

MIN_WIDTH = 25
MAX_WIDTH = 49   # odd only
MIN_HEIGHT = 19
MAX_HEIGHT = 37  # odd only

ROOM_TYPES_AFTER_FIRST_BED = ["Bedroom", "Office", "Laundry", "Storage", "Garage"]


def odd_choices(start, end):
    return [n for n in range(start, end + 1) if n % 2 == 1]


def log_stage(name, start_time):
    elapsed = time.perf_counter() - start_time
    print(f"{name}... {elapsed:.4f}s")
    return time.perf_counter()


def print_grid(grid):
    for row in grid:
        print("".join(row))


def room_area(room):
    return (room["x2"] - room["x1"] + 1) * (room["y2"] - room["y1"] + 1)


def room_center(room):
    return (room["x1"] + room["x2"]) // 2, (room["y1"] + room["y2"]) // 2


def create_wall_grid(width, height):
    return [["#" for _ in range(width)] for _ in range(height)]


def carve_room(grid, room):
    for y in range(room["y1"], room["y2"] + 1):
        for x in range(room["x1"], room["x2"] + 1):
            grid[y][x] = " "


def carve_cell(grid, x, y, char=" "):
    if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
        grid[y][x] = char


def carve_vertical_corridor(grid, x, y1, y2):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        carve_cell(grid, x, y)


def carve_horizontal_corridor(grid, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        carve_cell(grid, x, y)


def carve_corridor_L(grid, x1, y1, x2, y2):
    if random.random() < 0.5:
        carve_horizontal_corridor(grid, x1, x2, y1)
        carve_vertical_corridor(grid, x2, y1, y2)
    else:
        carve_vertical_corridor(grid, x1, y1, y2)
        carve_horizontal_corridor(grid, x1, x2, y2)


def find_path(grid, start, end, width, height):
    queue = deque([start])
    visited = {start}
    parent = {}

    while queue:
        x, y = queue.popleft()

        if (x, y) == end:
            path = []
            cur = end
            while cur != start:
                path.append(cur)
                cur = parent[cur]
            path.reverse()
            return path

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < width
                and 0 <= ny < height
                and (nx, ny) not in visited
                and grid[ny][nx] != "#"
            ):
                visited.add((nx, ny))
                parent[(nx, ny)] = (x, y)
                queue.append((nx, ny))

    return None


def draw_path(grid, path):
    for x, y in path:
        if grid[y][x] == " ":
            grid[y][x] = "."


def partition_vertical_strip(x1, x2, y1, y2, min_room_h=3, max_room_h=9):
    """
    Split a vertical strip into stacked rooms with 1-cell walls between them.
    """
    rooms = []
    cur_y = y1

    while cur_y <= y2:
        remaining = y2 - cur_y + 1
        if remaining < min_room_h:
            break

        max_h = min(max_room_h, remaining)

        # leave room for another segment + wall if possible
        possible_heights = []
        for h in range(min_room_h, max_h + 1):
            leftover = remaining - h
            if leftover == 0 or leftover >= min_room_h + 1:
                possible_heights.append(h)

        if not possible_heights:
            break

        h = random.choice(possible_heights)
        room = {"x1": x1, "x2": x2, "y1": cur_y, "y2": cur_y + h - 1}
        rooms.append(room)

        cur_y = room["y2"] + 2

    return rooms


def partition_horizontal_strip(x1, x2, y1, y2, min_room_w=5, max_room_w=11):
    """
    Split a horizontal strip into side-by-side rooms with 1-cell walls between them.
    """
    rooms = []
    cur_x = x1

    while cur_x <= x2:
        remaining = x2 - cur_x + 1
        if remaining < min_room_w:
            break

        max_w = min(max_room_w, remaining)

        possible_widths = []
        for w in range(min_room_w, max_w + 1):
            leftover = remaining - w
            if leftover == 0 or leftover >= min_room_w + 1:
                possible_widths.append(w)

        if not possible_widths:
            break

        w = random.choice(possible_widths)
        room = {"x1": cur_x, "x2": cur_x + w - 1, "y1": y1, "y2": y2}
        rooms.append(room)

        cur_x = room["x2"] + 2

    return rooms


def choose_room_labels(candidate_rooms, width, height):
    """
    Label rooms after geometry is set.

    Rules:
    - smallest room = Bath
    - must have at least one Bedroom
    - remaining use Bedroom/Office/Laundry/Storage/Garage
      with no repeats except Bedroom
    """
    rooms_sorted = sorted(candidate_rooms, key=room_area)
    labels = {}

    # smallest room becomes Bath
    bath_room = rooms_sorted[0]
    labels[id(bath_room)] = "Bath"

    remaining = [r for r in rooms_sorted if id(r) not in labels]

    # first bedroom: choose the largest remaining so it feels like a real bedroom
    if remaining:
        first_bedroom = max(remaining, key=room_area)
        labels[id(first_bedroom)] = "Bedroom"
        remaining = [r for r in remaining if id(r) not in labels]

    available_unique = ["Office", "Laundry", "Storage", "Garage"]

    for room in remaining:
        # Bedroom can always repeat
        choices = ["Bedroom"] + available_unique[:]
        chosen = random.choice(choices)

        if chosen != "Bedroom" and chosen in available_unique:
            available_unique.remove(chosen)

        labels[id(room)] = chosen

    return labels


def assign_final_labels(rooms, width, height):
    labels = {}

    special_rooms = []
    candidate_rooms = []

    for room in rooms:
        if room["type"] in {"Kitchen", "Dining", "Common", "Porch"}:
            labels[id(room)] = room["type"]
            special_rooms.append(room)
        else:
            candidate_rooms.append(room)

    generated = choose_room_labels(candidate_rooms, width, height)
    labels.update(generated)

    # 50% chance bottom-right Bedroom becomes Garage
    for room in candidate_rooms:
        if (
            labels[id(room)] == "Bedroom"
            and room["x2"] == width - 2
            and room["y2"] == height - 2
            and random.random() < 0.5
        ):
            labels[id(room)] = "Garage"

    return labels


def validate_room_sizes(rooms, labels):
    common = next(r for r in rooms if labels[id(r)] == "Common")
    kitchen = next(r for r in rooms if labels[id(r)] == "Kitchen")
    bath = next(r for r in rooms if labels[id(r)] == "Bath")
    bedrooms = [r for r in rooms if labels[id(r)] == "Bedroom"]

    if room_area(common) <= room_area(kitchen):
        return False, "common not bigger than kitchen"

    if bedrooms and not all(room_area(common) > room_area(b) for b in bedrooms):
        return False, "common not bigger than bedroom"

    if bedrooms and not all(room_area(b) > room_area(bath) for b in bedrooms):
        return False, "bedroom not bigger than bath"

    bw = bath["x2"] - bath["x1"] + 1
    bh = bath["y2"] - bath["y1"] + 1
    if max(bw, bh) > 5:
        return False, "bath too large"

    return True, "ok"


def build_house_layout(width, height):
    grid = create_wall_grid(width, height)

    kitchen_side = random.choice(["left", "right"])

    # 1) overall dimensions already chosen
    # 2) kitchen in either left or right back
    kitchen_h = random.choice([5, 7, 9])
    kitchen_w = random.choice([5, 7, 9])

    if kitchen_side == "left":
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": kitchen_h}
        dining = {"type": "Dining", "x1": kitchen_w + 2, "x2": width - 2, "y1": 1, "y2": kitchen_h}
    else:
        kitchen = {"type": "Kitchen", "x1": width - kitchen_w - 1, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        dining = {"type": "Dining", "x1": 1, "x2": kitchen["x1"] - 2, "y1": 1, "y2": kitchen_h}

    if room_area(kitchen) < 25:
        return None, "kitchen too small"
    if dining["x2"] - dining["x1"] + 1 < 7:
        return None, "dining too small"

    # 3–8) build around a central common room
    lower_y1 = kitchen_h + 3
    lower_y2 = height - 2

    common_margin_x = random.choice([7, 9, 11])
    common_x1 = common_margin_x
    common_x2 = width - common_margin_x - 1

    common_margin_bottom = random.choice([3, 5, 7])
    common_y1 = lower_y1
    common_y2 = height - common_margin_bottom

    common = {"type": "Common", "x1": common_x1, "x2": common_x2, "y1": common_y1, "y2": common_y2}

    if common["x2"] - common["x1"] + 1 < 9:
        return None, "common too narrow"
    if common["y2"] - common["y1"] + 1 < 7:
        return None, "common too short"

    # 9) optionally make a porch if common is large enough
    porch = None
    if room_area(common) > 140 and random.random() < 0.6:
        porch_w = random.choice([5, 7])
        common_cx, _ = room_center(common)
        porch_x1 = common_cx - porch_w // 2
        porch_x2 = porch_x1 + porch_w - 1
        porch_y2 = height - 2
        porch_y1 = porch_y2 - 2
        porch = {"type": "Porch", "x1": porch_x1, "x2": porch_x2, "y1": porch_y1, "y2": porch_y2}

        common["y2"] = porch_y1 - 2
        if common["y2"] - common["y1"] + 1 < 5:
            porch = None
            common["y2"] = height - common_margin_bottom

    rooms = [kitchen, dining, common]

    # left stripe (all connect to common)
    left_x1 = 1
    left_x2 = common["x1"] - 2
    if left_x2 - left_x1 + 1 >= 5:
        left_rooms = partition_vertical_strip(
            left_x1, left_x2, common["y1"], common["y2"], min_room_h=3, max_room_h=9
        )
        rooms.extend(left_rooms)

    # right stripe (all connect to common)
    right_x1 = common["x2"] + 2
    right_x2 = width - 2
    if right_x2 - right_x1 + 1 >= 5:
        right_rooms = partition_vertical_strip(
            right_x1, right_x2, common["y1"], common["y2"], min_room_h=3, max_room_h=9
        )
        rooms.extend(right_rooms)

    # bottom stripe (all connect to common)
    bottom_y1 = common["y2"] + 2
    bottom_y2 = height - 2
    if porch:
        bottom_y2 = porch["y1"] - 2

    if bottom_y2 - bottom_y1 + 1 >= 3:
        bottom_rooms = partition_horizontal_strip(
            common["x1"], common["x2"], bottom_y1, bottom_y2, min_room_w=5, max_room_w=11
        )
        rooms.extend(bottom_rooms)

    if porch:
        rooms.append(porch)

    # carve rooms
    for room in rooms:
        carve_room(grid, room)

    # 10) add doors and check path
    kitchen_cx, kitchen_cy = room_center(kitchen)
    dining_cx, dining_cy = room_center(dining)
    common_cx, common_cy = room_center(common)

    # B -> kitchen -> dining -> common
    carve_corridor_L(grid, kitchen_cx, kitchen_cy, dining_cx, dining_cy)
    carve_corridor_L(grid, dining_cx, dining_cy, common_cx, common["y1"])

    # all side rooms to common
    for room in rooms:
        if room["type"] in {"Kitchen", "Dining", "Common", "Porch"}:
            continue

        cx, cy = room_center(room)

        # left rooms
        if room["x2"] < common["x1"]:
            carve_corridor_L(grid, cx, cy, common["x1"], cy)

        # right rooms
        elif room["x1"] > common["x2"]:
            carve_corridor_L(grid, cx, cy, common["x2"], cy)

        # bottom rooms
        elif room["y1"] > common["y2"]:
            carve_corridor_L(grid, cx, cy, cx, common["y2"])

    # front door
    if porch:
        porch_cx, porch_cy = room_center(porch)
        carve_corridor_L(grid, porch_cx, porch_cy, common_cx, common["y2"])
        carve_cell(grid, porch_cx, height - 1, "F")
        end = (porch_cx, height - 2)
    else:
        fx_candidates = [common_cx, common_cx - 2, common_cx + 2]
        fx_candidates = [x for x in fx_candidates if common["x1"] <= x <= common["x2"] and x != kitchen_cx]
        if not fx_candidates:
            fx_candidates = [x for x in range(common["x1"], common["x2"] + 1) if x != kitchen_cx]
        fx = random.choice(fx_candidates)
        carve_cell(grid, fx, height - 1, "F")
        end = (fx, height - 2)

    carve_cell(grid, kitchen_cx, 0, "B")
    start = (kitchen_cx, 1)

    labels = assign_final_labels(rooms, width, height)
    valid, reason = validate_room_sizes(rooms, labels)
    if not valid:
        return None, reason

    return {
        "grid": grid,
        "rooms": rooms,
        "labels": labels,
        "start": start,
        "end": end,
        "kitchen_side": kitchen_side,
        "front_mode": "porch" if porch else "common",
    }, "ok"


def plot_house(grid, rooms, labels, width, height):
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_facecolor("white")

    for y in range(height):
        for x in range(width):
            if grid[y][x] != "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    for y in range(height):
        for x in range(width):
            if grid[y][x] == "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1)
                ax.add_patch(rect)

    for y in range(height):
        for x in range(width):
            if grid[y][x] == ".":
                cx = x + 0.5
                cy = height - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

    for y in range(height):
        for x in range(width):
            if grid[y][x] == "B":
                ax.text(
                    x + 0.5, height - y - 0.5, "B",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )
            elif grid[y][x] == "F":
                ax.text(
                    x + 0.5, height - y - 0.5, "F",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )

    for room in rooms:
        label = labels[id(room)]
        cx, cy = room_center(room)
        ax.text(
            cx + 0.5, height - cy - 0.5, label,
            ha="center", va="center", fontsize=9, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.85),
        )

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Random House Layout")
    plt.tight_layout()
    plt.show()


def try_generate_once(attempt):
    width = random.choice(odd_choices(MIN_WIDTH, MAX_WIDTH))
    height = random.choice(odd_choices(MIN_HEIGHT, MAX_HEIGHT))

    print(f"  Attempt {attempt}: size={width}x{height}")

    result, reason = build_house_layout(width, height)
    if result is None:
        print(f"    Rejected during template build: {reason}")
        return None

    grid = result["grid"]
    rooms = result["rooms"]
    labels = result["labels"]
    start = result["start"]
    end = result["end"]

    print(f"    Door mode: {result['front_mode']}")
    print(f"    Room areas: {[(labels[id(r)], room_area(r)) for r in rooms]}")

    path = find_path(grid, start, end, width, height)
    if not path:
        print("    Rejected during path check: no valid B-to-F path")
        return None

    draw_path(grid, path)
    print("    Accepted")
    return grid, rooms, labels, width, height, attempt


def generate_valid_house(max_attempts=80):
    for attempt in range(1, max_attempts + 1):
        result = try_generate_once(attempt)
        if result is not None:
            return result
    raise RuntimeError(f"Failed to generate a valid house after {max_attempts} attempts")


if __name__ == "__main__":
    total_start = time.perf_counter()
    stage_start = total_start

    print("Generating Layout")
    house, rooms, labels, width, height, attempts = generate_valid_house()
    stage_start = log_stage("Layout complete", stage_start)

    print("Checking Exit Path")
    stage_start = log_stage("Exit path confirmed", stage_start)

    print("Printing ASCII Layout")
    print(f"House size: {width} x {height}")
    print(f"Rooms: {len(rooms)}")
    print(f"Attempts: {attempts}")
    print_grid(house)
    stage_start = log_stage("ASCII output complete", stage_start)

    print("Generating Plot")
    plot_house(house, rooms, labels, width, height)
    stage_start = log_stage("Plot complete", stage_start)

    total_elapsed = time.perf_counter() - total_start
    print(f"Total time: {total_elapsed:.4f}s")