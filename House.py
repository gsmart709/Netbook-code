import random
from collections import deque
import matplotlib.pyplot as plt

WIDTH = 21   # keep odd
HEIGHT = 15  # keep odd


def create_empty_grid():
    return [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]


def print_grid(grid):
    for row in grid:
        print("".join(row))


def segment_center(start, end):
    """
    Returns the center cell of an inclusive segment.
    Assumes odd length.
    """
    length = end - start + 1
    if length % 2 == 0:
        raise ValueError(f"Segment {start}..{end} has even length; cannot center exactly.")
    return (start + end) // 2


def draw_outer_walls(grid):
    for x in range(WIDTH):
        grid[0][x] = "#"
        grid[HEIGHT - 1][x] = "#"
    for y in range(HEIGHT):
        grid[y][0] = "#"
        grid[y][WIDTH - 1] = "#"


def draw_vertical_wall(grid, x, y1, y2, door_y=None):
    for y in range(y1, y2 + 1):
        if y != door_y:
            grid[y][x] = "#"


def draw_horizontal_wall(grid, x1, x2, y, door_x=None):
    for x in range(x1, x2 + 1):
        if x != door_x:
            grid[y][x] = "#"


def place_front_back(grid, top_span, bottom_span):
    """
    B always on top wall, F always on bottom wall.
    Each is centered on its wall segment.
    top_span / bottom_span are (x_start, x_end) inclusive interior spans.
    """
    top_x = segment_center(top_span[0], top_span[1])
    bottom_x = segment_center(bottom_span[0], bottom_span[1])

    grid[0][top_x] = "B"
    grid[HEIGHT - 1][bottom_x] = "F"

    return (top_x, 1), (bottom_x, HEIGHT - 2)  # pathfinding starts just inside


def find_path(grid, start, end):
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
                0 <= nx < WIDTH
                and 0 <= ny < HEIGHT
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


def plot_house(grid):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor("white")

    # draw floor cells
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] != "#":
                rect = plt.Rectangle((x, HEIGHT - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    # draw walls
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == "#":
                rect = plt.Rectangle((x, HEIGHT - y - 1), 1, 1)
                ax.add_patch(rect)

    # draw path
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == ".":
                cx = x + 0.5
                cy = HEIGHT - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

    # draw B and F labels
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == "B":
                ax.text(
                    x + 0.5,
                    HEIGHT - y - 0.5,
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
                    HEIGHT - y - 0.5,
                    "F",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )

    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Random House Layout")
    plt.tight_layout()
    plt.show()


def build_two_room_vertical():
    """
    2 rooms split left/right.
    """
    grid = create_empty_grid()
    draw_outer_walls(grid)

    # even x makes left and right spans odd widths
    split_x = random.choice([6, 10, 14])

    door_y = segment_center(1, HEIGHT - 2)
    draw_vertical_wall(grid, split_x, 1, HEIGHT - 2, door_y=door_y)

    # choose top/bottom exterior room spans for B and F
    spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]
    top_span = random.choice(spans)
    bottom_span = random.choice(spans)

    start, end = place_front_back(grid, top_span, bottom_span)
    return grid, start, end, 2


def build_two_room_horizontal():
    """
    2 rooms split top/bottom.
    """
    grid = create_empty_grid()
    draw_outer_walls(grid)

    split_y = random.choice([4, 8, 10])

    door_x = segment_center(1, WIDTH - 2)
    draw_horizontal_wall(grid, 1, WIDTH - 2, split_y, door_x=door_x)

    # full top and bottom spans stay odd width
    top_span = (1, WIDTH - 2)
    bottom_span = (1, WIDTH - 2)

    start, end = place_front_back(grid, top_span, bottom_span)
    return grid, start, end, 2


def build_three_room():
    """
    3 rooms:
    full vertical split, then one horizontal split on either left or right side.
    Every room gets at least one centered door.
    """
    grid = create_empty_grid()
    draw_outer_walls(grid)

    split_x = random.choice([6, 10, 14])
    main_door_y = segment_center(1, HEIGHT - 2)
    draw_vertical_wall(grid, split_x, 1, HEIGHT - 2, door_y=main_door_y)

    side = random.choice(["left", "right"])
    split_y = random.choice([4, 8, 10])  # even so top/bottom room heights are odd

    if side == "left":
        door_x = segment_center(1, split_x - 1)
        draw_horizontal_wall(grid, 1, split_x - 1, split_y, door_x=door_x)

        top_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]
        bottom_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]
    else:
        door_x = segment_center(split_x + 1, WIDTH - 2)
        draw_horizontal_wall(grid, split_x + 1, WIDTH - 2, split_y, door_x=door_x)

        top_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]
        bottom_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]

    top_span = random.choice(top_spans)
    bottom_span = random.choice(bottom_spans)

    start, end = place_front_back(grid, top_span, bottom_span)
    return grid, start, end, 3


def build_four_room():
    """
    4 rooms:
    one full vertical wall + one full horizontal wall.
    Each wall segment gets a centered door so all rooms are accessible.
    """
    grid = create_empty_grid()
    draw_outer_walls(grid)

    split_x = random.choice([6, 10, 14])
    split_y = random.choice([4, 8, 10])

    # centered doors in each segment
    top_v_door = segment_center(1, split_y - 1)
    bottom_v_door = segment_center(split_y + 1, HEIGHT - 2)

    left_h_door = segment_center(1, split_x - 1)
    right_h_door = segment_center(split_x + 1, WIDTH - 2)

    # draw vertical wall in two segments
    draw_vertical_wall(grid, split_x, 1, split_y - 1, door_y=top_v_door)
    grid[split_y][split_x] = "#"  # center crossing cell
    draw_vertical_wall(grid, split_x, split_y + 1, HEIGHT - 2, door_y=bottom_v_door)

    # draw horizontal wall in two segments
    draw_horizontal_wall(grid, 1, split_x - 1, split_y, door_x=left_h_door)
    draw_horizontal_wall(grid, split_x + 1, WIDTH - 2, split_y, door_x=right_h_door)

    top_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]
    bottom_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]

    top_span = random.choice(top_spans)
    bottom_span = random.choice(bottom_spans)

    start, end = place_front_back(grid, top_span, bottom_span)
    return grid, start, end, 4


def generate_valid_house():
    builders = [
        build_two_room_vertical,
        build_two_room_horizontal,
        build_three_room,
        build_four_room,
    ]

    while True:
        builder = random.choice(builders)
        grid, start, end, room_count = builder()

        path = find_path(grid, start, end)
        if path:
            draw_path(grid, path)
            return grid, room_count


if __name__ == "__main__":
    house, rooms = generate_valid_house()
    print(f"Rooms: {rooms}")
    print_grid(house)
    plot_house(house)