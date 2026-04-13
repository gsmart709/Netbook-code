import random
from collections import deque
import matplotlib.pyplot as plt

WIDTH = 21
HEIGHT = 15


def create_empty_grid():
    return [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]


def add_outer_walls(grid):
    for x in range(WIDTH):
        grid[0][x] = "#"
        grid[HEIGHT - 1][x] = "#"
    for y in range(HEIGHT):
        grid[y][0] = "#"
        grid[y][WIDTH - 1] = "#"


def add_wall_with_door(grid, x1, y1, x2, y2):
    """
    Draw a straight wall between two points, leaving one door opening.
    Supports only vertical or horizontal walls.
    """
    if x1 == x2:
        ys = sorted([y1, y2])
        possible = [y for y in range(ys[0] + 1, ys[1]) if 0 < y < HEIGHT - 1]
        if not possible:
            return
        door_y = random.choice(possible)
        for y in range(ys[0], ys[1] + 1):
            if y != door_y:
                grid[y][x1] = "#"

    elif y1 == y2:
        xs = sorted([x1, x2])
        possible = [x for x in range(xs[0] + 1, xs[1]) if 0 < x < WIDTH - 1]
        if not possible:
            return
        door_x = random.choice(possible)
        for x in range(xs[0], xs[1] + 1):
            if x != door_x:
                grid[y1][x] = "#"


def add_room_walls(grid):
    """
    Create a house layout using only straight interior walls.
    """
    # Main vertical split
    main_v = random.choice([7, 8, 9, 10, 11, 12, 13])
    add_wall_with_door(grid, main_v, 1, main_v, HEIGHT - 2)

    # Left side horizontal split
    left_h = random.choice([4, 5, 6, 7, 8, 9, 10])
    add_wall_with_door(grid, 1, left_h, main_v, left_h)

    # Right side horizontal split
    right_h = random.choice([4, 5, 6, 7, 8, 9, 10])
    add_wall_with_door(grid, main_v, right_h, WIDTH - 2, right_h)

    # Optional extra room split on left
    if random.random() < 0.7:
        extra_v_left = random.choice([3, 4, 5, 6])
        top_or_bottom = random.choice(["top", "bottom"])
        if top_or_bottom == "top":
            add_wall_with_door(grid, extra_v_left, 1, extra_v_left, left_h)
        else:
            add_wall_with_door(grid, extra_v_left, left_h, extra_v_left, HEIGHT - 2)

    # Optional extra room split on right
    if random.random() < 0.7:
        extra_v_right = random.choice([main_v + 2, main_v + 3, main_v + 4, main_v + 5])
        extra_v_right = min(extra_v_right, WIDTH - 3)
        top_or_bottom = random.choice(["top", "bottom"])
        if top_or_bottom == "top":
            add_wall_with_door(grid, extra_v_right, 1, extra_v_right, right_h)
        else:
            add_wall_with_door(grid, extra_v_right, right_h, extra_v_right, HEIGHT - 2)


def get_empty_cells(grid):
    cells = []
    for y in range(1, HEIGHT - 1):
        for x in range(1, WIDTH - 1):
            if grid[y][x] == " ":
                cells.append((x, y))
    return cells


def place_points(grid):
    empties = get_empty_cells(grid)
    while True:
        start = random.choice(empties)
        end = random.choice(empties)
        if start != end:
            sx, sy = start
            ex, ey = end
            grid[sy][sx] = "E"
            grid[ey][ex] = "F"
            return start, end


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


def print_grid(grid):
    for row in grid:
        print("".join(row))


def plot_house(grid):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor("white")

    # Draw floor cells
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] != "#":
                rect = plt.Rectangle((x, HEIGHT - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    # Draw walls as filled black squares
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == "#":
                rect = plt.Rectangle((x, HEIGHT - y - 1), 1, 1)
                ax.add_patch(rect)

    # Draw path
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == ".":
                cx = x + 0.5
                cy = HEIGHT - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

    # Draw E and F labels
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == "E":
                ax.text(
                    x + 0.5,
                    HEIGHT - y - 0.5,
                    "E",
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


def generate_valid_house():
    while True:
        grid = create_empty_grid()
        add_outer_walls(grid)
        add_room_walls(grid)
        start, end = place_points(grid)
        path = find_path(grid, start, end)

        if path:
            draw_path(grid, path)
            return grid


if __name__ == "__main__":
    house = generate_valid_house()
    print_grid(house)
    plot_house(house)