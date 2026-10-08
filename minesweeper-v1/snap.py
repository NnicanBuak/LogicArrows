"""Square, mechanically stackable cells: all game logic and buses in a frame.

West/east ports relay north/south neighbor data to provide diagonals without
corner cables. Any copy can occupy any position; no cell stores coordinates.
"""
from collections import defaultdict,deque
import json,math,random
from itertools import permutations
from logic import *
from placement_backend import wire_cell
from arrow_layout import destinations
from mapdata import read_map,write_json,map_hash
from save_limits import write_map,SaveSizeError,parse_save_size
from display import REFERENCE,SEGMENTS,EXPECTED
from frame_routing import CongestionRouting
from borders import add_cell_walls
from diagonal_ports import corner_channels,contact as diagonal_contact
from mine_indicator import indicator as mine_indicator,BITMAP as MINE_BITMAP

BUILD=HERE/'build'
BUTTON_SIZE=5
GATE_TYPES['SET']=18
H_A=('M','Z','S','present','NM','NZ','NS','SM','SZ','SS','prefixReq','prefixLoss','prefixSat','choose','sample','ready','stop','busy')
H_B=('M','Z','S','present','NM','NZ','NS','SM','SZ','SS','rowReq','rowLoss','rowSat','busy')
V_A=('M','Z','S','present','carryReq','carryLoss','carrySat','choose','sample','ready','stop','busy')
V_B=('M','Z','S','present','totalReq','totalLoss','totalSat','busy')
H_AGG_A=('MP','MC','Z','S','present','prefixReq','prefixLoss','prefixSat','choose','sample','ready','stop','busy')
H_AGG_B=('MP','MC','Z','S','present','rowReq','rowLoss','rowSat','busy')
V_AGG_B=tuple(name for name in V_B if name!='totalReq')

def pulse(l,source,label,falling=False):
    delay=l.gate('BUF' if falling else 'NOT',source,name='edge_delay:'+label)
    result=l.gate('XOR' if falling else 'AND',source,delay,name='edge:'+label)
    l.graph.setdefault('_edges',[]).append([delay,result])
    return result

def face_names(side,output=False,diagonal_contacts=False,aggregate_neighbors=False):
    if aggregate_neighbors:
        return (H_AGG_A if (side=='W')!=output else H_AGG_B) if side in 'WE' else (V_A if (side=='N')!=output else V_AGG_B)
    names=(H_A if (side=='W')!=output else H_B) if side in 'WE' else (V_A if (side=='N')!=output else V_B)
    return tuple(n for n in names if not diagonal_contacts or n not in ('NM','NZ','NS','SM','SZ','SS'))

def graph_for_tile(structured=True,compact_or=False,or_inputs=None,logic_decoder=False,diagonal_contacts=False,aggregate_neighbors=False):
    if aggregate_neighbors:diagonal_contacts=False
    l=Logic('minesweeper_snap_cell_v1')
    if compact_or:l.or_arity=3
    if or_inputs is not None:l.or_arity=or_inputs
    faces={side:{n:l.input(side+':'+n) for n in face_names(side,False,diagonal_contacts,aggregate_neighbors)} for side in 'WENS'}
    diagonal={direction:{n:l.input('DG:'+direction+n) for n in ('M','Z','S')}
              for direction in ('NW','NE','SW','SE')} if diagonal_contacts else {}
    w,e,n,s=[faces[k] for k in 'WENS']
    if structured:l.scope='control'
    click=l.input('button0')
    noW=l.inv(w['present']);noN=l.inv(n['present']);noE=l.inv(e['present']);noS=l.inv(s['present'])
    request=l.sticky(l.both(click,l.inv('busy')),'request')
    busy=l.sticky(l.any(request,*[face['busy'] for face in faces.values()]),'busy')
    previousReq=l.any(w['prefixReq'],l.both(noW,n['carryReq']))
    previousLoss=l.any(w['prefixLoss'],l.both(noW,n['carryLoss']))
    previousSat=l.any(w['prefixSat'],
                      l.all(noW,n['present'],n['carrySat']),l.both(noW,noN))
    phase={name:l.sticky(l.any(w[name],n[name]),'phase:'+name) for name in ('choose','sample','ready','stop')}
    choose=pulse(l,phase['choose'],'choose')
    sample=pulse(l,phase['sample'],'sample')
    selected=l.sticky(l.all(request,l.inv(previousReq),choose),'selected')
    # Horizontal S/Z inputs are reductions over the sender's vertical triple.
    # Their union with N/S therefore covers exactly the eight neighbors.
    adjacent=lambda field:[w[field],e[field],n[field],s[field]] if aggregate_neighbors else [diagonal['NW'][field],n[field],diagonal['NE'][field],w[field],e[field],diagonal['SW'][field],s[field],diagonal['SE'][field]] if diagonal_contacts else [w['N'+field],n[field],e['N'+field],w[field],e[field],w['S'+field],s[field],e['S'+field]]
    protected=l.any(selected,*adjacent('S'))
    permitted=l.both(sample,l.inv(protected))
    # Serial random stages preserve the one-tick pulse and give 1/4 without
    # requiring two independently routed pulses to arrive simultaneously.
    mine=l.gate('TOGGLE',l.gate('RANDOM',l.gate('RANDOM',permitted)),name='mine')
    neighbors=None if aggregate_neighbors else adjacent('M')
    def add(a,b):
        out=[];carry=None
        for i in range(max(len(a),len(b))):
            bits=([a[i]] if i<len(a) else [])+([b[i]] if i<len(b) else [])+([carry] if carry else [])
            if len(bits)==1:out.append(bits[0]);carry=None
            else:out.append(l.gate('XOR',*bits));carry=l.gate('MAJ' if len(bits)==3 else 'AND',*bits)
        if carry:out.append(carry)
        return out
    if structured or aggregate_neighbors:
        l.scope='count/west'
        west=[w['MP'],w['MC']] if aggregate_neighbors else [neighbors[i] for i in (0,3,5)]
        if not aggregate_neighbors:west=[l.gate('XOR',*west),l.gate('MAJ',*west)]
        l.scope='count/east'
        east=[e['MP'],e['MC']] if aggregate_neighbors else [neighbors[i] for i in (2,4,7)]
        if not aggregate_neighbors:east=[l.gate('XOR',*east),l.gate('MAJ',*east)]
        l.scope='count/vertical'
        vertical=[l.gate('XOR',n['M'],s['M']),l.both(n['M'],s['M'])]
        if aggregate_neighbors:
            triple=(n['M'],mine,s['M'])
            mine_triple=[l.gate('XOR',*triple),l.gate('MAJ',*triple)]
        l.scope='count/merge'
        count=add(add(west,east),vertical)
        l.scope='game'
    else:
        pairs=[(l.gate('XOR',*neighbors[i:i+2]),l.both(*neighbors[i:i+2])) for i in range(0,8,2)]
        count=add(add(pairs[0],pairs[1]),add(pairs[2],pairs[3]))
    safe=l.inv(mine);zero=l.inv(l.any(*count))
    opened=l.sticky(l.all(phase['ready'],l.inv(phase['stop']),l.any(click,selected,l.both(safe,l.any(*adjacent('Z'))))),'opened')
    cascade=l.all(opened,safe,zero);loss=l.both(opened,mine);sat=l.any(mine,opened)
    own=dict(M=mine,Z=cascade,S=selected,present='const1',busy=busy)
    if structured:l.scope='scan'
    prefix=dict(Req=l.any(request,previousReq),Loss=l.any(loss,previousLoss),Sat=l.both(sat,previousSat))
    row={k:l.any(l.both(noE,value),e['row'+k]) for k,value in prefix.items()}
    # totalReq has no consumer: the header starts from the busy flood, while
    # first-click election needs prefix/row/carry Req, but no northbound total.
    total={k:l.any(l.both(noS,value),s['total'+k]) for k,value in row.items() if not aggregate_neighbors or k!='Req'}
    def out(side,name,net):
        key=side+':'+name
        if net=='const1':
            port='port:'+key;l.gate('NOT',name=port)
            l.graph['outputs'][key]=[dict(index=0,net=port)]
        else:l.output(key,net)
    if structured:l.scope='links'
    horizontal=dict(own)
    if aggregate_neighbors:
        horizontal.pop('M');horizontal.update(MP=mine_triple[0],MC=mine_triple[1])
        for field in ('S','Z'):horizontal[field]=l.any(own[field],n[field],s[field])
    for side in 'WENS':
        for name,net in (horizontal if aggregate_neighbors and side in 'WE' else own).items():out(side,name,net)
    if aggregate_neighbors:pass
    elif diagonal_contacts:
        for direction in diagonal:
            for name in ('M','Z','S'):out('DG',direction+name,own[name])
    else:
        for side in 'WE':
            for vertical,face in (('N',n),('S',s)):
                for name in ('M','Z','S'):out(side,vertical+name,face[name])
    for k in prefix:
        out('E','prefix'+k,prefix[k]);out('W','row'+k,row[k]);out('S','carry'+k,row[k])
        if k in total:out('N','total'+k,total[k])
    for name,net in phase.items():out('E',name,net);out('S',name,net)
    # Reuse the supplied native BCD decoder in the frame. Its raw seven
    # segment truth signals pass through an enable gate and change detector.
    if logic_decoder:
        # Only 0..8 are reachable from eight neighboring mines. Keep the
        # user's visible segment registers, synthesize their truth locally.
        l.scope='display/decoder'
        a,b,c,d=count;na,nb,nc=[l.inv(bit) for bit in (a,b,c)]
        bc=l.gate('XOR',b,c);bna=l.both(b,na);nanc=l.both(na,nc)
        raw=[l.any(d,b,nanc,l.both(c,a)),
             l.any(d,nc,l.inv(l.gate('XOR',a,b))),
             l.any(d,c,nb,a),
             l.any(d,bna,nanc,l.both(a,bc)),
             l.any(d,l.both(na,l.any(b,nc))),
             l.any(d,l.both(na,nb),l.both(c,l.any(na,nb))),
             l.any(d,bc,bna)]
        l.graph['_logic_decoder']=True
    else:raw=[l.input('decoder:'+str(i)) for i in range(7)]
    if structured:
        show={}
        for side in ('west',):
            l.scope='display/'+side
            local_safe=l.gate('NOT',mine,name='display_safe:'+side)
            show[side]=l.gate('AND',opened,local_safe,name='display_show:'+side)
        show['east']=show['west']
        l.graph['_segment_guards']=[]
    else:show=l.both(opened,safe)
    for i,value in enumerate(raw):
        if structured:
            side='west' if i<4 else 'east';l.scope='display/'+side
            enabled=l.gate('AND',show[side],value,name='segment_enable:'+str(i))
            l.graph['_segment_guards'].append(enabled)
        else:enabled=l.both(show,value)
        # Put the transition detector directly on the native display input.
        # Its shared splitter feeds the XOR directly and through one BUF.
        # This keeps both-edge pulses while removing a port buffer and a
        # separately routed pulse wire for each of the seven segments.
        delayed=l.gate('BUF',enabled,name='segment_delay:'+str(i))
        pulse_net=l.gate('XOR',enabled,delayed,name='segment_pulse:'+str(i))
        l.output('display:'+str(i),pulse_net)
    if not logic_decoder:
        for i,value in enumerate(count):l.output('decoder_bcd:'+str(i),value)
    # The already distributed total-loss bus reveals every mine. This is a
    # display override: opening safe cells remains gated by the stop memory.
    mine_revealed=l.both(mine,total['Loss'])
    l.output('mine_indicator',mine_revealed)
    l.graph['_count']=count
    l.graph['_states']=dict(mine=mine,opened=opened,selected=selected,request=request,busy=busy,cascade=cascade,loss=loss)
    if structured:l.graph['_structured']=True
    if aggregate_neighbors:l.graph['_aggregate_neighbors']=True
    return l.graph

def geometry(side,name,size,output,diagonal_contacts=False,aggregate_neighbors=False):
    center=size//2
    pitch=3 if size<=80 else 4 if size<128 else 6
    if side in 'WE':
        # Rightward lanes A: W input / E output. Leftward lanes B: E input / W output.
        names=face_names(side,output,diagonal_contacts,aggregate_neighbors)
        y=center-(len(face_names('W',False,diagonal_contacts,aggregate_neighbors))*pitch)//2+pitch*names.index(name)+(0 if (side=='W')!=output else pitch//2)
        x=0 if side=='W' else size-1
        rotation=(3 if side=='W' else 1) if output else (1 if side=='W' else 3)
    else:
        names=face_names(side,output,diagonal_contacts,aggregate_neighbors)
        x=center-(len(V_A)*pitch)//2+pitch*names.index(name)+(0 if (side=='N')!=output else pitch//2)
        y=0 if side=='N' else size-1
        rotation=(0 if side=='N' else 2) if output else (2 if side=='N' else 0)
    dx,dy=((0,-1),(1,0),(0,1),(-1,0))[rotation]
    fixture=(x+dx,y+dy) if output else (x-dx,y-dy)
    return (x,y),rotation,fixture

class FrameRouter(CongestionRouting,Router):
    def route_allowed(self,p):return 0<=p[0]<self.side and 0<=p[1]<self.side
    def validate(self):
        # Exact wire output sets plus explicit black-box interfaces. Native
        # reference pieces are fixed and may have their own stateful semantics.
        links=edges(self.cells);reverse=defaultdict(list)
        for p,targets in links.items():
            for q in targets:
                reverse[q].append(p)
                if (p,q) in self.native_links:continue
                if q in self.gates:
                    if p not in self.pins[q]:raise ValueError(f'Foreign gate input {p}->{q}')
                elif p in self.gates:
                    if self.owners[q]!=self.gates[p]['output']:raise ValueError(f'Foreign gate output {p}->{q}')
                elif self.owners[p]!=self.owners[q] and self.owners[p]!='constant:'+self.owners[q]:
                    raise ValueError(f'Crossed nets {p}->{q}: {self.owners[p]}, {self.owners[q]}')
        for p,pins in self.pins.items():
            if set(reverse[p])!=set(pins):raise ValueError(f'Broken gate {p}')
            for pin,net in zip(pins,self.gates[p]['inputs']):
                actual=self.gates[pin]['output'] if pin in self.gates else self.owners[pin]
                if actual!=net:raise ValueError(f'Wrong gate signal {pin}->{p}: {actual}, expected {net}')
        for p,c in self.native_initial.items():
            if self.cells[p]!=c:raise ValueError(f'Modified native display {p}')

def place_tile(size=112,seed=67,strategy='core_io',warm_start=None,structured=True,packed_counters=False,compact_or=False,or_inputs=None,orient_gates=False,route_order='fanout',logic_decoder=False,block_zones=False,tight_panel=False,corner_decoder=False,diagonal_contacts=False,aggregate_neighbors=False):
    if aggregate_neighbors:diagonal_contacts=False
    if aggregate_neighbors and size<=72 and not logic_decoder:corner_decoder=True
    graph=graph_for_tile(structured,compact_or,or_inputs,logic_decoder,diagonal_contacts,aggregate_neighbors);center=size//2
    cavity_radius=12 if size<128 else 24 if size<=128 else 32
    cavity_bounds=(center-15,center-12,center+15,center+4) if tight_panel else (center-cavity_radius,center-cavity_radius,center+cavity_radius,center+cavity_radius)
    gate_pitch=4 if aggregate_neighbors else 3 if size<=80 else 4 if size<=128 else 6
    display_origin=(center-19,center-10 if size<128 else center-12)
    mine_origin=(center+6,display_origin[1]+3)
    mine_local,mine_root=mine_indicator()
    mine_pixels={(x+mine_origin[0],y+mine_origin[1]):c for (x,y),c in mine_local.items()}
    mine_root=(mine_root[0]+mine_origin[0],mine_root[1]+mine_origin[1])
    button_y=display_origin[1]+4
    decoder_origin=(8 if corner_decoder else center-13,size-31 if corner_decoder else max(size-27,button_y+5))
    segment_columns=(size-24,size-12) if corner_decoder else (center-20,center+6)
    if aggregate_neighbors and corner_decoder:segment_columns=(6,size-6)
    reference=read_map(REFERENCE)
    native={};owners={};display={};decoder={}
    for (x,y),c in reference.items():
        if y<=13:
            p=(x+display_origin[0],y+display_origin[1]);native[p]=c;owners[p]='native:display';display[(x,y)]=p
        elif y>=19 and not logic_decoder:
            p=(x+decoder_origin[0],y+decoder_origin[1]-19);native[p]=c;owners[p]='native:decoder';decoder[(x,y)]=p
    bridges=corner_channels(size) if diagonal_contacts else {}
    assert not set(mine_pixels)&set(native)
    native.update(mine_pixels);owners.update({p:'native:mine' for p in mine_pixels})
    button_collectors={(center-3,button_y+row):Cell(1,2) for row in range(BUTTON_SIZE)}
    assert not set(button_collectors)&set(native)
    native.update(button_collectors);owners.update({p:'native:button_bus' for p in button_collectors})
    assert not set(bridges)&set(native)
    native.update(bridges);owners.update({p:'native:diagonal' for p in bridges})
    decoder_raw=[(x+decoder_origin[0],decoder_origin[1]-1) for x in range(6,13)]
    bit_contacts=((4,40),(3,40),(1,40),(0,38)) # supplied decoder: weights 1,2,4,8
    nodes=graph['nodes'];by_net={n['output']:n for n in nodes}
    input_nets={e['net'] for es in graph['inputs'].values() for e in es}
    vertices=[];positions=[];movable=[]
    for name,es in graph['inputs'].items():
        if ':' in name and name.split(':')[0] in 'WENS' and len(name.split(':')[0])==1:
            side,n=name.split(':');p,rot,fixture=geometry(side,n,size,False,diagonal_contacts,aggregate_neighbors)
        elif name.startswith('DG:'):
            key=name[3:];p,rot,fixture,_=diagonal_contact(key[:2],key[2:],size,False)
        elif name.startswith('button'):
            p=(center-3,button_y+BUTTON_SIZE);rot=3;fixture=(center-2,button_y+BUTTON_SIZE-1)
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
                side,key=name.split(':');p,rot,fixture=geometry(side,key,size,True,diagonal_contacts,aggregate_neighbors)
            elif name.startswith('DG:'):
                key=name[3:];p,rot,fixture,pin=diagonal_contact(key[:2],key[2:],size,True)
                v['cell_type']=11;v['pins']=[pin]
            elif name.startswith('display:'):
                i=int(name.split(':')[1]);p=(display_origin[0]+6+i,display_origin[1]+15);rot=0
                v['cell_type']=10;v['pins']=[(p[0],p[1]+1)]
            elif name.startswith('decoder_bcd:'):
                i=int(name.split(':')[1]);x,y=bit_contacts[i];contact=decoder[(x,y)]
                p=(contact[0]-1,contact[1]) if i==3 else (contact[0],contact[1]+1);rot=1 if i==3 else 0
            elif name=='mine_indicator':
                p=(mine_root[0],mine_root[1]-2);rot=2
                v['cell_type']=10;v['pins']=[(p[0],p[1]-1)]
            else:raise ValueError(name)
            v['rotation']=rot
        elif net.startswith('segment_delay:'):
            i=int(net.split(':')[1]);p=(display_origin[0]+6+i,display_origin[1]+17)
            v['rotation']=0;v['pins']=[(p[0],p[1]+1)]
        elif net.startswith('segment_pulse:'):
            i=int(net.split(':')[1]);p=(display_origin[0]+6+i,display_origin[1]+16)
            v['rotation']=0;v['pins']=[(p[0],p[1]+2),(p[0],p[1]+1)]
        elif net.startswith('segment_enable:'):
            i=int(net.split(':')[1]);p=(display_origin[0]+6+i,display_origin[1]+20)
            v['rotation']=0;v['pins']=[(p[0],p[1]+2),(p[0],p[1]+1)]
        elif structured and net.startswith(('edge:segment','edge_delay:segment')):
            i=int(net.split(':')[-1].removeprefix('segment'))
            side='west' if i<4 else 'east';j=i if i<4 else i-4
            x=segment_columns[0 if side=='west' else 1]
            y=decoder_origin[1]+2+4*j
            p=(x,y) if net.startswith('segment_enable:') else (x+3,y) if net.startswith('edge_delay:') else (x+4,y)
        elif structured and net.startswith(('display_safe:','display_show:')):
            side=net.split(':')[1];x=segment_columns[0 if side=='west' else 1]
            y=decoder_origin[1]+(18 if side=='west' else 14)
            p=(x-4,y) if net.startswith('display_safe:') else (x,y)
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
    allslots=[(x,y) for y in range(8,size-6,gate_pitch) for x in range(8,size-6,gate_pitch)
           if not (cavity_bounds[0]-2<=x<=cavity_bounds[2]+2 and cavity_bounds[1]-2<=y<=cavity_bounds[3]+2)
           and (logic_decoder or not (decoder_origin[0]-3<=x<=decoder_origin[0]+17 and decoder_origin[1]-3<=y<=size-1))
           and (size>=128 or all(abs(x-p[0])>3 or abs(y-p[1])>3 for p in positions if p is not None))]
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
    FrameRouter.side=size
    FrameRouter.routing_strategy=strategy
    FrameRouter.routing_order=route_order
    router=FrameRouter(graph,gate_pitch,15000,(vertices,positions,{}))
    router.native_links=set();router.native_initial=dict(native)
    for p,node in router.gates.items():
        if node['op'] in ('SET','TOGGLE'):
            router.reserved.update({(p[0],p[1]+1),(p[0],p[1]+2)})
    # Center is a user panel; only short display leads and the common button
    # collectors may enter it. All other routing stays in the surrounding frame.
    cavity={(x,y) for x in range(cavity_bounds[0],cavity_bounds[2]+1) for y in range(cavity_bounds[1],cavity_bounds[3]+1)}
    leads={(x,y) for x in range(display_origin[0]+6,display_origin[0]+13) for y in range(display_origin[1]+15,center+cavity_radius+1)}
    leads|={(center-3,y) for y in range(button_y+BUTTON_SIZE,cavity_bounds[3]+1)}
    leads|={(mine_root[0],y) for y in range(cavity_bounds[1],mine_origin[1]-1)}
    router.reserved.update(cavity-leads-set(native)-set(router.cells))
    mine_box={(mine_origin[0]+x,mine_origin[1]+y) for x in range(8) for y in range(8)}
    router.reserved.update(mine_box-set(mine_pixels))
    # Freeze untouched imported decoder / display cells and approve only the
    # interfaces that were cut at rows 13/14 and 18/19.
    nativepoints=set(native)
    for p,c in native.items():
        router.reserved.discard(p);router.add(p,owners[p],c)
    for p,c in native.items():
        for q in destinations(p,c):
            if q in nativepoints:router.native_links.add((p,q))
            elif q in decoder_raw or q==(center-3,button_y+BUTTON_SIZE):router.native_links.add((p,q))
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
    for row in range(BUTTON_SIZE):
        for col in range(BUTTON_SIZE):
            p=(center-2+col,button_y+row)
            c=Cell(24,3)
            router.reserved.discard(p);router.add(p,'native:button',c)
            router.native_initial[p]=c
            router.native_links.add((p,(p[0]-1,p[1])))
    # Protect all boundary cells except named connectors. No wire crosses an
    # unnamed part of the frame; adjacent copies cannot create stray links.
    router.reserved.update({(x,y) for x in range(size) for y in (0,size-1)}-{*router.cells})
    router.reserved.update({(x,y) for y in range(size) for x in (0,size-1)}-{*router.cells})
    router.fixed_cells=set(router.cells);router.fixed_outs={p:set(qs) for p,qs in router.outs.items()}
    print(f'Routing framed module {size}x{size}: {len(nodes)} logic gates',flush=True)
    cells=router.route()
    walls=add_cell_walls(cells,size)
    native_mem=[p for p,c in native.items() if c.type==19]
    memories=[p for p,n in router.gates.items() if n['op'] in ('SET','TOGGLE')]+native_mem
    meta=dict(schema=2,top=graph['top'],side=size,center=[center,center],cavity_radius=cavity_radius,cells=len(cells),map_hash=map_hash(cells),
              placement_seed=seed,routing_strategy=FrameRouter.routing_strategy,
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
                                  pixels=[list(p) for p in sorted(mine_pixels)]),
              button_size=BUTTON_SIZE,button=[[center-2+col,button_y+row] for row in range(BUTTON_SIZE) for col in range(BUTTON_SIZE)],
              button_collectors=[list(p) for p in button_collectors],
              inputs=router.inputs,outputs=router.outputs,memories=[list(p) for p in memories],
              segment_registers=[list(display[p]) for p in SEGMENTS],
              states={name:list(next(p for p,n in router.gates.items() if n['output']==net)) for name,net in graph['_states'].items()},
              count_roots=[list(router.roots[net]) for net in graph['_count']],
              profile='GraphDLC-01232bd',verified_against_current_game=False)
    return cells,meta,router

def build_tile(sizes=(112,120,128),stem='cell',seeds=(67,31,101,173,17),strategy='core_io',warm_start=None,structured=True,packed_counters=False,compact_or=False,or_inputs=None,orient_gates=False,route_order='fanout',logic_decoder=False,block_zones=False,tight_panel=False,corner_decoder=False,max_save_bytes=None,diagonal_contacts=False,aggregate_neighbors=False):
    errors=[]
    for size in sizes:
        for seed in seeds:
            try:cells,meta,router=place_tile(size,seed,strategy,warm_start,structured,packed_counters,compact_or,or_inputs,orient_gates,route_order,logic_decoder,block_zones,tight_panel,corner_decoder,diagonal_contacts,aggregate_neighbors);break
            except ValueError as ex:errors.append(str(ex));print('Frame retry:',size,seed,ex,flush=True)
        else:continue
        break
    else:raise ValueError(errors)
    meta.update(write_map(BUILD,stem,cells,max_save_bytes));write_json(BUILD/(stem+'.layout.json'),meta)
    write_json(BUILD/(stem+'.logic.json'),graph_for_tile(structured,compact_or,or_inputs,logic_decoder,diagonal_contacts,aggregate_neighbors))
    print('Snap cell built:',len(cells),meta['side'],flush=True)
    return cells,meta

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--side',type=int);p.add_argument('--stem',default='cell')
    p.add_argument('--seed',type=int);p.add_argument('--strategy',choices=('core_io','all'),default='core_io');p.add_argument('--warm-start')
    p.add_argument('--aggregate-neighbors',action='store_true',help='Send vertical triple reductions horizontally; omit diagonal channels and unused totalReq')
    p.add_argument('--diagonal-contacts',action='store_true')
    p.add_argument('--max-save-size',type=parse_save_size,default=None,help='Опциональный размер .save.txt: 3MB, 3MiB или байты; по умолчанию без лимита')
    p.add_argument('--structured',dest='structured',action='store_true',default=True);p.add_argument('--flat',dest='structured',action='store_false');p.add_argument('--packed-counters',action='store_true');p.add_argument('--compact-or',action='store_true');p.add_argument('--or-inputs',type=int,choices=(2,3,4));p.add_argument('--orient-gates',action='store_true');p.add_argument('--route-order',choices=('fanout','short','long','full'),default='fanout');p.add_argument('--logic-decoder',action='store_true');p.add_argument('--block-zones',action='store_true');p.add_argument('--tight-panel',action='store_true');p.add_argument('--corner-decoder',action='store_true');a=p.parse_args()
    try:
        build_tile((a.side,) if a.side else (112,120,128),a.stem,(a.seed,) if a.seed is not None else (67,31,101,173,17),a.strategy,a.warm_start,a.structured,a.packed_counters,a.compact_or,a.or_inputs,a.orient_gates,a.route_order,a.logic_decoder,a.block_zones,a.tight_panel,a.corner_decoder,a.max_save_size,a.diagonal_contacts,a.aggregate_neighbors)
    except SaveSizeError as ex:p.exit(2,str(ex)+'\n')
