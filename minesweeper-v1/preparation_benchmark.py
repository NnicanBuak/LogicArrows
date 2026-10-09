"""Measure physical first-click phase transitions on saved game boards."""
import json
from snap_verify import *


def measure(stem,first=55,seed=123456789):
    cells=read_map(BUILD/(stem+'.save.txt'));meta=json.loads((BUILD/(stem+'.layout.json')).read_text())
    tm=moved(meta['cell'],*meta['tiles'][first]['origin'])
    button=sources(cells,tm,['button0'])['button0']
    gates={v['net']:v['at'] for v in meta['cell']['gate_positions']}
    last=meta['tiles'][-1]['origin'];p=gates['phase:ready']
    observed={name:gates['phase:'+name] for name in ('choose','sample','ready')}
    observed.update(last_ready=[p[0]+last[0],p[1]+last[1]],selected=tm['states']['selected'],opened=tm['states']['opened'])
    cold=30000;ticks=cold+(230000 if meta.get('timer_mode')!='counter' else 30000)
    signal=[0]*cold+[1]*64+[0]*(ticks-cold-64)
    report=simulate(cells,dict(ticks=ticks,seed=seed,inputs=[dict(at=list(button),values=signal)],expect=[],observe=list(observed.values())),timeout=240)
    events={}
    for name,trace in zip(observed,report['observations']):
        values=trace['values'];event=next((i+1-cold for i in range(cold,len(values)) if values[i]==1),None)
        assert event is not None,(name,stem)
        events[name]=event
    result=dict(map_hash=meta['map_hash'],size=meta['size'],first=first,seed=seed,
        cold_ticks=cold,events_after_click=events,preparation_ticks=events['last_ready'],
        arrows=meta['cells'],timer_cells=meta.get('timer_cells'),timer_delay_cells=meta['timer_delay_cells'])
    write_json(BUILD/(stem+'.latency.json'),result)
    print(result,flush=True)
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--before',default='baselines/legacy-preparation-96/minesweeper-10x10')
    p.add_argument('--after',default='minesweeper-10x10')
    p.add_argument('--output',default='preparation.comparison.json')
    a=p.parse_args()
    before=measure(a.before)
    after=measure(a.after)
    report=dict(before=before,after=after,speedup=before['preparation_ticks']/after['preparation_ticks'],
        arrow_reduction=before['arrows']-after['arrows'],
        limitation='Measured first-click readiness, same seed and center click; tile still 96x96')
    write_json(BUILD/a.output,report)
    print('Preparation speedup:',report['speedup'],flush=True)
