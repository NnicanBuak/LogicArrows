"""Compile the compact topology, verify physical gameplay, publish locally."""
import argparse
from shutil import copy2
from snap import BUILD,json,build_tile,write_json
from strip_walls import build as strip_walls
from serial_board import build as build_board
from compile_panel import verify,promote
from first_click_matrix import verify as verify_cold
from first_click_timing import verify as verify_late
from preparation_benchmark import measure
from serial_quality import audit

DESTINATION='releases/compact-56x64'


def build(destination=DESTINATION,cell_source=None):
    if cell_source is None:
        cell_source=destination+'/stages/cell'
        build_tile(sizes=(56,),height=64,seeds=(67,),stem=cell_source,
            strategy='all',packed_counters=True,or_inputs=3,orient_gates=True,
            route_order='full',logic_decoder=True,tight_panel=True,
            serial_control=True,carry_save=True)
    strip_walls(source=cell_source,stem=destination+'/cell')
    for size in (3,5,10):build_board(size,cell_stem=destination+'/cell',gap=6)


def check_and_publish(destination=DESTINATION):
    verify(destination)
    for size in (3,5,10):
        stem=destination+f'/minesweeper-{size}x{size}'
        verify_cold(stem);verify_late(stem);audit(destination,size)
        path=BUILD/(stem+'.layout.json');meta=json.loads(path.read_text())
        meta['preparation_contract_verified']=True;write_json(path,meta)
    after=measure(destination+'/minesweeper-10x10')
    legacy=json.loads((BUILD/'baselines/legacy-preparation-96/minesweeper-10x10.latency.json').read_text())
    previous=json.loads((BUILD/'releases/optimized-92/minesweeper-10x10.latency.json').read_text())
    old=json.loads((BUILD/'releases/optimized-92/cell.layout.json').read_text())
    new=json.loads((BUILD/destination/'cell.layout.json').read_text())
    comparison=dict(before=legacy,previous_compact=previous,after=after,
        speedup=legacy['preparation_ticks']/after['preparation_ticks'],
        relative_to_previous=previous['preparation_ticks']/after['preparation_ticks'],
        before_cell=dict(width=old['side'],height=old['side'],arrows=old['cells'],hash=old['map_hash']),
        after_cell=dict(width=new['width'],height=new['height'],arrows=new['cells'],hash=new['map_hash']),
        cell_area_reduction=old['side']**2/(new['width']*new['height']),
        cell_arrow_reduction=old['cells']/new['cells'],field_arrow_reduction=previous['arrows']/after['arrows'],
        limitation='Same seed 123456789, first 55, cold 30000; latency tradeoff; minimum size not proved')
    write_json(BUILD/destination/'comparison.json',comparison)
    promote(destination)
    copy2(BUILD/destination/'comparison.json',BUILD/'preparation.comparison.json')
    copy2(BUILD/destination/'autotests.json',BUILD/'autotests.json')
    print('Compact release:',new['width'],new['height'],new['cells'],'arrows;',after['preparation_ticks'],'preparation ticks',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',default=DESTINATION)
    p.add_argument('--cell-source');p.add_argument('--verify-and-publish',action='store_true');a=p.parse_args()
    if a.verify_and_publish:check_and_publish(a.destination)
    else:build(a.destination,a.cell_source)
