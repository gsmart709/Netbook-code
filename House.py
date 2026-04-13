import random

WIDTH = 15
HEIGHT = 9

def create_empty_grid():
    return [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]

def add_walls(grid):
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if x == 0 or x == WIDTH-1 or y == 0 or y == HEIGHT-1:
                grid[y][x] = "#"

    # random interior walls
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
            return

def print_grid(grid):
    for row in grid:
        print("".join(row))

def generate_house():
    grid = create_empty_grid()
    add_walls(grid)
    place_points(grid)
    return grid

if __name__ == "__main__":
    house = generate_house()
    print_grid(house)
