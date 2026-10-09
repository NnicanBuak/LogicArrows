"""Compile an area-first search with the shared ArrowsHDL heuristic; no tests."""
import argparse
import json
from pathlib import Path
from shutil import copy2
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'ArrowsHDL/src'))
from compact_search import search_footprints

DEST='experiments/maximum-compactness'

def worker(width,height,seed,stem,margin=8):
    from snap import build_tile
    from strip_walls import build
    source=stem+'/raw'
    build_tile(sizes=(width,),height=height,seeds=(seed,),stem=source,
        strategy='all',packed_counters=True,or_inputs=3,orient_gates=True,
        route_order='full',logic_decoder=True,tight_panel=True,
        serial_control=True,carry_save=True,placement_margin=margin)
    build(source=source,stem=stem+'/cell')

def run(budget,timeout,destination=DEST,margin=8,baseline_source='cell'):
    build=HERE/'build'; out=build/destination; out.mkdir(parents=True,exist_ok=True)
    old=json.loads((build/(baseline_source+'.layout.json')).read_text(encoding='utf-8'))
    baseline=dict(width=old['width'],height=old['height'],arrows=old['cells'],stem=baseline_source)
    def compile_candidate(width,height,seed):
        stem=f'{destination}/candidates/{width}x{height}-{seed}'
        folder=build/stem; folder.mkdir(parents=True,exist_ok=True)
        started=time.monotonic()
        with (folder/'compile.log').open('w',encoding='utf-8') as log:
            try:
                result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),
                    '--worker',str(width),str(height),str(seed),stem,'--margin',str(margin)],
                    stdout=log,stderr=subprocess.STDOUT,timeout=timeout,cwd=HERE.parent)
            except subprocess.TimeoutExpired:
                raise TimeoutError(f'Compilation budget {timeout}s exceeded') from None
        if result.returncode:
            lines=(folder/'compile.log').read_text(encoding='utf-8',errors='replace').splitlines()
            raise ValueError(' / '.join(lines[-2:]))
        meta=json.loads((build/(stem+'/cell.layout.json')).read_text(encoding='utf-8'))
        return dict(width=meta['width'],height=meta['height'],arrows=meta['cells'],
                    map_hash=meta['map_hash'],stem=stem+'/cell',seconds=time.monotonic()-started)
    def progress(record,best,trials):
        print(f"{len(trials):02d}: {record['width']}x{record['height']} seed={record['seed']} "
              f"{record['status']}; best={best['width']}x{best['height']} {best['arrows']} arrows",flush=True)
        (out/'search.json').write_text(json.dumps(dict(baseline=baseline,best=best,trials=trials,
            tests_run=False,simulation_verified=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=search_footprints(compile_candidate,baseline,range(40,57,4),range(48,65,4),
                             max_trials=budget,on_trial=progress)
    report.update(baseline=baseline,placement_margin=margin,tests_run=False,simulation_verified=False)
    best=report['best']
    for suffix in ('.save.txt','.map.json','.layout.json','.logic.json'):
        copy2(build/(best['stem']+suffix),out/('cell'+suffix))
    (out/'search.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('RESULT',json.dumps(best,ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',nargs=4)
    parser.add_argument('--budget',type=int,default=32)
    parser.add_argument('--timeout',type=int,default=90)
    parser.add_argument('--margin',type=int,default=8)
    parser.add_argument('--destination',default=DEST)
    parser.add_argument('--baseline-source',default='cell')
    args=parser.parse_args()
    if args.worker:
        w,h,s,stem=args.worker;worker(int(w),int(h),int(s),stem,args.margin)
    else:run(args.budget,args.timeout,args.destination,args.margin,args.baseline_source)
