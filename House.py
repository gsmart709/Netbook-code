import random
from collections import deque

WIDTH = 15
HEIGHT = 9

def create_empty_grid():
    return [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]

def add_walls(grid):
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if x == 0 or x == WIDTH-1 or y == 0 or y == HEIGHT-1:
                grid[y][x] = "#"

    for _ in range(20):
        x = random.randint(1, WIDTH-2)
        y = random.randint(1, HEIGHT-2)
        grid[y][x] = "#"

def place_points(grid):
    while True:
        ex, ey = random.randint(1, WIDTH-2), random.randint(1, HEIGHT-2)
        fx, fy = random.randint(1, WIDTH-2), random.randint(1, HEIGHT-2)

        if grid[ey][ex] == " " and grid[fy][fx] == " " and (ex, ey) != (fx, fy):
            grid[ey][ex] = "E"
            grid[fy][fx] = "F"
            return (ex, ey), (fx, fy)

def find_path(grid, start, end):
    queue = deque([start])
    visited = set([start])
    parent = {}

    while queue:
        x, y = queue.popleft()

        if (x, y) == end:
            path = []
            while (x, y) != start:
                path.append((x, y))
                x, y = parent[(x, y)]
            path.reverse()
            return path

        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x + dx, y + dy

            if (0 <= nx < WIDTH and 0 <= ny < HEIGHT and
                (nx, ny) not in visited and grid[ny][nx] != "#"):

                queue.append((nx, ny))
                visited.add((nx, ny))
                parent[(nx, ny)] = (x, y)

    return None

def draw_path(grid, path):
    for x, y in path:
        if grid[y][x] == " ":
            grid[y][x] = "."

def print_grid(grid):
    for row in grid:
        print("".join(row))

def generate_valid_house():
    while True:
        grid = create_empty_grid()
        add_walls(grid)
        start, end = place_points(grid)

        path = find_path(grid, start, end)

        if path:
            draw_path(grid, path)
            return grid

if __name__ == "__main__":
    house = generate_valid_house()
    print_grid(house)
