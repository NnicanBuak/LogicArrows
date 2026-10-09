"""Translate identical tile copies without adding or rerouting a single cell wire."""
from snap import *
from external_routing import Wiring
from status_display import add_status
from diagonal_ports import check_channels

class HeaderRouter(Router):
    def route_allowed(self,p):return 0<=p[0]<self.side and -100<=p[1]<0

def header(meta):
    l=Logic('minesweeper_header')
    busy,loss,sat=[l.input(n) for n in ('busy','loss','satisfied')]
    clocks={name:l.input(name+'Clock') for name in ('choose','sample','ready')}
    for name,net in clocks.items():l.output(name,net)
    stop=l.any(loss,l.both(clocks['ready'],sat))
    l.output('stop',stop)
    l.output('victory',l.all(clocks['ready'],sat,l.inv(loss)))
    l.output('defeat',loss)
    l.output('started',busy)
    graph=l.graph;side=meta['side'];vertices=[];positions=[];free=[]
    for name,es in graph['inputs'].items():
        if name in ('busy','loss','satisfied'):
            tileport=meta['outputs']['N:'+{'busy':'busy','loss':'totalLoss','satisfied':'totalSat'}[name]][0]
            p=tuple(tileport['fixture']);fixture=tuple(tileport['contact']);rot=0
        else:
            p=(0,-30-8*list(clocks).index(name[:-5]));fixture=(-1,p[1]);rot=1
        vertices.append(dict(kind='input',net=name,rotation=rot,fixture=fixture));positions.append(p)
    for node in graph['nodes']:
        v=dict(kind='gate',node=node,rotation=1)
        if node['output'].startswith('port:'):
            name=node['output'][5:]
            if name in ('choose','sample','ready','stop'):
                p=tuple(meta['inputs']['N:'+name][0]['fixture']);v['rotation']=2
            elif name in ('victory','defeat'):p=(side-16,-24+8*(name=='defeat'));v['rotation']=2
            elif name=='started':p=(0,-60);v['rotation']=3
        else:p=(20+len(free)*12,-80);free.append(len(vertices))
        vertices.append(v);positions.append(p)
    HeaderRouter.side=side
    r=HeaderRouter(graph,8,10000,(vertices,positions,{}));cells=r.route()
    hm=dict(inputs=r.inputs,outputs=r.outputs,memories=[],cells=len(cells))
    return cells,hm

def connector_check(template,meta):
    side=meta['side']
    out={tuple(es[0]['contact']):name for name,es in meta['outputs'].items()}
    bridges=set(map(tuple,meta.get('diagonal_bridges',[])))
    for p,c in template.items():
        for q in destinations(p,c):
            if not (0<=q[0]<side and 0<=q[1]<side):
                assert p in out or p in bridges,('stray crossing',p,q)
    for first,second,dx,dy in (('E','W',side,0),('S','N',0,side),('W','E',-side,0),('N','S',0,-side)):
        for name,es in meta['outputs'].items():
            if not name.startswith(first+':'):continue
            e=es[0];key=second+':'+name.split(':')[1]
            contact=meta['inputs'][key][0]['contact']
            assert e['fixture']==[contact[0]+dx,contact[1]+dy],('incompatible',name,key)
    if meta.get('diagonal_contacts'):check_channels(template,meta)
    return True

def build_board(size=10,max_save_bytes=None,cell_stem='cell',stem=None,timer_mode='counter'):
    stem=stem or f'minesweeper-{size}x{size}'
    tile=read_map(BUILD/(cell_stem+'.save.txt'));meta=json.loads((BUILD/(cell_stem+'.layout.json')).read_text())
    connector_check(tile,meta);side=meta['side'];cells={};tiles=[];memories=[]
    for y in range(size):
        for x in range(size):
            dx,dy=x*side,y*side
            cells.update({(p[0]+dx,p[1]+dy):c for p,c in tile.items()})
            tiles.append(dict(origin=[dx,dy]))
            memories.extend([[p[0]+dx,p[1]+dy] for p in meta['memories']])
    hc,hm=header(meta)
    assert not set(hc)&set(cells)
    cells.update(hc)
    status=add_status(cells,hm)
    bound=acyclic_bound_effective(cells,memories)
    # Header/timer interfaces are all outside the cell frame. The timers send
    # monotone levels; each tile produces its own exact one-tick capture pulse.
    started=hm['outputs']['started'][0]
    start=tuple(started['fixture'])
    cells[start]=Cell(1,3)
    sockets={}
    for name in ('choose','sample','ready'):
        e=hm['inputs'][name+'Clock'][0];p=tuple(e['fixture']);cells[p]=Cell(1,1);sockets[name]=list(p)
    boardmeta=dict(schema=2,size=size,side=side,tiles=tiles,cell=meta,header=hm,status=status,memories=memories,
        timer_input=list(start),timing_sockets=sockets,logic_settle_bound=bound,
        identical_tiles=True,connection_wires_added=0,cell_stem=cell_stem,profile='GraphDLC-01232bd',verified_against_current_game=False)
    if timer_mode=='counter':
        from preparation import add_compact_timer
        graph=json.loads((BUILD/(cell_stem+'.logic.json')).read_text())
        add_compact_timer(cells,boardmeta,graph)
    elif timer_mode=='legacy':add_level_timer(cells,boardmeta)
    else:raise ValueError('Unknown timer mode')
    boardmeta.update(cells=len(cells),bounds=bounds_of(cells),map_hash=map_hash(cells))
    (BUILD/stem).parent.mkdir(parents=True,exist_ok=True)
    boardmeta.update(write_map(BUILD,stem,cells,max_save_bytes))
    write_json(BUILD/(stem+'.layout.json'),boardmeta)
    print(f'Snap board {size}x{size}: {len(cells)} arrows, {bound} preparation bound',flush=True)
    return cells,boardmeta

def acyclic_bound_effective(cells,memories):
    from timing import propagation_bound
    return propagation_bound(cells,memories)

def add_level_timer(cells,meta):
    bound=meta['logic_settle_bound'];wait=3*bound
    width=300;rows=math.ceil(wait/(2*(width-1)));height=rows*3+20
    left=-width-70;top=-110-3*height
    timer={};outs=defaultdict(set)
    def line(a,b):
        assert a[0]==b[0] or a[1]==b[1]
        dx=0 if a[0]==b[0] else 1 if b[0]>a[0] else -1
        dy=0 if a[1]==b[1] else 1 if b[1]>a[1] else -1
        while a!=b:
            bnext=a[0]+dx,a[1]+dy;outs[a].add(bnext);a=bnext
    start=tuple(meta['timer_input'])
    # Enter above the first bank, avoiding its counter-directed row.
    line(start,(left-40,start[1]));line((left-40,start[1]),(left-40,top));line((left-40,top),(left,top))
    current=(left,top);taps={}
    for bank,name in enumerate(('choose','sample','ready')):
        banktop=top+bank*height
        if bank:line(current,(left-20,banktop));line((left-20,banktop),(left,banktop));current=(left,banktop)
        for row in range(rows):
            dx=1 if row%2==0 else -1;end=(left+width-1 if dx>0 else left,banktop+row*3)
            while current!=end:
                q=current[0]+dx,current[1];outs[current].add(q);timer[current]=Cell(4,1 if dx>0 else 3);current=q
            if row+1<rows:
                q=current[0],current[1]+3;line(current,q);current=q
        q=current[0],current[1]+5;line(current,q);current=q
        tap=left-20,current[1];line(current,tap);current=tap
        if bank<2:
            # Down continues into the next bank; left exposes the same level.
            source=(tap[0]-1,tap[1]);outs[tap].add(source)
        else:
            timer[tap]=Cell(1,3);source=(tap[0]-1,tap[1])
        taps[name]=source
    for p,qs in outs.items():
        if p not in timer:
            timer[p]=wire_cell(p,qs);assert timer[p] is not None,(p,qs)
    for p,c in timer.items():
        assert p not in cells or p==start,('clock collision',p)
        cells[p]=c
    # Only three leads require routing, and they are entirely outside the field.
    w=Wiring(cells)
    w.max_cells=2_000_000
    for name,source in taps.items():
        p=tuple(meta['timing_sockets'][name]);fixture=(p[0]-1,p[1])
        w.connection('clock:'+name,source,[(fixture,p)])
    cells.clear();cells.update(w.route_all())
    meta.update(phase_wait_ticks=rows*(width-1)*2,timer_delay_cells=3*rows*(width-1),
                full_settle_bound=acyclic_bound_effective(cells,meta['memories']))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=10)
    p.add_argument('--max-save-size',type=parse_save_size,default=None,help='Опциональный размер .save.txt: 3MB, 3MiB или байты; по умолчанию без лимита')
    p.add_argument('--timer-mode',choices=('counter','legacy'),default='counter')
    a=p.parse_args()
    try:build_board(a.size,a.max_save_size,timer_mode=a.timer_mode)
    except SaveSizeError as ex:p.exit(2,str(ex)+'\n')
