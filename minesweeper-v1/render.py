"""Previews from reimported physical saves and measured GraphDLC outputs."""
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json
from snap import BUILD,HERE
from logic import ROOT
from mapdata import read_map
from arrow_layout import bounds_of,destinations

COLORS={1:'#64748b',7:'#dd697f',10:'#3899d6',11:'#3899d6',12:'#3899d6',13:'#3899d6',14:'#3899d6',
        15:'#a778d6',16:'#a778d6',17:'#a778d6',18:'#e6a440',19:'#e6a440',20:'#55a675',24:'#d55469',25:'#25384f',2:'#55a675'}
def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)

def cell_preview():
    cells=read_map(BUILD/'cell.save.txt');meta=json.loads((BUILD/'cell.layout.json').read_text())
    return framed_preview(cells,meta)

def framed_preview(cells,meta,stem='cell'):
    side=meta['side'];scale=7;left=30;top=112
    im=Image.new('RGB',(side*scale+60,side*scale+190),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((28,18),'Сапёр v1 — стыкуемая ячейка',font=font(28),fill='#172c45')
    d.text((28,58),f'Рамка {side}×{side} • {len(cells)} стрелок • BCD внутри',font=font(17),fill='#55647a')
    d.text((28,82),'Число → кнопка 5×5 → мина 8×8',font=font(17),fill='#55647a')
    center=side//2
    radius=meta.get('cavity_radius',32)
    a,b,c,e=meta.get('panel_bounds',(center-radius,center-radius,center+radius,center+radius))
    d.rectangle((left+a*scale,top+b*scale,left+(c+1)*scale,top+(e+1)*scale),fill='white')
    sprites={}
    for (x,y),c in cells.items():
        px=left+x*scale;py=top+y*scale;token=c.type,c.rotation,c.mirrored
        d.rectangle((px,py,px+scale-1,py+scale-1),fill=COLORS.get(c.type,'#64748b'))
        if token not in sprites:
            sp=Image.open(ROOT/f'ArrowsHDL/assets/sprites/arrow{c.type}.png').convert('RGBA')
            if c.mirrored:sp=ImageOps.mirror(sp)
            sprites[token]=sp.rotate(-90*c.rotation).resize((scale-1,scale-1),Image.Resampling.LANCZOS)
        im.paste(sprites[token],(px,py),sprites[token])
    d.rectangle((left-2,top-2,left+side*scale+1,top+side*scale+1),outline='#294e71',width=2)
    x,y=meta['display_origin'];bx,by=meta['button'][0]
    d.rectangle((left+(x+6)*scale-4,top+y*scale-4,left+(x+14)*scale+4,top+(y+14)*scale+4),outline='#117b92',width=2)
    bs=meta.get('button_size',3)
    d.rectangle((left+bx*scale-4,top+by*scale-4,left+(bx+bs)*scale+4,top+(by+bs)*scale+4),outline='#b82b48',width=2)
    if 'mine_indicator' in meta:
        mx,my=meta['mine_indicator']['origin']
        d.rectangle((left+mx*scale-3,top+my*scale-3,left+(mx+8)*scale+3,top+(my+8)*scale+3),outline='#b82b48',width=2)
    dx,dy=meta['decoder_origin']
    if not meta.get('logic_decoder'):d.rectangle((left+dx*scale-3,top+dy*scale-3,left+(dx+14)*scale+3,top+(dy+22)*scale+3),outline='#654793',width=2)
    d.text((28,im.height-58),'Копии стыкуются вплотную; контакты противоположных сторон совпадают.',font=font(15),fill='#55647a')
    d.text((28,im.height-34),'Бирюзовый — дисплей. Красный — кнопка. Фиолетовый — внутренний декодер.',font=font(15),fill='#55647a')
    im.save(BUILD/(stem+'.preview.png'))

def panel_preview(stem='cell'):
    cells=read_map(BUILD/(stem+'.save.txt'));meta=json.loads((BUILD/(stem+'.layout.json')).read_text())
    a,b,c,e=meta['panel_bounds'];a-=3;b-=3;c+=3;e+=3;scale=18
    im=Image.new('RGB',((c-a+1)*scale+56,(e-b+1)*scale+175),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((24,17),'Число → кнопка 5×5 → мина 8×8',font=font(26),fill='#172c45')
    d.text((24,57),'Физическая компоновка центра ячейки',font=font(18),fill='#55647a')
    pa,pb,pc,pe=meta['panel_bounds']
    d.rectangle((28+(pa-a)*scale,92+(pb-b)*scale,28+(pc-a+1)*scale-1,92+(pe-b+1)*scale-1),fill='white')
    pixels=set(map(tuple,meta['mine_indicator']['pixels']));button=set(map(tuple,meta['button']));sprites={}
    for (x,y),cell in cells.items():
        if not(a<=x<=c and b<=y<=e):continue
        px=28+(x-a)*scale;py=92+(y-b)*scale
        fill='#df8193' if (x,y) in pixels or (x,y) in button else '#d5dee8'
        d.rectangle((px,py,px+scale-1,py+scale-1),fill=fill)
        token=cell.type,cell.rotation,cell.mirrored
        if token not in sprites:
            sp=Image.open(ROOT/f'ArrowsHDL/assets/sprites/arrow{cell.type}.png').convert('RGBA')
            if cell.mirrored:sp=ImageOps.mirror(sp)
            sprites[token]=sp.rotate(-90*cell.rotation).resize((scale-2,scale-2),Image.Resampling.LANCZOS)
        im.paste(sprites[token],(px+1,py+1),sprites[token])
    d.text((24,im.height-55),'Число слева. Мина справа. Их центры на одной высоте.',font=font(17),fill='#55647a')
    d.text((24,im.height-31),'Кнопка 5×5 между индикаторами. Вокруг — белый отступ.',font=font(17),fill='#55647a')
    im.save(BUILD/(stem+'.panel.preview.png'))

def status_preview(size=5):
    stem=f'minesweeper-{size}x{size}'
    cells=read_map(BUILD/(stem+'.save.txt'))
    meta=json.loads((BUILD/(stem+'.layout.json')).read_text())
    observations=json.loads((BUILD/(stem+'.status.observed.json')).read_text())
    assert observations['map_hash']==meta['map_hash']
    scale=12; panel_width=600
    im=Image.new('RGB',(3*panel_width,690),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((24,18),'Сапёр v1 — WIN / LOSE, шрифт ×2',font=font(30),fill='#172c45')
    d.text((24,61),'Формы из указанного алфавита. Свечение всех пикселей измерено в GraphDLC.',font=font(20),fill='#55647a')
    for column,(frame,title) in enumerate((('cold','До завершения'),('victory','Победа'),('defeat','Поражение'))):
        left=column*panel_width+24;top=150
        d.text((left,112),title,font=font(25),fill='#172c45')
        values=observations['frames'].get(frame,{})
        for (x,y),cell in cells.items():
            if not (118<=x<166 and -66<=y<-26):continue
            px=left+(x-118)*scale;py=top+(y+66)*scale
            d.rectangle((px,py,px+scale-2,py+scale-2),fill='#e2e8f0')
        for name,display in meta['status']['displays'].items():
            for j,(x,y) in enumerate(display['pixels']):
                px=left+(x-118)*scale;py=top+(y+66)*scale
                active=values.get(f'{name}:pixel{j}',0)
                d.rectangle((px,py,px+scale-1,py+scale-1),fill='#5138b2' if active else '#c8cdd7')
    d.text((24,im.height-37),'WIN: 28×8 клеток. LOSE: 38×8. Слова состоят из настоящих стрелок схемы.',font=font(20),fill='#55647a')
    im.save(BUILD/(stem+'.status.preview.png'))

def diagonal_preview():
    from diagonal_ports import OFFSETS,OPPOSITE,LANES
    template=read_map(BUILD/'cell.save.txt');meta=json.loads((BUILD/'cell.layout.json').read_text())
    if not meta.get('diagonal_contacts'):return
    side=meta['side'];scale=24;lo=side-10;width=20
    cells={(x+dx*side,y+dy*side):c for dx in (0,1) for dy in (0,1) for (x,y),c in template.items()}
    colours={'M':'#df8193','Z':'#73bfd7','S':'#86c796'};highlight={}
    for direction,(dx,dy) in OFFSETS.items():
        ox=side if dx<0 else 0;oy=side if dy<0 else 0
        for field in LANES:
            p=meta['outputs'][f'DG:{direction}{field}'][0]['contact'];p=(p[0]+ox,p[1]+oy)
            q=meta['inputs'][f'DG:{OPPOSITE[direction]}{field}'][0]['contact']
            target=(q[0]+ox+dx*side,q[1]+oy+dy*side)
            while True:
                highlight[p]=colours[field]
                if p==target:break
                p=next(destinations(p,cells[p]))
    im=Image.new('RGB',(width*scale+56,width*scale+175),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((24,16),'Угловые каналы четырёх модулей',font=font(24),fill='#172c45')
    d.text((24,54),'M — мина   Z — каскад   S — первый ход',font=font(19),fill='#55647a')
    sprites={}
    for (x,y),c in cells.items():
        if not(lo<=x<lo+width and lo<=y<lo+width):continue
        px=28+(x-lo)*scale;py=92+(y-lo)*scale
        colour=highlight.get((x,y),'#25384f' if c.type==25 else '#dde3eb')
        d.rectangle((px,py,px+scale-1,py+scale-1),fill=colour)
        token=c.type,c.rotation,c.mirrored
        if token not in sprites:
            sp=Image.open(ROOT/f'ArrowsHDL/assets/sprites/arrow{c.type}.png').convert('RGBA')
            if c.mirrored:sp=ImageOps.mirror(sp)
            sprites[token]=sp.rotate(-90*c.rotation).resize((scale-3,scale-3),Image.Resampling.LANCZOS)
        im.paste(sprites[token],(px+1,py+1),sprites[token])
    edge=28+10*scale;horizontal=92+10*scale
    d.line((edge,92,edge,92+width*scale),fill='#ec9b29',width=2)
    d.line((28,horizontal,28+width*scale,horizontal),fill='#ec9b29',width=2)
    d.text((24,im.height-55),'Цвет — назначение цепи. Линии — границы модулей.',font=font(16),fill='#55647a')
    d.text((24,im.height-31),'Все показанные стрелки взяты из готового сохранения.',font=font(16),fill='#55647a')
    im.save(BUILD/'cell.diagonal.preview.png')

def board_preview(size=10):
    stem=f'minesweeper-{size}x{size}'
    cells=read_map(BUILD/(stem+'.save.txt'));meta=json.loads((BUILD/(stem+'.layout.json')).read_text())
    b=bounds_of(cells);scale=max(1,min(2,2800//b['width']))
    im=Image.new('RGB',(b['width']*scale+60,b['height']*scale+160),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((24,15),f'Сапёр v1 — физическая схема {size}×{size}',font=font(28),fill='#172c45')
    d.text((24,58),f'{len(cells):,} стрелок • {size*size} модулей • независимые случайные мины • безопасный первый ход',font=font(18),fill='#55647a')
    for (x,y),c in cells.items():
        px=30+(x-b['min'][0])*scale;py=110+(y-b['min'][1])*scale
        d.rectangle((px,py,px+scale-1,py+scale-1),fill=COLORS.get(c.type,'#64748b'))
    for display in meta.get('status',{}).get('displays',{}).values():
        for x,y in display['pixels']:
            px=30+(x-b['min'][0])*scale;py=110+(y-b['min'][1])*scale
            d.rectangle((px,py,px+scale-1,py+scale-1),fill='#5844bc')
    for i,t in enumerate(meta['tiles']):
        if 'origin' in t:x,y=t['origin']
        else:x=t['inputs']['m0'][0]['contact'][0];y=t['inputs']['m0'][0]['contact'][1]
        px=30+(x-b['min'][0])*scale;py=110+(y-b['min'][1])*scale
        d.text((px,py-17),f'{i%size+1}:{i//size+1}',font=font(12),fill='#172c45')
    im.save(BUILD/(stem+'.preview.png'))

def measured_preview(size=10,defeat=False):
    stem=f'minesweeper-{size}x{size}'
    suffix='.defeat.demo' if defeat else '.demo'
    demo=json.loads((BUILD/(stem+suffix+'.json')).read_text());values=demo['measured'];tile=68
    meta=json.loads((BUILD/(stem+'.layout.json')).read_text());marker=meta['cell'].get('mine_indicator')
    im=Image.new('RGB',(max(760,size*tile+64),size*tile+190),'#f8fafc');d=ImageDraw.Draw(im)
    title='поражение, все мины показаны' if defeat else 'первый ход'
    d.text((28,18),f'Сапёр v1 — {title}, {size}×{size}',font=font(25),fill='#172c45')
    d.text((28,58),'Состояние измерено на физических выходах схемы через GraphDLC',font=font(17),fill='#55647a')
    for i in range(size*size):
        x=28+(i%size)*tile;y=110+(i//size)*tile
        mine_visible=bool(values.get(f'{i}:minePixel0',0))
        opened=bool(values[f'{i}:opened']) or mine_visible
        d.rounded_rectangle((x,y,x+tile-5,y+tile-5),radius=5,fill='#e3f3f1' if opened else '#c6d0df',outline='#6b829d',width=1)
        if f'{i}:segment0' in values:
            # Seven actual segment register states of the supplied display.
            bars=((x+6,y+13,x+18,y+15),(x+17,y+15,x+20,y+24),
                  (x+17,y+26,x+20,y+35),(x+6,y+35,x+18,y+37),
                  (x+4,y+26,x+7,y+35),(x+4,y+15,x+7,y+24),
                  (x+6,y+24,x+18,y+26))
            for j,rectangle in enumerate(bars):
                if values[f'{i}:segment{j}']:d.rectangle(rectangle,fill='#16655c')
        else:
            for k in range(15):
                px=x+34+5*(k%3);py=y+10+5*(k//3)
                if values[f'{i}:p{k}']:d.rectangle((px,py,px+3,py+3),fill='#16655c')
        marker_points=[(p[0]-marker['origin'][0],p[1]-marker['origin'][1]) for p in marker['pixels']] if marker else ((0,0),(2,0),(1,1),(0,2),(2,2))
        for j,(mx,my) in enumerate(marker_points):
            if values.get(f'{i}:minePixel{j}',0):
                px=x+45+2*mx;py=y+18+2*my
                d.rectangle((px,py,px+1,py+1),fill='#b52b49')
        for row in range(meta['cell'].get('button_size',3)):
            for col in range(meta['cell'].get('button_size',3)):
                px=x+27+3*col;py=y+19+3*row
                d.rectangle((px,py,px+1,py+1),fill='#94aaa7' if opened else '#be3c58')
        if i==demo['first']:d.rounded_rectangle((x+2,y+2,x+tile-7,y+tile-7),radius=4,outline='#ec9b29',width=2)
    caption='LOSE: показаны все мины; дальнейшие нажатия не раскрывают клетки.' if defeat else 'Закрыта: цифра погашена. Открыта: число 0–8. Кнопка 5×5 между индикаторами.'
    d.text((28,im.height-54),caption,font=font(16),fill='#55647a')
    im.save(BUILD/(stem+suffix+'.png'))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=10);p.add_argument('--cell-only',action='store_true');a=p.parse_args()
    cell_preview()
    panel_preview()
    diagonal_preview()
    if not a.cell_only:board_preview(a.size);measured_preview(a.size);measured_preview(a.size,True);status_preview(a.size)
