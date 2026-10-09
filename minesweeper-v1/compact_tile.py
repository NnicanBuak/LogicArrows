"""Compact physical tile: aligned decoder lanes and prewired local display rail.

This is a separate builder so concurrent UI changes and verified exports remain
reviewable. Game logic is imported from snap.py; local placement is independent.
"""
from snap import *
import hashlib
from copy import deepcopy
from snap import graph_for_tile as shared_graph_for_tile
from compact_panel import make_panel

def graph_for_tile(*args,**kwargs):
    graph=deepcopy(shared_graph_for_tile(*args,**kwargs))
    graph['inputs']={n:e for n,e in graph['inputs'].items() if not n.startswith('decoder:')}
    graph['outputs']={n:e for n,e in graph['outputs'].items() if not n.startswith('display:')}
    graph['nodes']=[n for n in graph['nodes'] if not n['output'].startswith(
        ('port:display:','segment_pulse:','segment_enable:','segment_delay:'))]
    # Shared graph optimization already relays monotone controller phases.
    net='port:panel_show'
    graph['nodes'].append(dict(id=net,op='BUF',inputs=['display_show:west'],output=net,scope='display/local'))
    graph['outputs']['panel_show']=[dict(index=0,net=net)]
    graph.pop('_segment_guards',None)
    return graph


class CompactRouter(FrameRouter):
    def __init__(self,*args,**kwargs):
        try:super().__init__(*args,**kwargs)
        except ValueError as error:
            if 'контактов' in str(error):
                name=str(error).split()[-1]
                p=next((p for p,n in self.gates.items() if n['id']==name),None)
                if p:
                    neighborhood={str((x,y)):dict(owner=self.owners.get((x,y)),
                        reserved=(x,y) in self.reserved,outs=list(self.outs.get((x,y),())))
                        for x in range(p[0]-1,p[0]+2) for y in range(p[1]-2,p[1]+3)}
                    print('Pin diagnostic:',name,p,neighborhood,flush=True)
            raise
    def add(self,key,owner,cell=None):
        if key in self.cells:
            raise ValueError(f'Occupied {key}: {owner} conflicts with {self.owners[key]}')
        return super().add(key,owner,cell)

def compact_geometry(side,name,size,output,diagonal_contacts=False,aggregate_neighbors=False):
    center=size//2;pitch=3
    names=face_names(side,output,diagonal_contacts,aggregate_neighbors)
    if side in 'WE':
        a=(side=='W')!=output
        origin=center-(len(face_names('W',False,diagonal_contacts,aggregate_neighbors))*pitch)//2
        p=(0 if side=='W' else size-1,origin+pitch*names.index(name)+(0 if a else 1))
        r=(3 if side=='W' else 1) if output else (1 if side=='W' else 3)
    else:
        a=(side=='N')!=output
        p=(center-10+pitch*names.index(name)+(0 if a else 1),0 if side=='N' else size-1)
        r=(0 if side=='N' else 2) if output else (2 if side=='N' else 0)
    dx,dy=((0,-1),(1,0),(0,1),(-1,0))[r]
    f=(p[0]+dx,p[1]+dy) if output else (p[0]-dx,p[1]-dy)
    return p,r,f

def place_compact_tile(size=112,seed=67,strategy='core_io',warm_start=None,structured=True,packed_counters=False,compact_or=False,or_inputs=None,orient_gates=False,route_order='fanout',logic_decoder=False,block_zones=False,tight_panel=False,corner_decoder=False,diagonal_contacts=False,aggregate_neighbors=False):
    if aggregate_neighbors:diagonal_contacts=False
    corner_decoder=False
    graph=graph_for_tile(structured,compact_or,or_inputs,logic_decoder,diagonal_contacts,aggregate_neighbors);center=size//2
    cavity_radius=12
    gate_pitch=4 if packed_counters else 3
    panel_origin=(center-13,min(center-10,size-46))
    panel=make_panel(True).moved(*panel_origin)
    display_origin=(panel_origin[0]-6,panel_origin[1])
    decoder_origin=(display_origin[0],panel_origin[1]+22)
    mine_origin=(panel_origin[0]+19,panel_origin[1]+3)
    mine_pixels={p:panel.cells[p] for p in panel.mine_pixels}
    button_y=panel_origin[1]+4
    cavity_bounds=(center-15,panel_origin[1]-2,center+15,panel_origin[1]+14)
    native=dict(panel.cells);owners={p:'native:panel' for p in native}
    bridges={};decoder_raw=[]
    nodes=graph['nodes'];by_net={n['output']:n for n in nodes}
    input_nets={e['net'] for es in graph['inputs'].values() for e in es}
    vertices=[];positions=[];movable=[]
    for name,es in graph['inputs'].items():
        if ':' in name and name.split(':')[0] in 'WENS' and len(name.split(':')[0])==1:
            side,n=name.split(':');p,rot,fixture=compact_geometry(side,n,size,False,diagonal_contacts,aggregate_neighbors)
        elif name.startswith('DG:'):
            key=name[3:];p,rot,fixture,_=diagonal_contact(key[:2],key[2:],size,False)
        elif name.startswith('button'):
            p=panel.outputs['click'];rot=3;fixture=panel.buttons[-5]
        else:
            p=decoder_raw[int(name.split(':')[1])];rot=1;fixture=(-1000,-1000-int(name.split(':')[1]))
        vertices.append(dict(kind='input',net=es[0]['net'],rotation=rot,fixture=fixture));positions.append(p)
    for constant in ('const0','const1'):
        if any(constant in n['inputs'] for n in nodes):
            movable.append(len(vertices));vertices.append(dict(kind='constant',net=constant));positions.append(None)
    for node in nodes:
        net=node['output'];v=dict(kind='gate',node=node,rotation=1)
        if packed_counters and node['op']=='OR':v['flexible_output']=True
        if net.startswith('port:'):
            name=net[5:]
            if name.split(':')[0] in ('W','E','N','S'):
                side,key=name.split(':');p,rot,fixture=compact_geometry(side,key,size,True,diagonal_contacts,aggregate_neighbors)
            elif name.startswith('DG:'):
                key=name[3:];p,rot,fixture,pin=diagonal_contact(key[:2],key[2:],size,True)
                v['cell_type']=11;v['pins']=[pin]
            else:
                label='bcd:'+name.split(':')[1] if name.startswith('decoder_bcd:') else 'show' if name=='panel_show' else 'mine' if name=='mine_indicator' else None
                if label is None:raise ValueError(name)
                p=panel.input_fixtures[label];rot=panel.input_rotations[label]
                # Keep all local controls outside the native macro itself.
            v['rotation']=rot
        else:p=None;movable.append(len(vertices))
        vertices.append(v);positions.append(p)
    # XOR and carry gates of an adder consume identical signals. Keep them
    # as one physical pair with three shared branch pins instead of routing
    # every input twice to independently placed gates.
    pairs={}
    if packed_counters:
        buckets=defaultdict(dict)
        for i,v in enumerate(vertices):
            node=v.get('node',{})
            if node.get('scope','').startswith('count/'):
                buckets[tuple(sorted(node['inputs']))][node['op']]=i
        for args,ops in buckets.items():
            carry='MAJ' if len(args)==3 else 'AND'
            if 'XOR' not in ops or carry not in ops:continue
            a,b=ops['XOR'],ops[carry]
            pairs[a]=b;movable.remove(b)
            vertices[b]['node']=dict(vertices[b]['node'],inputs=vertices[a]['node']['inputs'][:])
    # Placement uses the compiler's net router with a fixed square contract.
    # No compactor may move interface ports or the central user controls.
    # Sample slots from all four sides, not just the top strip.
    def slot_clear(p):
        x,y=p
        footprint={(x+dx,y+dy) for dx in (-1,0,1) for dy in range(-2,4)}
        return not footprint&(set(native)|panel.keepout) and all(
            abs(x-q[0])>3 or abs(y-q[1])>3 for q in positions if q is not None)
    allslots=[(x,y) for y in range(6,size-5,gate_pitch) for x in range(6,size-5,gate_pitch)
              if slot_clear((x,y))]
    if len(allslots)<len(movable):
        raise ValueError(f'Placement grid {size}x{size}: {len(allslots)} free slots for {len(movable)} movable gates; a denser placement is required')
    rng=random.Random(seed);slots=rng.sample(allslots,len(movable))
    if warm_start:
        warm=json.loads(Path(warm_start).read_text());available=set(allslots);slots=[]
        for i in movable:
            v=vertices[i];name=v.get('net',v.get('node',{}).get('output'))
            x,y=warm['positions'][name];target=(x*size/warm['side'],y*size/warm['side'])
            chosen=min(available,key=lambda p:(abs(p[0]-target[0])+abs(p[1]-target[1]),p))
            slots.append(chosen);available.remove(chosen)
    for i,p in zip(movable,slots):positions[i]=p
    def sync_pair(i):
        if i in pairs:
            x,y=positions[i];positions[pairs[i]]=(x,y+1)
    for a in pairs:sync_pair(a)
    # Empty frame slots participate in placement: a gate can move closer to
    # its signals instead of only exchanging places with another gate.
    real_movable=movable[:]
    vacant=[p for p in allslots if p not in set(slots)] if size<128 else []
    movable+=list(range(len(positions),len(positions)+len(vacant)))
    positions+=vacant
    sources={v.get('net',v.get('node',{}).get('output')):i for i,v in enumerate(vertices)}
    connections=[];incident=defaultdict(set)
    for i,v in enumerate(vertices):
        for net in v.get('node',{}).get('inputs',[]):
            a=sources[net];k=len(connections);connections.append((a,i));incident[a].add(k);incident[i].add(k)
    def cost(k):
        a,b=connections[k];p,q=positions[a],positions[b];return abs(p[0]-q[0])+abs(p[1]-q[1])
    zones={'count/west':(8,8,center-16,center-16),
           'count/east':(center+16,8,size-8,center-16),
           'count/vertical':(8,center-12,center-16,center+12),
           'count/merge':(8,center+14,center-24,size-8)}
    if logic_decoder:zones['display/decoder']=(center-12,center+14,center+12,size-8)
    if corner_decoder:zones['count/merge']=(center-12,center+14,center+12,size-8)
    if block_zones:
        zones.update(control=(center-12,8,center+12,center-16),
                     game=(8,center-12,center-16,center+12),
                     scan=(center+16,center+14,size-8,size-8))
    # Old count/merge bounds collapse to a single column at side=64.
    # Let connected macro inputs determine location instead of that old zone.
    zones={}
    def zone_cost(i):
        scope=vertices[i].get('node',{}).get('scope') if i<len(vertices) else None
        if scope not in zones:return 0
        x,y=positions[i];a,b,c,d=zones[scope]
        return 4*(max(a-x,0,x-c)+max(b-y,0,y-d))
    total=sum(cost(k) for k in range(len(connections)))+sum(zone_cost(i) for i in real_movable+list(pairs.values()));best=positions[:];score=total
    for step in range(65000):
        if vacant:a=rng.choice(real_movable);b=rng.choice(movable)
        else:a,b=rng.sample(movable,2)
        moved={a,b}|{pairs[k] for k in (a,b) if k in pairs}
        changed=set().union(*(incident[k] for k in moved));before=sum(cost(k) for k in changed)+sum(zone_cost(k) for k in moved)
        positions[a],positions[b]=positions[b],positions[a];sync_pair(a);sync_pair(b)
        delta=sum(cost(k) for k in changed)+sum(zone_cost(k) for k in moved)-before
        if delta<=0 or rng.random()<math.exp(-delta/(0.2+12*(1-step/65000)**3)):
            total+=delta
            if total<score:best=positions[:];score=total
        else:positions[a],positions[b]=positions[b],positions[a];sync_pair(a);sync_pair(b)
    positions=best
    for a,b in pairs.items():
        x,y=positions[a];args=vertices[a]['node']['inputs']
        pins=[(x,y-1),(x,y+2)]+([(x-1,y+1)] if len(args)==3 else [])
        vertices[a]['pins']=pins;vertices[b]['pins']=pins
    for delayed,edge in graph['_edges']:
        i=sources[edge];j=sources[delayed];x,y=positions[i];positions[j]=(x-1,y)
        vertices[j]['pins']=[(x-1,y-1)];vertices[i]['pins']=[(x-1,y-1),(x-1,y)]
    if orient_gates:
        consumers=defaultdict(list)
        probe_keepout=set()
        if aggregate_neighbors:
            for v,p in zip(vertices,positions):
                if v.get('node',{}).get('op') in ('SET','TOGGLE'):
                    probe_keepout.update(((p[0],p[1]+1),(p[0],p[1]+2)))
        for v,p in zip(vertices,positions):
            for net in v.get('node',{}).get('inputs',[]):consumers[net].append(p)
        for i in real_movable:
            v=vertices[i];node=v.get('node',{})
            if not node or 'pins' in v or node['op'] in ('SET','TOGGLE'):continue
            if node['op'] in ('OR','BUF'):
                v['flexible_output']=True
            if len(node['inputs'])>3:continue
            x,y=positions[i];choices=[]
            for rot,(dx,dy) in enumerate(((0,-1),(1,0),(0,1),(-1,0))):
                pins=[(x-dx,y-dy),(x+dy,y-dx),(x-dy,y+dx)]
                out=(x+dx,y+dy)
                for ps in permutations(pins,len(node['inputs'])):
                    if aggregate_neighbors and (out in probe_keepout or set(ps)&probe_keepout):continue
                    score=sum(abs(positions[sources[net]][0]-p[0])+abs(positions[sources[net]][1]-p[1]) for net,p in zip(node['inputs'],ps))
                    score+=sum(abs(out[0]-p[0])+abs(out[1]-p[1]) for p in consumers[node['output']])
                    choices.append((score,rot,ps))
            if not choices:raise ValueError(f"No gate orientation avoids memory probes: {node['output']} at {(x,y)}")
            _,v['rotation'],v['pins']=min(choices)
    for v,p in zip(vertices,positions):
        if v.get('node',{}).get('op')=='OR' and len(v['node']['inputs'])==4:
            x,y=p;v['flexible_output']=True
            v['pins']=[(x-1,y),(x,y-1),(x,y+1),(x+1,y)]
        if v.get('node',{}).get('op')=='SET':v['pins']=[(p[0]-1,p[1]),(p[0],p[1]-1)]
        if v.get('node',{}).get('op')=='TOGGLE':v['pins']=[(p[0]-1,p[1])]
    CompactRouter.side=size
    CompactRouter.routing_strategy=strategy
    CompactRouter.routing_order=route_order
    router=CompactRouter(graph,gate_pitch,15000,(vertices,positions,{}))
    router.native_links=set();router.native_initial=dict(native)
    for p,node in router.gates.items():
        if node['op'] in ('SET','TOGGLE'):
            router.reserved.update({(p[0],p[1]+1),(p[0],p[1]+2)})
    router.reserved.update(panel.keepout-set(router.cells))
    # Freeze untouched imported decoder / display cells and approve only the
    # interfaces that were cut at rows 13/14 and 18/19.
    nativepoints=set(native)
    for p,c in native.items():
        router.reserved.discard(p);router.add(p,owners[p],c)
    for p,c in native.items():
        for q in destinations(p,c):
            if q in nativepoints:router.native_links.add((p,q))
            elif q==panel.outputs['click']:router.native_links.add((p,q))
            else:router.reserved.add(q)
    for name,es in router.outputs.items():
        e=es[0];p=tuple(e['contact']);q=tuple(e['fixture'])
        if q in nativepoints:router.native_links.add((p,q))
    for p,n in list(router.gates.items()):
        if n['op']!='SET':continue
        trigger=n['inputs'][0];pins=router.pins[p];corner=(p[0]-1,p[1]-1)
        router.reserved.discard(corner);router.add(corner,trigger);router.outs[corner]=set(pins)
        router.sinks[trigger]=[q for q in router.sinks[trigger] if q not in pins]+[corner]
        if trigger in router.core_sinks:router.core_sinks[trigger].difference_update(pins);router.core_sinks[trigger].add(corner)
    # Protect all boundary cells except named connectors. No wire crosses an
    # unnamed part of the frame; adjacent copies cannot create stray links.
    router.reserved.update({(x,y) for x in range(size) for y in (0,size-1)}-{*router.cells})
    router.reserved.update({(x,y) for y in range(size) for x in (0,size-1)}-{*router.cells})
    assert all(0<=x<size and 0<=y<size for x,y in router.cells)
    router.fixed_cells=set(router.cells);router.fixed_outs={p:set(qs) for p,qs in router.outs.items()}
    print(f'Routing framed module {size}x{size}: {len(nodes)} logic gates',flush=True)
    cells=router.route()
    walls=add_cell_walls(cells,size)
    native_mem=[p for p,c in native.items() if c.type==19]
    memories=[p for p,n in router.gates.items() if n['op'] in ('SET','TOGGLE')]+native_mem
    meta=dict(schema=2,top=graph['top'],side=size,center=[center,center],cavity_radius=cavity_radius,cells=len(cells),map_hash=map_hash(cells),
              placement_seed=seed,routing_strategy=CompactRouter.routing_strategy,
              architecture='structured-packed' if packed_counters else 'structured' if structured else 'flat',
              shared_counter_pairs=len(pairs),
              oriented_gates=orient_gates,
              routing_order=route_order,
              logic_decoder=logic_decoder,
              block_zones=block_zones,
              tight_panel=tight_panel,panel_bounds=list(cavity_bounds),
              corner_decoder=corner_decoder,walls=walls,
              aggregate_neighbors=aggregate_neighbors,
              diagonal_contacts=diagonal_contacts,diagonal_bridges=[list(p) for p in bridges],
              gate_positions=[dict(at=list(p),net=n['output'],scope=n.get('scope','core'),op=n['op']) for p,n in router.gates.items()],
              wire_owners=[dict(at=list(p),net=owner) for p,owner in router.owners.items() if p in cells],
              display_origin=list(display_origin),decoder_origin=list(decoder_origin),
              mine_indicator=dict(origin=list(mine_origin),width=8,height=8,bitmap=MINE_BITMAP,
                                  pixels=[list(p) for p in panel.mine_pixels]),
              button=[list(p) for p in panel.buttons],button_size=5,button_bus=True,
              inputs=router.inputs,outputs=router.outputs,memories=[list(p) for p in memories],
              segment_registers=[list(p) for p in panel.segment_registers],
              states={name:list(next(p for p,n in router.gates.items() if n['output']==net)) for name,net in graph['_states'].items()},
              count_roots=[list(router.roots[net]) for net in graph['_count']],
              profile='GraphDLC-01232bd',verified_against_current_game=False)
    return cells,meta,router

def build_compact(side=72,seed=67,packed=True,or_inputs=3,stem=None,order='fanout'):
    target=BUILD/'experiments'/(stem or f'compact-{side}-{seed}')
    target.mkdir(parents=True,exist_ok=True)
    cells,meta,router=place_compact_tile(side,seed,strategy='all',or_inputs=or_inputs,
        orient_gates=True,route_order=order,tight_panel=True,aggregate_neighbors=True,
        packed_counters=packed)
    graph=graph_for_tile(or_inputs=or_inputs,aggregate_neighbors=True)
    meta.update(architecture='compact-macros',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                logic_source_sha256=hashlib.sha256((HERE/'snap.py').read_bytes()).hexdigest())
    meta.update(write_map(target,'cell',cells))
    write_json(target/'cell.layout.json',meta);write_json(target/'cell.logic.json',graph)
    print(f'Compact tile exported: {side}x{side}, {len(cells)} arrows, {target}',flush=True)
    return target,cells,meta

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--side',type=int,default=72)
    parser.add_argument('--seed',type=int,default=67);parser.add_argument('--or-inputs',type=int,default=3)
    parser.add_argument('--unpacked',action='store_true');parser.add_argument('--stem')
    parser.add_argument('--order',choices=('full','fanout','short','long'),default='fanout')
    args=parser.parse_args();build_compact(args.side,args.seed,not args.unpacked,args.or_inputs,args.stem,args.order)
