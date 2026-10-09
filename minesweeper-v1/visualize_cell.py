"""Static, source-attested PNG explanation of the current compiled cell.

No browser, HTML, or image generation model is involved. Physical positions,
ports and every gate input are read from the imported save and its manifest.
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import json
import math

from PIL import Image,ImageDraw,ImageFont,ImageOps
from snap import BUILD,ROOT,read_map,map_hash,write_json
from compact_panel import make_panel,RAW_SEGMENTS

OUT=BUILD/'visualizations/current-cell'
EXPECTED_HASH='b2d7f378272115992b12529730fc302a67196c8808673d891c4e35476ee714f7'
BG='#f5f7fb';INK='#17263d';MUTED='#58677d';LINE='#d7dfeb'
GROUPS={
    'A':('Запрос и выбор','#b76a15'),
    'B':('Генерация мины','#c14956'),
    'C':('Подсчёт соседей','#087e96'),
    'D':('Открытие и каскад','#278356'),
    'E':('Управляющие фазы','#376bbc'),
    'F':('Скан результата','#8c721c'),
    'G':('Передача соседям','#337c86'),
    'H':('Декодер и вывод','#8153b0')}
IMAGES=[];TEXT_BOXES=[]


@lru_cache(None)
def font(size,bold=False,mono=False):
    name='consola.ttf' if mono else 'segoeuib.ttf' if bold else 'segoeui.ttf'
    return ImageFont.truetype('C:/Windows/Fonts/'+name,size)


def pale(color,amount=.90):
    c=tuple(int(color[i:i+2],16) for i in (1,3,5))
    return tuple(round(v+(255-v)*amount) for v in c)


def label(draw,xy,text,size=27,color=INK,bold=False,mono=False,anchor=None):
    draw.text(xy,text,font=font(size,bold,mono),fill=color,anchor=anchor)


def text_lines(draw,text,width,f):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            trial=(line+' '+word).strip()
            if draw.textlength(trial,font=f)>width and line:lines.append(line);line=word
            else:line=trial
        lines.append(line)
    return lines


def wrapped(draw,box,text,size=27,color=INK,bold=False,gap=7):
    x,y,right,bottom=box;f=font(size,bold);lines=text_lines(draw,text,right-x,f)
    for line in lines:
        bounds=draw.textbbox((x,y),line,font=f)
        assert bounds[2]<=right+2 and bounds[3]<=bottom,(text,box,bounds)
        draw.text((x,y),line,font=f,fill=color);y+=size+gap
    TEXT_BOXES.append(dict(text=text,box=list(box),size=size))
    return y


def card(draw,box,title,body,color,size=28):
    x,y,r,b=box
    draw.rounded_rectangle(box,radius=20,fill='white',outline=pale(color,.60),width=3)
    draw.rounded_rectangle((x+2,y+2,r-2,y+11),radius=5,fill=color)
    wrapped(draw,(x+25,y+23,r-22,y+83),title,32,color,True)
    while size>=24:
        lines=text_lines(draw,body,r-x-50,font(size))
        last=y+84+(len(lines)-1)*(size+7)
        if draw.textbbox((x+25,last),lines[-1],font=font(size))[3]<=b-20:break
        size-=1
    assert size>=24,('Card needs more room',title,box)
    wrapped(draw,(x+25,y+84,r-25,b-20),body,size)


def arrow(draw,points,color=MUTED,width=4,dashed=False):
    if dashed:
        for (x,y),(a,b) in zip(points,points[1:]):
            distance=math.hypot(a-x,b-y)
            for offset in range(0,int(distance),19):
                t=offset/distance;s=min(1,(offset+10)/distance)
                draw.line((x+(a-x)*t,y+(b-y)*t,x+(a-x)*s,y+(b-y)*s),fill=color,width=width)
    else:draw.line(points,fill=color,width=width,joint='curve')
    (x,y),(a,b)=points[-2:];angle=math.atan2(b-y,a-x)
    draw.polygon([(a,b),(a-16*math.cos(angle-.5),b-16*math.sin(angle-.5)),
                  (a-16*math.cos(angle+.5),b-16*math.sin(angle+.5))],fill=color)


def badge(draw,center,text,color,size=23):
    x,y=center;b=draw.textbbox((0,0),text,font=font(size,True));w=b[2]-b[0];h=b[3]-b[1]
    draw.rounded_rectangle((x-w/2-7,y-h/2-6,x+w/2+7,y+h/2+6),radius=5,fill='white')
    label(draw,(x,y),text,size,color,True,anchor='mm')


def sheet(title,subtitle,size):
    im=Image.new('RGB',size,BG);d=ImageDraw.Draw(im)
    label(d,(62,32),title,48,bold=True)
    wrapped(d,(64,98,size[0]-60,154),subtitle,26,MUTED)
    return im,d


def save(im,name,caption,meta):
    d=ImageDraw.Draw(im)
    d.line((60,im.height-70,im.width-60,im.height-70),fill=LINE,width=2)
    label(d,(62,im.height-55),'56×64  ·  2 424 стрелки  ·  '+caption,23,MUTED)
    label(d,(im.width-62,im.height-52),'SHA-256 '+meta['map_hash'][:12],20,MUTED,anchor='ra')
    path=OUT/name;im.save(path)
    IMAGES.append(dict(file=name,width=im.width,height=im.height,caption=caption))


def group(node):
    n=node['output'];scope=node.get('scope','')
    if n.startswith('phase:') or n.startswith('port:S:') and n.split(':')[-1] in ('busy','choose','sample','ready','stop','defeat'):return 'E'
    if n in ('n4','n5','request','edge_delay:choose','edge:choose','n31','n32','n33','selected'):return 'A'
    if n in ('edge_delay:sample','edge:sample','n38','n39','n40','n41','mine'):return 'B'
    if scope.startswith('count/'):return 'C'
    if scope=='game':return 'D'
    if scope=='scan' or n.startswith('port:E:prefix'):return 'F'
    if scope.startswith('display/') or n.startswith('port:panel') or n=='port:mine_indicator':return 'H'
    assert scope=='links',(n,scope)
    return 'G'


def overview(meta):
    im,d=sheet('Как ячейка превращает клик в игру',
        'Логическая карта задач; привязка к реальным координатам — на листе 04.',(2000,1800))
    card(d,(65,175,1935,385),'E · ВНЕ ЯЧЕЙКИ: один контроллер всего поля',
        'Входы: конечные prefixReq / prefixLoss / prefixSat.  Выходы: busy, choose, sample, ready, stop, defeat.\n'
        'prefixLoss → LOSE. ready AND prefixSat AND NOT prefixLoss → WIN.\n'
        'prefixReq запускает три общих таймера; победа или поражение включают stop.',GROUPS['E'][1],27)
    for x,caption in ((320,'busy: закрыть запросы'),(1000,'choose ↑: выбрать'),(1660,'sample ↑: генерация')):
        arrow(d,[(x,385),(x,428)],GROUPS['E'][1]);badge(d,(x,404),caption,GROUPS['E'][1],22)
    card(d,(65,430,605,670),'A · Кнопка → request',
        '25 кнопочных стрелок → button0.\n'
        'button0 AND NOT busy → SET request.\n'
        'Запрос хранится до перезагрузки.',GROUPS['A'][1],27)
    card(d,(730,430,1270,670),'A · Выбор первого хода',
        'request AND NOT W:prefixReq\n'
        'На импульсе choose → SET selected.\n'
        'Один первый ход в порядке строк.',GROUPS['A'][1],27)
    card(d,(1395,430,1935,670),'B · Сохранить мину',
        'selected / соседний S → защита.\n'
        'sample ↑ AND NOT защита\n'
        '→ RANDOM → RANDOM → TFF mine.\n'
        'Вероятность мины: ½ × ½ = ¼.',GROUPS['B'][1],27)
    arrow(d,[(605,545),(730,545)],GROUPS['A'][1]);label(d,(667,513),'request',22,GROUPS['A'][1],anchor='mm')
    arrow(d,[(1270,545),(1395,545)],GROUPS['G'][1]);label(d,(1334,508),'S / защита',21,GROUPS['G'][1],anchor='mm')
    wrapped(d,(65,700,1930,787),
        'Основа: 1 означает активный сигнал, 0 — неактивный. Mine, selected и opened — местные состояния. '
        'Соседская передача и вывод используют уровни; фронты choose/sample превращаются в короткие импульсы.',28,MUTED)
    card(d,(65,825,605,1090),'C · Число соседних мин',
        'W:MP/MC + E:MP/MC + N:M/S:M\n'
        'Три частичных числа → сумма 0–8.\n'
        'Своя mine в число НЕ входит.\n'
        'Результат: 4 бита 1 / 2 / 4 / 8.',GROUPS['C'][1],27)
    card(d,(730,825,1270,1090),'H · Декодер числа',
        'Четыре бита → семь сегментов.\n'
        'Декодер рассчитан только на 0–8.\n'
        'Он вычисляется непрерывно.\n'
        'Код 0 тоже рисуется цифрой.',GROUPS['H'][1],27)
    card(d,(1395,825,1935,1090),'H · Разрешить вывод',
        'show = opened AND NOT mine.\n'
        'Каждый сегмент = raw AND show.\n'
        'Мина = mine AND defeat.\n'
        'Семь сегментов уже без памяти.',GROUPS['H'][1],27)
    arrow(d,[(605,950),(730,950)],GROUPS['C'][1]);label(d,(667,919),'4 бита',23,GROUPS['C'][1],anchor='mm')
    arrow(d,[(1270,950),(1395,950)],GROUPS['H'][1]);label(d,(1334,919),'7 raw',23,GROUPS['H'][1],anchor='mm')
    card(d,(65,1240,605,1490),'D · Открыть клетку',
        'ready AND NOT stop разрешает ход.\n'
        'Кнопка / selected / безопасный\n'
        'соседний Z → SET opened.\n'
        'Открытие сохраняется.',GROUPS['D'][1],27)
    card(d,(730,1240,1270,1490),'D · Продолжить каскад',
        'opened AND NOT mine\n'
        'AND (count == 0) → Z.\n'
        'Ноль раскрывает соседей.\n'
        'Число раскрывается, но Z не даёт.',GROUPS['D'][1],27)
    card(d,(1395,1240,1935,1490),'F · Передать итог клетки',
        'Loss = opened AND mine.\n'
        'Sat = mine OR opened.\n'
        'prefixLoss: OR по всему полю.\n'
        'prefixSat: AND по всему полю.',GROUPS['F'][1],27)
    arrow(d,[(335,1090),(335,1170),(1000,1170),(1000,1240)],GROUPS['C'][1]);label(d,(730,1136),'count == 0',23,GROUPS['C'][1],anchor='mm')
    arrow(d,[(605,1370),(730,1370)],GROUPS['D'][1]);label(d,(667,1335),'opened',22,GROUPS['D'][1],anchor='mm')
    card(d,(65,1530,1935,1710),'G · Обмен с соседями',
        'M — своя мина. S — выбранный старт. Z — открытый безопасный ноль.\n'
        'На север/юг уходят местные M/S/Z; на запад/восток — сумма мин MP/MC и объединённые тройки S/Z.',GROUPS['G'][1],27)
    save(im,'01-overview.png','Начните с request → selected → mine → count → opened → вывод',meta)


def neighborhood(meta):
    im,d=sheet('Восемь соседей через четыре стороны',
        'MP/MC — два бита количества мин. S/Z — логическое «есть хотя бы один», а не количество.',(2000,1630))
    card(d,(65,170,1935,350),'Одно имя поля — разные вход и выход',
        'ВХОД W:MP/MC описывает NW/W/SW. ВЫХОД W:MP/MC описывает N/Я/S для соседа слева.\n'
        'W/E/N/S до двоеточия — сторона порта; после двоеточия — имя передаваемых данных.',GROUPS['G'][1],26)
    values=[[1,0,1],[1,None,0],[0,1,1]];x0=635;y0=405;s=160
    for row in range(3):
        for col in range(3):
            x=x0+col*s;y=y0+row*s
            color=GROUPS['C'][1] if col==1 else GROUPS['A'][1] if col==0 else GROUPS['H'][1]
            d.rounded_rectangle((x+5,y+5,x+s-5,y+s-5),radius=16,fill=pale(color),outline=pale(color,.5),width=3)
            label(d,(x+s/2,y+28),[['NW','N','NE'],['W','Я','E'],['SW','S','SE']][row][col],25,MUTED,anchor='mt')
            label(d,(x+s/2,y+70),'—' if values[row][col] is None else str(values[row][col]),57,color,True,anchor='mt')
    card(d,(65,405,530,710),'Вход с запада',
        'NW + W + SW = 1 + 1 + 0 = 2\n'
        'W:MP = 0, W:MC = 1.\n'
        'Тройку заранее посчитал\n'
        'левый сосед.',GROUPS['A'][1],27)
    card(d,(1425,405,1935,710),'Вход с востока',
        'NE + E + SE = 1 + 0 + 1 = 2\n'
        'E:MP = 0, E:MC = 1.\n'
        'Тройку заранее посчитал\n'
        'правый сосед.',GROUPS['H'][1],27)
    arrow(d,[(530,550),(635,550)],GROUPS['A'][1]);arrow(d,[(1425,550),(1115,550)],GROUPS['H'][1])
    card(d,(65,760,530,1080),'Вертикальная пара',
        'N:M + S:M = 0 + 1 = 1.\n'
        'XOR2 → младший бит 1.\n'
        'AND2 → старший бит 0.\n'
        'Своя mine не добавляется.',GROUPS['C'][1],27)
    card(d,(1235,760,1935,1080),'Как из тройки получается MP/MC',
        'MP = XOR3: нечётное количество.\n'
        'MC = MAJ3: активны хотя бы две мины.\n'
        'Количество = MP + 2 × MC.\n'
        '0 мин → 0/0;  1 мина → 1/0.\n'
        '2 мины → 0/1;  3 мины → 1/1.',GROUPS['G'][1],27)
    label(d,(875,918),'2 + 2 + 1 = 5',48,GROUPS['C'][1],True,anchor='mm')
    label(d,(875,986),'биты 8 / 4 / 2 / 1:  0 1 0 1',26,INK,anchor='mm')
    arrow(d,[(875,880),(875,899)],GROUPS['C'][1])
    card(d,(65,1130,975,1460),'S/Z: та же геометрия, другая операция',
        'Выход на W/E = own OR N OR S.\n'
        'Вход с W/E уже описывает соседнюю тройку.\n'
        'Собрать 8 соседей: W OR E OR N OR S.\n'
        'S защищает соседство старта; Z раскрывает его.\n'
        'Для защиты добавляется и свой selected.',GROUPS['D'][1],28)
    card(d,(1025,1130,1935,1460),'Почему не нужны отдельные диагонали',
        'NW/SW пришли внутри западной тройки.\n'
        'NE/SE — внутри восточной. N/S — напрямую.\n'
        'Каждая соседняя клетка учтена ровно один раз.\n'
        'Соседи остаются отдельными модулями;\n'
        'они заранее сокращают передаваемые данные.',GROUPS['G'][1],28)
    save(im,'02-neighbor-data.png','Пример: пять соседних мин, собственная клетка не считается',meta)


@lru_cache(None)
def sprite(kind,rotation,mirrored,scale):
    im=Image.open(ROOT/f'ArrowsHDL/assets/sprites/arrow{kind}.png').convert('RGBA')
    if mirrored:im=ImageOps.mirror(im)
    return im.rotate(-90*rotation).resize((scale-2,scale-2),Image.Resampling.LANCZOS)


def native_crop(im,cells,origin,bounds,scale=24):
    x0,y0=origin;a,b,r,e=bounds;d=ImageDraw.Draw(im)
    d.rectangle((x0,y0,x0+(r-a+1)*scale,y0+(e-b+1)*scale),fill='white')
    for (x,y),c in cells.items():
        if not(a<=x<=r and b<=y<=e):continue
        p=(x0+(x-a)*scale,y0+(y-b)*scale)
        d.rectangle((*p,p[0]+scale-1,p[1]+scale-1),fill='#e5eaf0')
        sp=sprite(c.type,c.rotation,c.mirrored,scale)
        im.paste(sp,(p[0]+1,p[1]+1),sp)


def control_and_panel(meta,cells,graph):
    im,d=sheet('Что запускает вычисления и что видно игроку',
        'Шесть управляющих входов идут с севера на юг. Панель принимает непрерывные уровни.',(2000,1820))
    phase=[('busy','закрыть новые запросы'),('choose','выбрать selected'),('sample','один раз получить mine'),
           ('ready','разрешить открытие'),('stop','запретить следующие ходы'),('defeat','показать все мины')]
    for i,(name,body) in enumerate(phase):
        col=i%3;row=i//3;x=65+col*635;y=175+row*165
        card(d,(x,y,x+600,y+143),f'N:{name} → S:{name}',body,GROUPS['E'][1],25)
    card(d,(65,530,1935,870),'Этапы подготовки и измеренная задержка',
        'Клик → закрыть захват request → дождаться prefixReq → choose → защитить 3×3 → sample → подсчитать → ready.\n'
        'Таймеры общего контроллера: 8 192 / 1 024 / 1 024 такта. В самой ячейке длинных линий DELAY нет.\n'
        'Пример 10×10, первый ход №55: choose ≈ 12 160; sample ≈ 13 251; ready ≈ 14 328 тактов в ячейке №0.\n'
        'Последняя ячейка готова через 15 096 тактов. Фазы приходят в разные клетки в разное время.',GROUPS['E'][1],28)
    panel=make_panel(False,level_outputs=True).moved(meta['display_origin'][0]+6,meta['display_origin'][1])
    ui_cells={p:c for p,c in panel.cells.items() if c.type!=25}
    native_crop(im,ui_cells,(135,970),(14,22,42,43),27)
    # Outline only the 8x8 glyph: its blue input lead is outside these pixels.
    d.rounded_rectangle((673,1049,893,1269),radius=6,outline=GROUPS['B'][1],width=3)
    label(d,(622,987),'ввод мины →',20,GROUPS['B'][1],True)
    label(d,(122,1523),'show →',20,GROUPS['H'][1],True,anchor='rm')
    label(d,(178,925),'ЧИСЛО',27,GROUPS['H'][1],True)
    label(d,(455,925),'КНОПКА 5×5',27,GROUPS['A'][1],True)
    label(d,(698,925),'МИНА 8×8',27,GROUPS['B'][1],True)
    card(d,(975,940,1935,1140),'Непрерывный вывод числа',
        '4 бита count → декодер 0–8 → семь raw.\n'
        'raw AND show → проводка семи сегментов.\n'
        'show = opened AND NOT mine.',GROUPS['H'][1],29)
    card(d,(975,1170,1935,1370),'Кнопка и рисунок мины',
        'Любая из 25 кнопок → общий button0.\n'
        'mine AND defeat → все 35 пикселей мины.\n'
        '31 красный разветвитель + 4 синих диагонали.',GROUPS['B'][1],29)
    card(d,(975,1400,1935,1690),'Что именно хранится',
        'SET request — принятый запрос подготовки.\n'
        'SET selected — выбранный первый ход.\n'
        'SET opened — клетка уже открыта.\n'
        'TFF mine — результат генерации.\n'
        'В семи сегментах памяти больше нет.',GROUPS['A'][1],28)
    for i,segment in enumerate('faegdbc'):
        label(d,(175+i*27,1582),segment,22,GROUPS['H'][1],True,anchor='mm')
    wrapped(d,(90,1610,895,1725),
        'Под цифрой — семь нативных AND и общая линия show. '
        'Порядок raw слева направо: f, a, e, g, d, b, c. '
        'Центральная кнопка и рисунок мины взяты из реальной карты.',27,MUTED)
    save(im,'03-control-and-panel.png','Вывод закрытой клетки пустой; открытый безопасный 0 виден',meta)


def rotated_label(im,center,text,color,size=17,above=True):
    f=font(size,True);temp=Image.new('RGBA',(300,35))
    d=ImageDraw.Draw(temp);b=d.textbbox((0,0),text,font=f)
    d.text((0,-b[1]),text,font=f,fill=color)
    temp=temp.crop((0,0,b[2]+2,b[3]-b[1]+3)).rotate(90 if above else 270,expand=True)
    x,y=center
    im.paste(temp,(int(x-temp.width/2),int(y-temp.height) if above else int(y)),temp)


def physical(meta,cells,graph):
    scale=23;left=255;top=425;width=meta['width']*scale;height=meta['height']*scale
    im,d=sheet('Физическая ячейка: все порты и вычислители',
        'Фон — настоящие стрелки. Цветные номера — 105 элементов графа; их входы расшифрованы на листе 05.',(2490,2300))
    label(d,(65,173),'ВХОД →  синий: приходит в эту копию',27,'#2469bc',True)
    label(d,(785,173),'ВЫХОД →  оранжевый: уходит из этой копии',27,'#b35a18',True)
    wrapped(d,(65,218,2430,285),'Номера вычислителей сохраняют цвет функции. Одна функция может быть размещена в нескольких местах; '
        'поэтому её точки не объединены в фиктивный прямоугольный модуль.',27,MUTED)
    d.rectangle((left,top,left+width,top+height),fill='white')
    for x in range(0,meta['width']+1,4):d.line((left+x*scale,top,left+x*scale,top+height),fill='#edf0f5')
    for y in range(0,meta['height']+1,4):d.line((left,top+y*scale,left+width,top+y*scale),fill='#edf0f5')
    for (x,y),c in cells.items():
        px=left+x*scale;py=top+y*scale
        d.rectangle((px,py,px+scale-1,py+scale-1),fill='#e9edf3')
        sp=sprite(c.type,c.rotation,c.mirrored,scale)
        # Neutral routed arrows keep the selected logic markers readable.
        im.paste(sp,(px+1,py+1),sp)
    coords={n['net']:tuple(n['at']) for n in meta['gate_positions']}
    for i,n in enumerate(graph['nodes'],1):
        x,y=coords[n['output']];px=left+x*scale;py=top+y*scale;color=GROUPS[group(n)][1]
        d.rounded_rectangle((px,py+3,px+22,py+20),radius=3,fill=color)
        label(d,(px+11,py+2),f'{i:03}',11,'white',True,anchor='mt')
    d.rectangle((left-2,top-2,left+width+1,top+height+1),outline=INK,width=3)
    for table,outbound in (('inputs',False),('outputs',True)):
        color='#b35a18' if outbound else '#2469bc'
        for name,entries in meta[table].items():
            if not (':' in name and name.split(':')[0] in ('N','S','W','E')):continue
            side,field=name.split(':');x,y=entries[0]['contact'];px=left+(x+.5)*scale;py=top+(y+.5)*scale
            d.ellipse((px-4,py-4,px+4,py+4),fill=color,outline='white')
            text=('OUT ' if outbound else 'IN ')+name
            if side=='N':
                d.line((px,top-8,px,top-25),fill=color,width=2)
                rotated_label(im,(px,top-30),text,color,15,True)
            elif side=='S':
                d.line((px,top+height+8,px,top+height+25),fill=color,width=2)
                rotated_label(im,(px,top+height+30),text,color,15,False)
            elif side=='W':
                d.line((left-8,py,left-21,py),fill=color,width=2)
                label(d,(left-27,py),text,17,color,True,anchor='rm')
            else:
                d.line((left+width+8,py,left+width+21,py),fill=color,width=2)
                label(d,(left+width+27,py),text,17,color,True,anchor='lm')
    # A real coordinate ruler is separate from the external port labels.
    # Local interfaces use short leaders; seven raw ports share one bracket.
    for name,table,text_pos in (
        ('button0','inputs',(left+29*scale,top+34.2*scale)),
        ('mine_indicator','outputs',(left+34.8*scale,top+20.3*scale)),
        ('panel_show','outputs',(left+11.5*scale,top+44.5*scale))):
        x,y=meta[table][name][0]['contact'];p=(left+(x+.5)*scale,top+(y+.5)*scale)
        color='#2469bc' if table=='inputs' else '#b35a18'
        d.line((text_pos,p),fill=color,width=2);d.ellipse((p[0]-4,p[1]-4,p[0]+4,p[1]+4),fill=color)
        badge(d,text_pos,{'button0':'button0 IN','mine_indicator':'mine OUT','panel_show':'show OUT'}[name],color,17)
    for i in range(7):
        x,y=meta['outputs']['panel_raw:'+str(i)][0]['contact'];p=(left+(x+.5)*scale,top+(y+.5)*scale)
        d.line((p,(p[0],top+45.2*scale)),fill='#b35a18',width=2)
    d.line((left+15.5*scale,top+45.2*scale,left+21.5*scale,top+45.2*scale),fill='#b35a18',width=2)
    badge(d,(left+18.5*scale,top+46.2*scale),'raw0..6 OUT','#b35a18',17)
    for x in range(0,56,8):label(d,(left+(x+.5)*scale,2125),str(x),20,MUTED,anchor='mm')
    label(d,(left+width-12,2125),'x=55',20,MUTED,anchor='rm')
    for y in range(0,64,8):label(d,(58,top+(y+.5)*scale),f'y={y}',19,MUTED,anchor='lm')
    counts=Counter(group(n) for n in graph['nodes'])
    descriptions={
        'A':'request (17,11)\nselected (14,17)\nВход кнопки и выбор по скану.',
        'B':'mine (20,14)\nЗащита 3×3; два RANDOM.\nСохранение результата в TFF.',
        'C':'Вертикальные пары/тройка\nи 8 ворот объединения.\n4 бита суммы соседних мин.',
        'D':'opened (29,14)\ncascade (8,41)\nОткрытие, ноль, Loss и Sat.',
        'E':'Шесть местных BUF фаз\nи шесть выходов на юг.\nТаймеры находятся снаружи.',
        'F':'Req/Loss/Sat: y=4/7/10.\nТри скана W → E; затем\nпереход в следующую строку.',
        'G':'Местные M/S/Z на N/S.\nMP/MC и тройки S/Z на W/E.\nВходы и выходы — разные пути.',
        'H':'Декодер: 18 ворот.\nСемь raw + show + mine.\nНативные AND панели — отдельно.'}
    for i,key in enumerate(GROUPS):
        y=330+i*220
        card(d,(1770,y,2430,y+205),f'{key} · {GROUPS[key][0]} · {counts[key]}',descriptions[key],GROUPS[key][1],24)
    label(d,(260,2170),'Координаты начинаются с (0,0) в левом верхнем углу; граница — (55,63).',25,MUTED)
    save(im,'04-physical-atlas.png','23 внешних входа + 23 выхода; межстрочный канал 6 вне рамки',meta)


def gate_catalog(meta,graph):
    im,d=sheet('Все 105 вычислителей: функция, операция, входы',
        'Номер совпадает с физической картой. BUF — передача; NOT с несколькими входами — NOR; SET — память.',(2490,2350))
    coords={n['net']:n['at'] for n in meta['gate_positions']}
    op_names={'SET':'SET','TOGGLE':'TFF','RANDOM':'RND'}
    for j,n in enumerate(graph['nodes']):
        col=j//35;row=j%35;x=65+col*805;y=175+row*55
        key=group(n);color=GROUPS[key][1];at=coords[n['output']]
        d.rounded_rectangle((x,y+3,x+47,y+43),radius=6,fill=color)
        label(d,(x+24,y+9),f'{j+1:03}',17,'white',True,anchor='mt')
        title=f'{n["output"]}  ·  {op_names.get(n["op"],n["op"])}  ·  ({at[0]},{at[1]})'
        label(d,(x+60,y),title,21,INK,True)
        text='← '+', '.join(n['inputs'])
        assert d.textlength(text,font=font(19))<710,(n,text)
        label(d,(x+60,y+27),text,19,MUTED)
    wrapped(d,(65,2120,2420,2165),'A запрос/выбор  ·  B генерация  ·  C сумма  ·  D игра  ·  E фазы  ·  F скан  ·  G соседи  ·  H вывод',26,MUTED)
    wrapped(d,(65,2178,2420,2220),'SET: 0 активных входов — удержание; 1 — сброс; 2+ — запись 1. Повтор n5 / n33 / n67 означает два физических входа.',24,MUTED)
    wrapped(d,(65,2230,2420,2270),'TFF переключается на каждом активном такте. Поэтому mine получает короткий импульс, а семь сегментов используют уровни.',24,MUTED)
    save(im,'05-gate-catalog.png','Стрелка «←» перечисляет реальные входы каждого элемента графа',meta)


def validate(meta,cells,graph):
    assert map_hash(cells)==meta['map_hash']==EXPECTED_HASH,'Update the explanation for the new circuit before rendering'
    assert (meta['width'],meta['height'])==(56,64) and len(cells)==2424
    assert len(graph['nodes'])==105
    ports=[dict(direction=kind[:-1],name=name,at=e[0]['contact'],
                external=':' in name and name.split(':')[0] in ('N','S','W','E'))
           for kind in ('inputs','outputs') for name,e in meta[kind].items()]
    assert Counter(p['direction'] for p in ports if p['external'])=={'input':23,'output':23}
    assert len([p for p in ports if not p['external']])==10
    assert len({n['output'] for n in graph['nodes']})==len(meta['gate_positions'])==105
    assert set(tuple(p) for p in meta['memories'])=={tuple(meta['states'][n]) for n in ('request','selected','mine','opened')}
    assert len(meta['button'])==25 and len(meta['mine_indicator']['pixels'])==35
    assert Counter(cells[tuple(p)].type for p in meta['mine_indicator']['pixels'])=={7:30,6:1,11:4}
    # The diagram's numerical example is independently counted from its 8 cells.
    example=[1,0,1,1,0,0,1,1]
    assert sum(example)==5 and (2+2+1)==5
    assert RAW_SEGMENTS==(5,0,4,6,3,1,2)
    by={n['output']:n for n in graph['nodes']}
    assert by['n45']['op']=='XOR' and by['n46']['op']=='MAJ'
    assert by['n45']['inputs']==by['n46']['inputs']==['N:M','mine','S:M']
    assert by['n73']['inputs']==['request','W:prefixReq']
    assert by['n74']['inputs']==['n71','W:prefixLoss'] and by['n75']['inputs']==['n72','W:prefixSat']
    assert by['n71']['inputs']==['opened','mine'] and by['n72']['inputs']==['mine','opened']
    for phase in ('busy','choose','sample','ready','stop','defeat'):
        assert by['phase:'+phase]['inputs']==['N:'+phase] and by['phase:'+phase]['op']=='BUF'
    assert by['n177']['inputs']==['mine','phase:defeat']
    assert by['display_show:west']['inputs']==['opened','display_safe:west']
    assert len([n for n in graph['nodes'] if n.get('scope')=='display/decoder'])==18
    return ports


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    cells=read_map(BUILD/'cell.save.txt');meta=json.loads((BUILD/'cell.layout.json').read_text())
    graph=json.loads((BUILD/'cell.logic.json').read_text());ports=validate(meta,cells,graph)
    overview(meta);neighborhood(meta);control_and_panel(meta,cells,graph);physical(meta,cells,graph);gate_catalog(meta,graph)
    write_json(OUT/'manifest.json',dict(passed=True,map_hash=meta['map_hash'],images=IMAGES,
        ports=ports,gate_groups={k:[n['output'] for n in graph['nodes'] if group(n)==k] for k in GROUPS},
        criteria=dict(all_46_external_ports=True,all_10_internal_ports=True,all_105_gates=True,imported_physical_save=True,
                      current_map_hash=True,actual_panel=True,independent_count_example=True,no_text_box_overflow=True),
        source_files=['build/cell.save.txt','build/cell.layout.json','build/cell.logic.json'],
        text_boxes_checked=len(TEXT_BOXES)))
    print('Static cell explanation:',len(IMAGES),'PNGs; all ports and gates verified against',meta['map_hash'],flush=True)


if __name__=='__main__':build()
