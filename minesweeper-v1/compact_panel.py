"""Prewired seven-segment / 5x5 button / mine panel with white UI gaps.

The supplied visible display and mine glyph are preserved. Seven local ANDs,
one shared show rail and seven transition detectors need no general routing.
The optional supplied BCD decoder is aligned directly under the raw contacts.
Coordinates use the visible number's left/top as (0,0).
"""
from dataclasses import dataclass
from itertools import product
import random

from logic import Cell
from display import REFERENCE,SEGMENTS,EXPECTED
from mine_indicator import indicator,BITMAP
from mapdata import read_map,map_hash
from arrow_layout import destinations,bounds_of
from runner import simulate

# Physical columns of the supplied display: f,a,e,g,d,b,c, not a,b,c,d,e,f,g.
RAW_SEGMENTS=(5,0,4,6,3,1,2)


@dataclass
class Panel:
    cells: dict
    inputs: dict
    input_fixtures: dict
    input_rotations: dict
    outputs: dict
    raw_inputs: dict
    segment_registers: list
    mine_pixels: list
    buttons: list
    keepout: set
    decoder: bool

    def moved(self,x,y):
        shift=lambda p:(p[0]+x,p[1]+y)
        return Panel({shift(p):c for p,c in self.cells.items()},
                     {n:shift(p) for n,p in self.inputs.items()},
                     {n:shift(p) for n,p in self.input_fixtures.items()},
                     dict(self.input_rotations),
                     {n:shift(p) for n,p in self.outputs.items()},
                     {n:shift(p) for n,p in self.raw_inputs.items()},
                     [shift(p) for p in self.segment_registers],
                     [shift(p) for p in self.mine_pixels],
                     [shift(p) for p in self.buttons],
                     {shift(p) for p in self.keepout},self.decoder)

    def describe(self):
        return dict(arrows=len(self.cells),bounds=bounds_of(self.cells),
                    inputs=self.inputs,input_fixtures=self.input_fixtures,
                    outputs=self.outputs,raw_inputs=self.raw_inputs,
                    segment_registers=self.segment_registers,
                    mine_pixels=self.mine_pixels,buttons=self.buttons,
                    button_size=5,decoder=self.decoder,raw_segment_order=RAW_SEGMENTS,
                    map_hash=map_hash(self.cells))


def make_panel(with_decoder=True,level_outputs=False,click_side='bottom'):
    if click_side not in ('top','bottom'):
        raise ValueError('Button collector exit must be top or bottom')
    reference=read_map(REFERENCE)
    cells={};buttons=[]
    def add(p,c):
        if p in cells:raise AssertionError(('panel collision',p))
        cells[p]=c
    for (x,y),c in reference.items():
        if y<=13:add((x-6,y),Cell(1,c.rotation,c.mirrored) if level_outputs and c.type==19 else c)
        elif with_decoder and y>=19:add((x-6,y+3),c)
    mine,root=indicator()
    mine_pixels=[]
    for (x,y),c in mine.items():
        p=(x+19,y+3);add(p,c);mine_pixels.append(p)
    assert root==(3,0)
    for y in range(4,9):
        add((10,y),Cell(1,0 if click_side=='top' else 2))
        for x in range(11,16):
            add((x,y),Cell(24,3));buttons.append((x,y))
    if click_side=='top':
        for y in range(4):add((10,y),Cell(1,0))
    else:add((10,9),Cell(1,2))
    # Blank row 14 separates the visible digit from blue jump-two contacts.
    # Enabled output feeds its split fork immediately: no extra BUF on row19.
    for x in range(7):
        add((x,15),Cell(10,0))
        add((x,16),Cell(1 if level_outputs else 17,0))
        if not level_outputs:add((x,17),Cell(1,0))
        add((x,18),Cell(10 if level_outputs else 12,0))
        add((x,19),Cell(16,0))
        add((x,20),Cell(7 if x<6 else 1,0))
        add((x,21),Cell(10,0))
    add((-1,20),Cell(1,1))
    # Mine control also jumps over a white row into the original glyph root.
    add((22,1),Cell(10,2))
    raw={f'raw:{i}':(i,21) for i in range(7)}
    inputs={'show':(-1,20),'mine':(22,1)}
    fixtures={'show':(-2,20),'mine':(22,0)}
    rotations={'show':1,'mine':2}
    if with_decoder:
        for i,p in enumerate(((-2,43),(-3,43),(-5,43),(-6,41))):
            name='bcd:'+str(i);inputs[name]=p
            fixtures[name]=(p[0]-1,p[1]) if i==3 else (p[0],p[1]+1)
            rotations[name]=1 if i==3 else 0
    else:
        for name,p in raw.items():
            inputs[name]=p;fixtures[name]=(p[0],p[1]+1);rotations[name]=0
    outputs={'click':(10,-1 if click_side=='top' else 10)}
    # General frame wires must stay out of the visible UI and white row14.
    # A single click lead may leave below the button's collector column.
    keepout={(x,y) for x in range(27) for y in range(15)}-set(cells)
    keepout.difference_update((10,y) for y in (range(-1,4) if click_side=='top' else range(10,15)))
    keepout.update(q for p,c in cells.items() for q in destinations(p,c) if q not in cells)
    keepout.difference_update(outputs.values());keepout.difference_update(fixtures.values())
    return Panel(cells,inputs,fixtures,rotations,outputs,raw,
                 [(x-6,y) for x,y in SEGMENTS],sorted(mine_pixels),buttons,
                 keepout,with_decoder)


def control_harness(panel):
    cells=dict(panel.cells)
    for name,p in panel.input_fixtures.items():
        if p in cells:raise AssertionError(('input fixture collision',name,p))
        cells[p]=Cell(22,panel.input_rotations[name])
    return cells


def native_observe(cells,scenario):
    report=simulate(cells,scenario,optimize_cycles=False)
    if report['failures']:raise AssertionError(report['failures'][:10])
    return {tuple(o['at']):o['values'] for o in report['observations']}


def verify_display(with_decoder=True,level_outputs=False):
    panel=make_panel(with_decoder,level_outputs);cells=control_harness(panel)
    vectors=[(0,0,0)]+[(n,show,mine) for n,show,mine in product(range(9),(0,1),(0,1))]
    vectors+=list(reversed(vectors))
    def values(name):
        if name=='show':return [v[1] for v in vectors]
        if name=='mine':return [v[2] for v in vectors]
        i=int(name.split(':')[1])
        return [(v[0]>>i)&1 if with_decoder else (EXPECTED[v[0]]>>RAW_SEGMENTS[i])&1 for v in vectors]
    inputs=[dict(at=list(p),values=values(name)) for name,p in panel.input_fixtures.items()]
    observed=native_observe(cells,dict(ticks=len(vectors)*100,hold_ticks=100,
        inputs=inputs,expect=[],observe=[list(p) for p in panel.segment_registers+panel.mine_pixels]))
    for i,p in enumerate(panel.segment_registers):
        wanted=[((EXPECTED[n]>>i)&1)*show for n,show,mine in vectors]
        if observed[p]!=wanted:raise AssertionError(('segment',with_decoder,i,observed[p],wanted))
    for p in panel.mine_pixels:
        wanted=[mine for n,show,mine in vectors]
        if observed[p]!=wanted:raise AssertionError(('mine pixel',p,observed[p],wanted))
    return dict(**panel.describe(),level_outputs=level_outputs,transition_vectors=len(vectors),
                checked_segment_values=7*len(vectors),checked_mine_values=len(panel.mine_pixels)*len(vectors))


def verify_raw_interface():
    panel=make_panel(False);cells=control_harness(panel)
    vectors=[(mask,show) for mask,show in product(range(128),(0,1))]
    vectors+=list(reversed(vectors))
    inputs=[]
    for name,p in panel.input_fixtures.items():
        if name=='show':values=[show for mask,show in vectors]
        elif name=='mine':values=[0]*len(vectors)
        else:
            i=int(name.split(':')[1]);values=[(mask>>i)&1 for mask,show in vectors]
        inputs.append(dict(at=list(p),values=values))
    observed=native_observe(cells,dict(ticks=len(vectors)*60,hold_ticks=60,
        inputs=inputs,expect=[],observe=[list(p) for p in panel.segment_registers]))
    for segment,p in enumerate(panel.segment_registers):
        bit=RAW_SEGMENTS.index(segment)
        wanted=[((mask>>bit)&1)*show for mask,show in vectors]
        if observed[p]!=wanted:raise AssertionError(('raw mapping',segment,observed[p],wanted))
    return dict(raw_masks=128,show_states=2,transition_vectors=len(vectors),
                checked_segment_values=7*len(vectors),raw_segment_order=RAW_SEGMENTS)


def verify_buttons(click_side='bottom'):
    panel=make_panel(False,click_side=click_side);rng=random.Random(47019)
    patterns=[1<<i for i in range(25)]+[(1<<25)-1,0]+[rng.getrandbits(25) for _ in range(8)]
    checked=0
    for mask in patterns:
        cells=dict(panel.cells);inputs=[]
        # Only activated pixels become test level sources. The remaining
        # native #24 button cells still relay inputs through their row.
        for i,p in enumerate(panel.buttons):
            if mask&(1<<i):
                cells[p]=Cell(22,3)
                inputs.append(dict(at=list(p),values=[0,1,0,1,0]))
        cells[panel.outputs['click']]=Cell(23,0)
        report=simulate(cells,dict(ticks=5*40,hold_ticks=40,inputs=inputs,
            expect=[dict(at=list(panel.outputs['click']),values=[0,int(bool(mask)),0,int(bool(mask)),0])]),optimize_cycles=False)
        if not report['passed']:raise AssertionError(('button mask',mask,report['failures']))
        checked+=report['checked_samples']
    return dict(buttons=25,patterns=len(patterns),checked_samples=checked,click_side=click_side,
                each_button=True,release=True,all_pressed=True)


def verify_panel():
    return dict(passed=True,profile='GraphDLC-01232bd',
                direct=verify_display(False),decoder=verify_display(True),
                raw_interface=verify_raw_interface(),buttons=verify_buttons())


if __name__=='__main__':
    import json
    print(json.dumps(verify_panel(),indent=2))
