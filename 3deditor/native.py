"""Adapter around the repository's unmodified Computer v2 emulator.

Only keyboard forwarding and execution pacing belong to this adapter. Geometry,
terminal output and rendering are executed from the compiled ASM image.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT.parent / 'graphics3d/vendor/emulator'


class Native:
    def __init__(self, headless=False):
        if headless:
            os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
        sys.path.insert(0, str(VENDOR))
        spec = importlib.util.spec_from_file_location('computer_v2_compiler', VENDOR / 'compiler.py')
        vendor_compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vendor_compiler)
        previous = sys.modules.get('compiler')
        sys.modules['compiler'] = vendor_compiler
        task_cwd = Path.cwd()
        os.chdir(VENDOR)
        try:
            import pygame
            from emulator import Emulator
        finally:
            os.chdir(task_cwd)
            if previous is None:
                del sys.modules['compiler']
            else:
                sys.modules['compiler'] = previous
        self.pygame = pygame
        self.layout = json.loads((ROOT / 'layout.json').read_text())
        self.machine = Emulator()
        self.machine.filename = str(ROOT / '3deditor.asm')
        self.machine.load()
        if self.machine.compilation_error:
            raise RuntimeError(self.machine.compilation_console)
        image = (ROOT / '3deditor.bin').read_bytes()
        assert bytes(self.machine.memory[:len(image)]) == image, 'Native and official compiler images differ'
        self.single = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3, unicode='')
        self.machine.speed = 3_000_000
        self.native_events = []
        self.batches = 0

    def ready(self):
        wait = self.layout['blocks']['vm_key_wait']
        m = self.machine
        return (m.bank == wait['bank'] and wait['address'] <= m.index < wait['address'] + 5
                and not m.memory[62] and (m.index == wait['address'] or m.reg[0] == 0))

    def idle(self):
        m = self.machine
        m.pause = False
        for _ in range(600):
            if self.ready():
                m.pause = True
                wait = self.layout['blocks']['vm_key_wait']['address']
                while m.index != wait or m.bank != self.layout['blocks']['vm_key_wait']['bank']:
                    m.update([self.single], 60)
                return
            m.update([], 60)
            self.batches += 1
        raise RuntimeError(f'Native timeout: bank {m.bank}, IP {m.index}')

    def event(self, code, testing=False):
        p = self.pygame
        special = {17: p.K_LEFT, 18: p.K_UP, 19: p.K_RIGHT, 20: p.K_DOWN,
                   9: p.K_TAB, 10: p.K_RETURN, 13: p.K_RETURN, 8: p.K_BACKSPACE,
                   127: p.K_DELETE}
        if code == 27:
            # Tests never dispatch a native Escape KEYDOWN. F2 is adapter-only.
            event = p.event.Event(p.KEYDOWN, key=p.K_F2 if testing else p.K_ESCAPE, unicode='')
        else:
            event = p.event.Event(p.KEYDOWN, key=special.get(code, code), unicode=chr(code) if code >= 32 else '')
        return event

    def press(self, code, testing=False):
        self.idle()
        event = self.event(code, testing)
        self.native_events.append(dict(code=code, key=event.key))
        self.machine.update([event], 60)
        if code == 27:
            self.machine.memory[62] = 27
        # Consume the input before examining the wait loop again.
        self.machine.update([self.single], 60)
        self.idle()

    @property
    def blink_phase(self):
        return self.machine.memory[self.layout['constants']['BLINK_PHASE']]

    def advance_blink(self):
        self.idle()
        assert self.machine.memory[self.layout['constants']['BLINK_ACTIVE']], 'No cursor to blink'
        previous = self.blink_phase
        self.machine.pause = False
        for _ in range(100):
            self.machine.update([], 60)
            self.batches += 1
            if self.blink_phase != previous:
                self.idle()
                assert self.blink_phase != previous
                return
        raise RuntimeError('Native cursor blink timeout')

    def word(self, address):
        v = self.machine.memory[address] | (self.machine.memory[address + 1] << 8)
        return v - 65536 if v & 32768 else v

    def variable(self, name):
        return self.word(self.layout['variables'][name])

    def snapshot(self):
        c = self.layout['constants']
        return bytes(self.machine.memory[c['MESH']:c['MESH'] + c['MESH_BYTES']])

    def displayed(self):
        result = bytearray(64)
        for y in range(16):
            for x in range(16):
                for plane in range(2):
                    if self.machine.colors[x][y][plane]:
                        result[plane * 32 + y * 2 + x // 8] |= 128 >> (x % 8)
        return bytes(result)

    def terminal_surface(self, scale=4):
        p = self.pygame
        surface = p.Surface((12 * 6 * scale, 4 * 8 * scale))
        surface.fill('white')
        for y in range(4):
            for x in range(12):
                cell = self.machine.console[y][x]
                surface.blit(p.transform.scale(cell, (6 * scale, 8 * scale)), (x * 6 * scale, y * 8 * scale))
        return surface
