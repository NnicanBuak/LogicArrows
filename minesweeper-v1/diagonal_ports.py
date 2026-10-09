"""Corner channels connecting logical diagonal neighbors with native arrows.

Each channel crosses a reserved corner of an orthogonal neighbor, without
entering that neighbor's logic. All modules remain identical and abut flush.
Separate lanes avoid reciprocal links and carry M, Z and S concurrently.
"""
from logic import Cell
from arrow_layout import destinations

LANES={'M':2,'Z':5,'S':8}
OPPOSITE={'NW':'SE','NE':'SW','SW':'NE','SE':'NW'}
ROTATIONS={'NW':3,'NE':0,'SW':2,'SE':1}
OFFSETS={'NW':(-1,-1),'NE':(1,-1),'SW':(-1,1),'SE':(1,1)}

def corner_channels(side,fields=None):
    cells={}
    for direction,rotation in ROTATIONS.items():
        for field in (LANES if fields is None else fields):
            a=LANES[field]
            for k in range(1,a+1):
                x=a-k if direction in ('NW','SW') else side-1-a+k
                y=side-k if direction in ('NW','NE') else k-1
                p=(x,y)
                assert p not in cells
                cells[p]=Cell(11,rotation)
    return cells

def contact(direction,field,side,output):
    a=LANES[field]
    if output:
        x=a if direction in ('NW','SW') else side-1-a
        y=0 if direction in ('NW','NE') else side-1
        p=(x,y);rotation=ROTATIONS[direction]
        fixture=next(destinations(p,Cell(11,rotation)))
        pin=(x,1 if y==0 else side-2)
        return p,rotation,fixture,pin
    # Opposite diagonal's output arrives through the corner's other face.
    x=0 if direction in ('NW','SW') else side-1
    y=a if direction in ('NW','NE') else side-1-a
    incoming=ROTATIONS[OPPOSITE[direction]]
    dx,dy=OFFSETS[OPPOSITE[direction]]
    p=(x,y);fixture=(x-dx,y-dy)
    return p,1 if x==0 else 3,fixture,incoming

def check_channels(template,meta):
    side=meta['side']
    copies={(p[0]+dx*side,p[1]+dy*side):c for dx in (-1,0,1) for dy in (-1,0,1)
            for p,c in template.items()}
    for direction,(dx,dy) in OFFSETS.items():
        for field in meta.get('diagonal_signals',LANES):
            a=LANES[field]
            source=tuple(meta['outputs'][f'DG:{direction}{field}'][0]['contact'])
            target=meta['inputs'][f'DG:{OPPOSITE[direction]}{field}'][0]['contact']
            target=(target[0]+dx*side,target[1]+dy*side)
            p=source;seen=set()
            while p!=target:
                assert p not in seen,('diagonal cycle',direction,field,p)
                seen.add(p)
                qs=list(destinations(p,copies[p]))
                assert len(qs)==1 and qs[0] in copies,('broken corner channel',p,qs)
                q=qs[0]
                assert p not in destinations(q,copies[q]),('reciprocal corner link',p,q)
                p=q
            assert len(seen)==a+1,('unexpected corner length',direction,field,len(seen))
    return True
