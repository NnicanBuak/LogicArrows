"""Try shorter placement of the horizontal request path with shared routing."""
from collections import deque
from snap import *
from incremental_tile import recompile
from snap_board import connector_check


def request_distance(cells,meta):
    start=tuple(meta['inputs']['W:prefixReq'][0]['contact'])
    target=tuple(meta['outputs']['E:prefixReq'][0]['contact'])
    pending=deque([(start,0)]);seen={start}
    while pending:
        p,d=pending.popleft()
        if p==target:return d
        for q in destinations(p,cells[p]):
            if q in cells and q not in seen and p not in set(destinations(q,cells[q])):
                seen.add(q);pending.append((q,d+1))
    raise ValueError('Request path is disconnected')


def build(source='experiments/pruned-control-96/cell',stem='releases/optimized-control-96/cell'):
    original=read_map(BUILD/(source+'.save.txt'))
    meta=json.loads((BUILD/(source+'.layout.json')).read_text());graph=json.loads((BUILD/(source+'.logic.json')).read_text())
    nodes={n['output']:n for n in graph['nodes']}
    forward=nodes[graph['outputs']['E:prefixReq'][0]['net']]['inputs'][0]
    previous=next(n for n in nodes[forward]['inputs'] if n!='request')
    owners={tuple(v['at']):v['net'] for v in meta['wire_owners']}
    positions={v['net']:tuple(v['at']) for v in meta['gate_positions']}
    changed={forward,previous}|set(nodes[forward]['inputs'])|set(nodes[previous]['inputs'])
    fixed={tuple(v['at']) for v in meta['gate_positions']}
    a,b,c,d=meta['panel_bounds']
    def slot(net,target,rotation):
        old=positions[net]
        reverse=[q for q,arrow in original.items() if old in destinations(q,arrow) and q not in destinations(old,original[old])]
        offsets=[(q[0]-old[0],q[1]-old[1]) for q in reverse]
        candidates=[]
        for y in range(target[1]-8,target[1]+9):
            for x in range(target[0]-10,target[0]+11):
                p=(x,y);points={p}|{(x+dx,y+dy) for dx,dy in offsets}|set(destinations(p,Cell(original[old].type,rotation)))
                if any(q in fixed-{old} or (a<=q[0]<=c and b<=q[1]<=d) for q in points):continue
                if any(q in original and owners.get(q) not in changed for q in points):continue
                candidates.append(p)
        if not candidates:raise ValueError('No free request gate slot')
        return min(candidates,key=lambda p:abs(p[0]-target[0])+abs(p[1]-target[1]))
    old_distance=request_distance(original,meta)
    best=(len(original),old_distance,original,meta);attempts=[]
    scale=meta['side']/96
    target=lambda x,y:(round(x*scale),round(y*scale))
    scenarios=[{}, {previous:(target(24,34),1)},
               {previous:(target(28,34),1),forward:(target(72,34),0)}]
    for scenario in scenarios:
        moves={}
        try:
            moves={net:slot(net,p,rotation) for net,(p,rotation) in scenario.items()}
            cells,newmeta=recompile(graph,graph,original,meta,moves=moves,rotations={forward:0})
            connector_check(cells,newmeta)
            distance=request_distance(cells,newmeta)
            attempts.append(dict(moves={n:list(p) for n,p in moves.items()},arrows=len(cells),request_ticks=distance))
            if (len(cells),distance)<best[:2] and distance<=old_distance:best=(len(cells),distance,cells,newmeta)
            print('Request placement candidate:',len(cells),'arrows;',distance,'ticks',flush=True)
        except ValueError as ex:
            attempts.append(dict(targets={n:list(v[0]) for n,v in scenario.items()},failed=str(ex)))
            print('Request placement rejected:',str(ex),flush=True)
    cells,newmeta=best[2:]
    (BUILD/stem).parent.mkdir(parents=True,exist_ok=True)
    newmeta.update(write_map(BUILD,stem,cells,None))
    write_json(BUILD/(stem+'.layout.json'),newmeta);write_json(BUILD/(stem+'.logic.json'),graph)
    write_json(BUILD/(stem+'.routing.json'),dict(before=len(original),after=best[0],
        before_request_ticks=old_distance,after_request_ticks=best[1],attempts=attempts))
    return cells,newmeta


if __name__=='__main__':build()
