"""Native wall frames without moving or covering stackable connectors."""
from logic import Cell


def add_cell_walls(cells, side,height=None):
    height=height or side
    perimeter={(x,y) for x in range(side) for y in (0,height-1)}
    perimeter|={(x,y) for y in range(height) for x in (0,side-1)}
    walls=sorted(perimeter-set(cells))
    cells.update({p:Cell(25,0) for p in walls})
    return [list(p) for p in walls]
