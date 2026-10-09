"""Native truth, simultaneous transitions and one-tick pulse preservation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from compact_macros import verify_macros,adder_groups,latch_groups,edge_groups
from snap import graph_for_tile


class CompactMacroTests(unittest.TestCase):
    def test_native_macros(self):
        report=verify_macros()
        self.assertTrue(report['passed'])
        self.assertEqual(len(report['adders']),8)
        self.assertEqual(sum(a['checked_samples'] for a in report['adders']),1280)
        self.assertTrue(report['latch']['single_tick_trigger_retained'])
        self.assertEqual([e['pulse_count'] for e in report['edges']],[8,4])
        self.assertEqual([e['pulse_count'] for e in report['column_edges']],[8,4])

    def test_compiler_bindings(self):
        graph=graph_for_tile(or_inputs=3,aggregate_neighbors=True)
        groups=adder_groups(graph)
        self.assertEqual(len(groups),7)
        used=[]
        for group in groups:
            self.assertEqual(set(group['inputs'].values()),set(group['nodes']['sum']['inputs']))
            self.assertEqual(set(group['inputs'].values()),set(group['nodes']['carry']['inputs']))
            used.extend(n['output'] for n in group['nodes'].values())
        self.assertEqual(len(used),len(set(used)))
        self.assertEqual(len(latch_groups(graph)),4)
        edge_pairs=edge_groups(graph)
        self.assertEqual(len(edge_pairs),9)
        for group in edge_pairs:
            self.assertEqual(group['nodes']['delay']['inputs'],[group['inputs']['signal']])


if __name__=='__main__':unittest.main()
