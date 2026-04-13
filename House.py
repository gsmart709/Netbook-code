import random
import time
from collections import deque
import matplotlib.pyplot as plt

MIN_WIDTH = 19
MAX_WIDTH = 25   # odd only
MIN_HEIGHT = 13
MAX_HEIGHT = 17  # odd only


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


def room_center(room):
    """
    Center of rectangular room, dead center.
    room = dict with x1,x2,y1,y2 inclusive interior bounds
    """
    cx = segment_center(room["x1"], room["x2"])
    cy = segment_center(room["y1"], room["y2"])
    return cx, cy


def room_area(room):
    return (room["x2"] - room["x1"] + 1) * (room["y2"] - room["y1"] + 1)


def place_front_back(grid, width, height, top_room, bottom_room):
    bx, _ = room_center(top_room)
    fx, _ = room_center(bottom_room)

    grid[0][bx] = "B"
    grid[height - 1][fx] = "F"

    # path starts just inside the doors
    return (bx, 1), (fx, height - 2)


def label_rooms(rooms, b_room_index):
    """
    Rules:
    - room with B is Kitchen
    - biggest remaining room is Common
    - other decent rooms are Bedroom
    - smaller rooms are Bath
    """
    labels = {}

    labels[b_room_index] = "Kitchen"

    remaining = [i for i in range(len(rooms)) if i != b_room_index]

    if remaining:
        biggest_remaining = max(remaining, key=lambda i: room_area(rooms[i]))
        labels[biggest_remaining] = "Common"
        remaining.remove(biggest_remaining)

    if remaining:
        remaining_areas = [room_area(rooms[i]) for i in remaining]
        if remaining_areas:
            max_area = max(remaining_areas)
            for i in remaining:
                area = room_area(rooms[i])
                if area >= max_area * 0.65:
                    labels[i] = "Bedroom"
                else:
                    labels[i] = "Bath"

    return labels


def build_four_room(width, height):
    """
    Four rooms using one full vertical and one full horizontal split.
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    split_x_choices = [x for x in range(6, width - 6) if x % 2 == 0]
    split_y_choices = [y for y in range(4, height - 4) if y % 2 == 0]

    split_x = random.choice(split_x_choices)
    split_y = random.choice(split_y_choices)

    # centered doors in each segment
    top_v_door = segment_center(1, split_y - 1)
    bottom_v_door = segment_center(split_y + 1, height - 2)
    left_h_door = segment_center(1, split_x - 1)
    right_h_door = segment_center(split_x + 1, width - 2)

    draw_vertical_wall(grid, split_x, 1, split_y - 1, door_y=top_v_door)
    grid[split_y][split_x] = "#"
    draw_vertical_wall(grid, split_x, split_y + 1, height - 2, door_y=bottom_v_door)

    draw_horizontal_wall(grid, 1, split_x - 1, split_y, door_x=left_h_door)
    draw_horizontal_wall(grid, split_x + 1, width - 2, split_y, door_x=right_h_door)

    rooms = [
        {"x1": 1, "x2": split_x - 1, "y1": 1, "y2": split_y - 1},              # top left
        {"x1": split_x + 1, "x2": width - 2, "y1": 1, "y2": split_y - 1},      # top right
        {"x1": 1, "x2": split_x - 1, "y1": split_y + 1, "y2": height - 2},     # bottom left
        {"x1": split_x + 1, "x2": width - 2, "y1": split_y + 1, "y2": height - 2},  # bottom right
    ]

    top_rooms = [0, 1]
    bottom_rooms = [2, 3]

    b_room_index = random.choice(top_rooms)
    f_room_index = random.choice(bottom_rooms)

    start, end = place_front_back(grid, width, height, rooms[b_room_index], rooms[f_room_index])
    return grid, rooms, b_room_index, start, end


def build_five_room(width, height):
    """
    Five rooms:
    4-room base + split one quadrant again.
    """
    grid = create_empty_grid(width, height)
    draw_outer_walls(grid, width, height)

    split_x_choices = [x for x in range(6, width - 6) if x % 2 == 0]
    split_y_choices = [y for y in range(4, height - 4) if y % 2 == 0]

    split_x = random.choice(split_x_choices)
    split_y = random.choice(split_y_choices)

    # Main cross
    top_v_door = segment_center(1, split_y - 1)
    bottom_v_door = segment_center(split_y + 1, height - 2)
    left_h_door = segment_center(1, split_x - 1)
    right_h_door = segment_center(split_x + 1, width - 2)

    draw_vertical_wall(grid, split_x, 1, split_y - 1, door_y=top_v_door)
    grid[split_y][split_x] = "#"
    draw_vertical_wall(grid, split_x, split_y + 1, height - 2, door_y=bottom_v_door)

    draw_horizontal_wall(grid, 1, split_x - 1, split_y, door_x=left_h_door)
    draw_horizontal_wall(grid, split_x + 1, width - 2, split_y, door_x=right_h_door)

    base_rooms = [
        {"x1": 1, "x2": split_x - 1, "y1": 1, "y2": split_y - 1},              # 0 top left
        {"x1": split_x + 1, "x2": width - 2, "y1": 1, "y2": split_y - 1},      # 1 top right
        {"x1": 1, "x2": split_x - 1, "y1": split_y + 1, "y2": height - 2},     # 2 bottom left
        {"x1": split_x + 1, "x2": width - 2, "y1": split_y + 1, "y2": height - 2},  # 3 bottom right
    ]

    # Split one room that is big enough
    splittable = []
    for i, room in enumerate(base_rooms):
        rw = room["x2"] - room["x1"] + 1
        rh = room["y2"] - room["y1"] + 1
        if rw >= 7 or rh >= 7:
            splittable.append(i)

    split_room_index = random.choice(splittable)
    room = base_rooms[split_room_index]

    rw = room["x2"] - room["x1"] + 1
    rh = room["y2"] - room["y1"] + 1

    new_rooms = []

    if rw >= rh and rw >= 7:
        # vertical split inside room
        local_choices = [x for x in range(room["x1"] + 2, room["x2"] - 1) if x % 2 == 0]
        inner_x = random.choice(local_choices)
        door_y = segment_center(room["y1"], room["y2"])
        draw_vertical_wall(grid, inner_x, room["y1"], room["y2"], door_y=door_y)

        r1 = {"x1": room["x1"], "x2": inner_x - 1, "y1": room["y1"], "y2": room["y2"]}
        r2 = {"x1": inner_x + 1, "x2": room["x2"], "y1": room["y1"], "y2": room["y2"]}
        new_rooms = [r1, r2]
    else:
        # horizontal split inside room
        local_choices = [y for y in range(room["y1"] + 2, room["y2"] - 1) if y % 2 == 0]
        inner_y = random.choice(local_choices)
        door_x = segment_center(room["x1"], room["x2"])
        draw_horizontal_wall(grid, room["x1"], room["x2"], inner_y, door_x=door_x)

        r1 = {"x1": room["x1"], "x2": room["x2"], "y1": room["y1"], "y2": inner_y - 1}
        r2 = {"x1": room["x1"], "x2": room["x2"], "y1": inner_y + 1, "y2": room["y2"]}
        new_rooms = [r1, r2]

    rooms = []
    for i, r in enumerate(base_rooms):
        if i == split_room_index:
            rooms.extend(new_rooms)
        else:
            rooms.append(r)

    top_room_indices = [i for i, r in enumerate(rooms) if r["y1"] == 1]
    bottom_room_indices = [i for i, r in enumerate(rooms) if r["y2"] == height - 2]

    b_room_index = random.choice(top_room_indices)
    f_room_index = random.choice(bottom_room_indices)

    start, end = place_front_back(grid, width, height, rooms[b_room_index], rooms[f_room_index])
    return grid, rooms, b_room_index, start, end


def plot_house(grid, rooms, labels, width, height):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor("white")

    # floor cells
    for y in range(height):
        for x in range(width):
            if grid[y][x] != "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    # walls
    for y in range(height):
        for x in range(width):
            if grid[y][x] == "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1)
                ax.add_patch(rect)

    # path
    for y in range(height):
        for x in range(width):
            if grid[y][x] == ".":
                cx = x + 0.5
                cy = height - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

    # B and F
    for y in range(height):
        for x in range(width):
            if grid[y][x] == "B":
                ax.text(
                    x + 0.5, height - y - 0.5, "B",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black")
                )
            elif grid[y][x] == "F":
                ax.text(
                    x + 0.5, height - y - 0.5, "F",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black")
                )

    # room labels dead center
    for i, room in enumerate(rooms):
        label = labels[i]
        cx, cy = room_center(room)
        ax.text(
            cx + 0.5, height - cy - 0.5, label,
            ha="center", va="center", fontsize=10, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.85)
        )

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Random House Layout")
    plt.tight_layout()
    plt.show()


def generate_valid_house():
    width = random.choice(odd_choices(MIN_WIDTH, MAX_WIDTH))
    height = random.choice(odd_choices(MIN_HEIGHT, MAX_HEIGHT))

    builder = random.choice([build_four_room, build_five_room])

    while True:
        grid, rooms, b_room_index, start, end = builder(width, height)
        path = find_path(grid, start, end, width, height)
        if path:
            draw_path(grid, path)
            labels = label_rooms(rooms, b_room_index)
            return grid, rooms, labels, width, height


if __name__ == "__main__":
    total_start = time.perf_counter()
    stage_start = total_start

    print("Generating Layout")
    house, rooms, labels, width, height = generate_valid_house()
    stage_start = log_stage("Layout complete", stage_start)

    print("Checking Exit Path")
    stage_start = log_stage("Exit path confirmed", stage_start)

    print("Assigning Room Labels")
    stage_start = log_stage("Room labeling complete", stage_start)

    print("Printing ASCII Layout")
    print(f"House size: {width} x {height}")
    print(f"Rooms: {len(rooms)}")
    print_grid(house)
    stage_start = log_stage("ASCII output complete", stage_start)

    print("Generating Plot")
    plot_house(house, rooms, labels, width, height)
    stage_start = log_stage("Plot complete", stage_start)

    total_elapsed = time.perf_counter() - total_start
    print(f"Total time: {total_elapsed:.4f}s")