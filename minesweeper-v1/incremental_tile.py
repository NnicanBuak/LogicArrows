"""Tile interfaces and native fixtures for the shared incremental router."""
from snap import *
from incremental_routing import changed_nets,restore_wires
from pin_planning import choose_input_contacts


def recompile(before,graph,original,meta,*,moves=None,rotations=None,extra_nets=()):
    moves=moves or {};rotations=rotations or {}
    old_nodes={n['output']:n for n in before['nodes']}
    owners={tuple(v['at']):v['net'] for v in meta['wire_owners']}
    coordinates={v['net']:tuple(v['at']) for v in meta['gate_positions']}
    reverse=defaultdict(list)
    for p,c in original.items():
        for q in destinations(p,c):
            if q in original and p not in destinations(q,original[q]):reverse[q].append(p)
    affected=changed_nets(before,graph)|set(extra_nets)
    sources=dict(coordinates)
    sources.update({e['net']:tuple(meta['inputs'][name][e['index']]['contact'])
                    for name,es in graph['inputs'].items() for e in es})
    active={n['output'] for n in graph['nodes']}
    fixed={coordinates[n] for n in active}
    fixed.update(p for p,c in original.items() if c.type==25 or owners.get(p,'').startswith('native:'))
    fixed.update(tuple(e['contact']) for table in ('inputs','outputs') for es in meta[table].values() for e in es)
    for n in before['nodes']:
        if n['output'] in active and n['op'] in ('SET','TOGGLE'):
            p=coordinates[n['output']];fixed.update(((p[0],p[1]+1),(p[0],p[1]+2)))
    a,b,c,d=meta['panel_bounds']
    fixed.update((x,y) for x in range(a,c+1) for y in range(b,d+1) if (x,y) not in original)
    assigned={}
    for node in graph['nodes']:
        net=node['output'];p=coordinates[net];old=original[p]
        if node['inputs']==old_nodes[net]['inputs'] and net not in moves:
            for q in reverse[p]:assigned[q]=owners[q].removeprefix('gate:')
        flexible=node['op']=='OR' and (node['inputs']!=old_nodes[net]['inputs'] or old.type not in (10,11))
        if not flexible:
            physical=old if node['op'] in ('OR','BUF') else Cell(GATE_TYPES[node['op']],rotations.get(net,old.rotation),old.mirrored)
            for q in destinations(tuple(moves.get(net,p)),physical):assigned[q]=net
    vertices=[];positions=[]
    for name,es in graph['inputs'].items():
        for e in es:
            interface=meta['inputs'][name][e['index']]
            vertices.append(dict(kind='input',net=e['net'],rotation=interface['rotation'],fixture=interface['fixture']))
            positions.append(tuple(interface['contact']))
    for node in graph['nodes']:
        net=node['output'];oldp=coordinates[net];p=tuple(moves.get(net,oldp));old=original[oldp]
        available=list(reverse[oldp]);pins=[]
        for source in old_nodes[net]['inputs']:
            q=next(q for q in available if owners[q] in (source,'gate:'+source))
            pins.append((q[0]+p[0]-oldp[0],q[1]+p[1]-oldp[1]));available.remove(q)
        changed_inputs=node['inputs']!=old_nodes[net]['inputs']
        if changed_inputs:
            preferred={source:pin for source,pin in zip(old_nodes[net]['inputs'],pins)}
            def compatible(q,source):
                if q in fixed:return False
                if assigned.get(q) not in (None,source):return False
                owner=owners.get(q)
                if owner and owner.startswith('gate:'):owner=owner[5:]
                return owner is None or owner in affected or owner==source
            def plan(point):
                exclude=() if node['op']=='OR' else destinations(point,Cell(old.type,rotations.get(net,old.rotation),old.mirrored))
                return choose_input_contacts(node['inputs'],point,sources,compatible,excluded=exclude,preferred=preferred)
            try:pins=plan(p)
            except ValueError:
                candidates=[]
                for y in range(max(3,oldp[1]-6),min(meta['side']-3,oldp[1]+7)):
                    for x in range(max(3,oldp[0]-6),min(meta['side']-3,oldp[0]+7)):
                        q=(x,y);owner=owners.get(q,'').removeprefix('gate:')
                        if q in fixed or (q in original and owner not in affected):continue
                        outgoing=[] if node['op']=='OR' else list(destinations(q,old))
                        if any(t in fixed or (t in original and owners.get(t) not in affected) for t in outgoing):continue
                        try:ps=plan(q)
                        except ValueError:continue
                        score=sum(abs(sources[source][0]-pin[0])+abs(sources[source][1]-pin[1]) for source,pin in zip(node['inputs'],ps))
                        candidates.append((score+abs(x-oldp[0])+abs(y-oldp[1]),q,ps))
                if not candidates:raise
                _,p,pins=min(candidates);fixed.add(p);sources[net]=p
                print('Folded receiver placement:',net,oldp,'->',p,'inputs',len(pins),flush=True)
            for source,q in zip(node['inputs'],pins):assigned[q]=source
        if p!=oldp or net in rotations:
            affected.add(net);affected.update(node['inputs'])
        v=dict(kind='gate',node=node,rotation=rotations.get(net,old.rotation),mirrored=old.mirrored,pins=pins)
        if node['op'] in ('BUF','OR'):
            if changed_inputs and not net.startswith('port:'):v['flexible_output']=True
            elif old.type in (10,11):v['cell_type']=old.type
            elif not net.startswith('port:'):v['flexible_output']=True
        vertices.append(v);positions.append(p)
    FrameRouter.side=meta['side'];FrameRouter.routing_strategy='all';FrameRouter.routing_order='full'
    r=FrameRouter(graph,4,20000,(vertices,positions,{}))
    r.native_initial={p:c for p,c in original.items() if owners.get(p,'').startswith('native:')}
    r.native_links={(p,q) for p,c in r.native_initial.items() for q in destinations(p,c) if q in original}
    for p,c in r.native_initial.items():
        r.reserved.discard(p)
        if p not in r.cells:r.add(p,owners[p],c)
    for es in r.outputs.values():
        for e in es:
            p,q=tuple(e['contact']),tuple(e['fixture'])
            if q in r.native_initial:r.native_links.add((p,q))
    # Preserve the shared one-tick trigger branch of every existing SET.
    for p,n in r.gates.items():
        if n['op']!='SET':continue
        pins=set(r.pins[p]);corner=(p[0]-1,p[1]-1);trigger=n['inputs'][0]
        if corner not in original or owners.get(corner)!=trigger:continue
        if set(destinations(corner,original[corner]))!=pins:continue
        r.reserved.discard(corner)
        if corner not in r.cells:r.add(corner,trigger,original[corner])
        r.outs[corner]=pins
        r.sinks[trigger]=[q for q in r.sinks[trigger] if q not in pins]+[corner]
        if trigger in r.core_sinks:r.core_sinks[trigger].difference_update(pins);r.core_sinks[trigger].add(corner)
    a,b,c,d=meta['panel_bounds']
    r.reserved.update((x,y) for x in range(a,c+1) for y in range(b,d+1) if (x,y) not in original)
    r.reserved.update(p for p,c in original.items() if c.type==25)
    restore_wires(r,original,owners,affected)
    print('Incremental route:',sorted(affected),flush=True)
    cells=r.route();walls=add_cell_walls(cells,meta['side'])
    meta=dict(meta,cells=len(cells),map_hash=map_hash(cells),walls=walls,
        gate_positions=[dict(at=list(p),net=n['output'],scope=n.get('scope','core'),op=n['op']) for p,n in r.gates.items()],
        wire_owners=[dict(at=list(p),net=o) for p,o in r.owners.items() if p in cells],
        incremental_nets=sorted(affected))
    meta['memories']=[list(p) for p,n in r.gates.items() if n['op'] in ('SET','TOGGLE')]
    meta['memories'] += [list(p) for p,c in r.native_initial.items() if c.type==19]
    meta['states']={name:list(next(p for p,n in r.gates.items() if n['output']==net)) for name,net in graph['_states'].items()}
    meta['count_roots']=[list(r.roots[net]) for net in graph['_count']]
    return cells,meta
