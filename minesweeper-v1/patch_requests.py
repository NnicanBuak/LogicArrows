"""Recompile a request scan using the shared incremental routing backend."""
import json
from snap import *
from distributed_scan import parallelize_or_scan


def build(stem='experiments/parallel-requests-96/cell',source='cell'):
    original=read_map(BUILD/(source+'.save.txt'))
    meta=json.loads((BUILD/(source+'.layout.json')).read_text())
    before=json.loads((BUILD/(source+'.logic.json')).read_text())
    assert map_hash(original)==meta['map_hash']
    if meta.get('parallel_requests'):
        (BUILD/stem).parent.mkdir(parents=True,exist_ok=True)
        meta.update(write_map(BUILD,stem,original,None))
        write_json(BUILD/(stem+'.layout.json'),meta)
        write_json(BUILD/(stem+'.logic.json'),before)
        print('Parallel request tile reused:',len(original),flush=True)
        return original,meta
    # The physical snapshot identifies stable gate/net names, not source order.
    nodes={n['output']:n for n in before['nodes']}
    row=nodes['port:W:rowReq']['inputs'][0]
    graph=parallelize_or_scan(before,value='request',row=row,
        north_carry='N:carryReq',east_row='E:rowReq',carry_port='S:carryReq')
    from incremental_tile import recompile
    cells,meta=recompile(before,graph,original,meta)
    meta['parallel_requests']=True
    (BUILD/stem).parent.mkdir(parents=True,exist_ok=True)
    meta.update(write_map(BUILD,stem,cells,None));write_json(BUILD/(stem+'.layout.json'),meta)
    write_json(BUILD/(stem+'.logic.json'),graph)
    print('Incremental request tile:',len(cells),flush=True)
    return cells,meta


if __name__=='__main__':build()
