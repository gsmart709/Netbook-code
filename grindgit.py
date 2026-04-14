import math
import matplotlib.pyplot as plt
from dataclasses import dataclass


# -----------------------------
# Minimal room class
# -----------------------------
@dataclass
class SimpleRoom:
    name: str
    size: float
    estimated_area_to_get: float = 0.0
    rect: object = None

    def estimateAreaToGet(self, total_area: float, total_rooms_want: float) -> None:
        # Matches the repo idea: desired area scales from size^2
        scale = float(total_area) / float(total_rooms_want)
        self.estimated_area_to_get = (self.size ** 2) * scale


# -----------------------------
# Rectangle logic (same spirit as repo)
# -----------------------------
class Rectangle:
    def __init__(self, left_bottom, right_top):
        self.x1 = float(left_bottom[0])
        self.y1 = float(left_bottom[1])
        self.x2 = float(right_top[0])
        self.y2 = float(right_top[1])

    def width(self):
        return abs(self.x2 - self.x1)

    def height(self):
        return abs(self.y2 - self.y1)

    def area(self):
        return self.width() * self.height()

    def is_horizontal(self):
        return self.width() >= self.height()

    def ratio(self):
        w = self.width()
        h = self.height()
        if w == 0 or h == 0:
            return float("inf")
        return max(w / h, h / w) - 1.0

    def divide_horizontal(self, area):
        # vertical cut
        division_width = area / self.height()
        rect1 = Rectangle((self.x1, self.y1), (self.x1 + division_width, self.y2))
        rect2 = Rectangle((self.x1 + division_width, self.y1), (self.x2, self.y2))
        return rect1, rect2

    def divide_vertical(self, area):
        # horizontal cut
        division_height = area / self.width()
        rect1 = Rectangle((self.x1, self.y1), (self.x2, self.y1 + division_height))
        rect2 = Rectangle((self.x1, self.y1 + division_height), (self.x2, self.y2))
        return rect1, rect2

    def divide_auto(self, area):
        if self.is_horizontal():
            return self.divide_horizontal(area)
        return self.divide_vertical(area)


# -----------------------------
# Simple recursive treemap layout
# Not a perfect clone, but very close in intent
# -----------------------------
def layout_rooms(rect: Rectangle, areas: list[float]) -> list[Rectangle]:
    if not areas:
        return []
    if len(areas) == 1:
        return [rect]

    total = sum(areas)
    first = areas[0]

    rect1, rect2 = rect.divide_auto(rect.area() * (first / total))
    return [rect1] + layout_rooms(rect2, areas[1:])


def generate_treemap_floorplan(building_size=(12, 9), room_specs=None):
    if room_specs is None:
        room_specs = [
            ("Common", 5),
            ("Kitchen", 4),
            ("Bedroom 1", 4),
            ("Bedroom 2", 3.5),
            ("Bathroom", 2.5),
            ("Office", 3),
        ]

    rooms = [SimpleRoom(name, size) for name, size in room_specs]

    total_area = building_size[0] * building_size[1]
    total_rooms_want = sum(r.size ** 2 for r in rooms)

    for room in rooms:
        room.estimateAreaToGet(total_area, total_rooms_want)

    # Sort biggest first usually gives better treemap results
    rooms.sort(key=lambda r: r.estimated_area_to_get, reverse=True)

    building = Rectangle((0, 0), building_size)
    rects = layout_rooms(building, [r.estimated_area_to_get for r in rooms])

    for room, rect in zip(rooms, rects):
        room.rect = rect

    return rooms


def plot_floorplan(rooms, title="Treemap Floor Plan Test"):
    fig, ax = plt.subplots(figsize=(10, 7))

    for room in rooms:
        r = room.rect
        w = r.width()
        h = r.height()

        patch = plt.Rectangle(
            (r.x1, r.y1),
            w,
            h,
            fill=False,
            linewidth=2
        )
        ax.add_patch(patch)

        ax.text(
            r.x1 + w / 2,
            r.y1 + h / 2,
            f"{room.name}\n{w:.1f} x {h:.1f}",
            ha="center",
            va="center",
            fontsize=10
        )

    # outline
    xs = [room.rect.x1 for room in rooms] + [room.rect.x2 for room in rooms]
    ys = [room.rect.y1 for room in rooms] + [room.rect.y2 for room in rooms]

    ax.set_xlim(min(xs) - 0.5, max(xs) + 0.5)
    ax.set_ylim(min(ys) - 0.5, max(ys) + 0.5)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.grid(True)
    plt.show()


if __name__ == "__main__":
    rooms = generate_treemap_floorplan(
        building_size=(14, 10),
        room_specs=[
            ("Common", 5.5),
            ("Kitchen", 4.0),
            ("Dining", 3.5),
            ("Bedroom 1", 4.0),
            ("Bedroom 2", 3.5),
            ("Bathroom", 2.5),
            ("Office", 3.0),
        ]
    )
    plot_floorplan(rooms)