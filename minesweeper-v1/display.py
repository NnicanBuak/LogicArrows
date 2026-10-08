"""User supplied seven-segment circuit and non-invasive physical verification."""
import json
from logic import *
from mapdata import read_map,write_json
from arrow_layout import destinations
from runner import simulate

REFERENCE=HERE/'display.reference.save.txt'
INPUTS=((1,40),(3,40),(4,40),(0,38))
SEGMENTS=((10,2),(12,4),(13,11),(10,12),(7,11),(7,5),(10,7)) # a b c d e f g
EXPECTED=(0b0111111,0b0000110,0b1011011,0b1001111,0b1100110,0b1101101,0b1111101,0b0000111,0b1111111,0b1101111)

def detect(cells,p):
    from placement_backend import wire_cell
    for rotation,(dx,dy) in enumerate(((0,-1),(1,0),(0,1),(-1,0))):
        detector=(p[0]+dx,p[1]+dy);target=(p[0]+2*dx,p[1]+2*dy)
        if detector not in cells and target not in cells:
            trim={};valid=True
            for point,c in cells.items():
                outs=list(destinations(point,c))
                if target not in outs:continue
                if c.type not in (1,6,7,8,10,11,12,13,14):valid=False;break
                actual=[q for q in outs if q in cells]
                replacement=wire_cell(point,actual) if actual else None
                if replacement is None:valid=False;break
                trim[point]=replacement
            if valid:
                cells.update(trim);cells[detector]=Cell(5,rotation);cells[target]=Cell(23,0);return target
    raise ValueError(f'Cannot observe {p}')

def inspect_reference():
    cells=read_map(REFERENCE);sources=[]
    for i,p in enumerate(INPUTS):
        rotation=1 if i==3 else 0
        fixture=(p[0]-1,p[1]) if i==3 else (p[0],p[1]+1)
        assert fixture not in cells
        cells[fixture]=Cell(22,rotation);sources.append(fixture)
    # Display-only paths never reach any segment register or decoder input.
    # Replacing their first cells with test receivers observes the registers
    # without affecting number decoding or register updates.
    targets=[]
    for p in SEGMENTS:
        target=next(destinations(p,cells[p]));cells[target]=Cell(23,0);targets.append(target)
    masks=list(range(16))
    frames=[1]+[600]*len(masks)
    report=simulate(cells,dict(ticks=sum(frames),frame_ticks=frames,
        inputs=[dict(at=list(p),values=[0]+[(mask>>i)&1 for mask in masks]) for i,p in enumerate(sources)],
        expect=[dict(at=list(p),values=[0]+[None]*len(masks)) for p in targets]),optimize_cycles=False)
    assert report['passed'],report['failures'][:5]
    values=[sum(o['values'][i+1]<<j for j,o in enumerate(report['outputs'])) for i in range(len(masks))]
    result=dict(input_contacts=[list(p) for p in INPUTS],segment_states=values,expected=EXPECTED)
    write_json(HERE/'build/display.reference.observed.json',result)
    print(result,flush=True)
    return result

if __name__=='__main__':inspect_reference()
