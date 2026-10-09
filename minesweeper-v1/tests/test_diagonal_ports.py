"""Native corner channels: every simultaneous 12-bit input combination."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagonal_ports import corner_channels,contact,ROTATIONS,OFFSETS,OPPOSITE,LANES
from logic import Cell
from runner import simulate


class DiagonalChannelTests(unittest.TestCase):
    def test_exhaustive_independent_channels(self):
        side=32
        cells={(x+dx*side,y+dy*side):c for dx in (-1,0,1) for dy in (-1,0,1)
               for (x,y),c in corner_channels(side).items()}
        inputs=[];targets=[]
        for direction,(dx,dy) in OFFSETS.items():
            for field in LANES:
                p,rotation,fixture,pin=contact(direction,field,side,True)
                self.assertNotIn(p,cells);self.assertNotIn(pin,cells)
                cells[p]=Cell(11,rotation)
                cells[pin]=Cell(22,0 if p[1]==0 else 2)
                q,_,_,_=contact(OPPOSITE[direction],field,side,False)
                target=q[0]+dx*side,q[1]+dy*side
                self.assertNotIn(target,cells);cells[target]=Cell(23,0)
                inputs.append(pin);targets.append(target)
        vectors=range(4096);hold=40
        report=simulate(cells,dict(ticks=4096*hold,hold_ticks=hold,
            inputs=[dict(at=list(p),values=[(v>>i)&1 for v in vectors]) for i,p in enumerate(inputs)],
            expect=[dict(at=list(p),values=[(v>>i)&1 for v in vectors]) for i,p in enumerate(targets)]))
        self.assertTrue(report['passed'],report['failures'][:10])
        self.assertEqual(report['checked_samples'],4096*12)


if __name__=='__main__':unittest.main()
