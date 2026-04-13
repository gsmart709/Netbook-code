import random
import time
from collections import deque
import matplotlib.pyplot as plt


MIN_WIDTH = 23
MAX_WIDTH = 29   # odd only
MIN_HEIGHT = 17
MAX_HEIGHT = 21  # odd only


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


def carve_door_between(grid, room_a, room_b):
    """
    Carve exactly one door in the shared wall between two adjacent rectangular rooms.
    """
    # vertical adjacency: room_a left of room_b or vice versa
    if room_a["x2"] + 2 == room_b["x1"] or room_b["x2"] + 2 == room_a["x1"]:
        left = room_a if room_a["x2"] < room_b["x1"] else room_b
        right = room_b if left is room_a else room_a

        wall_x = left["x2"] + 1
        y1 = max(left["y1"], right["y1"])
        y2 = min(left["y2"], right["y2"])
        door_y = (y1 + y2) // 2
        carve_cell(grid, wall_x, door_y)

    # horizontal adjacency: room_a above room_b or vice versa
    elif room_a["y2"] + 2 == room_b["y1"] or room_b["y2"] + 2 == room_a["y1"]:
        top = room_a if room_a["y2"] < room_b["y1"] else room_b
        bottom = room_b if top is room_a else room_a

        wall_y = top["y2"] + 1
        x1 = max(top["x1"], bottom["x1"])
        x2 = min(top["x2"], bottom["x2"])
        door_x = (x1 + x2) // 2
        carve_cell(grid, door_x, wall_y)


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


def build_7_room_layout(width, height):
    """
    Robust carve-from-walls layout:
    Rooms:
      Kitchen, Dining, Common, Bedroom, Bath, Bedroom, Bottom-right room
    Bottom-right room becomes Porch if front door enters it,
    otherwise Bedroom/Garage.
    """
    grid = create_wall_grid(width, height)

    kitchen_side = random.choice(["left", "right"])
    front_mode = random.choice(["common", "small_room"])

    # Room sizes
    top_h = 5
    left_w = 5
    right_w = 5

    # central common area
    common_x1 = 7
    common_x2 = width - 8
    common_y1 = 7
    common_y2 = height - 2

    if common_x2 - common_x1 + 1 < 7:
        return None, "common too narrow"

    # Top band
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

    # Left side stack
    left_bed = {"type": "Bedroom", "x1": 1, "x2": left_w, "y1": 7, "y2": 11}
    bath = {"type": "Bath", "x1": 1, "x2": left_w, "y1": 13, "y2": 15}

    # Right side stack
    right_top = {"type": "Bedroom", "x1": width - right_w - 1, "x2": width - 2, "y1": 7, "y2": 11}
    right_bottom = {"type": "Bedroom", "x1": width - right_w - 1, "x2": width - 2, "y1": 13, "y2": height - 2}

    common = {"type": "Common", "x1": common_x1, "x2": common_x2, "y1": common_y1, "y2": common_y2}

    # Optional front porch: small room under common
    porch = None
    if front_mode == "small_room":
        porch_w = 5
        porch_x1 = (common_x1 + common_x2) // 2 - 2
        porch_x2 = porch_x1 + porch_w - 1
        porch_y1 = height - 4
        porch_y2 = height - 2
        porch = {"type": "Porch", "x1": porch_x1, "x2": porch_x2, "y1": porch_y1, "y2": porch_y2}

        # Pull common up slightly so porch is distinct
        common["y2"] = porch_y1 - 2

        if common["y2"] - common["y1"] + 1 < 5:
            return None, "common too short with porch"

    # Carve rooms
    rooms = [kitchen, dining, common, left_bed, bath, right_top, right_bottom]
    if porch is not None:
        rooms.append(porch)

    for room in rooms:
        carve_room(grid, room)

    # Interior doors
    carve_door_between(grid, kitchen, dining)

    # Dining connects downward into common by corridor
    dining_cx, dining_cy = room_center(dining)
    common_cx, common_cy = room_center(common)
    carve_vertical_corridor(grid, dining_cx, dining["y2"] + 1, common["y1"] - 1)
    carve_horizontal_corridor(grid, min(dining_cx, common_cx), max(dining_cx, common_cx), common["y1"] - 1)
    carve_cell(grid, common_cx, common["y1"] - 1)

    # Left bedroom and bath connect only via one door each to common/bedroom chain
    carve_door_between(grid, left_bed, common)
    carve_door_between(grid, left_bed, bath)

    # Right top bedroom connects to common
    carve_door_between(grid, right_top, common)

    # Bottom-right room:
    if porch is not None:
        # right bottom room connects to common
        carve_door_between(grid, right_bottom, common)
        # porch connects to common
        carve_door_between(grid, porch, common)
    else:
        carve_door_between(grid, right_bottom, common)

    # Exterior B door always into kitchen
    kitchen_cx, _ = room_center(kitchen)
    carve_cell(grid, kitchen_cx, 0, "B")
    start = (kitchen_cx, 1)

    # Exterior F door
    if porch is not None:
        porch_cx, _ = room_center(porch)
        carve_cell(grid, porch_cx, height - 1, "F")
        end = (porch_cx, height - 2)
    else:
        # enter common directly, offset if possible and not aligned with B
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

    for i, room in enumerate(rooms):
        label = labels[i]
        cx, cy = room_center(room)
        ax.text(
            cx + 0.5, height - cy - 0.5, label,
            ha="center", va="center", fontsize=10, fontweight="bold",
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

    print(f"  Attempt {attempt}: size={width}x{height}, type=7-room")

    result, reason = build_7_room_layout(width, height)

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


def generate_valid_house(max_attempts=100):
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