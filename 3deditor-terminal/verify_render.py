"""Check the compiled ASM projection and clipping against independent geometry.

The bundled emulator executes CPU instructions from the disk image. The floating
point reference below is only a test oracle; it never renders the application.
Use --revision <commit> to demonstrate the regression in an older disk image.
"""
import argparse
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
sys.path.insert(0, str(ROOT.parent / 'emulator'))
from backend import load_core


class CPU:
    """Run the ordinary CPU core in batches, stopping at its keyboard wait."""
    def __init__(self, image):
        self.machine = load_core().Emulator()
        self.machine.memory[:len(image)] = image
        self.machine.pause = False
        self.machine.speed = 3_000_000
        self.steps = 0
        self.ram = self.machine.memory

    @property
    def bank(self):
        return self.machine.bank

    @bank.setter
    def bank(self, value):
        self.machine.bank = value

    @property
    def ip(self):
        return self.machine.index

    @ip.setter
    def ip(self, value):
        self.machine.index = value

    def at(self, layout, name):
        entry = layout['blocks'][name]
        return self.bank == entry['bank'] and self.ip == entry['address']

    def until(self, predicate, limit):
        start = self.steps
        while self.steps - start < limit:
            if predicate(self):
                return
            self.steps += self.machine.update([], 60)
            if self.machine.stop:
                raise RuntimeError('Unexpected CPU halt')
        raise RuntimeError(f'CPU timeout: bank {self.bank}, IP {self.ip}')


class Harness(CPU):
    def __init__(self, revision=None):
        def read(name):
            if revision:
                return subprocess.check_output(['git', 'show', f'{revision}:3deditor-terminal/{name}'], cwd=ROOT.parent)
            return (ROOT / name).read_bytes()
        super().__init__(read('3deditor-terminal.bin'))
        self.layout = json.loads(read('layout.json'))
        self.constants = self.layout['constants']
        self.common = self.layout['common']

    def word(self, address):
        value = int.from_bytes(self.ram[address:address + 2], 'little')
        return value - 65536 if value & 32768 else value

    def put_word(self, address, value):
        self.ram[address:address + 2] = (value & 65535).to_bytes(2, 'little')

    def variable(self, name, value):
        self.put_word(self.layout['variables'][name], value)

    def invoke(self, name, stop_at=None, **arguments):
        for arg, value in arguments.items():
            self.variable(f'{name}.{arg}', value)
        target = self.layout['bytecode_labels'][name]
        sentinel = self.constants['TRIAL']
        key = self.layout['blocks']['op_key']
        table = self.constants['DISPATCH']
        self.ram[sentinel] = next(i + 1 for i in range(64)
                                  if self.ram[table + i * 2:table + i * 2 + 2] == [key['bank'], key['address']])
        for field, value in [('PC_BANK', target // 128), ('PC_ADDR', 128 + target % 128), ('SP', 0), ('RSP', 2)]:
            self.ram[self.common[field]] = value
        base = self.constants['RETURN_STACK']
        self.ram[base:base + 2] = bytes([sentinel // 128, 128 + sentinel % 128])
        entry = self.layout['blocks']['vm_dispatch']
        wait = self.layout['blocks']['vm_key_wait']
        self.bank, self.ip = entry['bank'], entry['address']
        self.until(lambda cpu: (cpu.at(self.layout, 'vm_dispatch')
                   and cpu.ram[self.common['PC_BANK']] == sentinel // 128
                   and cpu.ram[self.common['PC_ADDR']] == 128 + sentinel % 128)
                   or (cpu.bank == wait['bank'] and wait['address'] <= cpu.ip < wait['address'] + 9
                       and cpu.ram[self.common['PC_BANK']] == (sentinel + 1) // 128
                       and cpu.ram[self.common['PC_ADDR']] == 128 + (sentinel + 1) % 128)
                   or (stop_at is not None and cpu.at(self.layout, stop_at)), limit=24_000_000)
        return self.word(self.constants['STACK'])

    def points(self, vertices, yaw, pitch, projection, zoom):
        for name, value in [('view_yaw', yaw), ('view_pitch', pitch), ('projection', projection), ('zoom', zoom)]:
            self.variable(name, value)
        for i, vertex in enumerate(vertices):
            for axis, value in enumerate(vertex):
                self.put_word(self.constants['VERTICES'] + i * 6 + axis * 2, value)
        if 'project_model' in self.layout['bytecode_labels']:
            for name, phase in [('camera_sin_y', yaw), ('camera_cos_y', (yaw + 8) % 32),
                                ('camera_sin_p', pitch), ('camera_cos_p', (pitch + 8) % 32)]:
                self.variable(name, self.word(self.constants['VIEW_SINE'] + phase * 2))
            for i in range(len(vertices)):
                self.invoke('project_model', i=i)
        else:
            self.invoke('render', stop_at='op_begin')
        return [tuple(self.word(self.constants['POINTS'] + i * 4 + a * 2) for a in (0, 1))
                for i in range(len(vertices))]

    def clear_frame(self):
        start = self.constants['TERMINAL_FRAME']
        self.ram[start:start + 2304] = bytes(2304)

    def pixels(self):
        start = self.constants['TERMINAL_FRAME']
        return {(x, y) for y in range(72) for x in range(144)
                if self.ram[start + (y // 8) * 256 + x] & (1 << (y % 8))}


def rounded(value):
    return (-1 if value < 0 else 1) * math.floor(abs(value) + 0.5)


def reference(vertex, yaw, pitch, projection, zoom):
    x, y, z = (value / 16 for value in vertex)
    cy, sy = math.cos(yaw * math.tau / 32), math.sin(yaw * math.tau / 32)
    cp, sp = math.cos(pitch * math.tau / 32), math.sin(pitch * math.tau / 32)
    x, z = cy * x + sy * z, cy * z - sy * x
    y, z = cp * y + sp * z, cp * z - sp * y
    scale = zoom * 0.225 if projection else zoom * 7.2 / (32 + z)
    return 72 + x * scale, 36 - y * scale


def projection_checks(cpu):
    views = [(4, 3, 10), (5, 3, 10), (5, 4, 30), (1, 7, 5), (7, 1, 30),
             (8, 8, 30), (11, 13, 30), (16, 0, 30), (24, 24, 30), (31, 3, 10)]
    meshes = [[tuple(size if i & bit else -size for bit in (1, 2, 4)) for i in range(8)]
              for size in (80, 81, 176)]
    cases = 0
    worst = 0
    for vertices in meshes:
        for yaw, pitch, zoom in views:
            for projection in (1, 0):
                points = cpu.points(vertices, yaw, pitch, projection, zoom)
                tolerance = 2 if abs(vertices[0][0]) == 176 else 1
                for vertex, point in zip(vertices, points):
                    expected = reference(vertex, yaw, pitch, projection, zoom)
                    error = max(abs(actual - wanted) for actual, wanted in zip(point, expected))
                    worst = max(worst, error)
                    assert error <= tolerance, ('projection', yaw, pitch, projection, zoom, vertex, point, expected, error)
                if projection:
                    for bit in (1, 2, 4):
                        edges = [tuple(points[i ^ bit][a] - points[i][a] for a in (0, 1))
                                 for i in range(8) if not i & bit]
                        assert all(max(v[a] for v in edges) - min(v[a] for v in edges) <= 2 for a in (0, 1)), ('parallel edges', yaw, pitch, bit, edges)
                cases += 1
        print(f'Projection: mesh Q4 radius {abs(vertices[0][0])}, {cases} cases passed', flush=True)
    return cases, worst


def clipping_checks(cpu):
    cases = [((-300, 20, 500, 20), {(x, 20) for x in range(144)}),
             ((500, 20, -300, 20), {(x, 20) for x in range(144)}),
             ((20, -300, 20, 500), {(20, y) for y in range(72)}),
             ((-200, -200, 300, 300), {(i, i) for i in range(72)}),
             ((-100, -100, -1, -1), set()),
             ((150, 20, 600, 70), set()),
             ((143, 71, 143, 71), {(143, 71)})]
    for (x, y, tx, ty), expected in cases:
        cpu.clear_frame()
        cpu.invoke('terminal_line', x=x, y=y, tx=tx, ty=ty, color=1)
        assert cpu.pixels() == expected, ('clipping', x, y, tx, ty, len(cpu.pixels()), len(expected))
    cpu.clear_frame()
    cpu.invoke('fill_triangle', ax=-300, ay=-400, bx=0, by=600, cx=500, cy=-400)
    expected = {(x, y) for x in range(144) for y in range(72) if (x ^ y) & 1 == 0}
    assert cpu.pixels() == expected, ('large triangle', len(cpu.pixels()), len(expected))
    cpu.clear_frame()
    cpu.invoke('fill_triangle', ax=-56, ay=-56, bx=200, by=-56, cx=-56, cy=200)
    expected = {(x, y) for x in range(144) for y in range(72) if x + y <= 144 and (x ^ y) & 1 == 0}
    assert cpu.pixels() == expected, ('triangle area overflow', len(cpu.pixels()), len(expected))
    return len(cases) + 2


def arithmetic_checks(cpu):
    rng = random.Random(3050)
    for _ in range(80):
        value = rng.randint(-9180, 9180)
        factor = rng.randint(-800, 800)
        divisor = rng.choice((-1, 1)) * rng.randint(1, 1000)
        expected = ((rounded(value * factor / divisor) + 32768) & 65535) - 32768
        actual = cpu.invoke('multiply_divide', value=value, factor=factor, divisor=divisor)
        assert actual == expected, ('multiply/divide', value, factor, divisor, actual, expected)
    return 80


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision')
    args = parser.parse_args()
    cpu = Harness(args.revision)
    count, worst = projection_checks(cpu)
    clipped = clipping_checks(cpu)
    arithmetic = arithmetic_checks(cpu)
    print(json.dumps(dict(projection_cases=count, max_pixel_error=round(worst, 3),
                          clipping_cases=clipped, arithmetic_cases=arithmetic, cpu_steps=cpu.steps)))
