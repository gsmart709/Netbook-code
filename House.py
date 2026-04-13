import random
import time
from collections import deque
import matplotlib.pyplot as plt

WIDTH = 21
HEIGHT = 15


def log_stage(name, start_time):
    elapsed = time.perf_counter() - start_time
    print(f"{name}... {elapsed:.4f}s")
    return time.perf_counter()


def create_empty_grid():
    return [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]


def print_grid(grid):
    for row in grid:
        print("".join(row))


def segment_center(start, end):
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
    top_x = segment_center(top_span[0], top_span[1])
    bottom_x = segment_center(bottom_span[0], bottom_span[1])

    grid[0][top_x] = "B"
    grid[HEIGHT - 1][bottom_x] = "F"

    return (top_x, 1), (bottom_x, HEIGHT - 2)


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


def build_three_room():
    grid = create_empty_grid()
    draw_outer_walls(grid)

    split_x = random.choice([6, 10, 14])
    main_door_y = segment_center(1, HEIGHT - 2)
    draw_vertical_wall(grid, split_x, 1, HEIGHT - 2, door_y=main_door_y)

    side = random.choice(["left", "right"])
    split_y = random.choice([4, 8, 10])

    if side == "left":
        door_x = segment_center(1, split_x - 1)
        draw_horizontal_wall(grid, 1, split_x - 1, split_y, door_x=door_x)
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
    grid = create_empty_grid()
    draw_outer_walls(grid)

    split_x = random.choice([6, 10, 14])
    split_y = random.choice([4, 8, 10])

    top_v_door = segment_center(1, split_y - 1)
    bottom_v_door = segment_center(split_y + 1, HEIGHT - 2)
    left_h_door = segment_center(1, split_x - 1)
    right_h_door = segment_center(split_x + 1, WIDTH - 2)

    draw_vertical_wall(grid, split_x, 1, split_y - 1, door_y=top_v_door)
    grid[split_y][split_x] = "#"
    draw_vertical_wall(grid, split_x, split_y + 1, HEIGHT - 2, door_y=bottom_v_door)

    draw_horizontal_wall(grid, 1, split_x - 1, split_y, door_x=left_h_door)
    draw_horizontal_wall(grid, split_x + 1, WIDTH - 2, split_y, door_x=right_h_door)

    top_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]
    bottom_spans = [(1, split_x - 1), (split_x + 1, WIDTH - 2)]

    top_span = random.choice(top_spans)
    bottom_span = random.choice(bottom_spans)

    start, end = place_front_back(grid, top_span, bottom_span)
    return grid, start, end, 4


def flood_room_cells(grid, start, visited):
    queue = deque([start])
    room = []
    visited.add(start)

    while queue:
        x, y = queue.popleft()
        room.append((x, y))

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < WIDTH
                and 0 <= ny < HEIGHT
                and (nx, ny) not in visited
                and grid[ny][nx] != "#"
            ):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return room


def detect_rooms(grid):
    visited = set()
    rooms = []

    for y in range(1, HEIGHT - 1):
        for x in range(1, WIDTH - 1):
            if grid[y][x] != "#" and (x, y) not in visited:
                room = flood_room_cells(grid, (x, y), visited)
                rooms.append(room)

    return rooms


def room_centroid(room):
    avg_x = sum(x for x, _ in room) / len(room)
    avg_y = sum(y for _, y in room) / len(room)
    return avg_x, avg_y


def choose_room_label_layout(rooms):
    """
    Simple believable labeling:
    - Largest room = Common
    - Smallest room = Bath
    - Top-most remaining = Bed
    - Bottom-most remaining = Kitchen
    If only 3 rooms, Common / Bed / Kitchen
    """
    room_info = []
    for i, room in enumerate(rooms):
        cx, cy = room_centroid(room)
        room_info.append({
            "index": i,
            "cells": room,
            "size": len(room),
            "cx": cx,
            "cy": cy,
        })

    labels = {}

    sorted_by_size = sorted(room_info, key=lambda r: r["size"])
    sorted_by_y = sorted(room_info, key=lambda r: r["cy"])

    largest = max(room_info, key=lambda r: r["size"])
    labels[largest["index"]] = "Common"

    remaining = [r for r in room_info if r["index"] not in labels]

    if len(room_info) == 4:
        smallest = min(remaining, key=lambda r: r["size"])
        labels[smallest["index"]] = "Bath"
        remaining = [r for r in remaining if r["index"] not in labels]

    if remaining:
        topmost = min(remaining, key=lambda r: r["cy"])
        labels[topmost["index"]] = "Bed"
        remaining = [r for r in remaining if r["index"] not in labels]

    if remaining:
        bottommost = max(remaining, key=lambda r: r["cy"])
        labels[bottommost["index"]] = "Kitchen"
        remaining = [r for r in remaining if r["index"] not in labels]

    for r in remaining:
        labels[r["index"]] = "Room"

    return labels


def room_label_positions(rooms, labels):
    result = []
    for i, room in enumerate(rooms):
        cx, cy = room_centroid(room)
        result.append((labels[i], cx, cy))
    return result


def plot_house(grid, room_labels):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor("white")

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] != "#":
                rect = plt.Rectangle((x, HEIGHT - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == "#":
                rect = plt.Rectangle((x, HEIGHT - y - 1), 1, 1)
                ax.add_patch(rect)

    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == ".":
                cx = x + 0.5
                cy = HEIGHT - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

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

    for label, cx, cy in room_labels:
        ax.text(
            cx + 0.5,
            HEIGHT - cy - 0.5,
            label,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.85),
        )

    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Random House Layout")
    plt.tight_layout()
    plt.show()


def generate_valid_house():
    builders = [build_three_room, build_four_room]

    while True:
        grid, start, end, room_count = random.choice(builders)()

        path = find_path(grid, start, end)
        if path:
            draw_path(grid, path)
            return grid, room_count


if __name__ == "__main__":
    total_start = time.perf_counter()
    stage_start = total_start

    print("Generating Layout")
    house, rooms = generate_valid_house()
    stage_start = log_stage("Layout complete", stage_start)

    print("Checking Exit Path")
    # already checked inside generation, but this gives visible stage timing
    stage_start = log_stage("Exit path confirmed", stage_start)

    print("Detecting Rooms")
    detected_rooms = detect_rooms(house)
    stage_start = log_stage("Room detection complete", stage_start)

    print("Labeling Rooms")
    labels = choose_room_label_layout(detected_rooms)
    room_labels = room_label_positions(detected_rooms, labels)
    stage_start = log_stage("Room labeling complete", stage_start)

    print("Printing ASCII Layout")
    print(f"Rooms: {rooms}")
    print_grid(house)
    stage_start = log_stage("ASCII output complete", stage_start)

    print("Generating Plot")
    plot_house(house, room_labels)
    stage_start = log_stage("Plot complete", stage_start)

    total_elapsed = time.perf_counter() - total_start
    print(f"Total time: {total_elapsed:.4f}s")