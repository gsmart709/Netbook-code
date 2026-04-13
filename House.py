import random
import time
from collections import deque
import matplotlib.pyplot as plt


MIN_WIDTH = 25
MAX_WIDTH = 35   # odd only
MIN_HEIGHT = 19
MAX_HEIGHT = 27  # odd only


EXTRA_ROOM_TYPES = ["Bedroom", "Office", "Laundry", "Storage", "Garage"]


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
    grid[y][x] = char


def carve_vertical_corridor(grid, x, y1, y2):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        carve_cell(grid, x, y)


def carve_horizontal_corridor(grid, x1, x2, y):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        carve_cell(grid, x, y)


def carve_corridor_L(grid, x1, y1, x2, y2):
    # randomize bend order for slight variety
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


def assign_labels(rooms, width, height):
    labels = {}

    for i, room in enumerate(rooms):
        rtype = room["type"]

        if rtype == "Bedroom":
            # bottom-right bedroom can become garage 50% of the time
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

    if room_area(common) <= room_area(kitchen):
        return False, "common not bigger than kitchen"

    if bedrooms and not all(room_area(common) > room_area(b) for b in bedrooms):
        return False, "common not bigger than bedroom"

    if bedrooms and not all(room_area(b) > room_area(bath) for b in bedrooms):
        return False, "bedroom not bigger than bath"

    bw = bath["x2"] - bath["x1"] + 1
    bh = bath["y2"] - bath["y1"] + 1
    if max(bw, bh) > 5:
        return False, "bath too long"

    return True, "ok"


def build_house_layout(width, height):
    grid = create_wall_grid(width, height)

    kitchen_side = random.choice(["left", "right"])
    use_porch = random.random() < 0.4

    # --- Back row ---
    top_h = random.choice([5, 7])
    kitchen_w = random.choice([5, 7, 9])

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

    # --- Common hub ---
    common_margin_x = random.choice([6, 7, 8, 9])
    common_x1 = common_margin_x
    common_x2 = width - common_margin_x - 1
    common_y1 = top_h + 3
    common_y2 = height - 4

    common = {"type": "Common", "x1": common_x1, "x2": common_x2, "y1": common_y1, "y2": common_y2}

    if common["x2"] - common["x1"] + 1 < 9:
        return None, "common too narrow"
    if common["y2"] - common["y1"] + 1 < 7:
        return None, "common too short"

    # --- Porch or direct front ---
    porch = None
    if use_porch:
        porch_w = random.choice([5, 7])
        common_cx, _ = room_center(common)
        porch_x1 = common_cx - porch_w // 2
        porch_x2 = porch_x1 + porch_w - 1
        porch_y2 = height - 2
        porch_y1 = porch_y2 - 2
        porch = {"type": "Porch", "x1": porch_x1, "x2": porch_x2, "y1": porch_y1, "y2": porch_y2}
        common["y2"] = porch_y1 - 2
        if common["y2"] - common["y1"] + 1 < 5:
            return None, "common too short with porch"

    # --- Left required rooms ---
    side_w_left = random.choice([5, 7])
    left_x1 = 1
    left_x2 = side_w_left

    first_bed_h = random.choice([5, 7])
    first_bedroom = {
        "type": "Bedroom",
        "x1": left_x1,
        "x2": left_x2,
        "y1": common["y1"],
        "y2": common["y1"] + first_bed_h - 1,
    }

    bath = {
        "type": "Bath",
        "x1": left_x1,
        "x2": left_x2,
        "y1": first_bedroom["y2"] + 2,
        "y2": first_bedroom["y2"] + 4,
    }

    if bath["y2"] > height - 2:
        return None, "bath too low"

    # --- Right stack ---
    side_w_right = random.choice([5, 7])
    right_x1 = width - side_w_right - 1
    right_x2 = width - 2

    right_top_type = random.choice(EXTRA_ROOM_TYPES)
    right_bottom_type = random.choice(EXTRA_ROOM_TYPES)

    # keep required bedroom in house
    if right_top_type == "Garage":
        right_top_type = "Bedroom"
    if right_bottom_type == "Garage":
        right_bottom_type = "Bedroom"

    right_top_h = random.choice([5, 7])

    right_top = {
        "type": right_top_type,
        "x1": right_x1,
        "x2": right_x2,
        "y1": common["y1"],
        "y2": common["y1"] + right_top_h - 1,
    }

    right_bottom = {
        "type": right_bottom_type,
        "x1": right_x1,
        "x2": right_x2,
        "y1": right_top["y2"] + 2,
        "y2": height - 2,
    }

    if right_bottom["y1"] > right_bottom["y2"]:
        return None, "right stack invalid"

    rooms = [kitchen, dining, common, first_bedroom, bath, right_top, right_bottom]

    # --- Optional extras to reach 5–8 rooms ---
    target_total = random.choice([5, 6, 7, 8])

    # left upper pod
    if top_h + 3 < common["y1"] - 1:
        pod_h = random.choice([3, 5])
        pod_y1 = top_h + 2
        pod_y2 = min(common["y1"] - 2, pod_y1 + pod_h - 1)
        if pod_y1 <= pod_y2:
            rooms.append({
                "type": random.choice(EXTRA_ROOM_TYPES),
                "x1": left_x1,
                "x2": left_x2,
                "y1": pod_y1,
                "y2": pod_y2,
            })

    # right upper pod
    if len(rooms) < target_total and top_h + 3 < common["y1"] - 1:
        pod_h = random.choice([3, 5])
        pod_y1 = top_h + 2
        pod_y2 = min(common["y1"] - 2, pod_y1 + pod_h - 1)
        if pod_y1 <= pod_y2:
            rooms.append({
                "type": random.choice(EXTRA_ROOM_TYPES),
                "x1": right_x1,
                "x2": right_x2,
                "y1": pod_y1,
                "y2": pod_y2,
            })

    # lower-left pod
    if len(rooms) < target_total:
        pod_y1 = bath["y2"] + 2
        pod_h = random.choice([3, 5])
        pod_y2 = min(height - 2, pod_y1 + pod_h - 1)
        if pod_y1 <= pod_y2:
            rooms.append({
                "type": random.choice(EXTRA_ROOM_TYPES),
                "x1": left_x1,
                "x2": left_x2,
                "y1": pod_y1,
                "y2": pod_y2,
            })

    # add porch last
    if porch:
        rooms.append(porch)

    # trim to target count, but keep core rooms
    core_rooms = [kitchen, dining, common, first_bedroom, bath]
    optional_rooms = [r for r in rooms if r not in core_rooms]
    random.shuffle(optional_rooms)
    rooms = core_rooms + optional_rooms[: max(0, target_total - len(core_rooms))]

    # keep porch if used
    if porch and porch not in rooms:
        if len(rooms) < 8:
            rooms.append(porch)
        else:
            # replace one optional non-porch room
            for i in range(len(rooms) - 1, -1, -1):
                if rooms[i] not in core_rooms:
                    rooms[i] = porch
                    break

    # carve all rooms
    for room in rooms:
        carve_room(grid, room)

    # connect kitchen to dining
    kitchen_cx, kitchen_cy = room_center(kitchen)
    dining_cx, dining_cy = room_center(dining)
    carve_corridor_L(grid, kitchen_cx, kitchen_cy, dining_cx, dining_cy)

    # connect dining to common
    common_cx, common_cy = room_center(common)
    carve_corridor_L(grid, dining_cx, dining_cy, common_cx, common["y1"])

    # connect required side rooms to common
    bed_cx, bed_cy = room_center(first_bedroom)
    carve_corridor_L(grid, bed_cx, bed_cy, common["x1"], bed_cy)

    bath_cx, bath_cy = room_center(bath)
    carve_corridor_L(grid, bath_cx, bath_cy, bed_cx, bed_cy)

    rt_cx, rt_cy = room_center(right_top)
    carve_corridor_L(grid, rt_cx, rt_cy, common["x2"], rt_cy)

    rb_cx, rb_cy = room_center(right_bottom)
    if not use_porch:
        carve_corridor_L(grid, rb_cx, rb_cy, common["x2"], rb_cy)

    # connect optional rooms to common
    for room in rooms:
        if room in [kitchen, dining, common, first_bedroom, bath, right_top, right_bottom]:
            continue
        if room == porch:
            continue
        cx, cy = room_center(room)
        # connect from nearest side of common
        target_x = common["x1"] if cx < common_cx else common["x2"]
        carve_corridor_L(grid, cx, cy, target_x, cy)

    # porch
    if porch:
        porch_cx, porch_cy = room_center(porch)
        carve_corridor_L(grid, porch_cx, porch_cy, common_cx, common["y2"])
        carve_cell(grid, porch_cx, height - 1, "F")
        end = (porch_cx, height - 2)
    else:
        # front door opens directly to common, offset if possible
        fx_candidates = [common_cx, common_cx - 2, common_cx + 2]
        fx_candidates = [x for x in fx_candidates if common["x1"] <= x <= common["x2"] and x != kitchen_cx]
        if not fx_candidates:
            fx_candidates = [x for x in range(common["x1"], common["x2"] + 1) if x != kitchen_cx]
        fx = random.choice(fx_candidates)
        carve_cell(grid, fx, height - 1, "F")
        end = (fx, height - 2)

    # back door
    carve_cell(grid, kitchen_cx, 0, "B")
    start = (kitchen_cx, 1)

    return {
        "grid": grid,
        "rooms": rooms,
        "start": start,
        "end": end,
        "kitchen_side": kitchen_side,
        "front_mode": "porch" if use_porch else "common",
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
        label = labels.get(i, room["type"])
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