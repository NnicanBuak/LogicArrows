"""One controller, one field scan, reduced neighbor ports and column phases."""
from copy import deepcopy
from snap import *
from snap_board import header,acyclic_bound_effective
from status_display import add_status
from grid_wiring import connect_grid,contact
from preparation import add_compact_timer


def build(size=10,cell_stem='experiments/serial-64/cell',stem=None,gap=12):
    stem=stem or cell_stem.rsplit('/',1)[0]+f'/minesweeper-{size}x{size}'
    tile=read_map(BUILD/(cell_stem+'.save.txt'))
    m=json.loads((BUILD/(cell_stem+'.layout.json')).read_text());assert m['serial_control']
    side=m['side'];cells={};origins=[];memories=[]
    width=m.get('width',side);height=m.get('height',side)
    for row in range(size):
        for col in range(size):
            origin=(col*width,row*(height+gap));origins.append(origin)
            cells.update({(x+origin[0],y+origin[1]):c for (x,y),c in tile.items()})
            memories += [[x+origin[0],y+origin[1]] for x,y in m['memories']]
    shim=deepcopy(m)
    for name,x in (('busy',3),('totalLoss',7),('totalSat',11)):
        shim['outputs']['N:'+name]=[dict(contact=[x,-3],fixture=[x,-4])]
    for name in ('choose','sample','ready','stop'):
        shim['inputs']['N:'+name][0]['fixture'][1]=-4
    hc,hm=header(shim)
    assert not set(cells)&set(hc)
    cells.update(hc)
    defeat_targets=[]
    for col in range(size):
        inp=contact(m,origins,col,'N:defeat');defeat_targets.append((inp['fixture'],inp['contact']))
    fixtures=[contact(m,origins,i,name)['fixture'] for i in range(size*size) for name in m['inputs']]
    fixtures += [(x+ox,y+oy) for ox,oy in origins for y in range(height) for x in range(width)]
    status=add_status(cells,hm,extra_targets={'defeat':defeat_targets},reserved=fixtures)
    terminals={}
    for field,name in (('Req','busy'),('Loss','loss'),('Sat','satisfied')):
        out=contact(m,origins,size*size-1,'E:prefix'+field,True)
        inp=hm['inputs'][name][0]
        terminals[field]=(out['fixture'],[(tuple(inp['fixture']),tuple(inp['contact']))])
        if field=='Req':
            for col in range(size):
                target=contact(m,origins,col,'N:busy')
                terminals[field][1].append((target['fixture'],target['contact']))
    broadcasts={}
    for name in ('choose','sample','ready','stop'):
        source=tuple(hm['outputs'][name][0]['fixture'])
        targets=[]
        for col in range(size):
            inp=contact(m,origins,col,'N:'+name)
            targets.append((inp['fixture'],inp['contact']))
        broadcasts[name]=(source,targets)
    cells,wiring=connect_grid(cells,m,origins,size,vertical_gap=True,
        row_scan=('prefixReq','prefixLoss','prefixSat'),start_values={'prefixSat':1},
        terminal_targets=terminals,broadcasts=broadcasts,reserved=fixtures)
    bound=acyclic_bound_effective(cells,memories)
    start=tuple(hm['outputs']['started'][0]['fixture']);cells[start]=Cell(1,3)
    sockets={}
    for name in ('choose','sample','ready'):
        p=tuple(hm['inputs'][name+'Clock'][0]['fixture']);cells[p]=Cell(1,1);sockets[name]=list(p)
    meta=dict(schema=3,size=size,side=side,tiles=[dict(origin=list(p)) for p in origins],cell=m,header=hm,status=status,
        memories=memories,timer_input=list(start),timing_sockets=sockets,logic_settle_bound=bound,
        identical_tiles=True,connection_wires_added=wiring['added_cells'],wiring=wiring,row_gap=gap,
        cell_stem=cell_stem,serial_control=True,profile='GraphDLC-01232bd',verified_against_current_game=False)
    graph=json.loads((BUILD/(cell_stem+'.logic.json')).read_text())
    add_compact_timer(cells,meta,graph)
    meta.update(cells=len(cells),bounds=bounds_of(cells),map_hash=map_hash(cells))
    meta.update(write_map(BUILD,stem,cells,None));write_json(BUILD/(stem+'.layout.json'),meta)
    print('Serial board built:',size,len(cells),meta['bounds'],flush=True)
    return cells,meta


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=3)
    p.add_argument('--cell-source',default='experiments/serial-64/cell');p.add_argument('--stem');p.add_argument('--gap',type=int,default=12)
    a=p.parse_args();build(a.size,a.cell_source,a.stem,a.gap)
