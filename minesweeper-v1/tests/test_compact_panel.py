"""Native prewired display truth, mine controls and all 25 click positions."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from compact_panel import make_panel,verify_panel,verify_buttons


class CompactPanelTests(unittest.TestCase):
    def test_native_controls_and_transitions(self):
        report=verify_panel()
        self.assertTrue(report['passed'])
        self.assertEqual(report['decoder']['checked_segment_values'],518)
        self.assertEqual(report['raw_interface']['checked_segment_values'],3584)
        self.assertEqual(report['buttons']['checked_samples'],175)

    def test_white_gaps_and_fixed_ui(self):
        panel=make_panel(True)
        self.assertEqual(len(panel.buttons),25)
        self.assertEqual(set(panel.buttons),{(x,y) for x in range(11,16) for y in range(4,9)})
        self.assertTrue(all((x,14) not in panel.cells for x in range(8)))
        self.assertTrue(all((x,y) not in panel.cells for x in (8,9,16,17,18) for y in range(14)))
        for x in range(7):self.assertEqual(panel.cells[(x,15)].type,10)
        self.assertEqual(set(panel.inputs),{'show','mine','bcd:0','bcd:1','bcd:2','bcd:3'})
        # Placement suggested for a 64x64 host keeps every fixture inside it.
        placed=panel.moved(19,18)
        for x,y in set(placed.cells)|set(placed.input_fixtures.values()):
            self.assertTrue(0<=x<64 and 0<=y<64,(x,y))

    def test_top_collector_preserves_all_25_buttons_and_visible_displays(self):
        bottom=make_panel(False,level_outputs=True)
        top=make_panel(False,level_outputs=True,click_side='top')
        self.assertEqual(bottom.buttons,top.buttons)
        self.assertEqual(bottom.mine_pixels,top.mine_pixels)
        self.assertEqual(bottom.inputs,top.inputs)
        self.assertEqual(bottom.raw_inputs,top.raw_inputs)
        self.assertEqual({p:c for p,c in bottom.cells.items() if p[0]!=10},
                         {p:c for p,c in top.cells.items() if p[0]!=10})
        self.assertTrue(verify_buttons('top')['each_button'])


if __name__=='__main__':unittest.main()
