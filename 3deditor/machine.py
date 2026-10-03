"""Headless ISA harness; used to inspect the compiled editor, not to run its logic."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'graphics3d/vendor/cpu_model'))
from debug_cpu import CPU


class Machine(CPU):
    def __init__(self):
        self.layout = json.loads((ROOT / 'layout.json').read_text())
        super().__init__((ROOT / '3deditor.bin').read_bytes())
        self.front = bytearray(64)
        self.console = [''] * 4
        self.column = 0
        self.max_sp = 0
        self.max_rsp = 0
        self.frames = 0

    def write(self, address, value):
        value &= 255
        physical = self.physical(address)
        if physical < 25 or 128 <= physical < self.layout['native_bytes'] or physical >= self.layout['constants']['PROGRAM']:
            raise AssertionError(('write outside working memory', physical, self.bank, self.ip))
        super().write(address, value)
        if address == 60 and self.devices & 1:
            if value == 12:
                self.console = [''] * 4
                self.column = 0
            elif value == 10:
                self.console = self.console[1:] + ['']
                self.column = 0
            elif value >= 32:
                self.console[-1] += chr(value)
                self.column += 1
                if self.column == 12:
                    self.console = self.console[1:] + ['']
                    self.column = 0
        if 64 <= address < 128 and self.devices & 16:
            self.front[address - 64] = value
            if address == 127:
                self.frames += 1
        common = self.layout['common']
        if address == common['SP']:
            self.max_sp = max(self.max_sp, value)
        if address == common['RSP']:
            self.max_rsp = max(self.max_rsp, value)

    def idle(self):
        self.until(lambda c: c.at(self.layout, 'vm_key_wait'), limit=12_000_000)

    def type(self, codes):
        if isinstance(codes, str):
            codes = [ord(ch) for ch in codes]
        for key in codes:
            self.idle()
            self.keys.append(key)
            self.step()
            self.until(lambda c: not c.keys and c.at(self.layout, 'vm_key_wait'), limit=12_000_000)

    def word(self, address):
        v = int.from_bytes(self.ram[address:address + 2], 'little')
        return v - 65536 if v & 32768 else v

    def variable(self, name):
        return self.word(self.layout['variables'][name])

    def vertices(self):
        base = self.layout['constants']['VERTICES']
        alive = self.layout['constants']['VLIVE']
        return {i: [self.word(base + i * 6 + a * 2) for a in range(3)] for i in range(32) if self.ram[alive + i]}

    def snapshot(self):
        c = self.layout['constants']
        return bytes(self.ram[c['MESH']:c['MESH'] + c['MESH_BYTES']])


if __name__ == '__main__':
    m = Machine()
    m.idle()
    print(dict(steps=m.steps, console=m.console, mode=m.variable('mode'),
               cursor=m.variable('cursor'), vertices=m.vertices(),
               stack=m.max_sp, calls=m.max_rsp, frames=m.frames,
               screen=list(m.front)))
