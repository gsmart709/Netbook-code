import random
import matplotlib.pyplot as plt
from collections import deque

MIN_W, MAX_W = 27, 51
MIN_H, MAX_H = 19, 37


def odd(n1, n2):
    return [x for x in range(n1, n2+1) if x % 2 == 1]


def make_grid(w, h):
    return [["#" for _ in range(w)] for _ in range(h)]


def carve(grid, r):
    for y in range(r["y1"], r["y2"]+1):
        for x in range(r["x1"], r["x2"]+1):
            grid[y][x] = " "


def center(r):
    return (r["x1"] + r["x2"])//2, (r["y1"] + r["y2"])//2


def area(r):
    return (r["x2"]-r["x1"]+1)*(r["y2"]-r["y1"]+1)


def corridor(grid, x1,y1,x2,y2):
    if random.random() < 0.5:
        for x in range(min(x1,x2), max(x1,x2)+1):
            grid[y1][x] = " "
        for y in range(min(y1,y2), max(y1,y2)+1):
            grid[y][x2] = " "
    else:
        for y in range(min(y1,y2), max(y1,y2)+1):
            grid[y][x1] = " "
        for x in range(min(x1,x2), max(x1,x2)+1):
            grid[y2][x] = " "


def bfs(grid, start, end):
    w,h = len(grid[0]), len(grid)
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
                if grid[ny][nx] != "#":
                    seen.add((nx,ny))
                    parent[(nx,ny)] = (x,y)
                    q.append((nx,ny))
    return None


def build():
    w = random.choice(odd(MIN_W, MAX_W))
    h = random.choice(odd(MIN_H, MAX_H))

    grid = make_grid(w,h)

    kitchen_side = random.choice(["left","right"])
    kitchen_w = random.choice([7,9,11])  # wider kitchen
    kitchen_h = random.choice([5,7,9])

    # --- Kitchen ---
    if kitchen_side=="left":
        kitchen = {"type":"Kitchen","x1":1,"x2":kitchen_w,"y1":1,"y2":kitchen_h}
        dining = {"type":"Dining","x1":kitchen_w+2,"x2":w-2,"y1":1,"y2":kitchen_h}
        split_x = kitchen_w+1
    else:
        kitchen = {"type":"Kitchen","x1":w-kitchen_w-1,"x2":w-2,"y1":1,"y2":kitchen_h}
        dining = {"type":"Dining","x1":1,"x2":kitchen["x1"]-2,"y1":1,"y2":kitchen_h}
        split_x = kitchen["x1"]-1

    rooms = [kitchen, dining]

    # --- extend kitchen wall down ---
    for y in range(kitchen_h+1, h-1):
        grid[y][split_x] = "#"

    # --- extend bottom of kitchen across ---
    for x in range(1, w-1):
        grid[kitchen_h+1][x] = "#"

    # --- optional dining split ---
    if random.random()<0.5:
        if dining["x2"]-dining["x1"] > 12:
            if kitchen_side=="left":
                cut = dining["x1"]+6
                new = {"x1":cut+2,"x2":dining["x2"],"y1":1,"y2":kitchen_h}
                dining["x2"]=cut
            else:
                cut = dining["x2"]-6
                new = {"x1":dining["x1"],"x2":cut-2,"y1":1,"y2":kitchen_h}
                dining["x1"]=cut

            rooms.append(new)

    # --- carve rooms ---
    for r in rooms:
        carve(grid,r)

    # --- collect regions (simple flood fill) ---
    regions = []
    seen=set()

    for y in range(h):
        for x in range(w):
            if grid[y][x]==" " and (x,y) not in seen:
                stack=[(x,y)]
                pts=[]
                seen.add((x,y))
                while stack:
                    cx,cy=stack.pop()
                    pts.append((cx,cy))
                    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nx,ny=cx+dx,cy+dy
                        if 0<=nx<w and 0<=ny<h and grid[ny][nx]==" " and (nx,ny) not in seen:
                            seen.add((nx,ny))
                            stack.append((nx,ny))

                xs=[p[0] for p in pts]
                ys=[p[1] for p in pts]

                regions.append({
                    "x1":min(xs),"x2":max(xs),
                    "y1":min(ys),"y2":max(ys),
                    "cells":pts
                })

    # --- label rooms ---
    regions.sort(key=area)
    labels={}

    labels[id(regions[0])] = "Bath"

    remaining = regions[1:]

    # biggest = common
    common = max(remaining, key=area)
    labels[id(common)]="Common"
    remaining.remove(common)

    # ensure at least 1 bedroom
    if remaining:
        big = max(remaining, key=area)
        labels[id(big)]="Bedroom"
        remaining.remove(big)

    pool = ["Office","Laundry","Storage","Garage"]

    for r in remaining:
        choice = random.choice(["Bedroom"]+pool)
        labels[id(r)] = choice
        if choice in pool:
            pool.remove(choice)

    # --- porch ---
    porch=None
    if random.random()<0.5:
        cx,_=center(common)
        porch={"type":"Porch","x1":cx-2,"x2":cx+2,"y1":h-3,"y2":h-2}
        carve(grid,porch)

    # --- doors ---
    kc=center(kitchen)
    dc=center(dining)
    cc=center(common)

    corridor(grid,*kc,*dc)
    corridor(grid,*dc,*cc)

    for r in regions:
        if r is common:
            continue
        rc=center(r)
        corridor(grid,*rc,*cc)

    # front/back
    grid[0][kc[0]]="B"

    if porch:
        pc=center(porch)
        grid[h-1][pc[0]]="F"
        corridor(grid,*pc,*cc)
        end=(pc[0],h-2)
    else:
        grid[h-1][cc[0]]="F"
        end=(cc[0],h-2)

    start=(kc[0],1)

    path=bfs(grid,start,end)
    if not path:
        return None

    for x,y in path:
        if grid[y][x]==" ":
            grid[y][x]="."

    return grid, regions, labels, w, h


def plot(grid, regions, labels, w, h):
    fig, ax = plt.subplots(figsize=(8,6))

    for y in range(h):
        for x in range(w):
            if grid[y][x]=="#":
                ax.add_patch(plt.Rectangle((x,h-y-1),1,1))
            else:
                ax.add_patch(plt.Rectangle((x,h-y-1),1,1,fill=False,linewidth=0.5))

    for r in regions:
        cx,cy=center(r)
        ax.text(cx+0.5,h-cy-0.5,labels[id(r)],ha="center",va="center",fontsize=8,
                bbox=dict(fc="white",ec="black"))

    for y in range(h):
        for x in range(w):
            if grid[y][x] in ("B","F"):
                ax.text(x+0.5,h-y-0.5,grid[y][x],ha="center",va="center")

    ax.set_xlim(0,w)
    ax.set_ylim(0,h)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.show()


if __name__=="__main__":
    for _ in range(50):
        res=build()
        if res:
            grid,regions,labels,w,h=res
            plot(grid,regions,labels,w,h)
            break