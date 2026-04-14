import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


# ============================================================
# ROUND 1 GOAL
# ------------------------------------------------------------
# Build a clean "house program" skeleton:
# - house footprint
# - room definitions
# - zoning (public / private / service)
# - adjacency rules (preferred / forbidden)
# - simple plot output
#
# This is NOT the final room-growth generator yet.
# It is the structure we will use for Round 2+.
# ============================================================


# ------------------------------------------------------------
# Data classes
# ------------------------------------------------------------

@dataclass
class RoomSpec:
    name: str
    room_type: str
    zone: str
    target_area: float
    min_aspect: float = 0.5
    max_aspect: float = 2.5
    preferred_adjacent: List[str] = field(default_factory=list)
    forbidden_adjacent: List[str] = field(default_factory=list)


@dataclass
class ZoneBlock:
    name: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class RoomBlock:
    room: RoomSpec
    x: float
    y: float
    w: float
    h: float


# ------------------------------------------------------------
# House program
# ------------------------------------------------------------

def build_default_program() -> List[RoomSpec]:
    """
    Default room list for the first pass.
    These sizes are target areas in square "units" only.
    They are not architectural gospel. They are enough to drive structure.
    """

    rooms = [
        # PUBLIC ZONE
        RoomSpec(
            name="Common",
            room_type="common",
            zone="public",
            target_area=32,
            preferred_adjacent=["kitchen", "dining", "hall", "entry", "bathroom", "office"],
            forbidden_adjacent=[]
        ),
        RoomSpec(
            name="Dining",
            room_type="dining",
            zone="public",
            target_area=16,
            preferred_adjacent=["common", "kitchen"],
            forbidden_adjacent=["garage"]
        ),
        RoomSpec(
            name="Office",
            room_type="office",
            zone="public",
            target_area=10,
            preferred_adjacent=["common"],
            forbidden_adjacent=["garage"]
        ),

        # SERVICE ZONE
        RoomSpec(
            name="Kitchen",
            room_type="kitchen",
            zone="service",
            target_area=18,
            preferred_adjacent=["dining", "common", "pantry", "garage"],
            forbidden_adjacent=["bedroom"]
        ),
        RoomSpec(
            name="Pantry",
            room_type="pantry",
            zone="service",
            target_area=6,
            preferred_adjacent=["kitchen"],
            forbidden_adjacent=["bedroom"]
        ),
        RoomSpec(
            name="Bathroom",
            room_type="bathroom",
            zone="service",
            target_area=8,
            preferred_adjacent=["common", "bedroom", "hall"],
            forbidden_adjacent=["dining"]
        ),
        RoomSpec(
            name="Garage",
            room_type="garage",
            zone="service",
            target_area=24,
            preferred_adjacent=["kitchen", "hall", "entry"],
            forbidden_adjacent=["bedroom", "dining"]
        ),

        # PRIVATE ZONE
        RoomSpec(
            name="Bedroom 1",
            room_type="bedroom",
            zone="private",
            target_area=18,
            preferred_adjacent=["bathroom", "hall", "bedroom"],
            forbidden_adjacent=["garage", "kitchen"]
        ),
        RoomSpec(
            name="Bedroom 2",
            room_type="bedroom",
            zone="private",
            target_area=16,
            preferred_adjacent=["bathroom", "hall", "bedroom"],
            forbidden_adjacent=["garage", "kitchen"]
        ),
    ]
    return rooms


# ------------------------------------------------------------
# Zone logic
# ------------------------------------------------------------

def zone_area_totals(rooms: List[RoomSpec]) -> Dict[str, float]:
    totals: Dict[str, float] = {"public": 0.0, "private": 0.0, "service": 0.0}
    for room in rooms:
        totals[room.zone] += room.target_area
    return totals


def split_house_into_zones(
    house_w: float,
    house_h: float,
    zone_totals: Dict[str, float]
) -> Dict[str, ZoneBlock]:
    """
    Simple zone-first layout, inspired by the papers:
    - public near entry/front
    - private away from entry
    - service near public

    Assumption for this first pass:
    - front of house is along y = 0
    - public zone sits across the front band
    - remaining rear area gets split into private and service
    """

    total = sum(zone_totals.values())
    if total <= 0:
        raise ValueError("Total zone area must be > 0.")

    public_ratio = zone_totals["public"] / total
    private_ratio = zone_totals["private"] / total
    service_ratio = zone_totals["service"] / total

    # Public is a front strip.
    public_h = house_h * public_ratio
    public_h = max(house_h * 0.22, min(public_h, house_h * 0.45))

    rear_h = house_h - public_h
    rear_total = private_ratio + service_ratio
    if rear_total <= 0:
        rear_total = 1.0

    private_w = house_w * (private_ratio / rear_total)
    private_w = max(house_w * 0.35, min(private_w, house_w * 0.70))
    service_w = house_w - private_w

    zones = {
        "public": ZoneBlock("public", 0.0, 0.0, house_w, public_h),
        "private": ZoneBlock("private", 0.0, public_h, private_w, rear_h),
        "service": ZoneBlock("service", private_w, public_h, service_w, rear_h),
    }
    return zones


# ------------------------------------------------------------
# Placeholder room layout inside each zone
# ------------------------------------------------------------

def pack_rooms_in_zone(zone: ZoneBlock, rooms: List[RoomSpec]) -> List[RoomBlock]:
    """
    Placeholder packing ONLY for Round 1.
    We slice the zone into strips so you can inspect:
    - room membership
    - room relative size
    - zone groupings

    Round 2 will replace this with actual room placement logic.
    """

    if not rooms:
        return []

    total_area = sum(r.target_area for r in rooms)
    room_blocks: List[RoomBlock] = []

    # Sort biggest first for cleaner plotting
    rooms_sorted = sorted(rooms, key=lambda r: r.target_area, reverse=True)

    horizontal = zone.w >= zone.h

    if horizontal:
        # Slice vertically across width
        cursor_x = zone.x
        for i, room in enumerate(rooms_sorted):
            frac = room.target_area / total_area
            width = zone.w * frac if i < len(rooms_sorted) - 1 else (zone.x + zone.w - cursor_x)
            room_blocks.append(RoomBlock(room, cursor_x, zone.y, width, zone.h))
            cursor_x += width
    else:
        # Slice horizontally across height
        cursor_y = zone.y
        for i, room in enumerate(rooms_sorted):
            frac = room.target_area / total_area
            height = zone.h * frac if i < len(rooms_sorted) - 1 else (zone.y + zone.h - cursor_y)
            room_blocks.append(RoomBlock(room, zone.x, cursor_y, zone.w, height))
            cursor_y += height

    return room_blocks


# ------------------------------------------------------------
# Adjacency reporting
# ------------------------------------------------------------

def build_adjacency_summary(rooms: List[RoomSpec]) -> List[str]:
    lines = []
    for room in rooms:
        pref = ", ".join(room.preferred_adjacent) if room.preferred_adjacent else "-"
        forb = ", ".join(room.forbidden_adjacent) if room.forbidden_adjacent else "-"
        lines.append(
            f"{room.name:10s} | zone={room.zone:7s} | area={room.target_area:>5.1f} | "
            f"prefer=[{pref}] | avoid=[{forb}]"
        )
    return lines


def build_room_type_color(room_type: str) -> str:
    color_map = {
        "common": "#d9ead3",
        "dining": "#fff2cc",
        "office": "#cfe2f3",
        "kitchen": "#f4cccc",
        "pantry": "#fce5cd",
        "bathroom": "#d9d2e9",
        "garage": "#d0d0d0",
        "bedroom": "#ead1dc",
        "hall": "#eeeeee",
        "entry": "#ffe599",
    }
    return color_map.get(room_type, "#ffffff")


# ------------------------------------------------------------
# Plotting
# ------------------------------------------------------------

def plot_round1(
    house_w: float,
    house_h: float,
    zones: Dict[str, ZoneBlock],
    room_blocks: List[RoomBlock],
    show_zone_labels: bool = True
) -> None:
    fig, ax = plt.subplots(figsize=(12, 8))

    # Outer house
    ax.add_patch(
        Rectangle((0, 0), house_w, house_h, fill=False, linewidth=3)
    )

    # Zone outlines
    zone_styles = {
        "public": {"linestyle": "--", "linewidth": 2},
        "private": {"linestyle": "--", "linewidth": 2},
        "service": {"linestyle": "--", "linewidth": 2},
    }

    for zone_name, zone in zones.items():
        ax.add_patch(
            Rectangle(
                (zone.x, zone.y),
                zone.w,
                zone.h,
                fill=False,
                edgecolor="black",
                linestyle=zone_styles[zone_name]["linestyle"],
                linewidth=zone_styles[zone_name]["linewidth"],
            )
        )
        if show_zone_labels:
            ax.text(
                zone.x + zone.w / 2,
                zone.y + zone.h / 2,
                zone.name.upper(),
                ha="center",
                va="center",
                fontsize=16,
                alpha=0.25,
                weight="bold",
            )

    # Room placeholder blocks
    for rb in room_blocks:
        color = build_room_type_color(rb.room.room_type)
        ax.add_patch(
            Rectangle(
                (rb.x, rb.y),
                rb.w,
                rb.h,
                facecolor=color,
                edgecolor="black",
                linewidth=1.5,
                alpha=0.95,
            )
        )

        aspect = max(rb.w / max(rb.h, 1e-6), rb.h / max(rb.w, 1e-6))
        ax.text(
            rb.x + rb.w / 2,
            rb.y + rb.h / 2,
            f"{rb.room.name}\n{rb.room.room_type}\nA={rb.room.target_area:.0f}\nAR={aspect:.2f}",
            ha="center",
            va="center",
            fontsize=9,
            bbox=dict(facecolor="white", alpha=0.65, edgecolor="none", pad=1.5),
        )

    # Entry marker on front wall, centered on public zone
    public_zone = zones["public"]
    entry_x = public_zone.x + public_zone.w * 0.5
    entry_w = min(2.0, house_w * 0.08)
    ax.add_patch(
        Rectangle(
            (entry_x - entry_w / 2, -0.15),
            entry_w,
            0.3,
            facecolor="white",
            edgecolor="black",
            linewidth=2,
        )
    )
    ax.text(entry_x, -0.7, "ENTRY", ha="center", va="center", fontsize=10)

    ax.set_xlim(-1, house_w + 1)
    ax.set_ylim(-1.5, house_h + 1)
    ax.set_aspect("equal")
    ax.set_title("Round 1: House Program Skeleton (Zones + Placeholder Rooms)")
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------
# Main runner
# ------------------------------------------------------------

def main():
    # House footprint
    house_w = 16.0
    house_h = 12.0

    # Room program
    rooms = build_default_program()

    # Zone totals + split
    totals = zone_area_totals(rooms)
    zones = split_house_into_zones(house_w, house_h, totals)

    # Placeholder packing inside zones
    all_blocks: List[RoomBlock] = []
    for zone_name in ("public", "private", "service"):
        zone_rooms = [r for r in rooms if r.zone == zone_name]
        all_blocks.extend(pack_rooms_in_zone(zones[zone_name], zone_rooms))

    # Console output
    print("\n=== HOUSE FOOTPRINT ===")
    print(f"Width: {house_w:.1f}")
    print(f"Height: {house_h:.1f}")
    print(f"Area: {house_w * house_h:.1f}")

    print("\n=== ZONE TOTALS ===")
    for k, v in totals.items():
        print(f"{k:7s}: {v:.1f}")

    print("\n=== ROOM PROGRAM ===")
    for line in build_adjacency_summary(rooms):
        print(line)

    print("\n=== ZONE BLOCKS ===")
    for name, z in zones.items():
        print(
            f"{name:7s} -> x={z.x:.2f}, y={z.y:.2f}, w={z.w:.2f}, h={z.h:.2f}, "
            f"area={z.w * z.h:.2f}"
        )

    # Plot
    plot_round1(house_w, house_h, zones, all_blocks)


if __name__ == "__main__":
    main()