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
    """
    For an odd-length segment, return center / offset-left / offset-right.
    """
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
    # Back door in kitchen: centered on kitchen segment
    bx = segment_center(kitchen_room["x1"], kitchen_room["x2"])

    # Front door in common: center or offset
    modes = ["center", "left", "right"]
    random.shuffle(modes)

    fx = None
    for mode in modes:
        candidate = offset_position(common_room["x1"], common_room["x2"], mode)
        if candidate != bx:
            fx = candidate
            break

    if fx is None:
        # fallback: any x in common room not equal to bx
        possible = [x for x in range(common_room["x1"], common_room["x2"] + 1) if x != bx]
        fx = random.choice(possible)

    grid[0][bx] = "B"
    grid[height - 1][fx] = "F"

    start = (bx, 1)
    end = (fx, height - 2)
    return start, end


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


def build_four_room(width, height):
    """
    More random 4-room layout:
    - Kitchen always at back-left or back-right
    - Common always front-ish and biggest
    - Bedroom and Bath connect only to Common
    - Bath always compact/small
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    side = random.choice(["left", "right"])

    # Back band height
    kitchen_h = 3
    split_y = kitchen_h + 1
    lower_y1 = split_y + 1
    lower_y2 = height - 2

    # Compact bath: 3x3 or 5x3-ish footprint
    bath_w = random.choice([3, 5])
    bath_h = 3

    # Kitchen fixed side at back
    kitchen_w = random.choice([5, 7])

    if side == "left":
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": kitchen_h}
        back_other = {"x1": kitchen_w + 2, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        kitchen_common_door_x = segment_center(back_other["x1"], back_other["x2"])
    else:
        kitchen = {"type": "Kitchen", "x1": width - 1 - kitchen_w, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        back_other = {"x1": 1, "x2": kitchen["x1"] - 2, "y1": 1, "y2": kitchen_h}
        kitchen_common_door_x = segment_center(back_other["x1"], back_other["x2"])

    # Horizontal wall separating back band from rest
    draw_horizontal_wall(grid, 1, width - 2, split_y, door_x=kitchen_common_door_x)

    # Vertical divider in back band between kitchen and upper-back part
    back_divider_x = kitchen["x2"] + 1 if side == "left" else kitchen["x1"] - 1
    back_door_y = segment_center(1, kitchen_h)
    draw_vertical_wall(grid, back_divider_x, 1, kitchen_h, door_y=back_door_y)

    # Lower region split into bedroom/common/bath
    bath_top = lower_y2 - bath_h + 1

    if side == "left":
        # Bath on far right, compact
        bath = {"type": "Bath", "x1": width - 2 - bath_w + 1, "x2": width - 2, "y1": bath_top, "y2": lower_y2}
        bath_wall_x = bath["x1"] - 1

        # Bedroom on far left lower
        bedroom_w = random.choice([5, 7])
        bedroom = {"type": "Bedroom", "x1": 1, "x2": bedroom_w, "y1": lower_y1, "y2": lower_y2}
        bed_wall_x = bedroom["x2"] + 1

        common = {
            "type": "Common",
            "x1": bed_wall_x + 1,
            "x2": bath_wall_x - 1,
            "y1": lower_y1,
            "y2": lower_y2,
        }

        if common["x2"] - common["x1"] + 1 < 7:
            return None

        bed_door_y = segment_center(lower_y1, lower_y2)
        draw_vertical_wall(grid, bed_wall_x, lower_y1, lower_y2, door_y=bed_door_y)

        bath_door_x = segment_center(bath["x1"], bath["x2"])
        draw_horizontal_wall(grid, bath["x1"], bath["x2"], bath["y1"] - 1, door_x=bath_door_x)
        draw_vertical_wall(grid, bath_wall_x, lower_y1, bath["y1"] - 2, door_y=None)

    else:
        # Bath on far left, compact
        bath = {"type": "Bath", "x1": 1, "x2": bath_w, "y1": bath_top, "y2": lower_y2}
        bath_wall_x = bath["x2"] + 1

        # Bedroom on far right lower
        bedroom_w = random.choice([5, 7])
        bedroom = {"type": "Bedroom", "x1": width - 2 - bedroom_w + 1, "x2": width - 2, "y1": lower_y1, "y2": lower_y2}
        bed_wall_x = bedroom["x1"] - 1

        common = {
            "type": "Common",
            "x1": bath_wall_x + 1,
            "x2": bed_wall_x - 1,
            "y1": lower_y1,
            "y2": lower_y2,
        }

        if common["x2"] - common["x1"] + 1 < 7:
            return None

        bed_door_y = segment_center(lower_y1, lower_y2)
        draw_vertical_wall(grid, bed_wall_x, lower_y1, lower_y2, door_y=bed_door_y)

        bath_door_x = segment_center(bath["x1"], bath["x2"])
        draw_horizontal_wall(grid, bath["x1"], bath["x2"], bath["y1"] - 1, door_x=bath_door_x)
        draw_vertical_wall(grid, bath_wall_x, lower_y1, bath["y1"] - 2, door_y=None)

    rooms = [kitchen, bedroom, common, bath]

    start, end = place_exterior_doors(grid, width, height, kitchen, common)
    return grid, rooms, start, end


def build_five_room(width, height):
    """
    More random 5-room layout:
    - Kitchen back-left or back-right
    - Common front-middle and biggest
    - 2 bedrooms
    - 1 compact bath
    - Bedrooms/Bath each one door only to Common
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    side = random.choice(["left", "right"])

    kitchen_h = 3
    split_y = kitchen_h + 1
    lower_y1 = split_y + 1
    lower_y2 = height - 2

    kitchen_w = random.choice([5, 7])

    if side == "left":
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": kitchen_h}
        back_other = {"x1": kitchen_w + 2, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        kitchen_common_door_x = segment_center(back_other["x1"], back_other["x2"])
    else:
        kitchen = {"type": "Kitchen", "x1": width - 1 - kitchen_w, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        back_other = {"x1": 1, "x2": kitchen["x1"] - 2, "y1": 1, "y2": kitchen_h}
        kitchen_common_door_x = segment_center(back_other["x1"], back_other["x2"])

    draw_horizontal_wall(grid, 1, width - 2, split_y, door_x=kitchen_common_door_x)

    back_divider_x = kitchen["x2"] + 1 if side == "left" else kitchen["x1"] - 1
    back_door_y = segment_center(1, kitchen_h)
    draw_vertical_wall(grid, back_divider_x, 1, kitchen_h, door_y=back_door_y)

    # Lower area columns: left room / common / right room
    side_room_w = 5
    left_wall_x = side_room_w + 1
    right_wall_x = width - 2 - side_room_w

    if right_wall_x - left_wall_x - 1 < 7:
        return None

    common = {
        "type": "Common",
        "x1": left_wall_x + 1,
        "x2": right_wall_x - 1,
        "y1": lower_y1,
        "y2": lower_y2,
    }

    # Left side split into Bedroom + Bath compact
    bath_h = 3
    left_split_y = lower_y2 - bath_h
    if left_split_y - lower_y1 < 2:
        return None

    bedroom1 = {"type": "Bedroom", "x1": 1, "x2": left_wall_x - 1, "y1": lower_y1, "y2": left_split_y - 1}
    bath = {"type": "Bath", "x1": 1, "x2": left_wall_x - 1, "y1": left_split_y + 1, "y2": lower_y2}

    bedroom2 = {"type": "Bedroom", "x1": right_wall_x + 1, "x2": width - 2, "y1": lower_y1, "y2": lower_y2}

    # Common connections only
    left_common_door_y = segment_center(lower_y1, lower_y2)
    right_common_door_y = segment_center(lower_y1, lower_y2)
    draw_vertical_wall(grid, left_wall_x, lower_y1, lower_y2, door_y=left_common_door_y)
    draw_vertical_wall(grid, right_wall_x, lower_y1, lower_y2, door_y=right_common_door_y)

    # Split left column into bedroom+bath with one centered door into bath from above
    bath_door_x = segment_center(bath["x1"], bath["x2"])
    draw_horizontal_wall(grid, bath["x1"], bath["x2"], bath["y1"] - 1, door_x=bath_door_x)

    rooms = [kitchen, bedroom1, common, bath, bedroom2]

    start, end = place_exterior_doors(grid, width, height, kitchen, common)
    return grid, rooms, start, end


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
    """
    Enforce:
    Common > Kitchen > Bedrooms > Bath
    """
    common = next(r for r in rooms if r["type"] == "Common")
    kitchen = next(r for r in rooms if r["type"] == "Kitchen")
    bath = next(r for r in rooms if r["type"] == "Bath")
    bedrooms = [r for r in rooms if r["type"] == "Bedroom"]

    if not (room_area(common) > room_area(kitchen)):
        return False
    if not all(room_area(kitchen) > room_area(b) for b in bedrooms):
        return False
    if not all(room_area(b) > room_area(bath) for b in bedrooms):
        return False

    # Bath should be compact, not long
    bath_w = bath["x2"] - bath["x1"] + 1
    bath_h = bath["y2"] - bath["y1"] + 1
    if max(bath_w, bath_h) > 5:
        return False

    return True


def generate_valid_house():
    attempts = 0

    while True:
        attempts += 1

        width = random.choice(odd_choices(MIN_WIDTH, MAX_WIDTH))
        height = random.choice(odd_choices(MIN_HEIGHT, MAX_HEIGHT))

        builder = random.choice([build_four_room, build_five_room])
        result = builder(width, height)

        if result is None:
            continue

        grid, rooms, start, end = result

        if not validate_room_sizes(rooms):
            continue

        path = find_path(grid, start, end, width, height)
        if not path:
            continue

        draw_path(grid, path)
        labels = assign_labels(rooms)
        return grid, rooms, labels, width, height, attempts


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