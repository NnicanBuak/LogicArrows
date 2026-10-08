"""Previews from reimported physical saves and measured GraphDLC outputs."""
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json
from snap import BUILD,HERE
from logic import ROOT
from mapdata import read_map
from arrow_layout import bounds_of

COLORS={1:'#64748b',7:'#dd697f',10:'#3899d6',11:'#3899d6',12:'#3899d6',13:'#3899d6',14:'#3899d6',
        15:'#a778d6',16:'#a778d6',17:'#a778d6',18:'#e6a440',19:'#e6a440',20:'#55a675',24:'#d55469',2:'#55a675'}
def font(n):return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)

def cell_preview():
    cells=read_map(BUILD/'cell.save.txt');meta=json.loads((BUILD/'cell.layout.json').read_text())
    return framed_preview(cells,meta)

def framed_preview(cells,meta,stem='cell'):
    side=meta['side'];scale=7;left=30;top=112
    im=Image.new('RGB',(side*scale+60,side*scale+190),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((28,18),'Сапёр v1 — стыкуемая ячейка',font=font(28),fill='#172c45')
    d.text((28,58),f'Рамка {side}×{side} • {len(cells)} стрелок • BCD внутри',font=font(17),fill='#55647a')
    d.text((28,82),'Дисплей 0–8 и кнопка 3×3 в центре',font=font(17),fill='#55647a')
    center=side//2
    radius=meta.get('cavity_radius',32)
    a,b,c,e=meta.get('panel_bounds',(center-radius,center-radius,center+radius,center+radius))
    d.rectangle((left+a*scale,top+b*scale,left+(c+1)*scale,top+(e+1)*scale),fill='#e9f2f0')
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
    d.rectangle((left+bx*scale-4,top+by*scale-4,left+(bx+3)*scale+4,top+(by+3)*scale+4),outline='#b82b48',width=2)
    dx,dy=meta['decoder_origin']
    if not meta.get('logic_decoder'):d.rectangle((left+dx*scale-3,top+dy*scale-3,left+(dx+14)*scale+3,top+(dy+22)*scale+3),outline='#654793',width=2)
    d.text((28,im.height-58),'Копии стыкуются вплотную; контакты противоположных сторон совпадают.',font=font(15),fill='#55647a')
    d.text((28,im.height-34),'Бирюзовый — дисплей. Красный — кнопка. Фиолетовый — внутренний декодер.',font=font(15),fill='#55647a')
    im.save(BUILD/(stem+'.preview.png'))

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
    for i,t in enumerate(meta['tiles']):
        if 'origin' in t:x,y=t['origin']
        else:x=t['inputs']['m0'][0]['contact'][0];y=t['inputs']['m0'][0]['contact'][1]
        px=30+(x-b['min'][0])*scale;py=110+(y-b['min'][1])*scale
        d.text((px,py-17),f'{i%size+1}:{i//size+1}',font=font(12),fill='#172c45')
    im.save(BUILD/(stem+'.preview.png'))

def measured_preview(size=10):
    stem=f'minesweeper-{size}x{size}'
    demo=json.loads((BUILD/(stem+'.demo.json')).read_text());values=demo['measured'];tile=68
    im=Image.new('RGB',(max(760,size*tile+64),size*tile+190),'#f8fafc');d=ImageDraw.Draw(im)
    d.text((28,18),f'Сапёр v1 — первый ход на поле {size}×{size}',font=font(28),fill='#172c45')
    d.text((28,58),'Состояние измерено на физических выходах схемы через GraphDLC',font=font(17),fill='#55647a')
    for i in range(size*size):
        x=28+(i%size)*tile;y=110+(i//size)*tile;opened=bool(values[f'{i}:opened'])
        d.rounded_rectangle((x,y,x+tile-5,y+tile-5),radius=5,fill='#e3f3f1' if opened else '#c6d0df',outline='#6b829d',width=1)
        if f'{i}:segment0' in values:
            # Seven actual segment register states of the supplied display.
            bars=((x+31,y+8,x+46,y+11),(x+45,y+10,x+48,y+22),
                  (x+45,y+24,x+48,y+36),(x+31,y+35,x+46,y+38),
                  (x+29,y+24,x+32,y+36),(x+29,y+10,x+32,y+22),
                  (x+31,y+22,x+46,y+25))
            for j,rectangle in enumerate(bars):
                if values[f'{i}:segment{j}']:d.rectangle(rectangle,fill='#16655c')
        else:
            for k in range(15):
                px=x+34+5*(k%3);py=y+10+5*(k//3)
                if values[f'{i}:p{k}']:d.rectangle((px,py,px+3,py+3),fill='#16655c')
        for row in range(3):
            for col in range(3):
                px=x+8+5*col;py=y+40+5*row
                d.rectangle((px,py,px+3,py+3),fill='#94aaa7' if opened else '#be3c58')
        if i==demo['first']:d.rounded_rectangle((x+2,y+2,x+tile-7,y+tile-7),radius=4,outline='#ec9b29',width=2)
    d.text((28,im.height-54),'Закрыта: цифра погашена. Открыта: видимое число 0–8. Красные точки — кнопка 3×3.',font=font(16),fill='#55647a')
    im.save(BUILD/(stem+'.demo.png'))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=10);p.add_argument('--cell-only',action='store_true');a=p.parse_args()
    cell_preview()
    if not a.cell_only:board_preview(a.size);measured_preview(a.size)
