"""Colour real routed nets, cutting exactly at compiler gates and native blocks."""
from collections import deque
import colorsys,json
from PIL import Image,ImageDraw,ImageOps
from snap import BUILD,ROOT,REFERENCE,read_map,destinations
from render import font
from mapdata import write_json,map_hash

def recover_nets(cells,meta):
    gates={tuple(g['at']):g for g in meta['gate_positions']}
    native=set(map(tuple,meta['button']))|{p for p,c in cells.items() if c.type==25}|set(map(tuple,meta.get('diagonal_bridges',[])))
    native.update(map(tuple,meta.get('mine_indicator',{}).get('pixels',[])))
    native.update(map(tuple,meta.get('button_collectors',[])))
    for (x,y) in read_map(REFERENCE):
        if y<=13:native.add((x+meta['display_origin'][0],y+meta['display_origin'][1]))
        elif y>=19 and not meta.get('logic_decoder'):native.add((x+meta['decoder_origin'][0],y+meta['decoder_origin'][1]-19))
    owners={};starts=[]
    for name,entries in meta['inputs'].items():
        starts.append((name,tuple(entries[0]['contact'])))
    for p,g in gates.items():
        starts.extend((g['net'],q) for q in destinations(p,cells[p]) if q in cells)
    for net,start in starts:
        todo=deque([start]);seen=set()
        while todo:
            p=todo.popleft()
            if p in seen or p in gates or p in native or p not in cells:continue
            seen.add(p)
            assert p not in owners or owners[p]==net,('mixed nets',p,owners.get(p),net)
            owners[p]=net
            todo.extend(q for q in destinations(p,cells[p]) if q in cells)
    assert set(cells)==set(owners)|set(gates)|native,('unassigned',set(cells)-set(owners)-set(gates)-native)
    if 'wire_owners' in meta:
        exact={tuple(e['at']):e['net'] for e in meta['wire_owners']}
        assert all(exact[p]==net for p,net in owners.items()),'Colour reconstruction differs from compiler nets'
    return owners,gates,native

def render_nets(stem,layout=None):
    cells=read_map(BUILD/(stem+'.save.txt'))
    meta=json.loads((BUILD/((layout or stem)+'.layout.json')).read_text())
    assert map_hash(cells)==meta['map_hash']
    owners,gates,native=recover_nets(cells,meta)
    names=sorted(set(owners.values()))
    palette={name:tuple(round(v*255) for v in colorsys.hls_to_rgb((i*.61803398875)%1,.75,.67)) for i,name in enumerate(names)}
    side=meta['side'];scale=10;left=28;top=108
    im=Image.new('RGB',(side*scale+56,side*scale+194),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((28,16),f'Сапёр v1 — цветная разводка {side}×{side}',font=font(28),fill='#172c45')
    d.text((28,56),f'{len(cells):,} стрелок • {len(names)} проводных цепей • действительная скомпилированная схема',font=font(17),fill='#55647a')
    sprites={}
    for p,c in cells.items():
        x,y=p;px=left+x*scale;py=top+y*scale
        color=palette[owners[p]] if p in owners else '#cbd5e1' if p in native else '#707d91'
        if c.type==24:color='#e58a9f'
        if c.type==25:color='#25384f'
        d.rectangle((px,py,px+scale-1,py+scale-1),fill=color)
        token=c.type,c.rotation,c.mirrored
        if token not in sprites:
            sp=Image.open(ROOT/f'ArrowsHDL/assets/sprites/arrow{c.type}.png').convert('RGBA')
            if c.mirrored:sp=ImageOps.mirror(sp)
            alpha=sp.getchannel('A');sp=ImageOps.grayscale(sp).convert('RGBA');sp.putalpha(alpha)
            sprites[token]=sp.rotate(-90*c.rotation).resize((scale-1,scale-1),Image.Resampling.LANCZOS)
        im.paste(sprites[token],(px,py),sprites[token])
    d.rectangle((left-2,top-2,left+side*scale+1,top+side*scale+1),outline='#294e71',width=2)
    x,y=meta['display_origin'];bx,by=meta['button'][0]
    d.rectangle((left+(x+6)*scale-3,top+y*scale-3,left+(x+14)*scale+3,top+(y+14)*scale+3),outline='#117b92',width=3)
    bs=meta.get('button_size',3)
    d.rectangle((left+bx*scale-3,top+by*scale-3,left+(bx+bs)*scale+3,top+(by+bs)*scale+3),outline='#b82b48',width=3)
    d.text((28,im.height-66),'Цвет — отдельная цепь. Серый — логические элементы и исходные блоки дисплея.',font=font(17),fill='#55647a')
    d.text((28,im.height-38),'Окраска показывает соединения, а не текущее состояние сигналов.',font=font(17),fill='#55647a')
    path=BUILD/(stem+'.nets.preview.png');im.save(path)
    write_json(BUILD/(stem+'.nets.json'),dict(map_hash=meta['map_hash'],side=side,physical_arrows=len(cells),
        net_count=len(names),wire_arrows=len(owners),source='compiler gates and physical arrow connections',
        nets=[dict(name=n,color=palette[n],cells=[list(p) for p,owner in owners.items() if owner==n]) for n in names]))
    print('Verified net colours:',stem,side,len(cells),len(names),len(owners),flush=True)
    return path

def render_board_nets(size):
    """Overview of the physical field; controllers remain in the full preview."""
    stem=f'minesweeper-{size}x{size}'
    board=read_map(BUILD/(stem+'.save.txt'))
    bm=json.loads((BUILD/(stem+'.layout.json')).read_text())
    tile=read_map(BUILD/'cell.save.txt');meta=json.loads((BUILD/'cell.layout.json').read_text())
    assert bm['cell']['map_hash']==map_hash(tile)
    assert bm['map_hash']==map_hash(board)
    owners,gates,native=recover_nets(tile,meta)
    names=sorted(set(owners.values()))
    palette={n:tuple(round(v*255) for v in colorsys.hls_to_rgb((i*.61803398875)%1,.75,.67)) for i,n in enumerate(names)}
    side=meta['side'];scale=max(1,min(3,1600//(side*size)));left=28;top=106
    im=Image.new('RGB',(max(1100,side*size*scale+56),side*size*scale+180),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((28,16),f'Сапёр v1 — {size}×{size} ячеек по {side}×{side}',font=font(28),fill='#172c45')
    d.text((28,56),f'Игровая сетка {side*size}×{side*size} • стеночки на границах • прямое соединение контактов',font=font(18),fill='#55647a')
    for t in bm['tiles']:
        dx,dy=t['origin']
        for p,c in tile.items():
            x,y=p;assert board[(dx+x,dy+y)]==c
            px=left+(dx+x)*scale;py=top+(dy+y)*scale
            color=palette[owners[p]] if p in owners else '#cbd5e1' if p in native else '#707d91'
            if c.type==24:color='#e58a9f'
            if c.type==25:color='#25384f'
            d.rectangle((px,py,px+scale-1,py+scale-1),fill=color)
    d.text((28,im.height-50),'Тёмная рамка — настоящие стеночки; проходы в ней оставлены для сигнальных контактов.',font=font(17),fill='#55647a')
    d.text((28,im.height-26),'Внешний контроллер включён в сохранение и показан на отдельном полном предпросмотре.',font=font(17),fill='#55647a')
    path=BUILD/(stem+'.nets.preview.png');im.save(path)
    print('Physical wall-grid preview:',path,flush=True)
    return path


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stem');p.add_argument('--layout');p.add_argument('--board-size',type=int);a=p.parse_args()
    render_nets(a.stem,a.layout)
    if a.board_size:render_board_nets(a.board_size)
