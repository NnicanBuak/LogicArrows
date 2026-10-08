"""Audit exported maps and require matching simulation evidence before delivery."""
import json
from collections import Counter,defaultdict
from snap import BUILD,REFERENCE,read_map,map_hash,destinations
from snap_board import connector_check
from mapdata import write_json
from save_limits import parse_save_size
from status_display import alphabet
from mine_indicator import BITMAP as MINE_BITMAP

def audit(max_save_bytes=None,size=10):
    tile=read_map(BUILD/'cell.save.txt')
    stem=f'minesweeper-{size}x{size}'
    board=read_map(BUILD/(stem+'.save.txt'))
    meta=json.loads((BUILD/'cell.layout.json').read_text())
    bm=json.loads((BUILD/(stem+'.layout.json')).read_text())
    cv=json.loads((BUILD/'cell.verification.json').read_text())
    runs=json.loads((BUILD/(stem+'.seeds.verification.json')).read_text())['runs']
    side=meta['side'];criteria={}
    save_sizes={p.name:p.stat().st_size for p in BUILD.glob('*.save.txt')}
    criteria['configured_save_limit_respected']=max_save_bytes is None or all(n<=max_save_bytes for n in save_sizes.values())
    criteria['export_hashes_match']=map_hash(tile)==meta['map_hash'] and map_hash(board)==bm['map_hash']
    criteria['cell_stays_inside_frame']=all(0<=x<side and 0<=y<side for x,y in tile)
    bounds=meta.get('panel_bounds')
    panel=[bounds[2]-bounds[0]+1,bounds[3]-bounds[1]+1] if bounds else [meta['cavity_radius']*2+1]*2
    criteria['central_panel_31x17']=panel==[31,17]
    center=meta['center'];dx,dy=meta['display_origin']
    button={(center[0]-2+x,dy+4+y) for x in range(5) for y in range(5)}
    criteria['center_button_5x5']=meta['button_size']==5 and set(map(tuple,meta['button']))==button and all(tile[p].type==24 for p in button)
    criteria['native_mine_toggle']=tile[tuple(meta['states']['mine'])].type==19
    criteria['native_open_memory']=tile[tuple(meta['states']['opened'])].type==18
    ox,oy=meta['display_origin']
    visible={(x+ox,y+oy):c for (x,y),c in read_map(REFERENCE).items() if y<=13}
    criteria['supplied_visible_display_preserved']=all(tile.get(p)==c for p,c in visible.items())
    criteria['all_four_connectors_match']=connector_check(tile,meta)
    perimeter={(x,y) for x in range(side) for y in (0,side-1)}|{(x,y) for y in range(side) for x in (0,side-1)}
    ports={tuple(e['contact']) for table in ('inputs','outputs') for es in meta[table].values() for e in es}
    ports.update(map(tuple,meta.get('diagonal_bridges',[])))
    criteria['wall_frame_preserves_connectors']=all(tile[p].type==25 for p in perimeter-ports) and all(tile[p].type!=25 for p in perimeter&ports)
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
    actual={p:c for p,c in board.items() if 0<=p[0]<side*size and 0<=p[1]<side*size}
    criteria[f'identical_{size*size}_copies']=len(bm['tiles'])==size*size and expected==actual and bm['cell']['map_hash']==meta['map_hash']
    criteria['zero_intercell_connection_wires']=expected==actual
    criteria['exhaustive_256_neighbor_masks']=cv['passed'] and cv['neighbor_masks']==256 and cv['transition_vectors']==512 and cv['side']==side
    criteria['all_25_physical_button_squares']=cv.get('button_squares')==25 and cv.get('button_press_release_checks')==50
    criteria['simulation_evidence_matches_maps']=cv.get('map_hash')==meta['map_hash'] and all(r.get('map_hash')==bm['map_hash'] for r in runs)
    criteria['board_two_seeds_and_first_positions']=len(runs)>=2 and len({r['seed'] for r in runs})>=2 and {0,(size//2)*size+size//2}<={r['first'] for r in runs} and all(r['passed'] for r in runs)
    criteria['win_and_loss_freeze']=all({'mine-defeat','blocked-after-defeat','victory','blocked-after-victory'}<=set(r['scenarios']) for r in runs)
    marker=meta['mine_indicator'];ox,oy=marker['origin']
    mine_shape={(ox+x,oy+y) for y,row in enumerate(MINE_BITMAP) for x,bit in enumerate(row) if bit=='1'}
    mine_box={(ox+x,oy+y) for x in range(8) for y in range(8)}
    criteria['native_mine_shape_8x8']=marker['width']==marker['height']==8 and mine_shape==set(map(tuple,marker['pixels'])) and all(p in tile for p in mine_shape) and not (mine_box-mine_shape)&set(tile)
    dx,dy=meta['display_origin']
    criteria['number_button_mine_horizontal']=dx+6==center[0]-13 and ox==center[0]+6 and oy==dy+3 and max(x for x,y in button)<ox and dx+13<min(x for x,y in button)
    digit_padding={(x,y) for x in range(dx+4,dx+16) for y in range(dy-2,dy+15)
                   if not(dx+6<=x<dx+14 and dy<=y<dy+14)}
    marker_padding={(x,y) for x in range(ox-2,ox+10) for y in range(oy-2,oy+10)}-mine_box
    feed=tuple(meta['outputs']['mine_indicator'][0]['contact'])
    feed_lane={(feed[0],oy-2)}
    criteria['indicator_white_padding']=not digit_padding&set(tile) and not (marker_padding-feed_lane)&set(tile)
    criteria['defeat_reveals_all_mines_and_freezes_safe_cells']=all({'all-mines-revealed','safe-cells-stay-closed-after-defeat'}<=set(r['scenarios']) and r['mine_indicator_pixels']==size*size*len(mine_shape) for r in runs)
    glyphs,version=alphabet();status_ok=bm['status']['scale']==2 and bm['status']['source_version']==version
    for display in bm['status']['displays'].values():
        wanted=set()
        for letter in display['letters']:
            ox,oy=letter['origin']
            for y,row in enumerate(glyphs[letter['letter']]):
                for x,bit in enumerate(row):
                    if bit=='1':wanted.update((ox+2*x+dx,oy+2*y+dy) for dx in (0,1) for dy in (0,1))
        status_ok &= wanted==set(map(tuple,display['pixels'])) and all(board[p].type in (1,6,7,8,10,11,12,13,14) for p in wanted)
    criteria['native_alphabet_at_exactly_2x']=status_ok
    criteria['win_lose_all_pixels_and_startup_blank']=all({'status-blank-before-start','win-lose-all-pixels'}<=set(r['scenarios']) and r['status_pixels']==220 for r in runs)
    result=dict(passed=all(criteria.values()),criteria=criteria,side=side,target_96_met=side<=96,target_64_met=side<=64,
                central_panel=panel,arrows=len(tile),board_arrows=len(board),map_hash=meta['map_hash'],board_map_hash=bm['map_hash'],
                save_limit_bytes=max_save_bytes,save_sizes=save_sizes,grid=[size,size],field_size=[side*size]*2,
                phase_wait_ticks=bm['phase_wait_ticks'],save_bytes=bm['save_bytes'])
    write_json(BUILD/(stem+'.quality.json'),result)
    if size==10:write_json(BUILD/'quality.json',result)
    assert result['passed'],[k for k,v in criteria.items() if not v]
    print('Quality audit passed:',side,len(tile),len(board),flush=True)
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--max-save-size',type=parse_save_size,default=None)
    p.add_argument('--size',type=int,default=10)
    a=p.parse_args();audit(a.max_save_size,a.size)
