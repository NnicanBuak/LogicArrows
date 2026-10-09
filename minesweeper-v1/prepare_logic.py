"""Bind placement hints to the redesigned neighbor protocol."""
from snap import *
from placement_binding import rebind_positions


def prepare(carry_save=False):
    before=json.loads((BUILD/'cell.logic.json').read_text())
    meta=json.loads((BUILD/'cell.layout.json').read_text())
    graph=graph_for_tile(or_inputs=3,aggregate_flags=True,carry_save=carry_save)
    positions={v['net']:v['at'] for v in meta['gate_positions']}
    positions.update({e['net']:meta['inputs'][name][e['index']]['contact'] for name,es in before['inputs'].items() for e in es})
    bound,renamed=rebind_positions(before,graph,positions,fallback=meta['center'])
    stem='experiments/hybrid-carry' if carry_save else 'experiments/hybrid-flags'
    (BUILD/stem).mkdir(parents=True,exist_ok=True)
    path=BUILD/stem/'warm.json'
    write_json(path,dict(side=meta['side'],positions=bound,renamed=renamed))
    write_json(BUILD/stem/'logic.json',graph)
    print('Redesigned logic:',len(before['nodes']),'->',len(graph['nodes']),
          'external inputs',len(graph['inputs'])-8,'matched positions',len(renamed),flush=True)
    return path


if __name__=='__main__':prepare();prepare(True)
