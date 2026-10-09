"""Incrementally compile the native panel through the shared ArrowsHDL backend."""
import argparse
import json
from collections import Counter
from pathlib import Path
from shutil import copy2

from snap import BUILD,read_map,write_map,write_json,map_hash
from mine_indicator import indicator
from native_macros import replace_native_cells

DESTINATION='experiments/red-mine-panel-96'
STEMS=['cell']+[f'minesweeper-{size}x{size}' for size in (3,5,10)]


def compile_panel():
    native,root=indicator()
    tile_meta=json.loads((BUILD/'cell.layout.json').read_text())
    ox,oy=tile_meta['mine_indicator']['origin']
    replacement={(x+ox,y+oy):c for (x,y),c in native.items()}
    assert set(replacement)==set(map(tuple,tile_meta['mine_indicator']['pixels']))
    output=BUILD/DESTINATION;output.mkdir(parents=True,exist_ok=True)
    compiled_tile=None;report=[]
    for stem in STEMS:
        old=read_map(BUILD/(stem+'.save.txt'))
        meta=json.loads((BUILD/(stem+'.layout.json')).read_text())
        assert map_hash(old)==meta['map_hash']
        if stem=='cell':
            patches=replacement
        else:
            assert meta['cell']['map_hash']==tile_meta['map_hash'],'Board uses a different cell'
            patches={(x+t['origin'][0],y+t['origin'][1]):c for t in meta['tiles'] for (x,y),c in replacement.items()}
        cells=replace_native_cells(old,patches,combinational=True)
        meta.update(cells=len(cells),map_hash=map_hash(cells),
                    native_recompile=dict(component='mine_indicator',previous_hash=map_hash(old)))
        if stem=='cell':
            meta['mine_indicator'].update(style='red-splitters-four-diagonals',
                types={str(k):v for k,v in sorted(Counter(c.type for c in native.values()).items())},
                blue_pixels=[[x+ox,y+oy] for (x,y),c in sorted(native.items()) if c.type==11])
        else:meta['cell']=compiled_tile
        meta.update(write_map(output,stem,cells,None))
        write_json(output/(stem+'.layout.json'),meta)
        source=BUILD/(stem+'.logic.json')
        if source.exists():copy2(source,output/source.name)
        if stem=='cell':compiled_tile=meta
        report.append(dict(stem=stem,arrows=len(cells),map_hash=meta['map_hash'],recompiled_pixels=len(patches)))
        print('Compiled:',stem,len(cells),'arrows;',len(patches),'mine pixels',flush=True)
    write_json(output/'compilation.json',dict(passed=True,backend='ArrowsHDL.native_macros.replace_native_cells',
        same_footprint=True,same_external_connections=True,acyclic=True,exports=report))
    return report


def promote(destination=DESTINATION):
    source=BUILD/destination
    for stem in STEMS:
        report=json.loads((source/(stem+'.verification.json')).read_text())
        meta=json.loads((source/(stem+'.layout.json')).read_text())
        assert report['passed'] and report['map_hash']==meta['map_hash'],stem
    previous=json.loads((BUILD/'cell.layout.json').read_text())['map_hash']
    archive=BUILD/'experiments'/('before-release-'+previous[:12])
    archive.mkdir(parents=True,exist_ok=True)
    for stem in STEMS:
        for file in BUILD.glob(stem+'.*'):
            if not (archive/file.name).exists():copy2(file,archive/file.name)
        for suffix in ('.save.txt','.map.json','.layout.json','.verification.json','.logic.json',
                       '.seeds.verification.json','.observed.json','.demo.json','.defeat.demo.json','.status.observed.json',
                       '.latency.json','.first-click-matrix.json','.first-click-timing.json'):
            file=source/(stem+suffix)
            if file.exists():copy2(file,BUILD/file.name)
        if stem!='cell':
            file=BUILD/(stem+'.layout.json')
            meta=json.loads(file.read_text());meta['cell_stem']='cell';write_json(file,meta)
    print('Published locally:',', '.join(STEMS),flush=True)
    if json.loads((BUILD/'cell.layout.json').read_text()).get('serial_control'):
        from serial_quality import audit
        for size in (3,5,10):report=audit('',size)
        write_json(BUILD/'quality.json',report)
    else:
        from quality import audit
        for size in (5,10):audit(size=size)


def verify(destination=DESTINATION):
    from snap_verify import verify_cell,verify_board
    verify_cell(destination+'/cell')
    summaries=[]
    for size in (3,5,10):
        stem=destination+f'/minesweeper-{size}x{size}'
        runs=[verify_board(size,123456789,stem=stem),
              verify_board(size,987654321,first=0,stem=stem)]
        write_json(BUILD/(stem+'.seeds.verification.json'),dict(passed=True,runs=runs))
        summaries.append(dict(size=size,seeds=len(runs),map_hash=runs[0]['map_hash']))
    write_json(BUILD/destination/'autotests.json',dict(passed=True,cell=True,boards=summaries))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--promote',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.promote:promote()
    elif a.verify:verify()
    else:compile_panel()
