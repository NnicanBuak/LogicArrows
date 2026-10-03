"""Portable integration checks for the shared emulator, GPL-3.0."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'emulator'))
from backend import Program
from model_io import export_model
import run


class EmulatorTests(unittest.TestCase):
    def test_source_only_from_other_directory(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            os.chdir(folder)
            try:
                editor = Program(ROOT / '3deditor/3deditor.asm')
                editor.idle()
                self.assertEqual(editor.variable('projection'), 1)
                self.assertEqual(editor.variable('editing'), 0)
                self.assertEqual(len(export_model(editor)['vertices']), 8)
                self.assertGreater(len(editor.image), 1024)
            finally:
                os.chdir(previous)

    def test_32kb_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'boundary.asm'
            source.write_text('image db ' + ','.join(['0'] * 32768), encoding='utf-8')
            self.assertEqual(len(Program(source).image), 32768)
            source.write_text('image db ' + ','.join(['0'] * 32769), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '32768'):
                Program(source)

    def test_all_graphics_programs(self):
        names = ('cube', 'cube_polygons', 'pyramid', 'pyramid_polygons', 'crystal', 'crystal_polygons',
                 'cylinder', 'cylinder_polygons', 'controls', 'pyramid_obj')
        for name in names:
            path = ROOT / 'graphics3d/build' / name / 'graphics3d.asm'
            with self.subTest(program=path.parent.name):
                program = Program(path)
                self.assertGreater(len(program.image), 1024)
                program.machine.pause = False
                for _ in range(200):
                    program.machine.update([], 60)
                    if any(any(any(pixel) for pixel in column) for column in program.machine.colors):
                        break
                self.assertTrue(any(any(any(pixel) for pixel in column) for column in program.machine.colors))

    def test_compact_input(self):
        viewer = Program(ROOT / '3dviewer/3dviewer.asm')
        self.assertTrue(viewer.waits)
        viewer.idle()
        self.assertEqual(len(viewer.image), 978)
        self.assertEqual(viewer.machine.memory[7], 4)
        viewer.press(19)
        self.assertEqual(viewer.machine.memory[7], 5)
        qr = Program(ROOT / 'qr-terminal/qr_terminal21.asm')
        qr.idle()
        self.assertTrue(qr.waits)
        self.assertEqual(len(qr.image), 864)
        qr.press(ord('A'))
        self.assertEqual(qr.machine.memory[35], 1)

    def test_queue_and_model_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'model.json'
            app = run.App(ROOT / '3deditor/3deditor.asm', target)
            program, p = app.program, app.p
            program.idle()
            for key, text in ((p.K_SPACE, ' '), (ord('2'), '2'), (p.K_RETURN, ''), (p.K_TAB, '')):
                app.handle(p.event.Event(p.KEYDOWN, key=key, unicode=text))
            for _ in range(1000):
                app.update()
                if not app.queue and program.ready():
                    break
            self.assertFalse(app.queue)
            self.assertEqual(program.variable('editing'), 1)
            self.assertEqual(program.variable('mode'), 2)
            self.assertEqual(sum(program.machine.memory[program.layout['constants']['SELECT']:program.layout['constants']['SELECT'] + 128]), 1)
            original = export_model(program)
            app.handle(p.event.Event(p.KEYDOWN, key=p.K_F5, unicode=''))
            app.update()
            self.assertEqual(json.loads(target.read_text()), original)
            for code in map(ord, '1a'):
                program.press(code)
            program.press(127)
            self.assertFalse(export_model(program)['vertices'])
            app.handle(p.event.Event(p.KEYDOWN, key=p.K_F6, unicode=''))
            app.update()
            self.assertEqual(export_model(program), original)
            self.assertEqual(program.variable('editing'), 1)
            program.press(ord('h'))
            for key in (p.K_F5, p.K_F6):
                app.handle(p.event.Event(p.KEYDOWN, key=key, unicode=''))
            self.assertFalse(app.queue)
            # Inject the CPU code through the test adapter; no Escape KEYDOWN.
            program.press(27)
            self.assertEqual(program.variable('gizmo'), 0)
            # Saving after a quickly queued transform must save its result.
            for key, text in ((p.K_RETURN, ''), (ord('g'), 'g'), (ord('x'), 'x'),
                              (ord('1'), '1'), (p.K_RETURN, '')):
                app.handle(p.event.Event(p.KEYDOWN, key=key, unicode=text))
            app.handle(p.event.Event(p.KEYDOWN, key=p.K_F5, unicode=''))
            for _ in range(1000):
                app.update()
                if not app.queue and program.ready():
                    break
            self.assertFalse(app.queue)
            changed = export_model(program)
            self.assertNotEqual(changed, original)
            self.assertEqual(json.loads(target.read_text()), changed)
            app.handle(p.event.Event(p.KEYDOWN, key=p.K_F1, unicode=''))
            self.assertTrue(program.machine.pause)
            app.handle(p.event.Event(p.KEYDOWN, key=ord('p'), unicode='p'))
            position = program.machine.bank, program.machine.index, list(program.machine.reg)
            app.update()
            self.assertEqual((program.machine.bank, program.machine.index, program.machine.reg), position)
            self.assertEqual(list(app.queue), [ord('p')])
            previous_projection = program.variable('projection')
            app.handle(p.event.Event(p.KEYDOWN, key=p.K_F1, unicode=''))
            app.update()
            program.idle()
            self.assertEqual(program.variable('projection'), 1 - previous_projection)
            app.handle(p.event.Event(p.KEYDOWN, key=p.K_F2, unicode=''))
            app.program.idle()
            self.assertEqual(export_model(app.program), original)
            self.assertEqual(app.program.variable('editing'), 0)
            with patch.object(run, 'choose_file', return_value=str(ROOT / '3dviewer/3dviewer.asm')):
                app.handle(p.event.Event(p.KEYDOWN, key=p.K_F4, unicode=''))
            self.assertEqual(app.program.path.name, '3dviewer.asm')
            self.assertFalse(app.program.has_model)
            app.draw()


if __name__ == '__main__':
    unittest.main()
