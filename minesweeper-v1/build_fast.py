"""Build, test and publish the standard game with compact preparation timers."""
import argparse
from shutil import copy2

from snap import BUILD,write_json,json
from patch_requests import build as build_requests
from prune_unused_request import prune
from optimize_routes import build as optimize_routes
from optimize_logic import build as optimize_logic
from snap_board import build_board
from compile_panel import verify,promote
from first_click_matrix import verify as verify_cold
from preparation_benchmark import measure

DESTINATION='releases/optimized'
BASELINE='baselines/legacy-preparation-96'


def build(cell_source='cell',destination=DESTINATION):
    baseline=BUILD/BASELINE;baseline.mkdir(parents=True,exist_ok=True)
    current=json.loads((BUILD/'minesweeper-10x10.layout.json').read_text())
    if current.get('timer_mode')!='counter':
        for stem in ('cell','minesweeper-10x10'):
            for suffix in ('.save.txt','.map.json','.layout.json','.logic.json'):
                source=BUILD/(stem+suffix);target=baseline/source.name
                if source.exists() and not target.exists():copy2(source,target)
    work=destination+'/stages'
    build_requests(stem=work+'/parallel/cell',source=cell_source)
    prune(source=work+'/parallel/cell',stem=work+'/pruned/cell')
    optimize_routes(source=work+'/pruned/cell',stem=work+'/routed/cell')
    optimize_logic(source=work+'/routed/cell',stem=destination+'/cell')
    source=json.loads((BUILD/(cell_source+'.layout.json')).read_text())
    result=json.loads((BUILD/destination/'cell.layout.json').read_text())
    write_json(BUILD/destination/'optimization.json',dict(
        source_hash=source['map_hash'],map_hash=result['map_hash'],
        before=source['cells'],after=result['cells'],
        pruned_total_requests=result['pruned_total_requests'],
        monotone_phases=result['monotone_phases']))
    for size in (3,5,10):
        build_board(size,cell_stem=destination+'/cell',
                    stem=destination+f'/minesweeper-{size}x{size}',timer_mode='counter')


def check_and_publish(destination=DESTINATION):
    verify(destination)
    for size in (3,5,10):verify_cold(destination+f'/minesweeper-{size}x{size}')
    before=measure(BASELINE+'/minesweeper-10x10')
    after=measure(destination+'/minesweeper-10x10')
    write_json(BUILD/destination/'comparison.json',dict(before=before,after=after,
        speedup=before['preparation_ticks']/after['preparation_ticks'],
        arrow_reduction=before['arrows']-after['arrows']))
    for size in (3,5,10):
        path=BUILD/destination/f'minesweeper-{size}x{size}.layout.json'
        meta=json.loads(path.read_text())
        assert meta['timer_mode']=='counter' and meta['timer_delay_cells']==0
        meta['preparation_contract_verified']=True;write_json(path,meta)
    promote(destination)
    copy2(BUILD/destination/'comparison.json',BUILD/'preparation.comparison.json')
    print('Preparation:',before['preparation_ticks'],'->',after['preparation_ticks'],
          'ticks;',round(before['preparation_ticks']/after['preparation_ticks'],2),'x faster',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify-and-publish',action='store_true')
    p.add_argument('--cell-source',default='cell');p.add_argument('--destination',default=DESTINATION);a=p.parse_args()
    if a.verify_and_publish:check_and_publish(a.destination)
    else:build(a.cell_source,a.destination)
