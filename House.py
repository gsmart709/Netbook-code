import random
import time
from collections import deque
import matplotlib.pyplot as plt

MIN_WIDTH = 25
MAX_WIDTH = 31
MIN_HEIGHT = 19
MAX_HEIGHT = 23

EXTRA_ROOM_POOL = ["Bedroom", "Office", "Laundry", "Storage", "Garage"]

def odd_choices(start, end):
    return [n for n in range(start, end + 1) if n % 2 == 1]

def room_area(room):
    return (room["x2"] - room["x1"] + 1) * (room["y2"] - room["y1"] + 1)

def room_center(room):
    return (room["x1"] + room["x2"]) // 2, (room["y1"] + room["y2"]) // 2

def create_grid(w, h):
    return [["#" for _ in range(w)] for _ in range(h)]

def carve_room(grid, r):
    for y in range(r["y1"], r["y2"] + 1):
        for x in range(r["x1"], r["x2"] + 1):
            grid[y][x] = " "

def carve(grid, x, y):
    grid[y][x] = " "

def is_open(grid, x, y):
    return grid[y][x] != "#"

def carve_door(grid, r1, r2):
    # vertical
    if r1["x2"] + 2 == r2["x1"] or r2["x2"] + 2 == r1["x1"]:
        left = r1 if r1["x2"] < r2["x1"] else r2
        right = r2 if left is r1 else r1

        x = left["x2"] + 1
        ys = range(max(left["y1"], right["y1"]), min(left["y2"], right["y2"]) + 1)

        valid = [y for y in ys if is_open(grid, x-1, y) and is_open(grid, x+1, y)]
        if not valid:
            return False

        y = valid[len(valid)//2]
        carve(grid, x, y)
        return True

    # horizontal
    if r1["y2"] + 2 == r2["y1"] or r2["y2"] + 2 == r1["y1"]:
        top = r1 if r1["y2"] < r2["y1"] else r2
        bot = r2 if top is r1 else r1

        y = top["y2"] + 1
        xs = range(max(top["x1"], bot["x1"]), min(top["x2"], bot["x2"]) + 1)

        valid = [x for x in xs if is_open(grid, x, y-1) and is_open(grid, x, y+1)]
        if not valid:
            return False

        x = valid[len(valid)//2]
        carve(grid, x, y)
        return True

    return False

def find_path(grid, start, end, w, h):
    q = deque([start])
    seen = {start}
    parent = {}

    while q:
        x,y = q.popleft()
        if (x,y)==end:
            path=[]
            while (x,y)!=start:
                path.append((x,y))
                x,y = parent[(x,y)]
            return path[::-1]

        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny = x+dx,y+dy
            if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and grid[ny][nx]!="":
                seen.add((nx,ny))
                parent[(nx,ny)] = (x,y)
                q.append((nx,ny))
    return None

def draw_path(grid, path):
    for x,y in path:
        if grid[y][x]==" ":
            grid[y][x]="."

def build_house(w,h):

    grid = create_grid(w,h)

    kitchen_side = random.choice(["left","right"])
    front_mode = random.choice(["common","porch"])

    kitchen_w = 5

    if kitchen_side=="left":
        kitchen={"type":"Kitchen","x1":1,"x2":kitchen_w,"y1":1,"y2":5}
        dining={"type":"Dining","x1":kitchen_w+2,"x2":w-2,"y1":1,"y2":5}
    else:
        kitchen={"type":"Kitchen","x1":w-kitchen_w-1,"x2":w-2,"y1":1,"y2":5}
        dining={"type":"Dining","x1":1,"x2":kitchen["x1"]-2,"y1":1,"y2":5}

    common={"type":"Common","x1":7,"x2":w-8,"y1":7,"y2":h-2}

    porch=None
    if front_mode=="porch":
        cx=(common["x1"]+common["x2"])//2
        porch={"type":"Porch","x1":cx-2,"x2":cx+2,"y1":h-4,"y2":h-2}
        common["y2"]=porch["y1"]-2

    bedroom={"type":"Bedroom","x1":1,"x2":5,"y1":7,"y2":11}
    bath={"type":"Bath","x1":1,"x2":5,"y1":13,"y2":15}

    right1={"type":random.choice(EXTRA_ROOM_POOL),"x1":w-6,"x2":w-2,"y1":7,"y2":11}
    right2={"type":random.choice(EXTRA_ROOM_POOL),"x1":w-6,"x2":w-2,"y1":13,"y2":h-2}

    rooms=[kitchen,dining,common,bedroom,bath,right1,right2]
    if porch: rooms.append(porch)

    for r in rooms:
        carve_room(grid,r)

    carve_door(grid,kitchen,dining)
    carve_door(grid,bedroom,common)
    carve_door(grid,bedroom,bath)
    carve_door(grid,right1,common)

    if porch:
        carve_door(grid,porch,common)
    else:
        carve_door(grid,right2,common)

    # FIXED LINE HERE
    for r in rooms:
        if r in [kitchen,dining,common,bedroom,bath,right1,right2]:
            continue
        carve_door(grid,r,common)

    kx=(kitchen["x1"]+kitchen["x2"])//2
    grid[0][kx]="B"

    if porch:
        fx=(porch["x1"]+porch["x2"])//2
        grid[h-1][fx]="F"
        end=(fx,h-2)
    else:
        fx=(common["x1"]+common["x2"])//2
        grid[h-1][fx]="F"
        end=(fx,h-2)

    start=(kx,1)

    return grid,rooms,start,end


def plot(grid,rooms,w,h):
    fig,ax=plt.subplots()

    for y in range(h):
        for x in range(w):
            if grid[y][x]=="#":
                ax.add_patch(plt.Rectangle((x,h-y-1),1,1))

    for y in range(h):
        for x in range(w):
            if grid[y][x]==".":
                ax.plot(x+.5,h-y-.5,"o")

    for r in rooms:
        cx,cy=room_center(r)
        ax.text(cx+.5,h-cy-.5,r["type"],ha="center")

    ax.set_xlim(0,w)
    ax.set_ylim(0,h)
    ax.set_aspect("equal")
    plt.show()


def main():
    w=random.choice(odd_choices(MIN_WIDTH,MAX_WIDTH))
    h=random.choice(odd_choices(MIN_HEIGHT,MAX_HEIGHT))

    grid,rooms,start,end=build_house(w,h)

    path=find_path(grid,start,end,w,h)
    if path:
        draw_path(grid,path)

    plot(grid,rooms,w,h)


if __name__=="__main__":
    main()