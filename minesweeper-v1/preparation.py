"""Stage-specific preparation timing using the shared physical analyzer."""
from snap import *
from timing import causal_depths,level_arrivals,propagation_bound
from native_macros import level_timer,timer_latency_bounds
from external_routing import Wiring


def stage_bounds(cells,meta,graph):
    tile=read_map(BUILD/(meta.get('cell_stem','cell')+'.save.txt'));m=meta['cell']
    pos={v['net']:tuple(v['at']) for v in m['gate_positions']};by={n['output']:n for n in graph['nodes']}
    move=lambda p,o:(p[0]+o[0],p[1]+o[1])
    origins=[t['origin'] for t in meta['tiles']];memory=set(map(tuple,meta['memories']))
    sets={name:[move(pos['phase:'+name],o) for o in origins] for name in ('choose','sample','ready')}
    clocks={name:tuple(meta['header']['inputs'][name+'Clock'][0]['contact']) for name in sets}
    arrival={name:level_arrivals(cells,{clocks[name]:0},memory-set(sets[name])) for name in sets}
    # Locate semantic dependencies, rather than fixed anonymous gate IDs.
    chosen=by['selected'];pending=list(chosen['inputs']);inverters=[];seen=set()
    while pending:
        net=pending.pop()
        if net in seen:continue
        seen.add(net);node=by.get(net)
        if not node:continue
        if node['op']=='NOT':inverters.append(node)
        elif node['op'] not in ('SET','TOGGLE'):pending.extend(node['inputs'])
    previous=next(n['output'] for n in inverters if n['output'] not in ('edge_delay:choose',) and n['inputs']!=['busy'])
    permitted=next(by[n['inputs'][0]] for n in graph['nodes'] if n['op']=='RANDOM' and by[n['inputs'][0]]['op']=='AND')
    protected=next(net for net in permitted['inputs'] if by[net]['op']=='NOT')
    requests=[move(pos['request'],o) for o in origins]
    depth=causal_depths(cells,memory,requests)
    election=max(depth[move(pos[previous],o)] or 0 for o in origins)
    busy=0 if graph.get('_serial_control') else propagation_bound(tile,set(map(tuple,m['memories']))-{pos['busy']},
        sources=[e[0]['contact'] for n,e in m['inputs'].items() if n.endswith(':busy')],
        sinks=[e[0]['contact'] for n,e in m['outputs'].items() if n.endswith(':busy')],margin=0)
    busy_flood=2*(meta['size']-1)*busy
    if graph.get('_serial_control') and 'phase:busy' in pos:
        end=m['outputs']['E:prefixReq'][0]['contact']
        busy_depth=causal_depths(cells,memory,[move(end,origins[-1])])
        started=tuple(meta['header']['inputs']['busy'][0]['contact'])
        busy_flood=max(0,max(busy_depth[move(pos['phase:busy'],o)] for o in origins)-busy_depth[started])
    choose=election+busy_flood+256
    depth=causal_depths(cells,memory-{move(pos['selected'],o) for o in origins},
        source_times={p:arrival['choose'][p] for p in sets['choose']})
    sample=max(depth[move(pos[protected],o)]-arrival['sample'][move(pos['phase:sample'],o)] for o in origins)+256
    depth=causal_depths(cells,memory-{move(pos['mine'],o) for o in origins},
        source_times={p:arrival['sample'][p] for p in sets['sample']})
    ready_sinks=m['count_roots']+m.get('decoder_level_contacts',[])+[es[0]['contact'] for name,es in m['inputs'].items() if name.startswith('decoder:')]
    ready=max(depth[move(p,o)]-arrival['ready'][move(pos['phase:ready'],o)]
        for o in origins for p in ready_sinks if depth[move(p,o)] is not None)+256
    return dict(choose=choose,sample=sample,ready=ready,election=election,busy_hop=busy,
        busy_flood=busy_flood,margin=256,contract='monotone header levels, one generation, verified graph')


def add_compact_timer(cells,meta,graph):
    bounds=stage_bounds(cells,meta,graph)
    macros={};exponents={};boundaries=[]
    for i,name in enumerate(('choose','sample','ready')):
        exponent=max(0,math.ceil(math.log2(max(1,bounds[name])/8)))
        macro=level_timer(exponent).moved(-120,-100-i*24)
        assert not set(cells)&set(macro.cells)
        cells.update(macro.cells);macros[name]=macro;exponents[name]=exponent
        boundaries.extend(macro.gates.values());boundaries.append((-120,-100-i*24))
    w=Wiring(cells);w.max_cells=2_000_000
    start=tuple(meta['timer_input']);source=(start[0]-1,start[1])
    first=macros['choose'].inputs['start'];fixture=(first[0],first[1]+1)
    w.connection('timer:start',source,[(fixture,first)])
    names=['choose','sample','ready']
    for i,name in enumerate(names):
        p=tuple(meta['timing_sockets'][name]);targets=[((p[0]-1,p[1]),p)]
        if i<2:
            entry=macros[names[i+1]].inputs['start'];targets.append(((entry[0],entry[1]+1),entry))
        w.connection('timer:'+name,macros[name].outputs['done'],targets)
    cells.clear();cells.update(w.route_all())
    cuts=list(map(tuple,meta['memories']))+boundaries
    leads={n:propagation_bound(cells,cuts,sources=[macros[n].outputs['done']],sinks=[meta['timing_sockets'][n]],margin=0)-1 for n in names}
    guaranteed={}
    for i,name in enumerate(names[1:],1):
        previous=names[i-1];entry=macros[name].inputs['start'];fixture=(entry[0],entry[1]+1)
        link=propagation_bound(cells,cuts,sources=[macros[previous].outputs['done']],sinks=[fixture],margin=0)-1
        gap=link+timer_latency_bounds(exponents[name])['min']+leads[name]-leads[previous]
        assert gap>=bounds[name],('unsafe stage gap',name,gap,bounds[name])
        guaranteed[name]=gap
    meta.update(timer_mode='counter',stage_timing=bounds,timer_exponents=exponents,
        timer_cells=sum(len(m.cells) for m in macros.values()),timer_delay_cells=0,
        phase_wait_ticks=max(8*(2**k) for k in exponents.values()),
        phase_waits={n:8*(2**k) for n,k in exponents.items()},
        timing_boundaries=[list(p) for p in boundaries],clock_lead_ticks=leads,
        guaranteed_stage_gaps=guaranteed,
        full_settle_bound=propagation_bound(cells,cuts),
        preparation_contract_verified=False)
