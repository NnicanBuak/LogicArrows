"""8x8 mine: red splitters and four blue arrows for diagonal spikes."""
from logic import Cell

BITMAP=(
    '00011000',
    '01011010',
    '00111100',
    '11101111',
    '11111111',
    '00111100',
    '01011010',
    '00011000',
)

def indicator():
    pixels={(x,y) for y,row in enumerate(BITMAP) for x,bit in enumerate(row) if bit=='1'}
    # Branch downward/right from the root, then return through the lower body
    # toward the left arm. No feedback: removing the input blanks every pixel.
    cells={p:Cell(7,1) for p in pixels}
    for p in ((4,4),(5,4),(6,4),(7,4),(3,4),(3,5),(4,5),(3,6),(4,6),
              (3,7),(4,7),(1,3),(0,3),(1,4),(0,4),(1,6)):
        cells[p]=Cell(7,2)
    for p in ((2,4),(2,3),(1,1)):
        cells[p]=Cell(7,3)
    cells[3,2]=Cell(6,1)
    cells[6,1]=Cell(7,0)
    for p,rotation in (((2,2),3),((5,2),0),((2,5),2),((5,5),1)):
        cells[p]=Cell(11,rotation)
    return cells,(3,0)
