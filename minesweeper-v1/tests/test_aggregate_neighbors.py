"""Exhaustive semantics of reduced neighbor contacts before physical routing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from snap import graph_for_tile,geometry,face_names
from snap_verify import aggregate_mine_inputs


def evaluator(graph,values):
    nodes={n['output']:n for n in graph['nodes']}
    cache=dict(values)
    def value(net):
        if net in cache:return cache[net]
        if net in ('const0','const1'):return int(net=='const1')
        if net not in nodes:return 0
        node=nodes[net];op=node['op']
        # State outputs are independently controlled for combinational tests.
        if op in ('SET','TOGGLE'):return 0
        args=[value(n) for n in node['inputs']]
        if op in ('BUF','OR'):result=int(any(args))
        elif op=='AND':result=int(all(args))
        elif op=='NOT':result=int(not any(args))
        elif op=='XOR':result=sum(args)%2
        elif op=='MAJ':result=int(sum(args)>=2)
        else:raise AssertionError(('unexpected operation',net,op))
        cache[net]=result
        return result
    return value


def encoded_or_inputs(mask,field):
    bits=[(mask>>i)&1 for i in range(8)]
    return {f'W:{field}':int(any(bits[i] for i in (0,3,5))),
            f'E:{field}':int(any(bits[i] for i in (2,4,7))),
            f'N:{field}':bits[1],f'S:{field}':bits[6]}


class AggregateNeighborTests(unittest.TestCase):
    def graph(self):
        return graph_for_tile(or_inputs=3,aggregate_neighbors=True)

    def test_all_neighbor_mine_counts(self):
        graph=self.graph()
        for mask in range(256):
            value=evaluator(graph,aggregate_mine_inputs(mask))
            actual=sum(value(net)<<i for i,net in enumerate(graph['_count']))
            self.assertEqual(actual,mask.bit_count(),mask)

    def test_all_protection_and_cascade_inputs(self):
        graph=self.graph();nodes={n['output']:n for n in graph['nodes']}
        # Inspect the condition driving the first native random stage.
        randoms=[n for n in graph['nodes'] if n['op']=='RANDOM']
        permitted=randoms[0]['inputs'][0]
        for mask in range(256):
            for own in (0,1):
                value=evaluator(graph,{**encoded_or_inputs(mask,'S'),
                                       'selected':own,'edge:sample':1})
                self.assertEqual(value(permitted),int(not (own or mask)),(mask,own))
            # Opening from a cascade must require a safe cell and a neighbor.
            trigger=nodes['opened']['inputs'][0]
            for mine in (0,1):
                value=evaluator(graph,{**encoded_or_inputs(mask,'Z'),
                                       'mine':mine,'phase:ready':1})
                self.assertEqual(value(trigger),int(bool(mask) and not mine),(mask,mine))

    def test_sender_vertical_triples(self):
        graph=self.graph();cascade=graph['_states']['cascade']
        for mask in range(8):
            north,own,south=[(mask>>i)&1 for i in range(3)]
            value=evaluator(graph,{'N:M':north,'mine':own,'S:M':south,
                                   'N:S':north,'selected':own,'S:S':south,
                                   'N:Z':north,cascade:own,'S:Z':south})
            for side in 'WE':
                actual=value('port:'+side+':MP')+2*value('port:'+side+':MC')
                self.assertEqual(actual,mask.bit_count(),(mask,side))
                for field in ('S','Z'):
                    self.assertEqual(value('port:'+side+':'+field),int(bool(mask)),(mask,side,field))
            for side,expected in (('N',own),('S',own)):
                self.assertEqual(value('port:'+side+':M'),expected)
                self.assertEqual(value('port:'+side+':S'),expected)
                self.assertEqual(value('port:'+side+':Z'),expected)

    def test_interface_contract_and_default_unchanged(self):
        graph=self.graph()
        self.assertFalse(any(name.startswith('DG:') for name in graph['inputs']))
        self.assertNotIn('S:totalReq',graph['inputs'])
        self.assertNotIn('N:totalReq',graph['outputs'])
        default=graph_for_tile(or_inputs=3,diagonal_contacts=True)
        self.assertIn('DG:NWM',default['inputs'])
        self.assertNotIn('S:totalReq',default['inputs'])
        self.assertNotIn('N:totalReq',default['outputs'])
        for size in (64,72,80,88):
            for side,other,offset in (('E','W',(size,0)),('S','N',(0,size)),
                                      ('W','E',(-size,0)),('N','S',(0,-size))):
                for name in face_names(side,True,aggregate_neighbors=True):
                    p,_,fixture=geometry(side,name,size,True,aggregate_neighbors=True)
                    q,_,_=geometry(other,name,size,False,aggregate_neighbors=True)
                    self.assertEqual(fixture,(q[0]+offset[0],q[1]+offset[1]))


if __name__=='__main__':unittest.main()
