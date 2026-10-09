"""Every button square reaches the common collector and releases cleanly."""
import random
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from logic import Cell
from runner import simulate

class ButtonBusTests(unittest.TestCase):
    def test_five_by_five_button(self):
        buttons=[(x,y) for y in range(5) for x in range(1,6)]
        cells={p:Cell(22,3) for p in buttons}
        cells.update({(0,y):Cell(1,2) for y in range(5)})
        cells[0,5]=Cell(23,0)
        rng=random.Random(5)
        masks=[0]+[1<<i for i in range(25)]+[(1<<25)-1]
        masks += [sum(1<<(5*y+x) for x in range(5)) for y in range(5)]
        masks += [sum(1<<(5*y+x) for y in range(5)) for x in range(5)]
        masks += [rng.randrange(1<<25) for _ in range(64)]
        values=[[v for mask in masks for v in ((mask>>i)&1,0)] for i in range(25)]
        report=simulate(cells,dict(ticks=len(masks)*2*40,hold_ticks=40,
            inputs=[dict(at=list(p),values=values[i]) for i,p in enumerate(buttons)],
            expect=[dict(at=[0,5],values=[v for mask in masks for v in (int(mask!=0),0)])]))
        self.assertTrue(report['passed'],report['failures'][:10])

    def test_all_button_combinations_and_release(self):
        # A native button and a level source both emit left while activated.
        # The source also preserves the button's propagation of incoming levels.
        buttons=[(x,y) for y in range(3) for x in range(1,4)]
        cells={p:Cell(22,3) for p in buttons}
        cells.update({(0,y):Cell(1,2) for y in range(3)})
        cells[0,3]=Cell(23,0)
        values=[[v for mask in range(512) for v in ((mask>>i)&1,0)] for i in range(9)]
        report=simulate(cells,dict(ticks=1024*40,hold_ticks=40,
            inputs=[dict(at=list(p),values=values[i]) for i,p in enumerate(buttons)],
            expect=[dict(at=[0,3],values=[v for mask in range(512) for v in (int(mask!=0),0)])]))
        self.assertTrue(report['passed'],report['failures'][:10])

if __name__=='__main__':unittest.main()
