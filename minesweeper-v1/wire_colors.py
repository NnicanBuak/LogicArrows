"""Colour real routed nets, cutting exactly at compiler gates and native blocks."""
from collections import deque
import base64,colorsys,json
from PIL import Image,ImageDraw,ImageOps
from snap import BUILD,ROOT,REFERENCE,read_map,destinations
from render import font
from mapdata import write_json,map_hash

def recover_nets(cells,meta):
    gates={tuple(g['at']):g for g in meta['gate_positions']}
    native=set(map(tuple,meta['button']))
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
    d.rectangle((left+bx*scale-3,top+by*scale-3,left+(bx+3)*scale+3,top+(by+3)*scale+3),outline='#b82b48',width=3)
    d.text((28,im.height-66),'Цвет — отдельная цепь. Серый — логические элементы и исходные блоки дисплея.',font=font(17),fill='#55647a')
    d.text((28,im.height-38),'Окраска показывает соединения, а не текущее состояние сигналов.',font=font(17),fill='#55647a')
    path=BUILD/(stem+'.nets.preview.png');im.save(path)
    write_json(BUILD/(stem+'.nets.json'),dict(map_hash=meta['map_hash'],side=side,physical_arrows=len(cells),
        net_count=len(names),wire_arrows=len(owners),source='compiler gates and physical arrow connections',
        nets=[dict(name=n,color=palette[n],cells=[list(p) for p,owner in owners.items() if owner==n]) for n in names]))
    viewer='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Цветная разводка сапёра</title><style>
body{margin:0;background:#f8fafc;color:#172c45;font:14px system-ui,sans-serif}
header{padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #cbd5e1}
button,select{font:inherit;padding:5px 8px}select{max-width:220px}#status{flex-basis:100%;min-height:20px}
#pane{height:calc(100vh - 108px);overflow:auto}#sheet{position:relative;margin:0 auto;line-height:0}
img{display:block;width:100%;height:auto}canvas{position:absolute;inset:0;width:100%;height:100%;cursor:crosshair}
</style><header><label>Цепь <select id="net"><option value="">Все цепи</option></select></label>
<button id="clear">Все цепи</button><label>Масштаб <input id="zoom" type="range" min="40" max="200" step="10" value="60"></label>
<output id="zoom-value">60%</output><div id="status" role="status" aria-live="polite">Все цепи. Нажмите на провод для выделения.</div></header>
<main id="pane"><div id="sheet"><img id="image" alt="Скомпилированная ячейка с цветными проводными цепями" src="__IMAGE__"><canvas id="overlay" aria-label="Выбор проводной цепи"></canvas></div></main>
<script>
const data=__DATA__;
const image=document.getElementById('image'),canvas=document.getElementById('overlay'),ctx=canvas.getContext('2d');
const sheet=document.getElementById('sheet'),select=document.getElementById('net'),status=document.getElementById('status');
const byName=new Map(data.nets.map(n=>[n.name,n])),grid=new Map(),gates=new Map();
data.nets.forEach(n=>{n.cells.forEach(([x,y])=>grid.set(y*data.side+x,n.name));const o=document.createElement('option');o.value=n.name;o.textContent=n.name;select.appendChild(o)});
data.gates.forEach(g=>gates.set(g.at[1]*data.side+g.at[0],g));
let chosen='';
function redraw(){
ctx.clearRect(0,0,canvas.width,canvas.height);image.style.opacity=chosen?'.18':'1';
if(!chosen){status.textContent='Все цепи. Нажмите на провод для выделения.';return}
const n=byName.get(chosen);if(!n)return;
n.cells.forEach(([x,y])=>{const px=data.left+x*data.scale,py=data.top+y*data.scale;ctx.drawImage(image,px,py,data.scale,data.scale,px,py,data.scale,data.scale)});
const g=data.gates.find(g=>g.net===chosen);
if(g){ctx.strokeStyle='#b45309';ctx.lineWidth=3;ctx.strokeRect(data.left+g.at[0]*data.scale-1,data.top+g.at[1]*data.scale-1,data.scale+2,data.scale+2)}
const groups={'control':'управление','game':'раскрытие','scan':'служебная цепочка','links':'стыки','count/west':'западные соседи','count/east':'восточные соседи','count/vertical':'север и юг','count/merge':'сумматор','display/west':'левая группа сегментов','display/east':'правая группа сегментов'};
const operations={'TOGGLE':'Т-триггер','SET':'память','NOT':'НЕ','AND':'И','OR':'ИЛИ','XOR':'XOR','MAJ':'перенос','BUF':'передача','RANDOM':'случайный пропуск'};
status.textContent=chosen+' · '+n.cells.length+' стрелок'+(g?' · '+(groups[g.scope]||g.scope)+' · '+(operations[g.op]||g.op):' · вход');
}
function choose(n){chosen=n;select.value=n;redraw()}
function coordinates(e){const r=canvas.getBoundingClientRect();return [Math.floor(((e.clientX-r.left)*canvas.width/r.width-data.left)/data.scale),Math.floor(((e.clientY-r.top)*canvas.height/r.height-data.top)/data.scale)]}
canvas.addEventListener('click',e=>{const [x,y]=coordinates(e);if(x<0||y<0||x>=data.side||y>=data.side)return;const p=y*data.side+x;const n=grid.get(p)||gates.get(p)?.net;if(byName.has(n))choose(n)});
canvas.addEventListener('pointermove',e=>{const [x,y]=coordinates(e);canvas.title=grid.get(y*data.side+x)||gates.get(y*data.side+x)?.net||''});
select.addEventListener('change',()=>choose(select.value));document.getElementById('clear').addEventListener('click',()=>choose(''));
function zoom(){const z=Number(document.getElementById('zoom').value);sheet.style.width=(image.naturalWidth*z/100)+'px';document.getElementById('zoom-value').textContent=z+'%'}
document.getElementById('zoom').addEventListener('input',zoom);
function start(){canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;zoom();redraw()}
image.addEventListener('load',start);if(image.complete&&image.naturalWidth)start();
</script></html>'''
    data=dict(side=side,scale=scale,left=left,top=top,
        nets=[dict(name=n,cells=[list(p) for p,o in owners.items() if o==n]) for n in names],
        gates=meta['gate_positions'])
    viewer=viewer.replace('__DATA__',json.dumps(data,separators=(',',':'))).replace('__IMAGE__','data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode())
    (BUILD/(stem+'.nets.viewer.html')).write_text(viewer,encoding='utf-8')
    print('Verified net colours:',stem,side,len(cells),len(names),len(owners),flush=True)
    return path

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stem');p.add_argument('--layout');a=p.parse_args()
    render_nets(a.stem,a.layout)
