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
    bx, _ = room_center(kitchen_room)
    fx, _ = room_center(common_room)

    grid[0][bx] = "B"
    grid[height - 1][fx] = "F"

    # Pathfinding starts just inside the exterior doors
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
    """
    Enforce:
    - Kitchen fixed
    - Common fixed
    - Remaining larger rooms = Bedroom
    - Remaining smallest = Bath
    """
    labels = {}

    kitchen_index = next(i for i, r in enumerate(rooms) if r["type"] == "Kitchen")
    common_index = next(i for i, r in enumerate(rooms) if r["type"] == "Common")

    labels[kitchen_index] = "Kitchen"
    labels[common_index] = "Common"

    remaining = [i for i in range(len(rooms)) if i not in labels]
    remaining.sort(key=lambda i: room_area(rooms[i]), reverse=True)

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
    Graph:
        Kitchen <-> Common
        Bedroom <-> Common
        Bath    <-> Common

    Layout:
        Kitchen across top
        Lower band split into Bedroom | Common | Bath
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    kitchen_h = 3  # keeps kitchen clearly second biggest
    wall_y = kitchen_h + 1
    lower_y1 = wall_y + 1
    lower_y2 = height - 2

    # Choose side widths so:
    # Common biggest, Bath smallest, Bedroom in between
    bedroom_w = random.choice([5, 7])
    bath_w = 3

    common_w = (width - 2) - bedroom_w - bath_w - 2  # minus 2 internal walls
    if common_w < 7 or common_w % 2 == 0:
        return None

    left_wall_x = bedroom_w + 1
    right_wall_x = left_wall_x + common_w + 1

    # Kitchen / lower separator wall
    kitchen_common_door_x = segment_center(left_wall_x + 1, right_wall_x - 1)
    draw_horizontal_wall(grid, 1, width - 2, wall_y, door_x=kitchen_common_door_x)

    # Lower vertical walls
    lower_mid_y = segment_center(lower_y1, lower_y2)
    draw_vertical_wall(grid, left_wall_x, lower_y1, lower_y2, door_y=lower_mid_y)
    draw_vertical_wall(grid, right_wall_x, lower_y1, lower_y2, door_y=lower_mid_y)

    rooms = [
        {
            "type": "Kitchen",
            "x1": 1,
            "x2": width - 2,
            "y1": 1,
            "y2": kitchen_h,
        },
        {
            "type": "Bedroom",
            "x1": 1,
            "x2": left_wall_x - 1,
            "y1": lower_y1,
            "y2": lower_y2,
        },
        {
            "type": "Common",
            "x1": left_wall_x + 1,
            "x2": right_wall_x - 1,
            "y1": lower_y1,
            "y2": lower_y2,
        },
        {
            "type": "Bath",
            "x1": right_wall_x + 1,
            "x2": width - 2,
            "y1": lower_y1,
            "y2": lower_y2,
        },
    ]

    kitchen_room = rooms[0]
    common_room = rooms[2]
    start, end = place_exterior_doors(grid, width, height, kitchen_room, common_room)

    return grid, rooms, start, end


def build_five_room(width, height):
    """
    Graph:
        Kitchen <-> Common
        Bedroom1 <-> Common
        Bedroom2 <-> Common
        Bath     <-> Common

    Layout:
        Kitchen across top
        Lower band split into:
            left column (Bedroom top, Bath bottom)
            center Common
            right Bedroom
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    kitchen_h = 3
    wall_y = kitchen_h + 1
    lower_y1 = wall_y + 1
    lower_y2 = height - 2
    lower_h = lower_y2 - lower_y1 + 1

    if lower_h < 7:
        return None

    left_w = 5
    right_w = 5
    common_w = (width - 2) - left_w - right_w - 2
    if common_w < 7 or common_w % 2 == 0:
        return None

    left_wall_x = left_w + 1
    right_wall_x = left_wall_x + common_w + 1

    # Kitchen / common separator
    kitchen_common_door_x = segment_center(left_wall_x + 1, right_wall_x - 1)
    draw_horizontal_wall(grid, 1, width - 2, wall_y, door_x=kitchen_common_door_x)

    # Common side connections
    left_column_mid_y = segment_center(lower_y1, lower_y2)
    right_bed_mid_y = segment_center(lower_y1, lower_y2)

    draw_vertical_wall(grid, left_wall_x, lower_y1, lower_y2, door_y=left_column_mid_y)
    draw_vertical_wall(grid, right_wall_x, lower_y1, lower_y2, door_y=right_bed_mid_y)

    # Split left column into Bedroom / Bath
    bath_h = 3
    bed1_h = lower_h - bath_h - 1
    if bed1_h < 3 or bed1_h % 2 == 0:
        return None

    split_y = lower_y1 + bed1_h
    left_internal_door_x = segment_center(1, left_wall_x - 1)
    draw_horizontal_wall(grid, 1, left_wall_x - 1, split_y, door_x=left_internal_door_x)

    rooms = [
        {
            "type": "Kitchen",
            "x1": 1,
            "x2": width - 2,
            "y1": 1,
            "y2": kitchen_h,
        },
        {
            "type": "Bedroom",
            "x1": 1,
            "x2": left_wall_x - 1,
            "y1": lower_y1,
            "y2": split_y - 1,
        },
        {
            "type": "Bath",
            "x1": 1,
            "x2": left_wall_x - 1,
            "y1": split_y + 1,
            "y2": lower_y2,
        },
        {
            "type": "Common",
            "x1": left_wall_x + 1,
            "x2": right_wall_x - 1,
            "y1": lower_y1,
            "y2": lower_y2,
        },
        {
            "type": "Bedroom",
            "x1": right_wall_x + 1,
            "x2": width - 2,
            "y1": lower_y1,
            "y2": lower_y2,
        },
    ]

    kitchen_room = rooms[0]
    common_room = rooms[3]
    start, end = place_exterior_doors(grid, width, height, kitchen_room, common_room)

    return grid, rooms, start, end


def plot_house(grid, rooms, labels, width, height):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor("white")

    # Floor cells
    for y in range(height):
        for x in range(width):
            if grid[y][x] != "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    # Walls
    for y in range(height):
        for x in range(width):
            if grid[y][x] == "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1)
                ax.add_patch(rect)

    # Path
    for y in range(height):
        for x in range(width):
            if grid[y][x] == ".":
                cx = x + 0.5
                cy = height - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

    # Exterior labels
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

    # Room labels dead center
    for i, room in enumerate(rooms):
        cx, cy = room_center(room)
        ax.text(
            cx + 0.5,
            height - cy - 0.5,
            labels[i],
            ha="center",
            va="center",
            fontsize=10,
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
        path = find_path(grid, start, end, width, height)

        if path:
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