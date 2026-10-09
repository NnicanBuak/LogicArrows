"""Check native propagation, mutually exclusive words, and complete turn-off."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from logic import Cell
from status_display import add_status, alphabet
from runner import simulate


class StatusDisplayTests(unittest.TestCase):
    def test_native_words_and_turn_off(self):
        cells = {(80,-24):Cell(22,2),(80,-16):Cell(22,2)}
        header = {'outputs':{name:[{'contact':[80,y],'fixture':[80,y+1]}]
                             for name,y in (('victory',-24),('defeat',-16))}}
        status = add_status(cells,header)
        pixels = [(name,p) for name,display in status['displays'].items() for p in display['pixels']]
        report = simulate(cells,dict(ticks=2500,hold_ticks=500,
            inputs=[dict(at=[80,-24],values=[0,1,0,0,0]),
                    dict(at=[80,-16],values=[0,0,0,1,0])],
            expect=[],observe=[p for name,p in pixels]))
        for (name,p),observation in zip(pixels,report['observations']):
            self.assertEqual(observation['values'],[0,1,0,0,0] if name=='victory' else [0,0,0,1,0],(name,p))
        glyphs,version=alphabet()
        self.assertEqual(version,174)
        self.assertEqual(glyphs['N'],['1001','1101','1011','1001'])
        self.assertEqual(status['displays']['victory']['width'],28)
        self.assertEqual(status['displays']['defeat']['width'],38)
        for display in status['displays'].values():
            wanted=set()
            for letter in display['letters']:
                ox,oy=letter['origin']
                for y,row in enumerate(letter['bitmap']):
                    for x,bit in enumerate(row):
                        if bit=='1':wanted.update((ox+2*x+dx,oy+2*y+dy) for dx in (0,1) for dy in (0,1))
            self.assertEqual({tuple(p) for p in display['pixels']},wanted)


if __name__=='__main__':unittest.main()
