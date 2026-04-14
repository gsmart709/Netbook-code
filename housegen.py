import random
import time
from collections import deque
import matplotlib.pyplot as plt

MIN_WIDTH = 25
MAX_WIDTH = 49
MIN_HEIGHT = 19
MAX_HEIGHT = 37

def odd_choices(start, end):
    return [n for n in range(start, end + 1) if n % 2 == 1]

def log_stage(name, start_time):
    elapsed = time.perf_counter() - start_time
    print(f"{name}... {elapsed:.4f}s")
    return time.perf_counter()

def print_grid(grid):
    for row in grid:
        print("".join(row))

def room_area(room):
    return (room["x2"] - room["x1"] + 1) * (room["y2"] - room["y1"] + 1)

def room_center(room):
    return (room["x1"] + room["x2"]) // 2, (room["y1"] + room["y2"]) // 2

def create_wall_grid(width, height):
    return [["#" for _ in range(width)] for _ in range(height)]

def carve_room(grid, room):
    for y in range(room["y1"], room["y2"] + 1):
        for x in range(room["x1"], room["x2"] + 1):
            grid[y][x] = " "

def carve_cell(grid, x, y, char=" "):
    if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
        grid[y][x] = char

def carve_corridor_L(grid, x1, y1, x2, y2):
    if random.random() < 0.5:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            carve_cell(grid, x, y1)
        for y in range(min(y1, y2), max(y1, y2) + 1):
            carve_cell(grid, x2, y)
    else:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            carve_cell(grid, x1, y)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            carve_cell(grid, x, y2)

def find_path(grid, start, end, width, height):
    queue = deque([start])
    visited = {start}
    parent = {}

    while queue:
        x, y = queue.popleft()
        if (x, y) == end:
            path = []
            while (x, y) != start:
                path.append((x, y))
                x, y = parent[(x, y)]
            return path[::-1]

        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited and grid[ny][nx] != "#":
                    visited.add((nx, ny))
                    parent[(nx, ny)] = (x, y)
                    queue.append((nx, ny))
    return None

def draw_path(grid, path):
    for x, y in path:
        if grid[y][x] == " ":
            grid[y][x] = "."

def partition_vertical_strip(x1, x2, y1, y2):
    rooms = []
    cur_y = y1
    while cur_y < y2:
        h = random.choice([3,5,7])
        if cur_y + h > y2:
            break
        room = {"x1": x1, "x2": x2, "y1": cur_y, "y2": cur_y + h}
        rooms.append(room)
        cur_y += h + 1
    return rooms

def partition_horizontal_strip(x1, x2, y1, y2):
    rooms = []
    cur_x = x1
    while cur_x < x2:
        w = random.choice([5,7,9])
        if cur_x + w > x2:
            break
        room = {"x1": cur_x, "x2": cur_x + w, "y1": y1, "y2": y2}
        rooms.append(room)
        cur_x += w + 1
    return rooms

def build_house_layout(width, height):
    grid = create_wall_grid(width, height)

    kitchen_side = random.choice(["left", "right"])
    kitchen_w = random.choice([7,9,11])
    kitchen_h = random.choice([5,7,9])

    if kitchen_side == "left":
        kitchen = {"type":"Kitchen","x1":1,"x2":kitchen_w,"y1":1,"y2":kitchen_h}
        split_x = kitchen_w + 1
        dining = {"type":"Dining","x1":kitchen_w+2,"x2":width-2,"y1":1,"y2":kitchen_h}
    else:
        kitchen = {"type":"Kitchen","x1":width-kitchen_w-1,"x2":width-2,"y1":1,"y2":kitchen_h}
        split_x = kitchen["x1"] - 1
        dining = {"type":"Dining","x1":1,"x2":kitchen["x1"]-2,"y1":1,"y2":kitchen_h}

    # Porch decision (safe)
    use_porch = random.random() < 0.5
    common_margin_bottom = 5 if use_porch else 3

    lower_y1 = kitchen_h + 3
    common = {
        "type":"Common",
        "x1": split_x+1 if kitchen_side=="left" else 1,
        "x2": width-2 if kitchen_side=="left" else split_x-1,
        "y1": lower_y1,
        "y2": height - common_margin_bottom
    }

    rooms = [kitchen, dining, common]

    # Dining split
    extra_dining_room = None
    if random.random() < 0.5 and (dining["x2"] - dining["x1"]) > 12:
        if kitchen_side == "left":
            cut = dining["x1"] + 6
            extra_dining_room = {"x1":cut+2,"x2":dining["x2"],"y1":1,"y2":kitchen_h}
            dining["x2"] = cut
        else:
            cut = dining["x2"] - 6
            extra_dining_room = {"x1":dining["x1"],"x2":cut-2,"y1":1,"y2":kitchen_h}
            dining["x1"] = cut
        rooms.append(extra_dining_room)

    # Partitions
    rooms.extend(partition_vertical_strip(1, split_x-1, common["y1"], common["y2"]))
    rooms.extend(partition_vertical_strip(split_x+1, width-2, common["y1"], common["y2"]))
    rooms.extend(partition_horizontal_strip(common["x1"], common["x2"], common["y2"]+1, height-2))

    # Porch
    porch = None
    if use_porch:
        cx,_ = room_center(common)
        porch = {"type":"Porch","x1":cx-2,"x2":cx+2,"y1":height-3,"y2":height-2}
        rooms.append(porch)

    # Carve
    for r in rooms:
        carve_room(grid, r)

    kc = room_center(kitchen)
    dc = room_center(dining)
    cc = room_center(common)

    carve_corridor_L(grid,*kc,*dc)
    carve_corridor_L(grid,*dc,*cc)

    if extra_dining_room:
        carve_corridor_L(grid,*room_center(extra_dining_room),*cc)

    for r in rooms:
        if r in [kitchen,dining,common,porch,extra_dining_room]:
            continue
        carve_corridor_L(grid,*room_center(r),*cc)

    carve_cell(grid,kc[0],0,"B")

    if porch:
        pc = room_center(porch)
        carve_cell(grid,pc[0],height-1,"F")
        carve_corridor_L(grid,*pc,*cc)
        end = (pc[0],height-2)
    else:
        carve_cell(grid,cc[0],height-1,"F")
        end = (cc[0],height-2)

    start = (kc[0],1)

    path = find_path(grid,start,end,width,height)
    if not path:
        return None, "no path"

    draw_path(grid,path)

    return {"grid":grid,"rooms":rooms}, "ok"

def generate_valid_house(max_attempts=200):
    for _ in range(max_attempts):
        w = random.choice(odd_choices(MIN_WIDTH,MAX_WIDTH))
        h = random.choice(odd_choices(MIN_HEIGHT,MAX_HEIGHT))
        res,_ = build_house_layout(w,h)
        if res:
            return res,w,h
    raise RuntimeError("failed")

def plot_house(grid,width,height):
    fig, ax = plt.subplots(figsize=(8,6))
    for y in range(height):
        for x in range(width):
            if grid[y][x] == "#":
                ax.add_patch(plt.Rectangle((x,height-y-1),1,1))
            else:
                ax.add_patch(plt.Rectangle((x,height-y-1),1,1,fill=False))
            if grid[y][x] in ("B","F"):
                ax.text(x+0.5,height-y-0.5,grid[y][x],ha="center",va="center")
    ax.set_xlim(0,width)
    ax.set_ylim(0,height)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.show()

if __name__ == "__main__":
    print("Generating Layout")
    house,w,h = generate_valid_house()
    print_grid(house["grid"])
    plot_house(house["grid"],w,h)