import random
import matplotlib.pyplot as plt
from collections import deque

MIN_W, MAX_W = 27, 51
MIN_H, MAX_H = 19, 37


def odd(a,b):
    return [x for x in range(a,b+1) if x%2==1]


def grid(w,h):
    return [["#" for _ in range(w)] for _ in range(h)]


def carve_rect(g,r):
    for y in range(r["y1"], r["y2"]+1):
        for x in range(r["x1"], r["x2"]+1):
            g[y][x] = " "


def carve_line_v(g,x,y1,y2):
    for y in range(y1,y2+1):
        g[y][x] = "#"


def carve_line_h(g,y,x1,x2):
    for x in range(x1,x2+1):
        g[y][x] = "#"


def center(r):
    return (r["x1"]+r["x2"])//2,(r["y1"]+r["y2"])//2


def corridor(g,x1,y1,x2,y2):
    if random.random()<0.5:
        for x in range(min(x1,x2),max(x1,x2)+1):
            g[y1][x]=" "
        for y in range(min(y1,y2),max(y1,y2)+1):
            g[y][x2]=" "
    else:
        for y in range(min(y1,y2),max(y1,y2)+1):
            g[y][x1]=" "
        for x in range(min(x1,x2),max(x1,x2)+1):
            g[y2][x]=" "


def bfs(g,s,e):
    w,h=len(g[0]),len(g)
    q=deque([s])
    seen={s}
    p={}
    while q:
        x,y=q.popleft()
        if (x,y)==e:
            path=[]
            while (x,y)!=s:
                path.append((x,y))
                x,y=p[(x,y)]
            return path[::-1]
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny=x+dx,y+dy
            if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and g[ny][nx]!="#":
                seen.add((nx,ny))
                p[(nx,ny)]=(x,y)
                q.append((nx,ny))
    return None


def build():

    w=random.choice(odd(MIN_W,MAX_W))
    h=random.choice(odd(MIN_H,MAX_H))

    g=grid(w,h)

    kitchen_side=random.choice(["left","right"])
    kw=random.choice([7,9,11])
    kh=random.choice([5,7,9])

    # --- Kitchen ---
    if kitchen_side=="left":
        kitchen={"type":"Kitchen","x1":1,"x2":kw,"y1":1,"y2":kh}
        split_x=kw+1
        dining={"type":"Dining","x1":kw+2,"x2":w-2,"y1":1,"y2":kh}
    else:
        kitchen={"type":"Kitchen","x1":w-kw-1,"x2":w-2,"y1":1,"y2":kh}
        split_x=kitchen["x1"]-1
        dining={"type":"Dining","x1":1,"x2":kitchen["x1"]-2,"y1":1,"y2":kh}

    # --- DRAW STRUCTURE FIRST ---
    # vertical drop from kitchen
    carve_line_v(g, split_x, kh+1, h-2)

    # horizontal under kitchen
    carve_line_h(g, kh+1, 1, w-2)

    # --- carve top rooms ---
    carve_rect(g,kitchen)
    carve_rect(g,dining)

    rooms=[kitchen,dining]

    # --- dining split ---
    if random.random()<0.5 and (dining["x2"]-dining["x1"])>12:
        if kitchen_side=="left":
            cut=dining["x1"]+6
            new={"x1":cut+2,"x2":dining["x2"],"y1":1,"y2":kh}
            dining["x2"]=cut
        else:
            cut=dining["x2"]-6
            new={"x1":dining["x1"],"x2":cut-2,"y1":1,"y2":kh}
            dining["x1"]=cut

        carve_rect(g,new)
        rooms.append(new)

    # --- bottom split ---
    split_y=random.randint(kh+3,h-5)
    carve_line_h(g,split_y,1,w-2)

    # --- left vertical split ---
    left_split=random.randint(3,split_x-3)
    carve_line_v(g,left_split,kh+2,split_y-1)

    # --- right vertical split ---
    right_split=random.randint(split_x+3,w-4)
    carve_line_v(g,right_split,kh+2,split_y-1)

    # --- define regions manually ---
    regions=[
        {"x1":1,"x2":left_split-1,"y1":kh+2,"y2":split_y-1},
        {"x1":left_split+1,"x2":split_x-1,"y1":kh+2,"y2":split_y-1},
        {"x1":split_x+1,"x2":right_split-1,"y1":kh+2,"y2":split_y-1},
        {"x1":right_split+1,"x2":w-2,"y1":kh+2,"y2":split_y-1}
    ]

    # carve regions
    for r in regions:
        if r["x2"]>r["x1"] and r["y2"]>r["y1"]:
            carve_rect(g,r)
            rooms.append(r)

    # --- COMMON = center region ---
    common=regions[1] if kitchen_side=="left" else regions[2]

    # --- porch ---
    porch=None
    if random.random()<0.5:
        cx,_=center(common)
        porch={"type":"Porch","x1":cx-2,"x2":cx+2,"y1":h-3,"y2":h-2}
        carve_rect(g,porch)
        rooms.append(porch)

    # --- doors ---
    kc=center(kitchen)
    dc=center(dining)
    cc=center(common)

    corridor(g,*kc,*dc)
    corridor(g,*dc,*cc)

    for r in regions:
        if r==common:
            continue
        corridor(g,*center(r),*cc)

    g[0][kc[0]]="B"

    if porch:
        pc=center(porch)
        g[h-1][pc[0]]="F"
        corridor(g,*pc,*cc)
        end=(pc[0],h-2)
    else:
        g[h-1][cc[0]]="F"
        end=(cc[0],h-2)

    start=(kc[0],1)

    path=bfs(g,start,end)
    if not path:
        return None

    for x,y in path:
        if g[y][x]==" ":
            g[y][x]="."

    return g,rooms,w,h


def plot(g,rooms,w,h):
    fig,ax=plt.subplots(figsize=(8,6))

    for y in range(h):
        for x in range(w):
            if g[y][x]=="#":
                ax.add_patch(plt.Rectangle((x,h-y-1),1,1))
            else:
                ax.add_patch(plt.Rectangle((x,h-y-1),1,1,fill=False,linewidth=0.5))

    for y in range(h):
        for x in range(w):
            if g[y][x] in ("B","F"):
                ax.text(x+0.5,h-y-0.5,g[y][x],ha="center",va="center")

    ax.set_xlim(0,w)
    ax.set_ylim(0,h)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.show()


if __name__=="__main__":
    for _ in range(100):
        r=build()
        if r:
            g,rooms,w,h=r
            plot(g,rooms,w,h)
            break