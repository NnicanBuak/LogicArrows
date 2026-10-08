"""Reimported save verification for mechanically stackable modules."""
import json
from snap import *
from display import EXPECTED
from runner import simulate

MINE_PORTS=('W:NM','N:M','E:NM','W:M','E:M','W:SM','S:M','E:SM')

def sources(cells,meta,ports):
    result={}
    for name in ports:
        es=meta['inputs'][name];p=tuple(es[0]['fixture']);rotation=es[0]['rotation']
        if name.startswith('button'):
            p=p[0]+2,p[1]
        assert p not in cells or cells[p].type==24
        cells[p]=Cell(22,rotation);result[name]=p
    return result

def register_probes(cells,meta,board=False):
    out={}
    for name,p in meta['states'].items():
        if name in ('cascade','loss'):
            if board:continue
            e=meta['outputs']['E:Z' if name=='cascade' else 'E:prefixLoss'][0]
            q=tuple(e['fixture']);assert q not in cells
            cells[q]=Cell(23,0);out[name]=q;continue
        p=tuple(p);q=p[0],p[1]+1;r=p[0],p[1]+2
        assert q not in cells and r not in cells,(name,p)
        cells[q]=Cell(5,2);cells[r]=Cell(23,0);out[name]=r
    return out

def segment_probes(cells,meta):
    out=[]
    for p in meta['segment_registers']:
        p=tuple(p);q=next(destinations(p,cells[p]));cells[q]=Cell(23,0);out.append(q)
    return out

def verify_cell(stem='cell'):
    cells=read_map(BUILD/(stem+'.save.txt'));meta=json.loads((BUILD/(stem+'.layout.json')).read_text())
    inp=sources(cells,meta,list(MINE_PORTS)+['N:ready','button0'])
    seg=segment_probes(cells,meta);states=register_probes(cells,meta)
    masks=list(range(256))+list(reversed(range(256)));hold=1600
    scenario=dict(ticks=len(masks)*hold,hold_ticks=hold,
        inputs=[dict(at=list(p),values=[(mask>>MINE_PORTS.index(name))&1 if name in MINE_PORTS else 1 for mask in masks]) for name,p in inp.items()],
        expect=[dict(at=list(p),values=[(EXPECTED[mask.bit_count()]>>j)&1 for mask in masks]) for j,p in enumerate(seg)]+
               [dict(at=list(states[name]),values=[int(name in ('opened','request','busy')) if name!='cascade' else int(mask==0) for mask in masks]) for name in ('mine','opened','selected','request','busy','cascade','loss')])
    r=simulate(cells,scenario,optimize_cycles=False,timeout=180)
    if not r['passed']:raise AssertionError(r['failures'][:12])
    result=dict(passed=True,neighbor_masks=256,transition_vectors=512,segment_checks=7*512,checked_samples=r['checked_samples'],side=meta['side'],map_hash=meta['map_hash'])
    write_json(BUILD/(stem+'.verification.json'),result)
    print('Framed cell verified:',result,flush=True)
    return result

def moved(meta,dx,dy):
    result=dict(meta)
    result['states']={name:[p[0]+dx,p[1]+dy] for name,p in meta['states'].items()}
    result['segment_registers']=[[p[0]+dx,p[1]+dy] for p in meta['segment_registers']]
    result['inputs']={name:[dict(e,contact=[e['contact'][0]+dx,e['contact'][1]+dy],fixture=[e['fixture'][0]+dx,e['fixture'][1]+dy]) for e in es] for name,es in meta['inputs'].items()}
    return result

def verify_board(size=10,seed=123456789,first=None):
    from runner import simulate as run_native
    from reference_model import flood
    stem=f'minesweeper-{size}x{size}'
    cells=read_map(BUILD/(stem+'.save.txt'));meta=json.loads((BUILD/(stem+'.layout.json')).read_text())
    first=(size//2)*size+size//2 if first is None else first
    ports={};buttons=[]
    for i,t in enumerate(meta['tiles']):
        tm=moved(meta['cell'],*t['origin'])
        buttons.append(sources(cells,tm,['button0'])['button0'])
        for name,p in register_probes(cells,tm,True).items():ports[f'{i}:{name}']=p
        for j,p in enumerate(segment_probes(cells,tm)):ports[f'{i}:segment{j}']=p
    for name in ('victory','defeat'):
        e=meta['header']['outputs'][name][0];q=tuple(e['fixture']);assert q not in cells
        cells[q]=Cell(23,0);ports[name]=q
    wait=max(50000,meta['full_settle_bound']*2+meta['logic_settle_bound']*2)
    initial=[max(2000,meta['logic_settle_bound']),64,wait]
    def run(events=()):
        durations=initial+[d for event in events for d in (64,max(20000,meta['logic_settle_bound']*3))]
        scenario=dict(ticks=sum(durations),frame_ticks=durations,seed=seed,
            inputs=[dict(at=list(p),values=[0,int(i==first),0]+[b for event in events for b in (int(i in event),0)]) for i,p in enumerate(buttons)],
            expect=[dict(at=list(p),values=[0,None,None]+[None]*(2*len(events))) for p in ports.values()])
        r=run_native(cells,scenario,optimize_cycles=False,timeout=240)
        assert r['passed'],r['failures'][:10]
        values={name:r['outputs'][j]['values'][-1] for j,name in enumerate(ports)}
        return values
    v=run();mines={i for i in range(size*size) if v[f'{i}:mine']}
    if size>=5:assert mines,'Fixed verification seed must produce mines'
    opened=flood(size,mines,set(),[first])
    selected={i for i in range(size*size) if v[f'{i}:selected']}
    write_json(BUILD/(stem+'.observed.json'),v)
    assert selected=={first},('selection',selected)
    x,y=first%size,first//size
    protected={first}|{(y+dy)*size+x+dx for dx,dy in DIRECTIONS if 0<=x+dx<size and 0<=y+dy<size}
    assert not mines&protected,('first protection',mines&protected)
    def check(values,expected,defeat=False):
        actual={i for i in range(size*size) if values[f'{i}:opened']}
        assert actual==expected,('opened',sorted(actual^expected))
        for i in range(size*size):
            assert values[f'{i}:mine']==int(i in mines),('mine changed',i)
            x,y=i%size,i//size
            count=sum((y+dy)*size+x+dx in mines for dx,dy in DIRECTIONS if 0<=x+dx<size and 0<=y+dy<size)
            word=EXPECTED[count] if i in expected and i not in mines else 0
            actualword=sum(values[f'{i}:segment{j}']<<j for j in range(7))
            assert actualword==word,('display',i,count,actualword,word)
        assert values['defeat']==int(defeat)
        assert values['victory']==int(not defeat and len(expected-mines)==size*size-len(mines))
    check(v,opened)
    write_json(BUILD/(stem+'.demo.json'),dict(size=size,first=first,mines=sorted(mines),opened=sorted(opened),measured=v))
    cases=['first-safe','neighbor-counts','cascade','closed-blank','visible-zero','stacked-connectors']
    if mines:
        mine=min(mines);dv=run([{mine},set(range(size*size))-mines-opened]);check(dv,opened|{mine},True)
        cases+=['mine-defeat','blocked-after-defeat']
    vv=run([set(range(size*size))-mines,mines]);check(vv,set(range(size*size))-mines)
    cases+=['victory','blocked-after-victory']
    result=dict(passed=True,size=size,seed=seed,first=first,mines=sorted(mines),first_opened=sorted(opened),scenarios=cases,map_hash=meta['map_hash'],
        measured_outputs=len(ports),wait_ticks=wait,identical_modules=True,connection_wires_added=0)
    write_json(BUILD/(stem+'.verification.json'),result)
    print('Snap board verified:',result,flush=True)
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=10);p.add_argument('--cell-only',action='store_true')
    p.add_argument('--seed',type=int,default=123456789);p.add_argument('--first',type=int);p.add_argument('--two-seeds',action='store_true');a=p.parse_args()
    verify_cell()
    if not a.cell_only:
        if a.two_seeds:
            assert a.size==10,'Two-seed delivery audit uses the base 10x10 board'
            runs=[verify_board(10,123456789,55),verify_board(10,987654321,0)]
            write_json(BUILD/'minesweeper-10x10.seeds.verification.json',dict(passed=True,runs=runs))
        else:verify_board(a.size,a.seed,a.first)
