"""Prune unused controller outputs through the shared ArrowsHDL passes."""
from __future__ import annotations

from copy import deepcopy
import json
from snap import BUILD
from mapdata import read_map, write_json, map_hash
from save_limits import write_map
from snap_board import connector_check
from borders import add_cell_walls
from netlist_optimization import prune_outputs
from incremental_routing import prune_dead_wires


def prune(source='cell',stem='experiments/pruned-control-96/cell'):
    original=read_map(BUILD/(source+'.save.txt'))
    meta=json.loads((BUILD/(source+'.layout.json')).read_text())
    before=json.loads((BUILD/(source+'.logic.json')).read_text())
    assert map_hash(original)==meta['map_hash']
    has_unused='N:totalReq' in before['outputs']
    graph=prune_outputs(before,['N:totalReq']) if has_unused else deepcopy(before)
    dead=set(graph['_pruning']['dead_nets']) if has_unused else set()
    owners={tuple(v['at']):v['net'] for v in meta['wire_owners']}
    removed={p for p,owner in owners.items() if owner in dead or (owner.startswith('gate:') and owner[5:] in dead)}
    cells={p:c for p,c in original.items() if p not in removed}
    meta=deepcopy(meta)
    meta['inputs']={n:es for n,es in meta['inputs'].items() if n in graph['inputs']}
    meta['outputs']={n:es for n,es in meta['outputs'].items() if n in graph['outputs']}
    meta['gate_positions']=[v for v in meta['gate_positions'] if v['net'] not in dead]
    protected={tuple(v['at']) for v in meta['gate_positions']}
    protected.update(p for p,o in owners.items() if o.startswith('native:'))
    protected.update(p for p,c in cells.items() if c.type==25)
    protected.update(tuple(e['contact']) for table in ('inputs','outputs') for es in meta[table].values() for e in es)
    cells=prune_dead_wires(cells,protected)
    walls=add_cell_walls(cells,meta['side'])
    meta['wire_owners']=[v for v in meta['wire_owners'] if tuple(v['at']) in cells and tuple(v['at']) not in removed]
    meta.update(cells=len(cells),map_hash=map_hash(cells),walls=walls,
        pruned_total_requests=True,source_map_hash=map_hash(original))
    connector_check(cells,meta)
    (BUILD/stem).parent.mkdir(parents=True,exist_ok=True)
    meta.update(write_map(BUILD,stem,cells))
    write_json(BUILD/(stem+'.layout.json'),meta);write_json(BUILD/(stem+'.logic.json'),graph)
    report=dict(source_map_hash=map_hash(original),map_hash=meta['map_hash'],before=len(original),
        after=len(cells),removed=len(original)-len(cells),removed_nets=sorted(dead),
        side=meta['side'],ports=len(meta['inputs'])-8,logic_nodes=len(graph['nodes']))
    write_json(BUILD/(stem+'.pruning.json'),report)
    print('Pruned unused totalReq:',report,flush=True)
    return cells,meta


if __name__ == '__main__':
    prune()
