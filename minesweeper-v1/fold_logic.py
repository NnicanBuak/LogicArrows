"""Recompile folded computation trees through the common compiler."""
from snap import *
from incremental_tile import recompile
from netlist_optimization import fold_or_trees
from snap_board import connector_check


def build(source='cell',stem='experiments/folded-logic-92/cell',max_inputs=9):
    original=read_map(BUILD/(source+'.save.txt'))
    meta=json.loads((BUILD/(source+'.layout.json')).read_text())
    before=json.loads((BUILD/(source+'.logic.json')).read_text())
    graph=fold_or_trees(before,max_inputs=max_inputs,
        keep_nets=list(before['_states'].values())+before['_count'])
    print('Folded logic:',len(before['nodes']),'->',len(graph['nodes']),'nodes',flush=True)
    cells,newmeta=recompile(before,graph,original,meta)
    connector_check(cells,newmeta)
    newmeta['folded_logic']=True
    newmeta.update(write_map(BUILD,stem,cells))
    write_json(BUILD/(stem+'.layout.json'),newmeta);write_json(BUILD/(stem+'.logic.json'),graph)
    write_json(BUILD/(stem+'.folding.json'),dict(before=len(original),after=len(cells),
        before_nodes=len(before['nodes']),after_nodes=len(graph['nodes']),pass_report=graph['_or_folding']))
    print('Folded physical cell:',len(original),'->',len(cells),flush=True)
    return cells,newmeta


if __name__=='__main__':build()
