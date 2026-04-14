import random
import time
from collections import deque
import matplotlib.pyplot as plt

MIN_WIDTH = 27
MAX_WIDTH = 51   # odd only
MIN_HEIGHT = 19
MAX_HEIGHT = 37  # odd only

UNIQUE_ROOM_TYPES = ["Office", "Laundry", "Storage", "Garage"]


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


def carve_corridor_L(grid, x1, y1, x2, y2):
    if random.random() < 0.5:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            carve_cell(grid, x, y1)
        for y in range(min(y1, y2), max(y1, y2) + 1):
            carve_cell(grid, x2, y)
    else:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            carve_cell(grid, x1, y)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            carve_cell(grid, x, y2)


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


def choose_labels(candidate_rooms, width, height):
    """
    Rules:
    - smallest = Bath
    - one Bedroom first
    - after that: Bedroom may repeat, other types no repeats
    """
    labels = {}
    if not candidate_rooms:
        return labels

    rooms_sorted = sorted(candidate_rooms, key=room_area)

    # smallest = bath
    bath_room = rooms_sorted[0]
    labels[id(bath_room)] = "Bath"

    remaining = [r for r in rooms_sorted if id(r) not in labels]

    # largest remaining = first bedroom
    if remaining:
        first_bed = max(remaining, key=room_area)
        labels[id(first_bed)] = "Bedroom"
        remaining = [r for r in remaining if id(r) not in labels]

    available_unique = UNIQUE_ROOM_TYPES[:]

    for room in remaining:
        choices = ["Bedroom"] + available_unique[:]
        chosen = random.choice(choices)
        labels[id(room)] = chosen

        if chosen in available_unique:
            available_unique.remove(chosen)

    # 50% chance bottom-right bedroom becomes garage
    for room in remaining + ([first_bed] if 'first_bed' in locals() else []):
        if (
            labels.get(id(room)) == "Bedroom"
            and room["x2"] == width - 2
            and room["y2"] >= height - 5
            and random.random() < 0.5
        ):
            labels[id(room)] = "Garage"

    return labels


def build_house_layout(width, height):
    grid = create_wall_grid(width, height)

    kitchen_side = random.choice(["left", "right"])
    kitchen_w = random.choice([7, 9, 11])
    kitchen_h = random.choice([5, 7, 9])

    use_porch = random.random() < 0.5
    use_dining_split = random.random() < 0.5

    bottom_room_limit = height - (5 if use_porch else 2)

    if kitchen_side == "left":
        # 1-2 kitchen
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": kitchen_h}
        divider_x = kitchen_w + 1

        # opposite top strip
        dining = {"type": "Dining", "x1": divider_x + 1, "x2": width - 2, "y1": 1, "y2": kitchen_h}

        # 3 vertical line from kitchen down
        # represented by not carving divider_x

        # 4 left lower rectangle split horizontally into 2 rooms
        left_x1 = 1
        left_x2 = divider_x - 1
        left_y1 = kitchen_h + 2
        left_y2 = bottom_room_limit

        if left_y2 - left_y1 < 6:
            return None, "left strip too short"

        split_left_y = random.randint(left_y1 + 2, left_y2 - 3)

        left_top = {"x1": left_x1, "x2": left_x2, "y1": left_y1, "y2": split_left_y - 1}
        left_bottom = {"x1": left_x1, "x2": left_x2, "y1": split_left_y + 1, "y2": left_y2}

        # 5 bottom horizontal kitchen line already implied by split at y = kitchen_h + 1

        # 6 divide big right rectangle vertically into common + right strip
        big_x1 = divider_x + 1
        big_x2 = width - 2
        big_y1 = kitchen_h + 2
        big_y2 = bottom_room_limit

        if big_x2 - big_x1 < 12:
            return None, "main body too narrow"

        divider2_x = random.randint(big_x1 + 8, big_x2 - 6)

        common = {"type": "Common", "x1": big_x1, "x2": divider2_x - 1, "y1": big_y1, "y2": big_y2}
        right_strip_x1 = divider2_x + 1
        right_strip_x2 = big_x2

        # 7 split right strip horizontally into possible 2 rooms
        right_rooms = []
        if right_strip_x2 - right_strip_x1 >= 4:
            if big_y2 - big_y1 >= 6:
                split_right_y = random.randint(big_y1 + 2, big_y2 - 3)
                right_top = {"x1": right_strip_x1, "x2": right_strip_x2, "y1": big_y1, "y2": split_right_y - 1}
                right_bottom = {"x1": right_strip_x1, "x2": right_strip_x2, "y1": split_right_y + 1, "y2": big_y2}
                right_rooms.extend([right_top, right_bottom])
            else:
                right_rooms.append({"x1": right_strip_x1, "x2": right_strip_x2, "y1": big_y1, "y2": big_y2})

        top_extra = None
        if use_dining_split and dining["x2"] - dining["x1"] >= 14:
            # split on far side from kitchen, keep 6 cells away from common connector zone
            split_x = dining["x2"] - 6
            top_extra = {
                "x1": split_x + 1,
                "x2": dining["x2"],
                "y1": dining["y1"],
                "y2": dining["y2"],
            }
            dining["x2"] = split_x - 1

    else:
        # mirrored
        kitchen = {"type": "Kitchen", "x1": width - kitchen_w - 1, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        divider_x = kitchen["x1"] - 1

        dining = {"type": "Dining", "x1": 1, "x2": divider_x - 1, "y1": 1, "y2": kitchen_h}

        left_x1 = 1
        left_x2 = divider_x - 1
        left_y1 = kitchen_h + 2
        left_y2 = bottom_room_limit

        if left_y2 - left_y1 < 6:
            return None, "left strip too short"

        split_left_y = random.randint(left_y1 + 2, left_y2 - 3)

        # big left rectangle becomes common + left strip
        big_x1 = 1
        big_x2 = divider_x - 1
        big_y1 = kitchen_h + 2
        big_y2 = bottom_room_limit

        if big_x2 - big_x1 < 12:
            return None, "main body too narrow"

        divider2_x = random.randint(big_x1 + 6, big_x2 - 8)

        left_strip_x1 = big_x1
        left_strip_x2 = divider2_x - 1
        common = {"type": "Common", "x1": divider2_x + 1, "x2": big_x2, "y1": big_y1, "y2": big_y2}

        left_top = {"x1": left_strip_x1, "x2": left_strip_x2, "y1": big_y1, "y2": split_left_y - 1}
        left_bottom = {"x1": left_strip_x1, "x2": left_strip_x2, "y1": split_left_y + 1, "y2": big_y2}

        # right of kitchen divider is narrow strip under kitchen
        right_x1 = divider_x + 1
        right_x2 = width - 2
        right_y1 = kitchen_h + 2
        right_y2 = bottom_room_limit

        right_rooms = []
        if right_y2 - right_y1 >= 6:
            split_right_y = random.randint(right_y1 + 2, right_y2 - 3)
            right_top = {"x1": right_x1, "x2": right_x2, "y1": right_y1, "y2": split_right_y - 1}
            right_bottom = {"x1": right_x1, "x2": right_x2, "y1": split_right_y + 1, "y2": right_y2}
            right_rooms.extend([right_top, right_bottom])
        else:
            right_rooms.append({"x1": right_x1, "x2": right_x2, "y1": right_y1, "y2": right_y2})

        top_extra = None
        if use_dining_split and dining["x2"] - dining["x1"] >= 14:
            split_x = dining["x1"] + 6
            top_extra = {
                "x1": dining["x1"],
                "x2": split_x - 1,
                "y1": dining["y1"],
                "y2": dining["y2"],
            }
            dining["x1"] = split_x + 1

    # porch
    porch = None
    if use_porch:
        ccx, _ = room_center(common)
        porch = {"type": "Porch", "x1": ccx - 2, "x2": ccx + 2, "y1": height - 3, "y2": height - 2}

    rooms = [kitchen, dining, common, left_top, left_bottom] + right_rooms
    if top_extra:
        rooms.append(top_extra)
    if porch:
        rooms.append(porch)

    # carve all rooms
    for room in rooms:
        carve_room(grid, room)

    # connect kitchen -> dining -> common
    kcx, kcy = room_center(kitchen)
    dcx, dcy = room_center(dining)
    ccx, ccy = room_center(common)

    carve_corridor_L(grid, kcx, kcy, dcx, dcy)
    carve_corridor_L(grid, dcx, dcy, ccx, common["y1"])

    # dining split extra room -> common
    if top_extra:
        ecx, ecy = room_center(top_extra)
        carve_corridor_L(grid, ecx, ecy, ccx, common["y1"])

    # side rooms -> common
    side_rooms = [left_top, left_bottom] + right_rooms
    for room in side_rooms:
        rcx, rcy = room_center(room)
        carve_corridor_L(grid, rcx, rcy, ccx, rcy if common["y1"] <= rcy <= common["y2"] else ccy)

    # porch -> common
    if porch:
        pcx, pcy = room_center(porch)
        carve_corridor_L(grid, pcx, pcy, ccx, common["y2"])

    # front/back doors
    carve_cell(grid, kcx, 0, "B")
    start = (kcx, 1)

    if porch:
        pcx, _ = room_center(porch)
        carve_cell(grid, pcx, height - 1, "F")
        end = (pcx, height - 2)
    else:
        carve_cell(grid, ccx, height - 1, "F")
        end = (ccx, height - 2)

    # labels after geometry
    labels = {
        id(kitchen): "Kitchen",
        id(dining): "Dining",
        id(common): "Common",
    }
    if porch:
        labels[id(porch)] = "Porch"

    candidate_rooms = [left_top, left_bottom] + right_rooms
    if top_extra:
        candidate_rooms.append(top_extra)

    labels.update(choose_labels(candidate_rooms, width, height))

    # validate path
    path = find_path(grid, start, end, width, height)
    if not path:
        return None, "no path"

    draw_path(grid, path)

    return {
        "grid": grid,
        "rooms": rooms,
        "labels": labels,
        "start": start,
        "end": end,
    }, "ok"


def try_generate_once(attempt):
    width = random.choice(odd_choices(MIN_WIDTH, MAX_WIDTH))
    height = random.choice(odd_choices(MIN_HEIGHT, MAX_HEIGHT))

    print(f"  Attempt {attempt}: size={width}x{height}")

    result, reason = build_house_layout(width, height)
    if result is None:
        print(f"    Rejected: {reason}")
        return None

    return result["grid"], result["rooms"], result["labels"], width, height, attempt


def generate_valid_house(max_attempts=100):
    for attempt in range(1, max_attempts + 1):
        result = try_generate_once(attempt)
        if result is not None:
            return result
    raise RuntimeError("Failed to generate a valid house")


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
            if grid[y][x] in {"B", "F"}:
                ax.text(
                    x + 0.5,
                    height - y - 0.5,
                    grid[y][x],
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )

    for room in rooms:
        label = labels.get(id(room), "")
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


if __name__ == "__main__":
    total_start = time.perf_counter()
    stage_start = total_start

    print("Generating Layout")
    house, rooms, labels, width, height, attempts = generate_valid_house()
    stage_start = log_stage("Layout complete", stage_start)

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