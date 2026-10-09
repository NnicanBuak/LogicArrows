"""Annotate actual arrow routes without moving or replacing any map cell.

Physical geometry comes from the common ArrowsHDL arrow_layout module. Net
ownership and gate coordinates come from the current compilation manifest.
Only the real branch leading to each illustrated receiver is emphasized.
"""
from collections import Counter,defaultdict,deque
from dataclasses import dataclass
from pathlib import Path
import json,math
from PIL import Image,ImageDraw
from snap import BUILD,read_map,map_hash,write_json
from arrow_layout import edges
from visualize_cell import font,label,wrapped,sprite,pale,validate,EXPECTED_HASH

OUT=BUILD/'visualizations/arrow-paths'
BG='#f6f8fb';INK='#18283e';MUTED='#617188'
COLORS=['#186fa8','#b96718','#2f8a62','#ad4d72','#7956ae','#078991',
        '#c14949','#687d22','#536dc1','#a3742b','#49813c','#9b4ba6',
        '#2d859f','#b95a34','#677191','#99568b']
PHASES=dict(busy='закрыть запросы',choose='выбрать старт',sample='генерировать мины',
            ready='разрешить игру',stop='запретить ходы',defeat='раскрыть мины')
PURPOSE={
 'n4':'захват разрешён','n5':'принять кнопку','request':'память запроса',
 'edge_delay:choose':'задержанная инверсия','edge:choose':'импульс choose',
 'edge_delay:sample':'задержанная инверсия','edge:sample':'импульс sample',
 'n31':'ранее запроса нет','n32':'первый запрос','n33':'записать старт','selected':'память старта',
 'n38':'вне защиты 3×3','n39':'импульс генерации','n40':'пропуск с шансом ½','n41':'пропуск с шансом ½','mine':'память мины',
 'n43':'пара N/S: вес 1','n44':'пара N/S: вес 2','n45':'моя тройка: вес 1','n46':'моя тройка: вес 2',
 'n51':'сумма: вес 1','n47':'перенос веса 2','n48':'сумма по весу 2','n49':'перенос веса 4',
 'n53':'сумма: вес 2','n50':'перенос веса 4','n55':'сумма: вес 4','n56':'сумма: вес 8',
 'n57':'нет мины','n60':'count = 0','n61':'нет stop','n63':'соседний ноль',
 'n64':'каскад без мины','n65':'причина открытия','n66':'разрешение хода','n67':'записать opened','opened':'память открытия',
 'n69':'открыта без мины','n70':'исходящий Z','n71':'открытая мина','n72':'мина либо открыта',
 'n73':'собрать запросы','n74':'собрать поражения','n75':'все клетки решены','n86':'S моей тройки','n87':'Z моей тройки',
 'n129':'NOT веса 1','n130':'NOT веса 2','n131':'NOT веса 4','n132':'веса 2/4 разные',
 'n133':'вес 2 AND NOT 1','n134':'NOT 1 AND NOT 4','n135':'вес 4 AND вес 1',
 'n136':'верхний сегмент a','n137':'веса 1/2 разные','n138':'веса 1/2 равны','n139':'правый верхний b',
 'n140':'правый нижний c','n141':'вес 1 AND n132','n142':'нижний сегмент d',
 'n143':'вес 2 OR NOT 4','n144':'левый нижний e','n145':'левый верхний f','n146':'средний сегмент g',
 'display_safe:west':'нет мины','display_show:west':'opened AND safe',
 'n177':'mine AND defeat','port:mine_indicator':'в рисунок мины','port:panel_show':'в общую шину show'}


def purpose(key):
 if key in PURPOSE:return PURPOSE[key]
 if key.startswith('phase:'):return PHASES[key.split(':')[1]]
 if key.startswith('port:panel_raw:'):return 'в сегмент '+'faegdbc'[int(key.rsplit(':',1)[1])]
 if key.startswith('port:'):return 'выход '+key[5:]
 return key


def input_purpose(key):
 if key=='button0':return 'кнопка 5×5'
 side,name=key.split(':')
 if name in PHASES:return PHASES[name]
 return dict(M='мина соседа '+side,MP='тройка '+side+': вес 1',MC='тройка '+side+': вес 2',
             S='защита старта от '+side,Z='каскад нуля от '+side,
             prefixReq='ранее принят запрос',prefixLoss='ранее открыта мина',prefixSat='предыдущие клетки решены')[name]


@dataclass
class Scene:
 slug:str
 title:str
 gates:list
 note:str
 native:str=None
 detail:bool=False


class Physical:
 def __init__(self,meta,graph,cells):
  self.meta=meta;self.graph=graph;self.cells=cells
  self.nodes={n['output']:n for n in graph['nodes']}
  self.pos={r['net']:tuple(r['at']) for r in meta['gate_positions']}
  self.ids={n['output']:i+1 for i,n in enumerate(graph['nodes'])}
  self.owners={tuple(r['at']):r['net'] for r in meta['wire_owners'] if tuple(r['at']) in cells}
  self.links=edges(cells);self.reverse=defaultdict(list)
  for p,targets in self.links.items():
   for q in targets:self.reverse[q].append(p)
  # Check the illustration's entire input-to-receiver mapping directly on
  # the imported arrows, including both equal inputs of every SET.
  for n in graph['nodes']:
   got=Counter()
   for p in self.reverse[self.pos[n['output']]]:
    owner=self.owners[p];got[owner[5:] if owner.startswith('gate:') else owner]+=1
   assert got==Counter(n['inputs']),(n['output'],got,n['inputs'])

 def source(self,net):
  return self.pos[net] if net in self.pos else tuple(self.meta['inputs'][net][0]['contact'])

 def trace(self,starts,targets,allowed,stop_at_targets=True):
  """Intersect real forward and reverse reachability, never synthesize routes."""
  starts=set(starts);targets=set(targets);allowed=set(allowed)|starts|targets
  seen=set(starts);todo=deque(starts)
  while todo:
   p=todo.popleft()
   if stop_at_targets and p in targets:continue
   for q in self.links[p]:
    if q in allowed and q not in seen:seen.add(q);todo.append(q)
  assert targets<=seen,('Physical target not reached',targets-seen)
  selected=set(targets);todo=deque(targets)
  while todo:
   for p in self.reverse[todo.popleft()]:
    if p in seen and p not in selected:selected.add(p);todo.append(p)
  assert starts<=selected,('Physical source missing',starts-selected)
  return selected,[(p,q) for p in selected if p not in targets for q in self.links[p] if q in selected]

 def edge(self,net,target):
  p=self.source(net);q=self.pos[target]
  allowed={a for a,owner in self.owners.items() if owner==net}
  points,arcs=self.trace([p],[q],allowed)
  contacts=[a for a in self.reverse[q] if a in points]
  assert len(contacts)==self.nodes[target]['inputs'].count(net),(net,target,contacts)
  return points,arcs,contacts

 def native_allowed(self):
  return {p for p,v in self.owners.items() if v=='native:panel' and self.cells[p].type not in (16,24)}

 def select(self,spec):
  sets=defaultdict(set);arcs=defaultdict(set);connections=[];computes=set(spec.gates)
  for target in spec.gates:
   sets[target].add(self.pos[target])
   for net in dict.fromkeys(self.nodes[target]['inputs']):
    points,links,contacts=self.edge(net,target)
    sets[net].update(points-{self.pos[target]});arcs[net].update(links)
    connections.append(dict(source=net,target=target,contacts=[list(p) for p in contacts],
                            points=[list(p) for p in sorted(points)],arcs=[[list(a),list(b)] for a,b in links]))
  annotations={k:(self.pos[k],purpose(k),k not in computes) for k in sets if k in self.pos}
  port_marks=[]
  for name,entries in self.meta['inputs'].items():
   if name in sets:
    port_marks.append((tuple(entries[0]['contact']),'IN '+name,name))
    if name=='button0':annotations[name]=(self.source(name),'кнопка 5×5',False)
  for name,entries in self.graph['outputs'].items():
   for e in entries:
    if e['net'] in computes:
     port_marks.append((tuple(self.meta['outputs'][name][0]['contact']),f'OUT {name} #{self.ids[e["net"]]:03}',e['net']))
     if name[:2] in ('W:','E:','N:','S:'):annotations.pop(e['net'],None)
  native=self.native_allowed()
  receivers=[next(q for q in self.links[tuple(p)] if self.cells[q].type==16) for p in self.meta['decoder_level_contacts']]
  if spec.native=='buttons':
   target=self.source('button0')
   pts,links=self.trace([tuple(p) for p in self.meta['button']],[target],native)
   sets['button0'].update(pts);arcs['button0'].update(links)
  if spec.native=='show':
   for p in receivers:
    pts,links=self.trace([self.pos['port:panel_show']],[p],native)
    sets['port:panel_show'].update(pts);arcs['port:panel_show'].update(links)
   annotations['native:show']=(receivers[3],'семь AND под числом',False)
  if spec.native and spec.native.startswith('segment:'):
   i=int(spec.native.split(':')[1]);letter='faegdbc'[i];receiver=receivers[i]
   assert self.cells[receiver].type==16
   for name,start in [('port:panel_raw:'+str(i),self.pos['port:panel_raw:'+str(i)]),('port:panel_show',self.pos['port:panel_show'])]:
    pts,links=self.trace([start],[receiver],native)
    sets[name].update(pts-{receiver});arcs[name].update(links)
   start=self.pos['port:panel_show'];sets['port:panel_show'].add(start)
   annotations['port:panel_show']=(start,'общий show',True)
   pts={receiver};todo=deque([receiver])
   while todo:
    for q in self.links[todo.popleft()]:
     if q in native and q not in pts:pts.add(q);todo.append(q)
   sets['pixels:'+letter].update(pts)
   annotations['pixels:'+letter]=(receiver,'AND: raw × show',False)
   register=tuple(self.meta['segment_registers']['abcdefg'.index(letter)])
   assert register in pts,(letter,register)
   annotations['segment:'+letter]=(register,'сегмент '+letter,False)
   port_marks.append((self.pos['port:panel_show'],'IN show','port:panel_show'))
  if spec.native=='mine':
   start=self.pos['port:mine_indicator'];pixels={tuple(p) for p in self.meta['mine_indicator']['pixels']}
   pts,links=self.trace([start],pixels,native,stop_at_targets=False)
   sets['pixels:mine'].update(pts-{start});arcs['pixels:mine'].update(links)
   roots={p for p in pixels if any(q not in pixels for q in self.reverse[p])}
   assert len(roots)==1,roots
   annotations['pixels:mine']=(next(iter(roots)),'мина: 35 пикселей',False)
  # A receiving gate belongs to its own output signal, even when several
  # colored input branches end there. Its original sprite stays visible.
  point_net={}
  for net,pts in sets.items():
   for p in pts:
    owner=self.owners.get(p,'')
    if not owner.startswith('gate:'):point_net[p]=net
  for net in sets:
   if net in self.pos:point_net[self.pos[net]]=net
  for net,(p,_,_) in annotations.items():
   if net.startswith('pixels:'):point_net[p]=net
  return sets,point_net,annotations,port_marks,connections,arcs

 def render(self,spec):
  sets,point_net,annotations,ports,connections,signal_arcs=self.select(spec)
  points=set(point_net)
  if spec.detail:bounds=(4,20,12,29);scale=88
  else:
   bounds=(max(0,min(x for x,y in points)-1),max(0,min(y for x,y in points)-1),
           min(55,max(x for x,y in points)+1),min(63,max(y for x,y in points)+1))
   bw=bounds[2]-bounds[0]+1;bh=bounds[3]-bounds[1]+1
   scale=36 if max(bw,bh)>45 else 44 if max(bw,bh)>30 else 52
  a,b,r,e=bounds;gw=(r-a+1)*scale;gh=(e-b+1)*scale
  left=245;top=520;width=max(1850,left+gw+750);height=max(1550,top+gh+350)
  im=Image.new('RGB',(width,height),BG);d=ImageDraw.Draw(im)
  label(d,(55,28),spec.title,43,INK,True)
  wrapped(d,(57,90,width-60,158),spec.note,25,MUTED)
  label(d,(57,185),'Настоящие стрелки · подложка различает сигналы · чёрная рамка отмечает вычислитель',24,MUTED)
  label(d,(57,224),'Остальная карта приглушена. Положение, тип, поворот и зеркальность стрелок сохранены.',23,MUTED)
  colors={net:COLORS[i%len(COLORS)] for i,net in enumerate(sets)}
  if spec.slug=='15-phases':colors={net:COLORS[list(PHASES).index(net.rsplit(':',1)[1])] for net in sets}
  def center(p):return left+(p[0]-a+.5)*scale,top+(p[1]-b+.5)*scale
  d.rectangle((left,top,left+gw,top+gh),fill='white')
  for p,c in self.cells.items():
   x,y=p
   if not(a<=x<=r and b<=y<=e):continue
   px=left+(x-a)*scale;py=top+(y-b)*scale
   active=p in point_net
   d.rectangle((px,py,px+scale-1,py+scale-1),fill=pale(colors[point_net[p]],.62) if active else '#f5f6f8')
   sp=sprite(c.type,c.rotation,c.mirrored,scale)
   if not active:
    sp=sp.copy();sp.putalpha(sp.getchannel('A').point(lambda n:round(n*.12)))
   im.paste(sp,(px+1,py+1),sp)
   if active:d.rectangle((px+1,py+1,px+scale-2,py+scale-2),outline=pale(colors[point_net[p]],.20),width=2)
  d.rectangle((left-1,top-1,left+gw,top+gh),outline='#9dafc3',width=2)
  for net in spec.gates:
   p=self.pos[net]
   if a<=p[0]<=r and b<=p[1]<=e:
    x,y=center(p);d.rectangle((x-scale/2-1,y-scale/2-1,x+scale/2+1,y+scale/2+1),outline=INK,width=3)
  for x in range(a,r+1):
   if scale>=70 or x%4==0:label(d,(center((x,b))[0],top-15),str(x),18,MUTED,anchor='mb')
  for y in range(b,e+1):
   if scale>=70 or y%4==0:label(d,(left-22,center((a,y))[1]),str(y),18,MUTED,anchor='rm')
  for p,text,net in ports:
   if not(a<=p[0]<=r and b<=p[1]<=e):continue
   color='#2670bd' if text.startswith('IN') else '#ae611c';x,y=center(p)
   if p[0] in (0,55):
    rightward=p[0]==55;end=left+gw+28 if rightward else left-28
    d.line((x,y,end,y),fill=color,width=2)
    label(d,(end+(7 if rightward else -7),y),text,20,color,True,anchor='lm' if rightward else 'rm')
   elif p[1] in (0,63):
    upward=p[1]==0;end=top-35 if upward else top+gh+35
    d.line((x,y,x,end),fill=color,width=2)
    self.vertical_label(im,(x,end),text,color,upward)
  active_boxes=[(center(p)[0]-scale/2-4,center(p)[1]-scale/2-4,
                 center(p)[0]+scale/2+4,center(p)[1]+scale/2+4) for p in points if a<=p[0]<=r and b<=p[1]<=e]
  used=[];label_records=[]
  # Put annotations on nearby faded context, never over an emphasized arrow.
  for net,(p,caption,external) in sorted(annotations.items(),key=lambda item:(item[1][0][1],item[1][0][0])):
   if not(a<=p[0]<=r and b<=p[1]<=e):continue
   x,y=center(p);number=self.ids.get(net)
   op=self.nodes[net]['op'] if net in self.nodes else ''
   op='TFF' if op=='TOGGLE' else 'NOR'+str(len(self.nodes[net]['inputs'])) if op=='NOT' and len(self.nodes[net]['inputs'])>1 else op
   if net in self.pos and op=='OR':
    actual=self.cells[self.pos[net]].type
    if actual==10:op='OR · прыжок 2'
    if actual==11:op='OR · диагональ'
   title=f'#{number:03} {op}' if number else 'AND' if net=='native:show' else net.split(':')[-1]
   if net=='button0':title='IN button0'
   if net=='port:panel_show':title=f'IN show · #{number:03}' if external else f'#{number:03} OUT show'
   if net.startswith('port:panel_raw:'):title=f'#{number:03} OUT raw:{net.rsplit(":",1)[1]}'
   if net=='port:mine_indicator':title=f'#{number:03} OUT mine'
   if external and net!='port:panel_show':title+=' · вход'
   tw=max(d.textlength(title,font=font(20,True)),d.textlength(caption,font=font(19)))+18
   bw=round(tw);bh=54;candidates=[]
   for radius in range(1,19):
    delta=radius*scale
    for dx,dy in ((delta,0),(-delta-bw,0),(0,delta),(0,-delta-bh),
                  (delta,delta),(-delta-bw,delta),(delta,-delta-bh),(-delta-bw,-delta-bh)):
     box=(round(x+dx),round(y+dy),round(x+dx+bw),round(y+dy+bh))
     if not(left-160<=box[0] and box[2]<=left+gw+175 and 270<=box[1] and box[3]<=top+gh+90):continue
     if any(overlap(box,q) for q in active_boxes+used):continue
     distance=math.hypot((box[0]+box[2])/2-x,(box[1]+box[3])/2-y)
     candidates.append((distance,box))
   assert candidates,('No clear annotation position',spec.slug,net)
   _,box=min(candidates);used.append((box[0]-8,box[1]-8,box[2]+8,box[3]+8))
   closest=(min(max(x,box[0]),box[2]),min(max(y,box[1]),box[3]))
   dx,dy=closest[0]-x,closest[1]-y;factor=scale*.56/max(abs(dx),abs(dy),1)
   dashed(d,(x+dx*factor,y+dy*factor),closest)
   d.rectangle((x-scale/2-1,y-scale/2-1,x+scale/2+1,y+scale/2+1),outline=INK,width=3)
   d.rounded_rectangle(box,radius=4,fill='white')
   label(d,(box[0]+8,box[1]+3),title,20,INK,True)
   label(d,(box[0]+8,box[1]+28),caption,19,colors.get(net,MUTED))
   label_records.append(dict(net=net,at=list(p),box=list(box),source_from_other_branch=external))
  lx=left+gw+390;ly=315
  label(d,(lx,ly),'Выделенные провода',25,INK,True);ly+=48
  legend_keys=[net for net in colors if not spec.slug=='15-phases' or net.startswith('phase:')]
  for net in legend_keys:
   color=colors[net]
   if spec.detail and not any(a<=p[0]<=r and b<=p[1]<=e for p in sets[net]):continue
   d.rounded_rectangle((lx,ly+6,lx+18,ly+24),radius=3,fill=color)
   text=net
   if net.startswith('pixels:'):text='пиксели '+net.split(':')[1]
   label(d,(lx+30,ly),text,21,INK,True)
   caption=purpose(net) if net in self.pos else input_purpose(net) if net in self.meta['inputs'] else 'нативная панель'
   label(d,(lx+30,ly+29),caption,18,MUTED);ly+=66
  assert ly<height-105,('Legend too long',spec.slug)
  d.line((55,height-75,width-55,height-75),fill='#d5deeb',width=2)
  visible_points={p for p in points if a<=p[0]<=r and b<=p[1]<=e}
  label(d,(57,height-55),'Координаты оригинала · '+'56×64 · текущая ячейка · '+str(len(visible_points))+' выделенных стрелок',21,MUTED)
  label(d,(width-57,height-55),EXPECTED_HASH[:12],20,MUTED,anchor='ra')
  path=OUT/(spec.slug+'.png');im.save(path)
  report=dict(image=path.name,title=spec.title,map_hash=EXPECTED_HASH,bounds=list(bounds),scale=scale,
              arrows=len(visible_points),all_selected_arrows=len(points),gate_nodes=spec.gates,annotations=label_records,
              selected_arrow_coordinates=[list(p) for p in sorted(points)],
              physical_arcs_by_signal={net:[[list(a),list(b)] for a,b in sorted(links)] for net,links in signal_arcs.items()},
              connections=connections,ports=[dict(at=list(p),name=t,net=n) for p,t,n in ports],
              criteria=dict(original_cells=True,original_coordinates=True,actual_emission_paths=True,
                            all_selected_receiver_inputs=True,no_label_over_active_arrow=True))
  write_json(OUT/(spec.slug+'.paths.json'),report)
  print(path.name,len(visible_points),'actual arrows',bounds,flush=True)
  return report

 def vertical_label(self,im,p,text,color,upward):
  f=font(18,True);bb=f.getbbox(text);tile=Image.new('RGBA',(bb[2]+5,28))
  ImageDraw.Draw(tile).text((1,-bb[1]),text,font=f,fill=color)
  tile=tile.rotate(90 if upward else 270,expand=True)
  im.paste(tile,(round(p[0]-tile.width/2),round(p[1]-tile.height) if upward else round(p[1])),tile)


def overlap(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]


def dashed(d,a,b):
 length=math.hypot(b[0]-a[0],b[1]-a[1])
 for t in range(0,round(length),12):
  u=t/max(1,length);v=min(1,(t+5)/max(1,length))
  d.line((a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u,a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v),fill='#596777',width=1)


def definitions(graph):
 S=Scene;specs=[
  S('01-button-request','01 · Кнопка: настоящая разводка до request',['phase:busy','n4','n5','request'],
    'Подсвечены 25 кнопок, их сборка и путь button0. NOT busy разрешает запись запроса в SET; обе копии n5 видны на входах памяти.','buttons'),
  S('02-select','02 · Как проводка выбирает первый ход',['phase:choose','edge_delay:choose','edge:choose','n31','n32','n33','selected'],
    'request и отсутствие более раннего W:prefixReq выбирают клетку. Прямой и инверсный пути choose создают короткий импульс записи selected.'),
  S('03-generate','03 · Защита 3×3 и проводка генерации',['phase:sample','edge_delay:sample','edge:sample','n38','n39','n40','n41','mine'],
    'Пять входов NOR защищают старт и соседей. Вне защиты импульс sample проходит два RANDOM и сохраняет mine в TFF.'),
  S('04-send-mines','04 · Исходящие мины: мои данные соседям',['n45','n46','port:W:MP','port:W:MC','port:E:MP','port:E:MC','port:N:M','port:S:M'],
    'N:M + mine + S:M образуют мою вертикальную тройку. XOR/MAJ дают биты MP/MC для W/E; на N/S отправляется только mine.'),
  S('05-receive-count','05 · Входящие мины: сложить соседние тройки',['n43','n44','n51','n47','n48','n49'],
    'Здесь видны именно входящие W/E:MP/MC и N/S:M. Они складываются; собственная mine в сумму не входит. Чёрные рамки отмечают суммы и переносы.'),
  S('06-carries','06 · Реальная разводка переносов',['n53','n50','n55','n56'],
    'n47 и n48 имеют вес 2; n49 — вес 4. Два полусумматора дают старшие биты 2/4/8. Младший бит n51 уже готов на листе 05.'),
  S('07-open-reasons','07 · Кнопка, старт и каскад: причины открытия',['n57','n63','n64','n65'],
    'Кнопка и selected приходят напрямую. Каскад от W/E/N/S проходит только через NOT mine; OR n65 объединяет причины открытия.'),
  S('08-open-memory','08 · Разрешение хода и память opened',['phase:ready','phase:stop','n61','n66','n67','opened'],
    'ready AND NOT stop пропускает причину n65. Два настоящих входа SET opened записывают открытие и затем удерживают его.'),
  S('09-zero','09 · Открытый безопасный ноль создаёт Z',['n60','n57','n69','n70'],
    'NOR четырёх битов проверяет count=0. Открытая клетка без мины поднимает Z, если вокруг тоже нет мин.'),
  S('10-send-s','10 · Только S: разводка защиты старта',['n86','port:W:S','port:E:S','port:N:S','port:S:S'],
    'На W/E уходит OR selected и северного/южного S. На N/S — собственный selected. Так защита достигает всех восьми соседей.'),
  S('11-send-z','11 · Только Z: разводка каскада',['n87','port:W:Z','port:E:Z','port:N:Z','port:S:Z'],
    'На W/E уходит OR собственного Z с N:Z/S:Z. На N/S — собственный Z. Числовая клетка открывается, но дальше каскад не передаёт.'),
  S('12-scan-request','12 · Только prefixReq: действующий скан запросов',['n73','port:E:prefixReq'],
    'W:prefixReq OR request → E:prefixReq. Этот путь используется при выборе первого хода: см. W:prefixReq на листе 02.'),
  S('13-scan-loss','13 · Только prefixLoss: проводка поражения',['n71','n74','port:E:prefixLoss'],
    'opened AND mine создаёт местный Loss. OR с входящим W:prefixLoss передаёт итог на восток и затем в следующую строку.'),
  S('14-scan-sat','14 · Только prefixSat: проводка готовности',['n72','n75','port:E:prefixSat'],
    'mine OR opened даёт местный Sat. AND с W:prefixSat означает, что вся пройденная часть поля решена; итог читает общий контроллер.'),
  S('15-phases','15 · Настоящие столбцы шести управляющих фаз',
    ['phase:'+p for p in PHASES]+['port:S:'+p for p in PHASES],
    'busy/choose/sample/ready/stop/defeat приходят сверху, проходят местные BUF и выходят снизу. Здесь выделены только сквозные ветки.'),
  S('16-show','16 · Общая проводка разрешения числа',['display_safe:west','display_show:west','port:panel_show'],
    'opened AND NOT mine даёт show. Настоящая красная шина под числом раздаёт show семи AND; отдельные raw разобраны на следующих листах.','show')]
 g={n['output']:n for n in graph['nodes']}
 for i,letter in enumerate('faegdbc'):
  needed=set()
  def walk(n):
   if n in graph['_count'] or n in needed:return
   assert g[n].get('scope')=='display/decoder';needed.add(n)
   for src in g[n]['inputs']:walk(src)
  walk(graph['_raw_level_nets'][i]);needed.add('port:panel_raw:'+str(i))
  names=[n['output'] for n in graph['nodes'] if n['output'] in needed]
  specs.append(S(f'{17+i:02}-segment-{letter}',f'{17+i:02} · Стрелочная разводка сегмента {letter}',names,
    'Подсвечены нужные биты числа, вычислители этого raw, синий ввод через show и настоящие стрелки видимого сегмента. Прочие сегменты приглушены.',f'segment:{i}'))
 specs.append(S('24-mine','24 · Проводка до настоящего рисунка мины',['phase:defeat','n177','port:mine_indicator'],
   'mine AND defeat проходит через выход и синий прыжок к 35 пикселям. В рисунке 31 красный разветвитель и четыре синих диагонали.','mine'))
 specs.append(S('25-native-inputs','25 · Крупно: входы XOR и MAJ на стрелочках',['n45','n46'],
   'Неподвижный фрагмент (4…12, 20…29). N:M, mine и S:M подходят к обоим вычислителям через реальные обычные, диагональные и прыжковые контакты.',detail=True))
 return specs


def build():
 OUT.mkdir(parents=True,exist_ok=True)
 meta=json.loads((BUILD/'cell.layout.json').read_text(encoding='utf-8'))
 graph=json.loads((BUILD/'cell.logic.json').read_text(encoding='utf-8'));cells=read_map(BUILD/'cell.save.txt')
 validate(meta,cells,graph);physical=Physical(meta,graph,cells);specs=definitions(graph)
 reports=[physical.render(s) for s in specs]
 covered={n for s in specs for n in s.gates};assert covered==set(physical.nodes),set(physical.nodes)-covered
 assert map_hash(read_map(BUILD/'cell.save.txt'))==EXPECTED_HASH
 write_json(OUT/'manifest.json',dict(passed=True,map_hash=EXPECTED_HASH,images=reports,
    criteria=dict(all_105_gates=True,all_179_physical_inputs_matched=True,original_arrow_sprites=True,
                  original_arrow_coordinates=True,branches_selected_from_actual_edges=True,
                  no_annotations_cover_selected_arrows=True,source_save_unchanged=True)))
 lines=['# Настоящая разводка ячейки: 25 изображений','',
        'Каждый лист содержит стрелки из текущего сохранения **56×64**. Координаты, типы, повороты и зеркальность сохранены.',
        'Подсвечены только пути к выбранным вычислителям; остальные стрелки приглушены.',
        'Цвет подложки различает сигналы. Чёрная рамка отмечает вычислитель; пунктир связывает подпись с его настоящей стрелкой.','',
        '| Изображение | Что проследить |','|---|---|']
 lines += [f'| [{s.title}]({s.slug}.png) | {s.note} |' for s in specs]
 lines += ['', '[Все порты ячейки](../current-cell/04-physical-atlas.png). [Проверка связей](manifest.json).','',
           '**Проверено:** 105 вычислителей и все 179 их входов совпали с реальными передающими стрелками.',
           'На рисунках не прокладываются новые провода и не перемещаются элементы.','',
           'Воспроизведение из корня: `python minesweeper-v1/visualize_arrow_paths.py`.','']
 (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
 print('Physical arrow sheets complete:',len(reports),flush=True)


if __name__=='__main__':build()
