"""Native WIN/LOSE pixels, using the supplied bold alphabet at exactly 2x."""
import json
import random
from collections import defaultdict

from logic import HERE, Cell
from arrowasm import decode
from arrow_layout import destinations
from placement_backend import wire_cell
from external_routing import Wiring

SOURCE_URL = 'https://logic-arrows.io/map--132oac3'
BOXES = {'W': (47,61,51,64), 'I': (41,54,41,57), 'N': (9,12,12,15),
         'L': (9,61,11,64), 'O': (13,61,16,64), 'S': (31,61,33,64),
         'E': (25,54,27,57)}


def alphabet():
    document = json.loads((HERE/'reference/alphabet/mapguest.json').read_text(encoding='utf-8'))
    source = decode(document['data'])
    glyphs = {}
    for letter,(x0,y0,x1,y1) in BOXES.items():
        rows = [''.join('1' if (x,y) in source else '0' for x in range(x0,x1+1))
                for y in range(y0,y1+1)]
        # This alphabet omits Latin M/N. Mirror its bold Cyrillic И for N.
        if letter == 'N': rows = [row[::-1] for row in rows]
        glyphs[letter] = rows
    return glyphs, document['version']


def glyph_tree(rows,scale=2):
    mask = {(scale*x+dx,scale*y+dy) for y,row in enumerate(rows) for x,bit in enumerate(row)
            if bit == '1' for dx in range(scale) for dy in range(scale)}
    for seed in range(2000):
        rng = random.Random(seed)
        root = rng.choice(sorted(p for p in mask if p[1] == 0))
        seen = {root}; outs = defaultdict(set)
        while len(seen) < len(mask):
            candidates = [(p,q) for p in sorted(seen) for q in sorted(mask-seen)
                          if max(abs(p[0]-q[0]),abs(p[1]-q[1])) <= 1
                          and wire_cell(p,outs[p]|{q})]
            if not candidates: break
            p,q = rng.choice(candidates); outs[p].add(q); seen.add(q)
        if seen != mask: continue
        cells = {}
        forbidden = mask | {(root[0],-i) for i in range(1,5)}
        for p in sorted(mask):
            if outs[p]: cells[p] = wire_cell(p,outs[p])
            else:
                cells[p] = next((Cell(k,r,m) for k in (1,10,11)
                                 for m in (False,True) for r in range(4)
                                 if not set(destinations(p,Cell(k,r,m))) & forbidden),None)
        if all(cells.values()):
            assert all(set(destinations(p,c)) & mask == outs[p] for p,c in cells.items())
            return cells,root
    raise ValueError('Cannot connect alphabet glyph without filling its blank pixels')


def add_status(cells,header,extra_targets=None,reserved=()):
    glyphs,version = alphabet(); displays = {}; targets = {}
    for name,word,y in (('victory','WIN',-60),('defeat','LOSE',-36)):
        x = 124; pixels = []; letters = []; roots = []
        for letter in word:
            local,root = glyph_tree(glyphs[letter]); origin = (x,y)
            placed = {(p[0]+x,p[1]+y):c for p,c in local.items()}
            assert not set(placed) & set(cells)
            cells.update(placed); pixels.extend(sorted(placed))
            roots.append((root[0]+x,root[1]+y))
            letters.append(dict(letter=letter,origin=list(origin),source_box=BOXES[letter],
                                mirrored_source=letter=='N',bitmap=glyphs[letter]))
            x += 2*len(glyphs[letter][0])+4
        bus_y = y-4; bus_start = (120,bus_y); last_x = roots[-1][0]
        for bx in range(bus_start[0],last_x+1):
            p = bx,bus_y
            qs = {(bx+1,bus_y)} if bx < last_x else set()
            if (bx,y) in roots: qs.add((bx,bus_y+1))
            cells[p] = wire_cell(p,qs)
            assert cells[p] is not None
        for rx,ry in roots:
            for by in range(bus_y+1,ry):
                assert (rx,by) not in cells
                cells[rx,by] = Cell(1,2)
        displays[name] = dict(word=word,scale=2,height=8,width=x-124-4,
                              origin=[124,y],pixels=[list(p) for p in pixels],letters=letters)
        targets[name] = ((119,bus_y),bus_start)
    router = Wiring(cells,reserved=reserved)
    for name,target in targets.items():
        source = tuple(header['outputs'][name][0]['fixture'])
        router.connection('status:'+name,source,[target]+(extra_targets or {}).get(name,[]))
    routed = router.route_all()
    cells.clear(); cells.update(routed)
    return dict(source_url=SOURCE_URL,source_version=version,scale=2,
                note='N is mirrored Cyrillic U+0418 from the same bold font',displays=displays)
