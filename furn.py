import copy
import matplotlib.pyplot as plt
import housegen


def get_kitchen_room(rooms, labels):
    for room in rooms:
        if labels[id(room)] == "Kitchen":
            return room
    return None


def make_furniture_overlay(width, height):
    return [[" " for _ in range(width)] for _ in range(height)]


def place_kitchen_furniture(overlay, kitchen):
    x1, x2 = kitchen["x1"], kitchen["x2"]
    y1, y2 = kitchen["y1"], kitchen["y2"]

    # Top interior row under the B wall = all counters
    for x in range(x1, x2 + 1):
        overlay[y1][x] = "c"

    # Side wall pattern, shaved off from the end if it does not fit
    full_pattern = ["c", "c", "f", "c", "c", "w"]
    available_side_cells = y2 - y1  # rows below the top counter row
    usable_pattern = full_pattern[:available_side_cells]

    # Kitchen is either on left exterior wall or right exterior wall
    side_x = x1 if x1 == 1 else x2
    start_y = y1 + 1

    for i, item in enumerate(usable_pattern):
        overlay[start_y + i][side_x] = item

    return True, f"placed {len(usable_pattern)} side items"


def merge_for_ascii(base_grid, furniture_overlay):
    merged = copy.deepcopy(base_grid)

    for y in range(len(base_grid)):
        for x in range(len(base_grid[0])):
            if furniture_overlay[y][x] != " " and merged[y][x] in [" ", "."]:
                merged[y][x] = furniture_overlay[y][x]

    return merged


def print_grid(grid):
    for row in grid:
        print("".join(row))


def plot_house_base(base_grid, rooms, labels, width, height):
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_facecolor("white")

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] != "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] == "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1)
                ax.add_patch(rect)

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] == ".":
                cx = x + 0.5
                cy = height - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] == "B":
                ax.text(
                    x + 0.5, height - y - 0.5, "B",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )
            elif base_grid[y][x] == "F":
                ax.text(
                    x + 0.5, height - y - 0.5, "F",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )

    for room in rooms:
        label = labels[id(room)]
        cx, cy = housegen.room_center(room)
        ax.text(
            cx + 0.5, height - cy - 0.5, label,
            ha="center", va="center", fontsize=9, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.85),
        )

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Base House Layout")
    plt.tight_layout()
    plt.show()


def plot_house_with_furniture(base_grid, furniture_overlay, rooms, labels, width, height):
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.set_facecolor("white")

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] != "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1, fill=False, linewidth=0.5)
                ax.add_patch(rect)

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] == "#":
                rect = plt.Rectangle((x, height - y - 1), 1, 1)
                ax.add_patch(rect)

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] == ".":
                cx = x + 0.5
                cy = height - y - 0.5
                ax.plot(cx, cy, marker="o", markersize=4)

    for y in range(height):
        for x in range(width):
            if base_grid[y][x] == "B":
                ax.text(
                    x + 0.5, height - y - 0.5, "B",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )
            elif base_grid[y][x] == "F":
                ax.text(
                    x + 0.5, height - y - 0.5, "F",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="black"),
                )

    for room in rooms:
        label = labels[id(room)]
        cx, cy = housegen.room_center(room)
        ax.text(
            cx + 0.5, height - cy - 0.5, label,
            ha="center", va="center", fontsize=9, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black", alpha=0.85),
        )

    for y in range(height):
        for x in range(width):
            item = furniture_overlay[y][x]
            if item != " ":
                ax.text(
                    x + 0.5, height - y - 0.5, item,
                    ha="center", va="center", fontsize=12, fontweight="bold"
                )

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Kitchen Furniture Layout")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    base_grid, rooms, labels, width, height, attempts = housegen.generate_valid_house()

    kitchen = get_kitchen_room(rooms, labels)
    if kitchen is None:
        raise RuntimeError("No kitchen found in generated house.")

    furniture_overlay = make_furniture_overlay(width, height)
    ok, message = place_kitchen_furniture(furniture_overlay, kitchen)

    print(f"House size: {width} x {height}")
    print(f"Attempts: {attempts}")
    print(f"Kitchen bounds: {kitchen}")
    print(f"Kitchen furniture: {message}")

    print("\nBase layout:\n")
    print_grid(base_grid)

    merged = merge_for_ascii(base_grid, furniture_overlay)

    print("\nLayout with kitchen furniture:\n")
    print_grid(merged)

    plot_house_base(base_grid, rooms, labels, width, height)
    plot_house_with_furniture(base_grid, furniture_overlay, rooms, labels, width, height)