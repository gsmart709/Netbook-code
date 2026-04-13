import random
import time
from collections import deque
import matplotlib.pyplot as plt


MIN_WIDTH = 25
MAX_WIDTH = 31   # odd only
MIN_HEIGHT = 19
MAX_HEIGHT = 23  # odd only


EXTRA_ROOM_POOL = [
    "Bedroom",
    "Office",
    "Laundry",
    "Storage",
    "Garage",
]


def odd_choices(start, end):
    return [n for n in range(start, end + 1) if n % 2 == 1]


def log_stage(name, start_time):
    elapsed = time.perf_counter() - start_time
    print(f"{name}... {elapsed:.4f}s")
    return time.perf_counter()


def room_area(room):
    return (room["x2"] - room["x1"] + 1) * (room["y2"] - room["y1"] + 1)


def room_center(room):
    cx = (room["x1"] + room["x2"]) // 2
    cy = (room["y1"] + room["y2"]) // 2
    return cx, cy


def print_grid(grid):
    for row in grid:
        print("".join(row))


def create_wall_grid(width, height):
    return [["#" for _ in range(width)] for _ in range(height)]


def carve_room(grid, room):
    for y in range(room["y1"], room["y2"] + 1):
        for x in range(room["x1"], room["x2"] + 1):
            grid[y][x] = " "


def carve_cell(grid, x, y, char=" "):
    grid[y][x] = char


def is_open_cell(grid, x, y):
    return grid[y][x] != "#"


def can_carve_vertical_door(grid, x, y):
    if x - 1 < 0 or x + 1 >= len(grid[0]):
        return False
    return is_open_cell(grid, x - 1, y) and is_open_cell(grid, x + 1, y)


def can_carve_horizontal_door(grid, x, y):
    if y - 1 < 0 or y + 1 >= len(grid):
        return False
    return is_open_cell(grid, x, y - 1) and is_open_cell(grid, x, y + 1)


def carve_door_between(grid, room_a, room_b):
    # vertical adjacency
    if room_a["x2"] + 2 == room_b["x1"] or room_b["x2"] + 2 == room_a["x1"]:
        left = room_a if room_a["x2"] < room_b["x1"] else room_b
        right = room_b if left is room_a else room_a

        wall_x = left["x2"] + 1
        y1 = max(left["y1"], right["y1"])
        y2 = min(left["y2"], right["y2"])

        candidates = [y for y in range(y1, y2 + 1) if can_carve_vertical_door(grid, wall_x, y)]
        if not candidates:
            return False

        door_y = candidates[len(candidates) // 2]
        carve_cell(grid, wall_x, door_y)
        return True

    # horizontal adjacency
    if room_a["y2"] + 2 == room_b["y1"] or room_b["y2"] + 2 == room_a["y1"]:
        top = room_a if room_a["y2"] < room_b["y1"] else room_b
        bottom = room_b if top is room_a else room_a

        wall_y = top["y2"] + 1
        x1 = max(top["x1"], bottom["x1"])
        x2 = min(top["x2"], bottom["x2"])

        candidates = [x for x in range(x1, x2 + 1) if can_carve_horizontal_door(grid, x, wall_y)]
        if not candidates:
            return False

        door_x = candidates[len(candidates) // 2]
        carve_cell(grid, door_x, wall_y)
        return True

    return False


def carve_vertical_corridor(grid, x, y1, y2):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        carve_cell(grid, x, y)


def carve_horizontal_corridor(grid, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        carve_cell(grid, x, y)


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


def weighted_extra_room():
    return random.choice(EXTRA_ROOM_POOL)


def assign_labels(rooms, width, height):
    labels = {}

    for i, room in enumerate(rooms):
        rtype = room["type"]

        if rtype == "Kitchen":
            labels[i] = "Kitchen"
        elif rtype == "Dining":
            labels[i] = "Dining"
        elif rtype == "Common":
            labels[i] = "Common"
        elif rtype == "Bath":
            labels[i] = "Bath"
        elif rtype == "Porch":
            labels[i] = "Porch"
        elif rtype in {"Office", "Laundry", "Storage"}:
            labels[i] = rtype
        elif rtype == "Garage":
            labels[i] = "Garage"
        elif rtype == "Bedroom":
            if room["x2"] == width - 2 and room["y2"] == height - 2 and random.random() < 0.5:
                labels[i] = "Garage"
            else:
                labels[i] = "Bedroom"
        else:
            labels[i] = rtype

    return labels


def validate_room_sizes(rooms):
    common = next(r for r in rooms if r["type"] == "Common")
    kitchen = next(r for r in rooms if r["type"] == "Kitchen")
    bath = next(r for r in rooms if r["type"] == "Bath")
    bedrooms = [r for r in rooms if r["type"] == "Bedroom"]

    if not (room_area(common) > room_area(kitchen)):
        return False, "common not bigger than kitchen"

    if bedrooms and not all(room_area(common) > room_area(b) for b in bedrooms):
        return False, "common not bigger than bedroom"

    if bedrooms and not all(room_area(b) > room_area(bath) for b in bedrooms):
        return False, "bedroom not bigger than bath"

    bath_w = bath["x2"] - bath["x1"] + 1
    bath_h = bath["y2"] - bath["y1"] + 1
    if max(bath_w, bath_h) > 5:
        return False, "bath too long"

    return True, "ok"


def build_house_layout(width, height):
    grid = create_wall_grid(width, height)

    kitchen_side = random.choice(["left", "right"])
    front_mode = random.choice(["common", "small_room"])

    # Back band
    top_h = 5
    kitchen_w = random.choice([5, 7])

    if kitchen_side == "left":
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": top_h}
        dining = {"type": "Dining", "x1": kitchen_w + 2, "x2": width - 2, "y1": 1, "y2": top_h}
    else:
        kitchen = {"type": "Kitchen", "x1": width - kitchen_w - 1, "x2": width - 2, "y1": 1, "y2": top_h}
        dining = {"type": "Dining", "x1": 1, "x2": kitchen["x1"] - 2, "y1": 1, "y2": top_h}

    if room_area(kitchen) < 25:
        return None, "kitchen too small"

    if dining["x2"] - dining["x1"] + 1 < 7:
        return None, "dining too small"

    # Main common room
    common_x1 = 7
    common_x2 = width - 8
    common_y1 = 7
    common_y2 = height - 2

    if common_x2 - common_x1 + 1 < 7:
        return None, "common too narrow"

    common = {"type": "Common", "x1": common_x1, "x2": common_x2, "y1": common_y1, "y2": common_y2}

    # Porch option
    porch = None
    if front_mode == "small_room":
        porch_w = 5
        porch_x1 = (common_x1 + common_x2) // 2 - 2
        porch_x2 = porch_x1 + porch_w - 1
        porch_y1 = height - 4
        porch_y2 = height - 2
        porch = {"type": "Porch", "x1": porch_x1, "x2": porch_x2, "y1": porch_y1, "y2": porch_y2}
        common["y2"] = porch_y1 - 2
        if common["y2"] - common["y1"] + 1 < 5:
            return None, "common too short with porch"

    # Required side rooms
    left_stack_x1, left_stack_x2 = 1, 5
    right_stack_x1, right_stack_x2 = width - 6, width - 2

    first_bedroom = {"type": "Bedroom", "x1": left_stack_x1, "x2": left_stack_x2, "y1": 7, "y2": 11}
    bath = {"type": "Bath", "x1": left_stack_x1, "x2": left_stack_x2, "y1": 13, "y2": 15}

    rooms = [kitchen, dining, common, first_bedroom, bath]
    if porch:
        rooms.append(porch)

    # Base right rooms
    right_top = {"type": weighted_extra_room(), "x1": right_stack_x1, "x2": right_stack_x2, "y1": 7, "y2": 11}
    right_bottom = {"type": weighted_extra_room(), "x1": right_stack_x1, "x2": right_stack_x2, "y1": 13, "y2": height - 2}

    # Ensure at least one extra bedroom exists beyond base bedroom sometimes via pool rules,
    # but keep common and bath intact
    if right_top["type"] == "Garage":
        right_top["type"] = "Bedroom"
    if right_bottom["type"] == "Garage":
        right_bottom["type"] = "Bedroom"

    rooms.extend([right_top, right_bottom])

    # Extra central side pods up to 8 rooms total
    target_room_count = random.choice([5, 6, 7, 8])

    # We already have 5 required + maybe porch + 2 right rooms
    # Count only real rooms, porch included as room.
    while len(rooms) < target_room_count:
        extra_type = weighted_extra_room()
        # place extra room branching off common
        side = random.choice(["left", "right"])
        y_band = random.choice(["upper", "lower"])

        if side == "left":
            x1, x2 = 1, 5
        else:
            x1, x2 = width - 6, width - 2

        if y_band == "upper":
            y1, y2 = 7, 11
        else:
            y1, y2 = 13, min(height - 2, 17)

        candidate = {"type": extra_type, "x1": x1, "x2": x2, "y1": y1, "y2": y2}

        # avoid duplicates of exact same rectangle
        overlap = False
        for r in rooms:
            if (r["x1"], r["x2"], r["y1"], r["y2"]) == (candidate["x1"], candidate["x2"], candidate["y1"], candidate["y2"]):
                overlap = True
                break
        if not overlap:
            rooms.append(candidate)
        else:
            break

    # Carve all rooms
    for room in rooms:
        carve_room(grid, room)

    # Back connection
    if not carve_door_between(grid, kitchen, dining):
        return None, "failed kitchen-dining door"

    # Dining to common corridor
    dining_cx, _ = room_center(dining)
    common_cx, _ = room_center(common)
    corridor_y = common["y1"] - 1
    carve_vertical_corridor(grid, dining_cx, dining["y2"] + 1, corridor_y)
    carve_horizontal_corridor(grid, min(dining_cx, common_cx), max(dining_cx, common_cx), corridor_y)
    carve_cell(grid, common_cx, corridor_y)

    # Required room connections
    if not carve_door_between(grid, first_bedroom, common):
        return None, "failed bedroom-common door"

    if not carve_door_between(grid, first_bedroom, bath):
        return None, "failed bedroom-bath door"

    if not carve_door_between(grid, right_top, common):
        return None, "failed right top-common door"

    if porch:
        if not carve_door_between(grid, porch, common):
            return None, "failed porch-common door"
    else:
        if not carve_door_between(grid, right_bottom, common):
            return None, "failed right bottom-common door"

    # Connect optional extras to common if adjacent
    for room in rooms:
        if room in {kitchen, dining, common, first_bedroom, bath, right_top, right_bottom}:
            continue
        carve_door_between(grid, room, common)

    # Exterior doors
    kitchen_cx, _ = room_center(kitchen)
    carve_cell(grid, kitchen_cx, 0, "B")
    start = (kitchen_cx, 1)

    if porch:
        porch_cx, _ = room_center(porch)
        carve_cell(grid, porch_cx, height - 1, "F")
        end = (porch_cx, height - 2)
    else:
        common_center_x = (common["x1"] + common["x2"]) // 2
        candidates = [common_center_x, common_center_x - 2, common_center_x + 2]
        candidates = [x for x in candidates if common["x1"] <= x <= common["x2"] and x != kitchen_cx]
        if not candidates:
            candidates = [x for x in range(common["x1"], common["x2"] + 1) if x != kitchen_cx]
        fx = random.choice(candidates)
        carve_cell(grid, fx, height - 1, "F")
        end = (fx, height - 2)

    return {
        "grid": grid,
        "rooms": rooms,
        "start": start,
        "end": end,
        "kitchen_side": kitchen_side,
        "front_mode": front_mode,
    }, "ok"


def plot_house(grid, rooms, labels, width, height):
    fig, ax = plt.subplots(figsize=(8, 6))
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
                    x + 0.5,
                    height - y - 0.5,
                    "B",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )
            elif grid[y][x] == "F":
                ax.text(
                    x + 0.5,
                    height - y - 0.5,
                    "F",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )

    for i, room in enumerate(rooms):
        label = labels.get(i, room["type"])
        cx, cy = room_center(room)
        ax.text(
            cx + 0.5,
            height - cy - 0.5,
            label,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
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
    start = result["start"]
    end = result["end"]

    labels = assign_labels(rooms, width, height)

    print(f"    Door mode: {result['front_mode']}")
    print(f"    Room areas: {[(labels[i], room_area(r)) for i, r in enumerate(rooms)]}")

    valid_sizes, reason = validate_room_sizes(rooms)
    if not valid_sizes:
        print(f"    Rejected during size validation: {reason}")
        return None

    path = find_path(grid, start, end, width, height)
    if not path:
        print("    Rejected during path check: no valid B-to-F path")
        return None

    draw_path(grid, path)
    print("    Accepted")
    return grid, rooms, labels, width, height, attempt


def generate_valid_house(max_attempts=120):
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

    print("Validating Room Rules")
    stage_start = log_stage("Room graph validated", stage_start)

    print("Checking Exit Path")
    stage_start = log_stage("Exit path confirmed", stage_start)

    print("Assigning Room Labels")
    stage_start = log_stage("Room labeling complete", stage_start)

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