"""Boundary-size and preservation checks for the actual save exporter."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from logic import Cell
from mapdata import read_map
import save_limits


class SaveLimitTests(unittest.TestCase):
    def test_decimal_and_binary_units(self):
        self.assertEqual(save_limits.parse_save_size('3MB'), 3_000_000)
        self.assertEqual(save_limits.parse_save_size('3MiB'), 3_145_728)
        self.assertEqual(save_limits.parse_save_size('1.5 MiB'), 1_572_864)
        self.assertEqual(save_limits.parse_save_size('123'), 123)
        for invalid in ('0', '-1MB', 'infinite', '3MK', '0.01B'):
            with self.assertRaises(ValueError):save_limits.parse_save_size(invalid)

    def test_default_has_no_limit(self):
        cells={(0,0):Cell(1,1)}
        with tempfile.TemporaryDirectory() as tmp:
            result=save_limits.write_map(Path(tmp),'test',cells)
            self.assertIsNone(result['save_limit_bytes'])
            self.assertEqual(read_map(Path(tmp)/'test.save.txt'),cells)

    def test_exact_boundary_and_overflow_preserve_previous_exports(self):
        small = {(0, 0): Cell(1, 1)}
        larger = {**small, (2, 0): Cell(15, 1)}
        limit = len((save_limits.encode(small) + '\n').encode('ascii'))
        self.assertGreater(len(save_limits.encode(larger)) + 1, limit)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            result = save_limits.write_map(folder, 'test', small, limit)
            saved = folder / 'test.save.txt'
            self.assertEqual(saved.stat().st_size, limit)
            self.assertEqual(result['save_bytes'], limit)
            self.assertEqual(read_map(saved), small)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            with self.assertRaises(save_limits.SaveSizeError):
                save_limits.write_map(folder, 'test', larger, limit)
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_overflow_does_not_create_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'new-build'
            with self.assertRaises(save_limits.SaveSizeError):
                save_limits.write_map(folder, 'test', {(0, 0): Cell(1, 1)}, 1)
            self.assertFalse(folder.exists())


if __name__ == '__main__':
    unittest.main()
