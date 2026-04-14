import random
import matplotlib.pyplot as plt

# ---------- CORE TREEMAP LOGIC ----------

def normalize_sizes(sizes, dx, dy):
    total = sum(sizes)
    return [s * dx * dy / total for s in sizes]


def worst_ratio(row, w):
    if not row:
        return float("inf")
    s = sum(row)
    return max((w**2 * max(row)) / (s**2), (s**2) / (w**2 * min(row)))


def layout_row(row, x, y, dx, dy):
    rects = []

    if dx >= dy:
        height = sum(row) / dx
        cur_x = x
        for r in row:
            width = r / height
            rects.append((cur_x, y, width, height))
            cur_x += width
        return rects, x, y + height, dx, dy - height
    else:
        width = sum(row) / dy
        cur_y = y
        for r in row:
            height = r / width
            rects.append((x, cur_y, width, height))
            cur_y += height
        return rects, x + width, y, dx - width, dy


def squarify(sizes, x, y, dx, dy):
    sizes = sorted(sizes, reverse=True)
    rects = []
    row = []

    while sizes:
        item = sizes[0]
        if not row or worst_ratio(row + [item], min(dx, dy)) <= worst_ratio(row, min(dx, dy)):
            row.append(item)
            sizes.pop(0)
        else:
            r, x, y, dx, dy = layout_row(row, x, y, dx, dy)
            rects.extend(r)
            row = []

    if row:
        r, x, y, dx, dy = layout_row(row, x, y, dx, dy)
        rects.extend(r)

    return rects


# ---------- DEMO GENERATOR ----------

ROOM_TYPES = [
    "Common",
    "Kitchen",
    "Dining",
    "Bedroom",
    "Bedroom",
    "Bathroom",
    "Office",
    "Storage",
    "Laundry"
]

ROOM_WEIGHTS = {
    "Common": 40,
    "Kitchen": 25,
    "Dining": 20,
    "Bedroom": 25,
    "Bathroom": 10,
    "Office": 15,
    "Storage": 10,
    "Laundry": 10,
}


def generate_treemap_layout(width, height):
    selected = random.sample(ROOM_TYPES, k=6)

    sizes = [ROOM_WEIGHTS[r] for r in selected]
    norm = normalize_sizes(sizes, width, height)

    rects = squarify(norm, 0, 0, width, height)

    rooms = []
    for rect, label in zip(rects, selected):
        x, y, w, h = rect

        room = {
            "x1": x,
            "y1": y,
            "x2": x + w,
            "y2": y + h,
            "label": label
        }
        rooms.append(room)

    return rooms


# ---------- PLOTTING ----------

def plot_treemap(rooms, width, height):
    fig, ax = plt.subplots(figsize=(10, 6))

    for room in rooms:
        x1, y1 = room["x1"], room["y1"]
        w = room["x2"] - room["x1"]
        h = room["y2"] - room["y1"]

        rect = plt.Rectangle((x1, y1), w, h, fill=False)
        ax.add_patch(rect)

        ax.text(
            x1 + w / 2,
            y1 + h / 2,
            room["label"],
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold"
        )

    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.set_aspect("equal")
    ax.set_title("Squarified Treemap Layout")
    plt.tight_layout()
    plt.show()


# ---------- MAIN ----------

if __name__ == "__main__":
    width = 40
    height = 25

    rooms = generate_treemap_layout(width, height)
    plot_treemap(rooms, width, height)