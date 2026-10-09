"""Physical footprint, game evidence and timing criteria for the new topology."""
from collections import Counter,defaultdict
from snap import *
from compact_panel import make_panel


def audit(destination='releases/serial-64',size=10):
    stem=(destination+'/' if destination else '')+f'minesweeper-{size}x{size}'
    m=json.loads((BUILD/destination/'cell.layout.json').read_text())
    bm=json.loads((BUILD/(stem+'.layout.json')).read_text())
    tile=read_map(BUILD/destination/'cell.save.txt');board=read_map(BUILD/(stem+'.save.txt'))
    g=json.loads((BUILD/destination/'cell.logic.json').read_text())
    cv=json.loads((BUILD/destination/'cell.verification.json').read_text())
    runs=json.loads((BUILD/(stem+'.seeds.verification.json')).read_text())['runs']
    cold=json.loads((BUILD/(stem+'.first-click-matrix.json')).read_text())
    late=json.loads((BUILD/(stem+'.first-click-timing.json')).read_text())
    width=m.get('width',m['side']);height=m.get('height',m['side']);step=height+bm['row_gap']
    expected={(x+t['origin'][0],y+t['origin'][1]):c for t in bm['tiles'] for (x,y),c in tile.items()}
    actual={p:c for p,c in board.items() if 0<=p[0]<width*size and 0<=p[1]<step*size and p[1]%step<height}
    panel=make_panel(not m['logic_decoder'],level_outputs=True,click_side=m.get('button_exit','bottom')).moved(m['display_origin'][0]+6,m['display_origin'][1])
    gates={tuple(n['at']):n['net'] for n in m['gate_positions']}
    owners={tuple(n['at']):n['net'] for n in m['wire_owners']};nodes={n['output']:n for n in g['nodes']}
    incoming=defaultdict(list)
    for p,c in tile.items():
        for q in destinations(p,c):
            if q in gates:incoming[q].append(gates.get(p,owners.get(p)))
    phases=('choose','sample','ready','stop','defeat')
    criteria=dict(
        native_panel_unchanged=all(tile.get(p)==c for p,c in panel.cells.items() if c.type!=25),
        button_5x5=set(map(tuple,m['button']))==set(panel.buttons),
        mine_8x8_red_splitters=set(map(tuple,m['mine_indicator']['pixels']))==set(panel.mine_pixels),
        four_memory_cells=len(m['memories'])==4 and all(tile[tuple(p)].type in (18,19) for p in m['memories']),
        all_actual_gate_inputs_match=all(Counter(incoming[p])==Counter(nodes[n]['inputs']) for p,n in gates.items()),
        footprint_respected=all(0<=x<width and 0<=y<height for x,y in tile),
        identical_modules_and_no_wiring_inside=actual==expected and bm['cell']['map_hash']==m['map_hash'],
        cell_simulation=cv['passed'] and cv['neighbor_masks']==256 and cv['transition_vectors']==512,
        every_button_square=cv['button_squares']==25 and cv['button_press_release_checks']==50,
        game_two_seeds=len(runs)==2 and len({r['seed'] for r in runs})==2 and all(r['passed'] for r in runs),
        cold_simultaneous_clicks=cold['passed'] and len(cold['cases'])==5,
        late_preparation_clicks=late['passed'] and len(late['cases'])==5 and late['map_hash']==bm['map_hash'],
        hashes_match=map_hash(tile)==m['map_hash'] and map_hash(board)==bm['map_hash'] and
            cv['map_hash']==m['map_hash'] and cold['map_hash']==bm['map_hash'] and all(r['map_hash']==bm['map_hash'] for r in runs),
        shared_counter_timers=bm['timer_mode']=='counter' and bm['timer_delay_cells']==0,
        stage_gaps_proved=all(bm['guaranteed_stage_gaps'][n]>=bm['stage_timing'][n] for n in ('sample','ready')),
        column_phases=all(nodes['phase:'+name]['op']=='BUF' and nodes['phase:'+name]['inputs']==['N:'+name] for name in phases),
        request_guard=nodes['phase:busy']['inputs']==['N:busy'] and g['_states']['busy']=='phase:busy',
        total_bus_removed=not any(name.split(':')[-1] in ('present','rowReq','carryReq','totalReq','rowLoss','carryLoss','totalLoss','rowSat','carrySat','totalSat')
                                  for table in ('inputs','outputs') for name in g[table]),
        no_html=not list(HERE.rglob('*.html')))
    report=dict(passed=all(criteria.values()),criteria=criteria,width=width,height=height,area=width*height,
                cell_fits_64=width<=64 and height<=64,
                target_64_met=width<=64 and height+bm['row_gap']<=64,
                tile_pitch=[width,height+bm['row_gap']],gate_count=len(g['nodes']),
                cell_arrows=len(tile),board_arrows=len(board),map_hash=m['map_hash'],board_map_hash=bm['map_hash'],
                cell_area_reduction=92*92/(width*height),cell_arrow_reduction=5122/len(tile),
                tile_area_reduction_with_gutter=92*92/(width*(height+bm['row_gap'])),
                field_arrow_reduction=(513569/len(board) if size==10 else None),
                field_area_reduction=(1040*1068/bm['bounds']['area'] if size==10 else None),row_gap=bm['row_gap'])
    write_json(BUILD/(stem+'.quality.json'),report)
    assert report['passed'],[k for k,v in criteria.items() if not v]
    print('Serial quality passed:',width,height,len(tile),len(board),flush=True)
    return report


if __name__=='__main__':audit()
