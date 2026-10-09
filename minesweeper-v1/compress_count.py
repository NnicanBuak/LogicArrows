"""Bind the cell's partial sums to a generic carry-save count compressor."""
from snap import *
from incremental_tile import recompile
from netlist_optimization import compress_three_counts
from snap_board import connector_check


def build(source='cell',stem='experiments/carry-save-92/cell'):
    original=read_map(BUILD/(source+'.save.txt'))
    meta=json.loads((BUILD/(source+'.layout.json')).read_text())
    before=json.loads((BUILD/(source+'.logic.json')).read_text())
    partials=[]
    for side in ('west','east','vertical'):
        nodes=[n for n in before['nodes'] if n.get('scope')=='count/'+side]
        partials.append([next(n['output'] for n in nodes if n['op']=='XOR'),
                         next(n['output'] for n in nodes if n['op'] in ('MAJ','AND'))])
    graph=compress_three_counts(before,partials=partials,outputs=before['_count'])
    print('Carry-save logic:',len(before['nodes']),'->',len(graph['nodes']),flush=True)
    cells,newmeta=recompile(before,graph,original,meta);connector_check(cells,newmeta)
    newmeta['carry_save_count']=True;newmeta.update(write_map(BUILD,stem,cells))
    write_json(BUILD/(stem+'.layout.json'),newmeta);write_json(BUILD/(stem+'.logic.json'),graph)
    write_json(BUILD/(stem+'.compression.json'),dict(before=len(original),after=len(cells),pass_report=graph['_carry_save']))
    print('Carry-save physical:',len(original),'->',len(cells),flush=True)
    return cells,newmeta


if __name__=='__main__':build()
