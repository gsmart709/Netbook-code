def build_house_layout(width, height):
    grid = create_wall_grid(width, height)

    kitchen_side = random.choice(["left", "right"])

    # --- Kitchen (wider) ---
    kitchen_h = random.choice([5, 7, 9])
    kitchen_w = random.choice([7, 9, 11])

    if kitchen_side == "left":
        kitchen = {"type": "Kitchen", "x1": 1, "x2": kitchen_w, "y1": 1, "y2": kitchen_h}
        split_x = kitchen_w + 1
        dining = {"type": "Dining", "x1": kitchen_w + 2, "x2": width - 2, "y1": 1, "y2": kitchen_h}
    else:
        kitchen = {"type": "Kitchen", "x1": width - kitchen_w - 1, "x2": width - 2, "y1": 1, "y2": kitchen_h}
        split_x = kitchen["x1"] - 1
        dining = {"type": "Dining", "x1": 1, "x2": kitchen["x1"] - 2, "y1": 1, "y2": kitchen_h}

    if room_area(kitchen) < 30:
        return None, "kitchen too small"

    rooms = [kitchen, dining]

    # --- Porch decision FIRST (your rule) ---
    use_porch = random.random() < 0.5

    # --- Common area (aligned to kitchen split) ---
    lower_y1 = kitchen_h + 3
    bottom_margin = 6 if use_porch else 3

    common = {
        "type": "Common",
        "x1": split_x + 1 if kitchen_side == "left" else 1,
        "x2": width - 2 if kitchen_side == "left" else split_x - 1,
        "y1": lower_y1,
        "y2": height - bottom_margin
    }

    # --- Dining split (50%) ---
    extra_dining_room = None
    if random.random() < 0.5 and (dining["x2"] - dining["x1"]) > 12:
        if kitchen_side == "left":
            cut = dining["x1"] + 6
            extra_dining_room = {
                "x1": cut + 2,
                "x2": dining["x2"],
                "y1": 1,
                "y2": kitchen_h
            }
            dining["x2"] = cut
        else:
            cut = dining["x2"] - 6
            extra_dining_room = {
                "x1": dining["x1"],
                "x2": cut - 2,
                "y1": 1,
                "y2": kitchen_h
            }
            dining["x1"] = cut

        rooms.append(extra_dining_room)

    # --- Left stripe (aligned with kitchen split) ---
    if kitchen_side == "left":
        left_x1, left_x2 = 1, split_x - 1
    else:
        left_x1, left_x2 = 1, split_x - 1

    if left_x2 - left_x1 + 1 >= 5:
        left_rooms = partition_vertical_strip(left_x1, left_x2, common["y1"], common["y2"])
        rooms.extend(left_rooms)

    # --- Right stripe ---
    if kitchen_side == "left":
        right_x1, right_x2 = split_x + 1, width - 2
    else:
        right_x1, right_x2 = split_x + 1, width - 2

    if right_x2 - right_x1 + 1 >= 5:
        right_rooms = partition_vertical_strip(right_x1, right_x2, common["y1"], common["y2"])
        rooms.extend(right_rooms)

    # --- Bottom stripe ---
    bottom_y1 = common["y2"] + 2
    bottom_y2 = height - 2

    if use_porch:
        bottom_y2 -= 3

    if bottom_y2 - bottom_y1 >= 3:
        bottom_rooms = partition_horizontal_strip(common["x1"], common["x2"], bottom_y1, bottom_y2)
        rooms.extend(bottom_rooms)

    # --- Porch ---
    porch = None
    if use_porch:
        cx, _ = room_center(common)
        porch = {
            "type": "Porch",
            "x1": cx - 2,
            "x2": cx + 2,
            "y1": height - 3,
            "y2": height - 2
        }
        rooms.append(porch)

    # --- Carve all rooms ---
    for room in rooms:
        carve_room(grid, room)

    # --- Connections ---
    kitchen_cx, kitchen_cy = room_center(kitchen)
    dining_cx, dining_cy = room_center(dining)
    common_cx, common_cy = room_center(common)

    # Kitchen → Dining → Common
    carve_corridor_L(grid, kitchen_cx, kitchen_cy, dining_cx, dining_cy)
    carve_corridor_L(grid, dining_cx, dining_cy, common_cx, common["y1"])

    # Extra dining room → Common
    if extra_dining_room:
        ex, ey = room_center(extra_dining_room)
        carve_corridor_L(grid, ex, ey, common_cx, common["y1"])

    # All other rooms → Common
    for room in rooms:
        if room in [kitchen, dining, common, porch, extra_dining_room]:
            continue

        cx, cy = room_center(room)

        if room["x2"] < common["x1"]:
            carve_corridor_L(grid, cx, cy, common["x1"], cy)
        elif room["x1"] > common["x2"]:
            carve_corridor_L(grid, cx, cy, common["x2"], cy)
        elif room["y1"] > common["y2"]:
            carve_corridor_L(grid, cx, cy, cx, common["y2"])

    # --- Doors ---
    carve_cell(grid, kitchen_cx, 0, "B")

    if porch:
        pcx, pcy = room_center(porch)
        carve_corridor_L(grid, pcx, pcy, common_cx, common["y2"])
        carve_cell(grid, pcx, height - 1, "F")
        end = (pcx, height - 2)
    else:
        carve_cell(grid, common_cx, height - 1, "F")
        end = (common_cx, height - 2)

    start = (kitchen_cx, 1)

    labels = assign_final_labels(rooms, width, height)
    valid, reason = validate_room_sizes(rooms, labels)
    if not valid:
        return None, reason

    return {
        "grid": grid,
        "rooms": rooms,
        "labels": labels,
        "start": start,
        "end": end,
        "kitchen_side": kitchen_side,
        "front_mode": "porch" if porch else "common",
    }, "ok"