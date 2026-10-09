"""Independent native proof of monotone defeat flooding and phase OR levels.

No production graph is changed. Defeat is a native SET fed by one ordinary
five-input OR arrow. Phase capture uses two permanent incoming levels and a
one-tick edge detector, without phase memory.
"""
from itertools import product
from compact_macros import Macro,sticky_latch,edge_detector,harness,validate_template
from logic import Cell
from runner import simulate


def flood_latch():
    latch=sticky_latch().moved(0,1)
    cells=dict(latch.cells)
    cells[(0,0)]=Cell(1,2)
    cells[(0,-1)]=Cell(1,2)
    cells[(-1,0)]=Cell(1,1)
    cells[(1,0)]=Cell(1,3)
    cells[(-1,-1)]=Cell(11,1)
    cells[(1,-1)]=Cell(11,2)
    return Macro(cells,{'local':(0,-1),'west':(-1,0),'east':(1,0),
                        'north':(-1,-1),'south':(1,-1)},
                 {'defeat':(2,2)},{'merge':(0,0),'defeat':(1,2)})


def phase_level():
    edge=edge_detector(True).moved(0,1)
    cells=dict(edge.cells);cells[(0,0)]=Cell(1,2)
    return Macro(cells,{'west':(-1,0),'north':(1,0)},
                 {'pulse':(2,2)},{'level':(0,0),'pulse':(1,2)})


def check(cells,scenario):
    report=simulate(cells,scenario,optimize_cycles=False)
    if report['failures']:raise AssertionError(report['failures'])
    return report


def verify_flood_latch():
    macro=flood_latch();validate_template(macro)
    cells={};inputs=[];expected=[]
    for mask in range(32):
        piece=macro.moved((mask%8)*7,(mask//8)*7)
        part,sources=harness(piece);cells.update(part)
        for i,(name,p) in enumerate(sources.items()):
            inputs.append(dict(at=list(p),values=[0,(mask>>i)&1,0,0]))
        expected.append(dict(at=list(piece.outputs['defeat']),values=[0,int(bool(mask)),int(bool(mask)),int(bool(mask))]))
    report=check(cells,dict(ticks=4*30,hold_ticks=30,inputs=inputs,expect=expected))
    return dict(**macro.describe(),input_masks=32,checked_samples=report['checked_samples'],
                input_release_retains_defeat=True)


def verify_monotone_phase():
    # Every incoming combination, simultaneous or independently delayed.
    cases=list(product((0,1),(0,1),range(9)))
    cells={};inputs=[];observe=[];expected={};ticks=30
    for i,(west,north,delay) in enumerate(cases):
        macro=phase_level().moved((i%9)*6,(i//9)*6)
        # Input contacts of this fixture are directly controlled source arrows.
        cells.update(macro.cells)
        for name,p in macro.inputs.items():
            cells[p]=Cell(22,1 if name=='west' else 3)
        cells[macro.outputs['pulse']]=Cell(23,0)
        left=[int(bool(west) and t>=3) for t in range(ticks)]
        top=[int(bool(north) and t>=3+delay) for t in range(ticks)]
        for name,values in (('west',left),('north',top)):
            inputs.append(dict(at=list(macro.inputs[name]),values=values))
        observe.extend([list(macro.gates['level']),list(macro.outputs['pulse'])])
        level=[0]+[int(bool(left[t-1] or top[t-1])) for t in range(1,ticks)]
        pulse=[0]*ticks
        for t in range(4,ticks):
            now=int(bool(left[t-4] or top[t-4]));before=int(bool(left[t-5] or top[t-5])) if t>=5 else 0
            pulse[t]=int(now and not before)
        expected[macro.gates['level']]=level
        expected[macro.outputs['pulse']]=pulse
    report=check(cells,dict(ticks=ticks,hold_ticks=1,inputs=inputs,expect=[],observe=observe))
    for record in report['observations']:
        p=tuple(record['at'])
        if record['values']!=expected[p]:raise AssertionError(('phase trace',p,record['values'],expected[p]))
    return dict(cases=len(cases),checked_ticks=len(cases)*ticks*2,
                input_delay_range=[0,8],one_pulse_per_nonzero_level=True,
                source_to_fixture_ticks=4)


def verify_controls():
    return dict(passed=True,profile='GraphDLC-01232bd',
                flood=verify_flood_latch(),phase=verify_monotone_phase())


if __name__=='__main__':
    import json
    print(json.dumps(verify_controls(),indent=2))
