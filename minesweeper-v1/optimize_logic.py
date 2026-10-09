"""Remove redundant phase memory under the standard controller contract."""
from snap import *
from incremental_tile import recompile
from netlist_optimization import forward_monotone_latches
from snap_board import connector_check


def build(source='releases/optimized-control-96/cell',stem='experiments/monotone-phases-96/cell'):
    original=read_map(BUILD/(source+'.save.txt'))
    meta=json.loads((BUILD/(source+'.layout.json')).read_text());before=json.loads((BUILD/(source+'.logic.json')).read_text())
    phases=('choose','sample','ready','stop')
    nodes={n['output']:n for n in before['nodes']}
    pending=[]
    for name in phases:
        net='phase:'+name;node=nodes[net]
        if node['op']=='SET':pending.append(net)
        else:assert node['op']=='OR' and set(node['inputs'])=={'W:'+name,'N:'+name},net
    if pending:
        graph=forward_monotone_latches(before,pending,
            levels=[side+':'+n for side in ('W','N') for n in phases])
        cells,newmeta=recompile(before,graph,original,meta)
    else:graph=before;cells=original;newmeta=dict(meta)
    connector_check(cells,newmeta)
    newmeta['monotone_phases']=True
    (BUILD/stem).parent.mkdir(parents=True,exist_ok=True)
    newmeta.update(write_map(BUILD,stem,cells,None))
    write_json(BUILD/(stem+'.layout.json'),newmeta);write_json(BUILD/(stem+'.logic.json'),graph)
    write_json(BUILD/(stem+'.optimization.json'),dict(before=len(original),after=len(cells),
        before_nodes=len(before['nodes']),after_nodes=len(graph['nodes']),removed_phase_memories=len(pending),
        contract=graph['_monotone_relays']['contract']))
    print('Phase relay optimization:',len(original),'->',len(cells),'arrows',flush=True)
    return cells,newmeta


if __name__=='__main__':build()
