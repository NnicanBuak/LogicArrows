"""Explicit native-arrow logic; no CPU, precomputed game, or HDL sequential emulation."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'ArrowsHDL' / 'src'))
from arrowasm import Cell
from placement_backend import Router
from arrow_layout import GATE_TYPES, edges, bounds_of

class ModuleRouter(Router):
    def route_allowed(self, position):
        # Embedded screen contacts are deliberately inside the module's frame.
        return True

DIGITS = (
    ('111','101','101','101','111'),
    ('010','110','010','010','111'),
    ('111','001','111','100','111'),
    ('111','001','111','001','111'),
    ('101','101','111','001','001'),
    ('111','100','111','001','111'),
    ('111','100','111','101','111'),
    ('111','001','010','010','010'),
    ('111','101','111','101','111'),
)
MINE = ('101','010','101','010','101')
DIRECTIONS = ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1))

class Logic:
    def __init__(self, name):
        self.graph = dict(top=name, inputs={}, outputs={}, nodes=[])
        self.counter = 0
        self.cache = {}
        self.scope = 'core'
        self.or_arity = 2
    def input(self, name):
        self.graph['inputs'][name] = [dict(index=0, net=name)]
        return name
    def gate(self, op, *inputs, name=None):
        key=self.scope,op,tuple(sorted(inputs)) if op in ('AND','OR','XOR','MAJ') else tuple(inputs)
        if name is None and op not in ('RANDOM','TOGGLE','SET') and key in self.cache:
            return self.cache[key]
        net = name or f'n{self.counter}'
        self.counter += 1
        self.graph['nodes'].append(dict(id=net, op=op, inputs=list(inputs), output=net))
        if self.scope!='core':self.graph['nodes'][-1]['scope']=self.scope
        if name is None:self.cache[key]=net
        return net
    def inv(self, a): return self.gate('NOT', a)
    def both(self, a, b): return self.gate('AND', a, b)
    def any(self, *nets):
        nets = list(nets)
        if not nets: return 'const0'
        while len(nets) > 1:
            width=self.or_arity
            nets = [self.gate('OR', *nets[i:i+width]) if i+1 < len(nets) else nets[i]
                    for i in range(0,len(nets),width)]
        return nets[0]
    def all(self, *nets):
        nets = list(nets)
        while len(nets) > 1:
            nets = [self.both(*nets[i:i+2]) if i+1 < len(nets) else nets[i]
                    for i in range(0,len(nets),2)]
        return nets[0]
    def sticky(self, trigger, name):
        # Native latch: two simultaneous inputs set, zero inputs retain.
        # The frame placer gives these inputs a single synchronized fork.
        return self.gate('SET', trigger, trigger, name=name)
    def output(self, name, net):
        port = 'port:' + name
        self.gate('BUF', net, name=port)
        self.graph['outputs'][name] = [dict(index=0,net=port)]
