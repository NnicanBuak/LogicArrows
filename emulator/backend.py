"""Shared Computer v2 host, GPL-3.0. Added 2026-10-04.

ASM instructions, display and terminal are executed by the bundled CPU core.
The host only loads source, queues keys and exposes optional model persistence.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / 'vendor/computer_v2'
_CORE = None


def load_core():
    global _CORE
    if _CORE is None:
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
        sys.path.insert(0, str(VENDOR))
        spec = importlib.util.spec_from_file_location('computer_v2_compiler', VENDOR / 'compiler.py')
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        previous = sys.modules.get('compiler')
        sys.modules['compiler'] = compiler
        previous_cwd = Path.cwd()
        os.chdir(VENDOR)
        try:
            spec = importlib.util.spec_from_file_location('computer_v2_core', VENDOR / 'emulator.py')
            core = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(core)
        finally:
            os.chdir(previous_cwd)
            if previous is None:
                del sys.modules['compiler']
            else:
                sys.modules['compiler'] = previous
        _CORE = core
    return _CORE


def profile(source):
    for line in source.splitlines():
        if line.startswith('; emulator-profile: '):
            data = json.loads(line.split(': ', 1)[1])
            if data.get('model') != '3DEditor-Q4':
                raise ValueError('Unsupported emulator profile')
            constants = data['constants']
            for name in ('COUNTS', 'VERTICES', 'VLIVE', 'EDGES', 'ELIVE', 'FACES', 'MESH', 'SELECT'):
                if type(constants[name]) is not int or not 128 <= constants[name] < 32768:
                    raise ValueError('Invalid memory address in emulator profile')
            if not 0 < constants['MESH_BYTES'] <= 1024 or constants['MESH'] + constants['MESH_BYTES'] > 32768:
                raise ValueError('Invalid mesh region')
            for name in ('tool', 'input_length', 'order_count', 'undo_valid', 'cursor', 'editing',
                         'view_yaw', 'view_pitch', 'zoom', 'gizmo'):
                address = data['variables'][name]
                if type(address) is not int or not 128 <= address <= 32766:
                    raise ValueError('Invalid variable address')
            wait = data['input_wait']
            if (type(wait['bank']) is not int or type(wait['address']) is not int
                    or not 1 <= wait['bank'] <= 255 or not 128 <= wait['address'] <= 251):
                raise ValueError('Invalid keyboard wait address')
            return data
    return {}


class Program:
    def __init__(self, filename):
        self.path = Path(filename).resolve()
        source = self.path.read_text(encoding='utf-8-sig')
        self.profile = profile(source)
        self.core = load_core()
        self.pygame = self.core.pygame
        image, diagnostics, error = self.core.compile(source)
        if error:
            raise ValueError(diagnostics)
        if not 0 < len(image) <= 32768:
            raise ValueError('Program must contain 1..32768 bytes')
        self.image = bytes(image)
        self.machine = self.core.Emulator()
        self.machine.filename = str(self.path)
        self.machine.compilation_console = diagnostics
        for address, value in enumerate(image):
            self.machine.memory[address] = value
            if 0x3A <= address <= 0x7F and address not in (0x3C, 0x3D):
                self.machine.update_ports(address, value)
        self.machine.speed = 3_000_000
        self.layout = {'constants': self.profile.get('constants', {}),
                       'variables': self.profile.get('variables', {})}
        wait = self.profile.get('input_wait')
        self.waits = [wait] if wait else self.keyboard_loops()
        self.single = self.pygame.event.Event(self.pygame.KEYDOWN, key=self.pygame.K_F3, unicode='')

    @property
    def has_model(self):
        return self.profile.get('model') == '3DEditor-Q4'

    def keyboard_loops(self):
        waits = []
        for physical in range(len(self.image) - 4):
            address = physical if physical < 128 else 128 + physical % 128
            # ld a, 62; test a; jz back to the port read.
            if self.image[physical:physical + 5] == bytes((0x50, 62, 0xB0, 0x08, address)):
                waits.append({'bank': max(1, physical // 128), 'address': address})
        return waits

    def ready(self):
        m = self.machine
        if m.memory[62]:
            return False
        for wait in self.waits:
            if (m.bank == wait['bank'] and wait['address'] <= m.index < wait['address'] + 5
                    and (m.index == wait['address'] or m.reg[0] == 0)):
                return True
        return not self.waits

    def word(self, address):
        memory = self.machine.memory
        value = memory[address] | (memory[address + 1] << 8)
        return value - 65536 if value & 32768 else value

    def variable(self, name):
        return self.word(self.layout['variables'][name])

    def idle(self):
        if not self.waits:
            return
        m = self.machine
        paused = m.pause
        m.pause = False
        try:
            for _ in range(1000):
                if self.ready():
                    return
                m.update([], 60)
            raise RuntimeError('Program did not reach keyboard input')
        finally:
            m.pause = paused

    def press(self, code):
        self.idle()
        self.machine.memory[62] = code
        self.machine.update([self.single], 60)
        self.idle()

    def terminal_surface(self, scale=4):
        p = self.pygame
        m = self.machine
        surface = p.Surface((m.console_w * 6 * scale, m.console_h * 8 * scale))
        surface.fill('white')
        for y in range(m.console_h):
            for x in range(m.console_w):
                surface.blit(p.transform.scale(m.console[y][x], (6 * scale, 8 * scale)),
                             (x * 6 * scale, y * 8 * scale))
        return surface
