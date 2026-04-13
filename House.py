import random
import time
from collections import deque
import matplotlib.pyplot as plt


MIN_WIDTH = 21
MAX_WIDTH = 25   # odd only
MIN_HEIGHT = 15
MAX_HEIGHT = 19  # odd only


def odd_choices(start, end):
    return [n for n in range(start, end + 1) if n % 2 == 1]


def log_stage(name, start_time):
    elapsed = time.perf_counter() - start_time
    print(f"{name}... {elapsed:.4f}s")
    return time.perf_counter()


def segment_center(start, end):
    length = end - start + 1
    if length % 2 == 0:
        raise ValueError(f"Segment {start}..{end} has even length; cannot center exactly.")
    return (start + end) // 2


def offset_position(start, end, mode):
    c = segment_center(start, end)
    if mode == "center":
        return c
    if mode == "left":
        return max(start, c - 2)
    if mode == "right":
        return min(end, c + 2)
    return c


def create_empty_grid(width, height):
    return [[" " for _ in range(width)] for _ in range(height)]


def print_grid(grid):
    for row in grid:
        print("".join(row))


def draw_outer_walls(grid, width, height):
    for x in range(width):
        grid[0][x] = "#"
        grid[height - 1][x] = "#"
    for y in range(height):
        grid[y][0] = "#"
        grid[y][width - 1] = "#"


def draw_vertical_wall(grid, x, y1, y2, door_y=None):
    for y in range(y1, y2 + 1):
        if y != door_y:
            grid[y][x] = "#"


def draw_horizontal_wall(grid, x1, x2, y, door_x=None):
    for x in range(x1, x2 + 1):
        if x != door_x:
            grid[y][x] = "#"


def room_center(room):
    cx = segment_center(room["x1"], room["x2"])
    cy = segment_center(room["y1"], room["y2"])
    return cx, cy


def room_area(room):
    return (room["x2"] - room["x1"] + 1) * (room["y2"] - room["y1"] + 1)


def place_exterior_doors(grid, width, height, kitchen_room, common_room):
    """
    B is always on the back (top) and kitchen is always back-left or back-right.
    F is always on the front (bottom) and can be center / offset left / offset right.
    B must never line up exactly with F.
    """
    bx = segment_center(kitchen_room["x1"], kitchen_room["x2"])

    modes = ["center", "left", "right"]
    random.shuffle(modes)

    fx = None
    chosen_mode = None
    for mode in modes:
        candidate = offset_position(common_room["x1"], common_room["x2"], mode)
        if candidate != bx:
            fx = candidate
            chosen_mode = mode
            break

    if fx is None:
        possible = [x for x in range(common_room["x1"], common_room["x2"] + 1) if x != bx]
        fx = random.choice(possible)
        chosen_mode = "fallback"

    grid[0][bx] = "B"
    grid[height - 1][fx] = "F"

    return (bx, 1), (fx, height - 2), chosen_mode


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


def assign_labels(rooms):
    labels = {}
    kitchen_index = next(i for i, r in enumerate(rooms) if r["type"] == "Kitchen")
    common_index = next(i for i, r in enumerate(rooms) if r["type"] == "Common")

    labels[kitchen_index] = "Kitchen"
    labels[common_index] = "Common"

    remaining = [i for i in range(len(rooms)) if i not in labels]
    if remaining:
        smallest = min(remaining, key=lambda i: room_area(rooms[i]))
    else:
        smallest = None

    for i in remaining:
        if i == smallest:
            labels[i] = "Bath"
        else:
            labels[i] = "Bedroom"

    return labels


def build_four_room_template_a(width, height, kitchen_side):
    """
    4 rooms:
    Kitchen at back left/right
    Common large middle/front
    Bedroom side
    Bath compact corner
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    kitchen_h = 3
    split_y = kitchen_h + 1
    lower_y1 = split_y + 1
    lower_y2 = height - 2

    kitchen_w = random.choice([5, 7])
    bedroom_w = random.choice([5, 7])
    bath_w = 3
    bath_h = 3

    if kitchen_side == "left":
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": kitchen_h}
        upper_other_x1 = kitchen_w + 2
        upper_other_x2 = width - 2
        top_divider_x = kitchen["x2"] + 1
    else:
        kitchen = {"type": "Kitchen", "x1": width - 1 - kitchen_w, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        upper_other_x1 = 1
        upper_other_x2 = kitchen["x1"] - 2
        top_divider_x = kitchen["x1"] - 1

    if upper_other_x2 - upper_other_x1 + 1 < 7:
        return None, "top span too small"

    kitchen_common_door_x = segment_center(upper_other_x1, upper_other_x2)
    draw_horizontal_wall(grid, 1, width - 2, split_y, door_x=kitchen_common_door_x)
    draw_vertical_wall(grid, top_divider_x, 1, kitchen_h, door_y=segment_center(1, kitchen_h))

    bath_top = lower_y2 - bath_h + 1

    if kitchen_side == "left":
        bedroom = {"type": "Bedroom", "x1": 1, "x2": bedroom_w, "y1": lower_y1, "y2": lower_y2}
        bath = {"type": "Bath", "x1": width - bath_w - 1, "x2": width - 2, "y1": bath_top, "y2": lower_y2}
        left_wall_x = bedroom["x2"] + 1
        right_wall_x = bath["x1"] - 1
    else:
        bath = {"type": "Bath", "x1": 1, "x2": bath_w, "y1": bath_top, "y2": lower_y2}
        bedroom = {"type": "Bedroom", "x1": width - bedroom_w - 1, "x2": width - 2, "y1": lower_y1, "y2": lower_y2}
        left_wall_x = bath["x2"] + 1
        right_wall_x = bedroom["x1"] - 1

    common = {
        "type": "Common",
        "x1": left_wall_x + 1,
        "x2": right_wall_x - 1,
        "y1": lower_y1,
        "y2": lower_y2,
    }

    if common["x2"] - common["x1"] + 1 < 7:
        return None, "common too narrow"

    if kitchen_side == "left":
        draw_vertical_wall(grid, left_wall_x, lower_y1, lower_y2, door_y=segment_center(lower_y1, lower_y2))
        draw_vertical_wall(grid, right_wall_x, lower_y1, bath["y1"] - 2, door_y=None)
    else:
        draw_vertical_wall(grid, right_wall_x, lower_y1, lower_y2, door_y=segment_center(lower_y1, lower_y2))
        draw_vertical_wall(grid, left_wall_x, lower_y1, bath["y1"] - 2, door_y=None)

    draw_horizontal_wall(grid, bath["x1"], bath["x2"], bath["y1"] - 1, door_x=segment_center(bath["x1"], bath["x2"]))

    rooms = [kitchen, bedroom, common, bath]
    return (grid, rooms), "ok"


def build_five_room_template_a(width, height, kitchen_side):
    """
    5 rooms:
    Kitchen back-left/right
    Common big center/front
    2 Bedrooms
    1 compact Bath
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    kitchen_h = 3
    split_y = kitchen_h + 1
    lower_y1 = split_y + 1
    lower_y2 = height - 2
    lower_h = lower_y2 - lower_y1 + 1

    kitchen_w = random.choice([5, 7])
    side_room_w = 5
    bath_h = 3

    if kitchen_side == "left":
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": kitchen_h}
        upper_other_x1 = kitchen_w + 2
        upper_other_x2 = width - 2
        top_divider_x = kitchen["x2"] + 1
    else:
        kitchen = {"type": "Kitchen", "x1": width - 1 - kitchen_w, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        upper_other_x1 = 1
        upper_other_x2 = kitchen["x1"] - 2
        top_divider_x = kitchen["x1"] - 1

    if upper_other_x2 - upper_other_x1 + 1 < 7:
        return None, "top span too small"

    kitchen_common_door_x = segment_center(upper_other_x1, upper_other_x2)
    draw_horizontal_wall(grid, 1, width - 2, split_y, door_x=kitchen_common_door_x)
    draw_vertical_wall(grid, top_divider_x, 1, kitchen_h, door_y=segment_center(1, kitchen_h))

    left_wall_x = side_room_w + 1
    right_wall_x = width - 2 - side_room_w

    common = {
        "type": "Common",
        "x1": left_wall_x + 1,
        "x2": right_wall_x - 1,
        "y1": lower_y1,
        "y2": lower_y2,
    }

    if common["x2"] - common["x1"] + 1 < 7:
        return None, "common too narrow"

    left_split_y = lower_y2 - bath_h
    if left_split_y - lower_y1 < 2:
        return None, "left column too short"

    bedroom1 = {"type": "Bedroom", "x1": 1, "x2": left_wall_x - 1, "y1": lower_y1, "y2": left_split_y - 1}
    bath = {"type": "Bath", "x1": 1, "x2": left_wall_x - 1, "y1": left_split_y + 1, "y2": lower_y2}
    bedroom2 = {"type": "Bedroom", "x1": right_wall_x + 1, "x2": width - 2, "y1": lower_y1, "y2": lower_y2}

    draw_vertical_wall(grid, right_wall_x, lower_y1, lower_y2, door_y=segment_center(lower_y1, lower_y2))
    draw_vertical_wall(grid, left_wall_x, lower_y1, lower_y2, door_y=segment_center(lower_y1, left_split_y - 1))
    draw_horizontal_wall(grid, bath["x1"], bath["x2"], bath["y1"] - 1, door_x=segment_center(bath["x1"], bath["x2"]))

    rooms = [kitchen, bedroom1, common, bath, bedroom2]
    return (grid, rooms), "ok"


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
        cx, cy = room_center(room)
        ax.text(
            cx + 0.5, height - cy - 0.5, labels[i],
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


def try_generate_once(attempt):
    width = random.choice(odd_choices(MIN_WIDTH, MAX_WIDTH))
    height = random.choice(odd_choices(MIN_HEIGHT, MAX_HEIGHT))
    house_type = random.choice(["4-room", "5-room"])
    kitchen_side = random.choice(["left", "right"])

    print(f"  Attempt {attempt}: size={width}x{height}, type={house_type}, kitchen={kitchen_side}")

    if house_type == "4-room":
        result, reason = build_four_room_template_a(width, height, kitchen_side)
    else:
        result, reason = build_five_room_template_a(width, height, kitchen_side)

    if result is None:
        print(f"    Rejected during template build: {reason}")
        return None

    grid, rooms = result
    labels = assign_labels(rooms)

    start, end, front_mode = place_exterior_doors(
        grid,
        width,
        height,
        next(r for r in rooms if r["type"] == "Kitchen"),
        next(r for r in rooms if r["type"] == "Common"),
    )
    print(f"    Door mode: front={front_mode}")
    print(f"    Room areas: {[(r['type'], room_area(r)) for r in rooms]}")

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


def generate_valid_house(max_attempts=200):
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