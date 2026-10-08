"""Audit exported maps and require matching simulation evidence before delivery."""
import json
from collections import Counter,defaultdict
from snap import BUILD,REFERENCE,read_map,map_hash,destinations
from snap_board import connector_check
from mapdata import write_json

def audit():
    tile=read_map(BUILD/'cell.save.txt')
    board=read_map(BUILD/'minesweeper-10x10.save.txt')
    meta=json.loads((BUILD/'cell.layout.json').read_text())
    bm=json.loads((BUILD/'minesweeper-10x10.layout.json').read_text())
    cv=json.loads((BUILD/'cell.verification.json').read_text())
    runs=json.loads((BUILD/'minesweeper-10x10.seeds.verification.json').read_text())['runs']
    side=meta['side'];criteria={}
    criteria['export_hashes_match']=map_hash(tile)==meta['map_hash'] and map_hash(board)==bm['map_hash']
    criteria['cell_stays_inside_frame']=all(0<=x<side and 0<=y<side for x,y in tile)
    bounds=meta.get('panel_bounds')
    panel=[bounds[2]-bounds[0]+1,bounds[3]-bounds[1]+1] if bounds else [meta['cavity_radius']*2+1]*2
    criteria['central_panel_at_most_25']=max(panel)<=25
    center=meta['center'];button={(center[0]-1+x,center[1]+7+y) for x in range(3) for y in range(3)}
    criteria['center_button_3x3']=set(map(tuple,meta['button']))==button and all(tile[p].type==24 for p in button)
    criteria['native_mine_toggle']=tile[tuple(meta['states']['mine'])].type==19
    criteria['native_open_memory']=tile[tuple(meta['states']['opened'])].type==18
    ox,oy=meta['display_origin']
    visible={(x+ox,y+oy):c for (x,y),c in read_map(REFERENCE).items() if y<=13}
    criteria['supplied_visible_display_preserved']=all(tile.get(p)==c for p,c in visible.items())
    criteria['all_four_connectors_match']=connector_check(tile,meta)
    graph=json.loads((BUILD/'cell.logic.json').read_text())
    nodes={n['output']:n for n in graph['nodes']}
    gates={tuple(g['at']):g['net'] for g in meta['gate_positions']}
    owners={tuple(w['at']):w['net'] for w in meta['wire_owners']}
    incoming=defaultdict(list)
    for p,c in tile.items():
        for q in destinations(p,c):
            if q in gates:incoming[q].append(gates.get(p,owners.get(p)))
    criteria['physical_gate_inputs_match']=all(Counter(incoming[p])==Counter(nodes[net]['inputs']) for p,net in gates.items())
    expected={(x+t['origin'][0],y+t['origin'][1]):c for t in bm['tiles'] for (x,y),c in tile.items()}
    actual={p:c for p,c in board.items() if 0<=p[0]<side*10 and 0<=p[1]<side*10}
    criteria['identical_100_copies']=len(bm['tiles'])==100 and expected==actual and bm['cell']['map_hash']==meta['map_hash']
    criteria['zero_intercell_connection_wires']=expected==actual
    criteria['exhaustive_256_neighbor_masks']=cv['passed'] and cv['neighbor_masks']==256 and cv['transition_vectors']==512 and cv['side']==side
    criteria['simulation_evidence_matches_maps']=cv.get('map_hash')==meta['map_hash'] and all(r.get('map_hash')==bm['map_hash'] for r in runs)
    criteria['board_two_seeds_and_first_positions']=len(runs)>=2 and len({r['seed'] for r in runs})>=2 and {0,55}<={r['first'] for r in runs} and all(r['passed'] for r in runs)
    criteria['win_and_loss_freeze']=all({'mine-defeat','blocked-after-defeat','victory','blocked-after-victory'}<=set(r['scenarios']) for r in runs)
    result=dict(passed=all(criteria.values()),criteria=criteria,side=side,target_96_met=side<=96,target_64_met=side<=64,
                central_panel=panel,arrows=len(tile),board_arrows=len(board),map_hash=meta['map_hash'],board_map_hash=bm['map_hash'])
    write_json(BUILD/'quality.json',result)
    assert result['passed'],[k for k,v in criteria.items() if not v]
    print('Quality audit passed:',side,len(tile),len(board),flush=True)
    return result

if __name__=='__main__':audit()
