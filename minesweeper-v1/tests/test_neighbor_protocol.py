"""Independent neighborhood truth checks for the candidate flag reductions."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from snap import graph_for_tile


def evaluate(graph,net,known):
    nodes={n['output']:n for n in graph['nodes']}
    values=dict(known,const0=0,const1=1)
    def value(name):
        if name in values:return values[name]
        node=nodes[name];bits=[value(n) for n in node['inputs']];count=sum(bits)
        op=node['op']
        if op in ('OR','BUF'):result=int(count>0)
        elif op=='NOT':result=int(count==0)
        elif op=='AND':result=int(all(bits))
        elif op=='MAJ':result=int(count>=2)
        elif op=='XOR':result=count%2
        else:raise AssertionError('State must be supplied explicitly: '+name)
        values[name]=result;return result
    return value(net)


class NeighborProtocolTests(unittest.TestCase):
    def test_sender_reduces_flags_only_horizontally(self):
        graph=graph_for_tile(or_inputs=3,aggregate_flags=True)
        for field,state in (('S','selected'),('Z','cascade')):
            for mask in range(8):
                bits=[(mask>>i)&1 for i in range(3)]
                known={graph['_states'][state]:bits[0],'N:'+field:bits[1],'S:'+field:bits[2]}
                for side in 'WE':
                    out=graph['outputs'][side+':'+field][0]['net']
                    self.assertEqual(evaluate(graph,out,known),int(any(bits)))
                for side in 'NS':
                    out=graph['outputs'][side+':'+field][0]['net']
                    self.assertEqual(evaluate(graph,out,known),bits[0])

    def test_every_neighbor_mask_preserves_protection_cascade_and_count(self):
        for carry_save in (False,True):
            graph=graph_for_tile(or_inputs=3,aggregate_flags=True,carry_save=carry_save)
            nodes={n['output']:n for n in graph['nodes']}
            random2=nodes[graph['_states']['mine']]['inputs'][0]
            random1=nodes[random2]['inputs'][0]
            permitted=nodes[random1]['inputs'][0]
            sample=nodes[permitted]['inputs'][0]
            opened_trigger=nodes[graph['_states']['opened']]['inputs'][0]
            for mask in range(256):
                bits=[(mask>>i)&1 for i in range(8)]
                known={e['net']:0 for es in graph['inputs'].values() for e in es}
                for field in ('S','Z'):
                    known.update({'W:'+field:int(any(bits[i] for i in (0,3,5))),
                                  'E:'+field:int(any(bits[i] for i in (2,4,7))),
                                  'N:'+field:bits[1],'S:'+field:bits[6]})
                known.update({'W:M':bits[3],'E:M':bits[4],'N:M':bits[1],'S:M':bits[6]})
                for direction,i in zip(('NW','NE','SW','SE'),(0,2,5,7)):known['DG:'+direction+'M']=bits[i]
                for own in (0,1):
                    source=dict(known,**{graph['_states']['selected']:own,sample:1})
                    self.assertEqual(evaluate(graph,permitted,source),int(not (own or mask)))
                source=dict(known,**{graph['_states']['selected']:0,graph['_states']['mine']:0,
                                     'phase:ready':1,'phase:stop':0})
                self.assertEqual(evaluate(graph,opened_trigger,source),int(mask!=0))
                count=sum(evaluate(graph,net,known)<<i for i,net in enumerate(graph['_count']))
                self.assertEqual(count,mask.bit_count())


if __name__=='__main__':unittest.main()
