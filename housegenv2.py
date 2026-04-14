import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


# ============================================================
# ROUND 4: LAYOUT + CONNECTIVITY + SMARTER DOORS + FLOW
# ------------------------------------------------------------
# New vs Round 3:
# - entry must connect to Common
# - one door per room-pair, placed near center of shared wall
# - stronger bedroom shaping
# - pantry behaves like a kitchen sidekick
# - better bedroom privacy / pantry logic in scoring
# - plot title includes Round 4
# ============================================================


@dataclass
class RoomSpec:
    name: str
    room_type: str
    zone: str
    target_area: int
    min_aspect: float = 0.5
    max_aspect: float = 2.5
    preferred_adjacent: List[str] = field(default_factory=list)
    forbidden_adjacent: List[str] = field(default_factory=list)


@dataclass
class ZoneRect:
    name: str
    x0: int
    y0: int
    x1: int  # exclusive
    y1: int  # exclusive

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def area(self) -> int:
        return self.width * self.height


DIR4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def neighbors4(x: int, y: int, w: int, h: int):
    for dx, dy in DIR4:
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny


def room_color(room_type: str) -> str:
    cmap = {
        "common": "#d9ead3",
        "dining": "#fff2cc",
        "office": "#cfe2f3",
        "kitchen": "#f4cccc",
        "pantry": "#fce5cd",
        "bathroom": "#d9d2e9",
        "garage": "#d0d0d0",
        "bedroom": "#ead1dc",
    }
    return cmap.get(room_type, "#ffffff")


def build_program(house_w: int, house_h: int, rng: random.Random) -> List[RoomSpec]:
    house_area = house_w * house_h

    rooms = [
        RoomSpec(
            name="Common",
            room_type="common",
            zone="public",
            target_area=max(18, round(house_area * 0.18)),
            preferred_adjacent=["dining", "kitchen", "office", "bathroom"],
            forbidden_adjacent=[]
        ),
        RoomSpec(
            name="Dining",
            room_type="dining",
            zone="public",
            target_area=max(10, round(house_area * 0.09)),
            preferred_adjacent=["common", "kitchen"],
            forbidden_adjacent=["garage"]
        ),
        RoomSpec(
            name="Office",
            room_type="office",
            zone="public",
            target_area=max(6, round(house_area * 0.05)),
            preferred_adjacent=["common"],
            forbidden_adjacent=["garage"]
        ),
        RoomSpec(
            name="Kitchen",
            room_type="kitchen",
            zone="service",
            target_area=max(10, round(house_area * 0.10)),
            preferred_adjacent=["common", "dining", "pantry", "garage"],
            forbidden_adjacent=["bedroom"]
        ),
        RoomSpec(
            name="Pantry",
            room_type="pantry",
            zone="service",
            target_area=max(4, round(house_area * 0.03)),
            min_aspect=0.5,
            max_aspect=1.8,
            preferred_adjacent=["kitchen"],
            forbidden_adjacent=["bedroom", "common", "dining", "office"]
        ),
        RoomSpec(
            name="Bathroom",
            room_type="bathroom",
            zone="service",
            target_area=max(5, round(house_area * 0.05)),
            min_aspect=0.6,
            max_aspect=2.0,
            preferred_adjacent=["bedroom", "common"],
            forbidden_adjacent=["dining"]
        ),
        RoomSpec(
            name="Bedroom 1",
            room_type="bedroom",
            zone="private",
            target_area=max(10, round(house_area * 0.10)),
            min_aspect=0.7,
            max_aspect=1.9,
            preferred_adjacent=["bedroom", "bathroom"],
            forbidden_adjacent=["garage", "kitchen"]
        ),
        RoomSpec(
            name="Bedroom 2",
            room_type="bedroom",
            zone="private",
            target_area=max(9, round(house_area * 0.09)),
            min_aspect=0.7,
            max_aspect=1.9,
            preferred_adjacent=["bedroom", "bathroom"],
            forbidden_adjacent=["garage", "kitchen"]
        ),
    ]

    if house_area >= 220 and rng.random() < 0.65:
        rooms.append(
            RoomSpec(
                name="Bedroom 3",
                room_type="bedroom",
                zone="private",
                target_area=max(8, round(house_area * 0.08)),
                min_aspect=0.7,
                max_aspect=1.9,
                preferred_adjacent=["bedroom", "bathroom"],
                forbidden_adjacent=["garage", "kitchen"]
            )
        )

    garage_probability = 0.15
    if house_area >= 180:
        garage_probability = 0.45
    if house_area >= 240:
        garage_probability = 0.70

    if rng.random() < garage_probability:
        rooms.append(
            RoomSpec(
                name="Garage",
                room_type="garage",
                zone="service",
                target_area=max(14, round(house_area * 0.12)),
                preferred_adjacent=["kitchen", "common"],
                forbidden_adjacent=["bedroom", "dining"]
            )
        )

    return rooms


def zone_totals(rooms: List[RoomSpec]) -> Dict[str, int]:
    totals = {"public": 0, "private": 0, "service": 0}
    for r in rooms:
        totals[r.zone] += r.target_area
    return totals


def split_zones(house_w: int, house_h: int, totals: Dict[str, int]) -> Dict[str, ZoneRect]:
    total = sum(totals.values())
    public_ratio = totals["public"] / total if total else 0.3

    public_h = max(4, min(round(house_h * public_ratio), max(4, house_h // 2)))
    public_h = min(public_h, house_h - 4)

    rear_total = totals["private"] + totals["service"]
    if rear_total == 0:
        private_w = house_w // 2
    else:
        private_w = round(house_w * (totals["private"] / rear_total))
        private_w = max(4, min(private_w, house_w - 4))

    return {
        "public": ZoneRect("public", 0, 0, house_w, public_h),
        "private": ZoneRect("private", 0, public_h, private_w, house_h),
        "service": ZoneRect("service", private_w, public_h, house_w, house_h),
    }


class Layout:
    def __init__(self, house_w: int, house_h: int, rooms: List[RoomSpec], zones: Dict[str, ZoneRect], seed: int):
        self.w = house_w
        self.h = house_h
        self.rooms = rooms
        self.zones = zones
        self.rng = random.Random(seed)

        self.grid = np.full((self.w, self.h), -1, dtype=int)
        self.room_cells: Dict[int, Set[Tuple[int, int]]] = {i: set() for i in range(len(rooms))}
        self.room_seeds: Dict[int, Tuple[int, int]] = {}

        self.zone_map = np.empty((self.w, self.h), dtype=object)
        for zname, z in zones.items():
            for x in range(z.x0, z.x1):
                for y in range(z.y0, z.y1):
                    self.zone_map[x, y] = zname

    def room_bbox(self, rid: int) -> Optional[Tuple[int, int, int, int]]:
        cells = self.room_cells[rid]
        if not cells:
            return None
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        return min(xs), min(ys), max(xs), max(ys)

    def room_aspect(self, rid: int) -> float:
        bbox = self.room_bbox(rid)
        if bbox is None:
            return 1.0
        x0, y0, x1, y1 = bbox
        bw = x1 - x0 + 1
        bh = y1 - y0 + 1
        return max(bw / bh, bh / bw)

    def room_frontier(self, rid: int) -> Set[Tuple[int, int]]:
        frontier = set()
        zone_name = self.rooms[rid].zone
        for x, y in self.room_cells[rid]:
            for nx, ny in neighbors4(x, y, self.w, self.h):
                if self.grid[nx, ny] == -1 and self.zone_map[nx, ny] == zone_name:
                    frontier.add((nx, ny))
        return frontier


def pick_seed_for_room(layout: Layout, rid: int):
    room = layout.rooms[rid]
    zone = layout.zones[room.zone]
    best_score = -1e18
    best_cell = None

    kitchen_seed = None
    for orid, (ox, oy) in layout.room_seeds.items():
        if layout.rooms[orid].room_type == "kitchen":
            kitchen_seed = (ox, oy)
            break

    bath_seeds = []
    for orid, (ox, oy) in layout.room_seeds.items():
        if layout.rooms[orid].room_type == "bathroom":
            bath_seeds.append((ox, oy))

    for x in range(zone.x0, zone.x1):
        for y in range(zone.y0, zone.y1):
            if layout.grid[x, y] != -1:
                continue

            score = 0.0

            if room.zone == "public":
                score -= y * 1.2
            elif room.zone == "private":
                score += y * 0.8
            elif room.zone == "service":
                score += x * 0.7

            if room.room_type == "garage":
                score += x * 2.0
                score -= y * 1.0

            if room.room_type == "kitchen":
                score -= abs(y - zone.y0) * 0.6

            if room.room_type == "bedroom":
                score += y * 1.0
                score -= abs(x - (zone.x0 + zone.x1) / 2.0) * 0.08

            if room.room_type == "pantry":
                score += x * 0.6
                if kitchen_seed is not None:
                    score += max(0, 14 - (abs(x - kitchen_seed[0]) + abs(y - kitchen_seed[1]))) * 3.0

            if room.room_type == "bathroom":
                score += x * 0.2

            for other_rid, (ox, oy) in layout.room_seeds.items():
                other_type = layout.rooms[other_rid].room_type
                dist = abs(x - ox) + abs(y - oy)

                if other_type in room.preferred_adjacent:
                    score += max(0, 10 - dist) * 1.8

                if other_type in room.forbidden_adjacent:
                    score -= max(0, 10 - dist) * 2.2

            if room.room_type == "bedroom" and bath_seeds:
                best_bath_dist = min(abs(x - bx) + abs(y - by) for bx, by in bath_seeds)
                score += max(0, 12 - best_bath_dist) * 1.0

            score += layout.rng.uniform(-0.2, 0.2)

            if score > best_score:
                best_score = score
                best_cell = (x, y)

    if best_cell is None:
        raise RuntimeError(f"Could not place seed for room {room.name}")

    layout.room_seeds[rid] = best_cell
    layout.room_cells[rid].add(best_cell)
    layout.grid[best_cell] = rid


def place_all_seeds(layout: Layout):
    priority = {
        "common": 100,
        "kitchen": 90,
        "bedroom": 80,
        "bathroom": 75,
        "garage": 70,
        "dining": 65,
        "office": 60,
        "pantry": 50,
    }
    order = sorted(
        range(len(layout.rooms)),
        key=lambda i: (priority.get(layout.rooms[i].room_type, 0), layout.rooms[i].target_area),
        reverse=True,
    )
    for rid in order:
        pick_seed_for_room(layout, rid)


def candidate_score(layout: Layout, rid: int, cell: Tuple[int, int]) -> float:
    x, y = cell
    room = layout.rooms[rid]
    score = 0.0

    own_contacts = 0
    preferred_contacts = 0
    forbidden_contacts = 0
    neutral_contacts = 0
    touching_room_types = set()

    for nx, ny in neighbors4(x, y, layout.w, layout.h):
        oid = layout.grid[nx, ny]
        if oid == rid:
            own_contacts += 1
        elif oid != -1:
            other_type = layout.rooms[oid].room_type
            touching_room_types.add(other_type)
            if other_type in room.preferred_adjacent:
                preferred_contacts += 1
            elif other_type in room.forbidden_adjacent:
                forbidden_contacts += 1
            else:
                neutral_contacts += 1

    score += own_contacts * 2.8
    score += preferred_contacts * 2.4
    score -= forbidden_contacts * 4.0
    score -= neutral_contacts * 0.2

    old_cells = layout.room_cells[rid]
    xs = [c[0] for c in old_cells] + [x]
    ys = [c[1] for c in old_cells] + [y]
    bw = max(xs) - min(xs) + 1
    bh = max(ys) - min(ys) + 1
    new_aspect = max(bw / bh, bh / bw)

    score -= max(0.0, new_aspect - room.max_aspect) * 8.0

    if room.room_type == "garage":
        score += x * 0.4
        score -= y * 0.6

    if room.room_type == "bedroom":
        score += y * 0.40
        score -= max(0.0, new_aspect - 1.8) * 4.5
        if "common" in touching_room_types:
            score -= 1.5

    if room.room_type == "common":
        score -= max(0.0, new_aspect - 1.8) * 2.5

    if room.room_type == "bathroom":
        score -= max(0.0, new_aspect - 1.8) * 3.5
        if "bedroom" in touching_room_types:
            score += 2.0

    if room.room_type == "pantry":
        score -= max(0.0, new_aspect - 1.6) * 6.0
        if "kitchen" in touching_room_types:
            score += 5.0
        if any(t in touching_room_types for t in ("bedroom", "common", "dining", "office")):
            score -= 4.0

    if room.room_type == "kitchen":
        if "pantry" in touching_room_types:
            score += 2.5

    score += layout.rng.uniform(-0.15, 0.15)
    return score


def grow_rooms(layout: Layout, max_passes: int = 5000):
    room_ids = list(range(len(layout.rooms)))

    for _ in range(max_passes):
        incomplete = [rid for rid in room_ids if len(layout.room_cells[rid]) < layout.rooms[rid].target_area]
        if not incomplete:
            break

        layout.rng.shuffle(incomplete)
        progressed = False

        for rid in incomplete:
            frontier = list(layout.room_frontier(rid))
            if not frontier:
                continue

            frontier.sort(key=lambda c: candidate_score(layout, rid, c), reverse=True)
            chosen = frontier[0]

            layout.grid[chosen] = rid
            layout.room_cells[rid].add(chosen)
            progressed = True

        if not progressed:
            break


def fill_unassigned(layout: Layout):
    for zone_name, z in layout.zones.items():
        changed = True
        while changed:
            changed = False
            for x in range(z.x0, z.x1):
                for y in range(z.y0, z.y1):
                    if layout.grid[x, y] != -1:
                        continue

                    boundary = defaultdict(int)
                    for nx, ny in neighbors4(x, y, layout.w, layout.h):
                        rid = layout.grid[nx, ny]
                        if rid != -1 and layout.rooms[rid].zone == zone_name:
                            boundary[rid] += 1

                    if boundary:
                        best_rid = max(boundary, key=boundary.get)
                        layout.grid[x, y] = best_rid
                        layout.room_cells[best_rid].add((x, y))
                        changed = True


def build_room_graph(layout: Layout) -> Dict[int, Set[int]]:
    graph = {rid: set() for rid in range(len(layout.rooms))}
    for x in range(layout.w):
        for y in range(layout.h):
            rid = layout.grid[x, y]
            if rid == -1:
                continue
            for nx, ny in neighbors4(x, y, layout.w, layout.h):
                orid = layout.grid[nx, ny]
                if orid != -1 and orid != rid:
                    graph[rid].add(orid)
    return graph


def find_entry_room(layout: Layout) -> Optional[int]:
    common_ids = [rid for rid, r in enumerate(layout.rooms) if r.room_type == "common"]
    if not common_ids:
        return None
    common_id = common_ids[0]

    entry_x = layout.w // 2
    if layout.grid[entry_x, 0] == common_id:
        return common_id

    search_order = [entry_x]
    for offset in range(1, layout.w):
        if entry_x - offset >= 0:
            search_order.append(entry_x - offset)
        if entry_x + offset < layout.w:
            search_order.append(entry_x + offset)

    for x in search_order:
        if layout.grid[x, 0] == common_id:
            return common_id

    return None


def connectivity_score(layout: Layout) -> Tuple[float, int]:
    entry_room = find_entry_room(layout)
    if entry_room is None:
        return -140.0, 0

    room_graph = build_room_graph(layout)

    visited = set([entry_room])
    q = deque([entry_room])

    while q:
        rid = q.popleft()
        for nbr in room_graph[rid]:
            if nbr not in visited:
                visited.add(nbr)
                q.append(nbr)

    reachable_count = len(visited)
    total_rooms = len(layout.rooms)

    score = 25.0
    score += reachable_count * 12.0

    if reachable_count < total_rooms:
        score -= (total_rooms - reachable_count) * 35.0

    return score, reachable_count


def shared_boundaries(layout: Layout) -> Dict[Tuple[int, int], List[Tuple[Tuple[int, int], Tuple[int, int]]]]:
    pairs = defaultdict(list)

    for x in range(layout.w):
        for y in range(layout.h):
            rid = layout.grid[x, y]
            if rid == -1:
                continue

            for nx, ny in ((x + 1, y), (x, y + 1)):
                if not (0 <= nx < layout.w and 0 <= ny < layout.h):
                    continue
                orid = layout.grid[nx, ny]
                if orid == -1 or orid == rid:
                    continue

                a, b = sorted((rid, orid))
                room_a = layout.rooms[a]
                room_b = layout.rooms[b]

                if room_b.room_type in room_a.forbidden_adjacent:
                    continue
                if room_a.room_type in room_b.forbidden_adjacent:
                    continue

                pairs[(a, b)].append(((x, y), (nx, ny)))

    return pairs


def pair_door_priority(layout: Layout, a: int, b: int) -> float:
    ta = layout.rooms[a].room_type
    tb = layout.rooms[b].room_type
    types = {ta, tb}

    if types == {"common", "dining"}:
        return 100
    if types == {"common", "kitchen"}:
        return 98
    if types == {"kitchen", "pantry"}:
        return 96
    if types == {"kitchen", "garage"}:
        return 95
    if types == {"common", "office"}:
        return 92
    if types == {"bedroom", "bathroom"}:
        return 90
    if types == {"common", "bathroom"}:
        return 75
    if types == {"common", "bedroom"}:
        return 60
    if "pantry" in types:
        return 40
    return 50


def choose_single_door_for_pair(layout: Layout, a: int, b: int, boundaries: List[Tuple[Tuple[int, int], Tuple[int, int]]]):
    ax0, ay0, ax1, ay1 = layout.room_bbox(a)
    bx0, by0, bx1, by1 = layout.room_bbox(b)
    acx = (ax0 + ax1) / 2.0
    acy = (ay0 + ay1) / 2.0
    bcx = (bx0 + bx1) / 2.0
    bcy = (by0 + by1) / 2.0
    target_x = (acx + bcx) / 2.0
    target_y = (acy + bcy) / 2.0

    best = None
    best_score = -1e18

    for (x1, y1), (x2, y2) in boundaries:
        mx = (x1 + x2) / 2.0 + 0.5
        my = (y1 + y2) / 2.0 + 0.5
        dist_penalty = abs(mx - target_x) + abs(my - target_y)

        score = 0.0
        score -= dist_penalty

        if x1 != x2:
            score += 0.2
        if y1 != y2:
            score += 0.2

        if score > best_score:
            best_score = score
            best = ((x1, y1), (x2, y2))

    return best


def find_smart_doors(layout: Layout) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    boundaries = shared_boundaries(layout)
    if not boundaries:
        return []

    room_graph = build_room_graph(layout)
    entry_room = find_entry_room(layout)
    chosen = []

    # First, force useful backbone doors from common outward.
    if entry_room is not None:
        visited = set([entry_room])
        q = deque([entry_room])

        while q:
            rid = q.popleft()
            nbrs = sorted(room_graph[rid], key=lambda n: -pair_door_priority(layout, rid, n))
            for nbr in nbrs:
                if nbr in visited:
                    continue
                pair = tuple(sorted((rid, nbr)))
                if pair in boundaries:
                    door = choose_single_door_for_pair(layout, pair[0], pair[1], boundaries[pair])
                    if door is not None:
                        chosen.append(door)
                visited.add(nbr)
                q.append(nbr)

    # Then add pantry-kitchen if somehow missing.
    kitchen_ids = [i for i, r in enumerate(layout.rooms) if r.room_type == "kitchen"]
    pantry_ids = [i for i, r in enumerate(layout.rooms) if r.room_type == "pantry"]
    for kid in kitchen_ids:
        for pid in pantry_ids:
            pair = tuple(sorted((kid, pid)))
            if pair in boundaries:
                door = choose_single_door_for_pair(layout, pair[0], pair[1], boundaries[pair])
                if door is not None and door not in chosen:
                    chosen.append(door)

    # Also make sure every bedroom has at least one access door if possible.
    bedroom_ids = [i for i, r in enumerate(layout.rooms) if r.room_type == "bedroom"]
    for bid in bedroom_ids:
        already = False
        for door in chosen:
            c1, c2 = door
            r1 = layout.grid[c1]
            r2 = layout.grid[c2]
            if bid in (r1, r2):
                already = True
                break
        if already:
            continue

        candidates = []
        for nbr in room_graph[bid]:
            pair = tuple(sorted((bid, nbr)))
            if pair in boundaries:
                candidates.append((pair_door_priority(layout, bid, nbr), pair))
        if candidates:
            candidates.sort(reverse=True)
            pair = candidates[0][1]
            door = choose_single_door_for_pair(layout, pair[0], pair[1], boundaries[pair])
            if door is not None and door not in chosen:
                chosen.append(door)

    return chosen


def adjacency_report(layout: Layout) -> Dict[str, Set[str]]:
    report = {r.name: set() for r in layout.rooms}
    for x in range(layout.w):
        for y in range(layout.h):
            rid = layout.grid[x, y]
            if rid == -1:
                continue
            for nx, ny in neighbors4(x, y, layout.w, layout.h):
                orid = layout.grid[nx, ny]
                if orid != -1 and orid != rid:
                    report[layout.rooms[rid].name].add(layout.rooms[orid].name)
    return report


def score_layout(layout: Layout) -> Tuple[float, Dict[str, float]]:
    details: Dict[str, float] = {}

    adj_score = 0.0
    for rid, room in enumerate(layout.rooms):
        touching_types = set()
        touching_ids = set()
        for x, y in layout.room_cells[rid]:
            for nx, ny in neighbors4(x, y, layout.w, layout.h):
                orid = layout.grid[nx, ny]
                if orid != -1 and orid != rid:
                    touching_types.add(layout.rooms[orid].room_type)
                    touching_ids.add(orid)

        for t in room.preferred_adjacent:
            if t in touching_types:
                adj_score += 6.0

        for t in room.forbidden_adjacent:
            if t in touching_types:
                adj_score -= 12.0

        if room.room_type == "pantry":
            if "kitchen" in touching_types:
                adj_score += 18.0
            else:
                adj_score -= 25.0
            if any(t in touching_types for t in ("common", "dining", "office", "bedroom")):
                adj_score -= 10.0

        if room.room_type == "bedroom":
            if "bathroom" in touching_types:
                adj_score += 7.0
            if "common" in touching_types:
                adj_score -= 2.5

    aspect_score = 0.0
    for rid, room in enumerate(layout.rooms):
        aspect = layout.room_aspect(rid)

        if aspect <= room.max_aspect:
            aspect_score += 3.0
        else:
            aspect_score -= (aspect - room.max_aspect) * 10.0

        if room.room_type == "bedroom" and aspect > 1.9:
            aspect_score -= 12.0
        if room.room_type == "bathroom" and aspect > 2.1:
            aspect_score -= 10.0
        if room.room_type == "pantry" and aspect > 1.8:
            aspect_score -= 14.0
        if room.room_type == "common" and aspect > 2.6:
            aspect_score -= 8.0

    semantic_score = 0.0
    for rid, room in enumerate(layout.rooms):
        bbox = layout.room_bbox(rid)
        if bbox is None:
            continue
        x0, y0, x1, y1 = bbox
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2

        if room.room_type == "bedroom":
            semantic_score += cy * 0.7
        if room.room_type == "garage":
            semantic_score += cx * 1.0 - cy * 0.9
        if room.room_type == "common":
            semantic_score += max(0, 6 - cy) * 1.6
        if room.room_type == "kitchen":
            semantic_score += cx * 0.25
        if room.room_type == "pantry":
            semantic_score += cx * 0.15
        if room.room_type == "office":
            semantic_score += max(0, 5 - cy) * 0.5

    conn_score, reachable = connectivity_score(layout)

    # Flow score: reward sensible common-centered access.
    flow_score = 0.0
    graph = build_room_graph(layout)
    common_ids = [rid for rid, r in enumerate(layout.rooms) if r.room_type == "common"]
    if common_ids:
        common_id = common_ids[0]
        common_neighbors = {layout.rooms[n].room_type for n in graph[common_id]}
        if "dining" in common_neighbors:
            flow_score += 12.0
        if "kitchen" in common_neighbors:
            flow_score += 12.0
        if "office" in common_neighbors:
            flow_score += 7.0

    smart_doors = find_smart_doors(layout)
    door_score = 0.0
    door_score += len(smart_doors) * 1.0

    total_score = adj_score + aspect_score + semantic_score + conn_score + flow_score + door_score

    details["adjacency"] = adj_score
    details["aspect"] = aspect_score
    details["semantic"] = semantic_score
    details["connectivity"] = conn_score
    details["flow"] = flow_score
    details["doors"] = door_score
    details["reachable_rooms"] = float(reachable)
    details["total"] = total_score
    return total_score, details


def plot_layout(layout: Layout, title: str):
    fig, ax = plt.subplots(figsize=(12, 8))

    for zname, z in layout.zones.items():
        ax.add_patch(
            Rectangle((z.x0, z.y0), z.width, z.height, fill=False, linestyle="--", linewidth=2)
        )
        ax.text(
            z.x0 + z.width / 2,
            z.y0 + z.height / 2,
            zname.upper(),
            ha="center",
            va="center",
            fontsize=18,
            alpha=0.15,
            weight="bold",
        )

    for x in range(layout.w):
        for y in range(layout.h):
            rid = layout.grid[x, y]
            if rid != -1:
                ax.add_patch(
                    Rectangle(
                        (x, y), 1, 1,
                        facecolor=room_color(layout.rooms[rid].room_type),
                        edgecolor="black",
                        linewidth=0.8
                    )
                )

    smart_doors = find_smart_doors(layout)
    for (x1, y1), (x2, y2) in smart_doors:
        mx = (x1 + x2) / 2 + 0.5
        my = (y1 + y2) / 2 + 0.5
        ax.add_patch(Rectangle((mx - 0.14, my - 0.14), 0.28, 0.28, facecolor="black", edgecolor="black"))

    for rid, room in enumerate(layout.rooms):
        cells = list(layout.room_cells[rid])
        if not cells:
            continue
        cx = sum(c[0] + 0.5 for c in cells) / len(cells)
        cy = sum(c[1] + 0.5 for c in cells) / len(cells)
        aspect = layout.room_aspect(rid)
        ax.text(
            cx, cy,
            f"{room.name}\n{room.room_type}\nA={len(cells)}\nAR={aspect:.2f}",
            ha="center",
            va="center",
            fontsize=9,
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=1.5)
        )

    entry_x = layout.w / 2 - 0.5
    ax.add_patch(
        Rectangle((entry_x, -0.15), 1.0, 0.3, facecolor="white", edgecolor="black", linewidth=2)
    )
    ax.text(layout.w / 2, -0.8, "ENTRY", ha="center", va="center", fontsize=10)

    ax.set_xlim(-1, layout.w + 1)
    ax.set_ylim(-1.5, layout.h + 1)
    ax.set_aspect("equal")
    ax.set_xticks(range(layout.w + 1))
    ax.set_yticks(range(layout.h + 1))
    ax.grid(True, alpha=0.20)
    ax.set_title(title)
    plt.tight_layout()
    plt.show()


def generate_best_layout(house_w: int = 18, house_h: int = 12, trials: int = 50, base_seed: int = 100):
    best_layout = None
    best_score = -1e18
    best_details = None

    for t in range(trials):
        seed = base_seed + t
        rng = random.Random(seed)

        rooms = build_program(house_w, house_h, rng)
        totals = zone_totals(rooms)
        zones = split_zones(house_w, house_h, totals)

        layout = Layout(house_w, house_h, rooms, zones, seed=seed)
        place_all_seeds(layout)
        grow_rooms(layout)
        fill_unassigned(layout)

        score, details = score_layout(layout)
        if score > best_score:
            best_score = score
            best_layout = layout
            best_details = details

    return best_layout, best_score, best_details


def print_summary(layout: Layout, score: float, details: Dict[str, float]):
    print("\n=== BEST LAYOUT SUMMARY ===")
    print(f"House size: {layout.w} x {layout.h} = {layout.w * layout.h}")
    print(f"Score: {score:.2f}")
    for k, v in details.items():
        if k == "reachable_rooms":
            print(f"  {k:14s}: {int(v)} / {len(layout.rooms)}")
        else:
            print(f"  {k:14s}: {v:.2f}")

    print("\n=== ROOM LIST ===")
    for rid, room in enumerate(layout.rooms):
        print(
            f"{room.name:10s} | type={room.room_type:8s} | zone={room.zone:7s} | "
            f"target={room.target_area:3d} | actual={len(layout.room_cells[rid]):3d} | "
            f"aspect={layout.room_aspect(rid):.2f}"
        )

    print("\n=== ADJACENCY REPORT ===")
    report = adjacency_report(layout)
    for room_name, neighbors in report.items():
        print(f"{room_name:10s}: {sorted(neighbors)}")

    print("\n=== SMART DOORS ===")
    doors = find_smart_doors(layout)
    print(f"Smart doors found: {len(doors)}")


if __name__ == "__main__":
    layout, score, details = generate_best_layout(
        house_w=18,
        house_h=12,
        trials=60,
        base_seed=100
    )
    print_summary(layout, score, details)
    plot_layout(layout, title=f"Round 4: Layout + Flow + Smart Doors | score={score:.1f}")