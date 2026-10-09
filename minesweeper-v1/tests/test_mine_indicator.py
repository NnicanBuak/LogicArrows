"""Check the complete native 8x8 silhouette and level-controlled blanking."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mine_indicator import BITMAP,indicator
from logic import Cell
from runner import simulate
from collections import Counter
from arrow_layout import depth_of

class MineIndicatorTests(unittest.TestCase):
    def test_shape_and_native_transitions(self):
        cells,root=indicator();pixels=sorted(cells)
        wanted={(x,y) for y,row in enumerate(BITMAP) for x,bit in enumerate(row) if bit=='1'}
        self.assertEqual(set(cells),wanted)
        self.assertEqual((min(x for x,y in cells),max(x for x,y in cells)),(0,7))
        self.assertEqual((min(y for x,y in cells),max(y for x,y in cells)),(0,7))
        counts=Counter(c.type for c in cells.values())
        self.assertEqual(counts[11],4)
        self.assertEqual(sum(counts[k] for k in (6,7,8)),31)
        self.assertEqual(set(counts),{6,7,11})
        self.assertGreater(depth_of(cells),0)
        source=(root[0],-1);cells[source]=Cell(22,2)
        report=simulate(cells,dict(ticks=1000,hold_ticks=200,
            inputs=[dict(at=list(source),values=[0,1,0,1,0])],expect=[],observe=[list(p) for p in pixels]))
        for observation in report['observations']:
            self.assertEqual(observation['values'],[0,1,0,1,0],observation['at'])

if __name__=='__main__':unittest.main()
