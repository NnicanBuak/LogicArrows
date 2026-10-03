"""Verify compiled instructions against independent arithmetic, geometry and pixels."""
import hashlib
import json
import math
import random
from pathlib import Path

from compiler import OPS
from machine import Machine, ROOT

checks = dict(arithmetic_cases=0, keyboard_events=0, pixel_frames=0, assertions=0)


def expect(value, message='check failed'):
    checks['assertions'] += 1
    assert value, message


def trunc(a, b):
    return (-1 if (a < 0) != (b < 0) else 1) * (abs(a) // abs(b))


def word(v):
    return ((v + 32768) & 65535) - 32768


def arithmetic():
    rng = random.Random(3010)
    m = Machine()
    c = m.layout['constants']
    code = bytearray()
    expected = []
    functions = dict(ADD=lambda a, b: a + b, SUB=lambda a, b: a - b,
                     MUL=lambda a, b: a * b, DIV=trunc,
                     MOD=lambda a, b: a - trunc(a, b) * b,
                     LT=lambda a, b: int(a < b), EQ=lambda a, b: int(a == b),
                     AND=lambda a, b: a & b, OR=lambda a, b: a | b,
                     XOR=lambda a, b: a ^ b, SHL=lambda a, b: a << b,
                     SHR=lambda a, b: a >> b)
    for op, fn in functions.items():
        for i in range(32):
            a = rng.randint(-32767, 32767)
            b = rng.randint(0, 15) if op in ('SHL', 'SHR') else rng.randint(-32767, 32767)
            if op in ('DIV', 'MOD') and b == 0:
                b = 1
            for value in [a, b]:
                code += bytes([OPS['CONST']]) + (value & 65535).to_bytes(2, 'little')
            code += bytes([OPS[op], OPS['SET']]) + (c['GLOBAL_WORDS'] + len(expected) * 2).to_bytes(2, 'little')
            expected.append(word(fn(a, b)))
    code += bytes([OPS['KEY']])
    m.ram[c['PROGRAM']:c['PROGRAM'] + len(code)] = code
    m.idle()
    for i, value in enumerate(expected):
        expect(m.word(c['GLOBAL_WORDS'] + i * 2) == value, ('arithmetic', i, value, m.word(c['GLOBAL_WORDS'] + i * 2)))
    checks['arithmetic_cases'] = len(expected)


def product(v, phase):
    phase %= 32
    negative = phase >= 16
    p = phase % 16
    p = min(p, 16 - p)
    value = round(abs(v) * math.sin(p * math.tau / 32))
    return -value if negative != (v < 0) else value


def pair(u, v, phase):
    return product(u, phase + 8) + product(v, phase), product(v, phase + 8) - product(u, phase)


def projected(m):
    result = {}
    for i, p in m.vertices().items():
        x, y, z = [trunc(v, 16) for v in p]
        x, z = pair(x, z, m.variable('view_yaw'))
        y, z = pair(y, z, m.variable('view_pitch'))
        expect(8 <= z + 32 <= 63 and -32 <= x <= 31 and -32 <= y <= 31, 'API projection range')
        zoom = m.variable('zoom')
        result[i] = [8 + trunc((x // 2) * zoom, 10), 8 + trunc(((-y) // 2) * zoom, 10)]
    return result


def line_pixels(a, b):
    x, y = a
    ex, ey = b
    dx, dy = abs(ex - x), abs(ey - y)
    sx, sy = (1 if ex >= x else -1), (1 if ey >= y else -1)
    major = max(dx, dy)
    error = (major - 1) // 2
    result = set()
    for i in range(major + 1):
        if 0 <= x < 16 and 0 <= y < 16:
            result.add((x, y))
        if dx >= dy:
            x += sx
            error -= dy
            if error < 0:
                error += dx
                y += sy
        else:
            y += sy
            error -= dx
            if error < 0:
                error += dy
                x += sx
    return result


def triangle_pixels(a, b, c):
    def cross(u, v, p):
        return (v[0] - u[0]) * (p[1] - u[1]) - (v[1] - u[1]) * (p[0] - u[0])
    if cross(a, b, c) == 0:
        return set()
    return {(x, y) for y in range(16) for x in range(16)
            if all(d >= 0 for d in [cross(a, b, (x, y)), cross(b, c, (x, y)), cross(c, a, (x, y))])
            or all(d <= 0 for d in [cross(a, b, (x, y)), cross(b, c, (x, y)), cross(c, a, (x, y))])}


def reference(m):
    points = projected(m)
    c = m.layout['constants']
    edges = {i: list(m.ram[c['EDGES'] + i * 2:c['EDGES'] + i * 2 + 2]) for i in range(64) if m.ram[c['ELIVE'] + i]}
    faces = {i: list(m.ram[c['FACES'] + i * 5 + 1:c['FACES'] + i * 5 + 1 + m.ram[c['FACES'] + i * 5]]) for i in range(32) if m.ram[c['FACES'] + i * 5]}

    def primitive(mode, i):
        if i < 0:
            return set()
        if mode == 1:
            x, y = points[i]
            return {(x, y)} if 0 <= x < 16 and 0 <= y < 16 else set()
        if mode == 2:
            a, b = edges[i]
            return line_pixels(points[a], points[b])
        face = faces[i]
        pixels = triangle_pixels(*[points[v] for v in face[:3]])
        if len(face) == 4:
            pixels |= triangle_pixels(*[points[face[v]] for v in [0, 2, 3]])
        return pixels

    base = set()
    for i in edges:
        base |= primitive(2, i)
    for i in points:
        base |= primitive(1, i)
    mode = m.variable('mode')
    selected = set()
    offset = [0, 0, 32, 96][mode]
    for i in (points if mode == 1 else (edges if mode == 2 else faces)):
        if m.ram[c['SELECT'] + offset + i]:
            selected |= primitive(mode, i)
    current = primitive(mode, m.variable('cursor'))
    result = bytearray(64)
    for y in range(16):
        for x in range(16):
            p = (x, y)
            color = 1 if p in current else (2 if p in selected else (3 if p in base else 0))
            address, mask = 2 * y + x // 8, 128 >> (x % 8)
            if color & 1:
                result[address] |= mask
            if color & 2:
                result[address + 32] |= mask
    return bytes(result)


def frame(m):
    expect(bytes(m.front) == reference(m), ('pixels', m.variable('mode'), m.variable('cursor'), list(m.front), list(reference(m))))
    checks['pixel_frames'] += 1
    c = m.layout['constants']
    points = projected(m)
    for i, p in points.items():
        expect([m.word(c['POINTS'] + i * 4 + a * 2) for a in range(2)] == p, ('projection', i, p))
    expect(m.max_sp < 128 and m.max_rsp < 128, 'stack capacity')


def type_keys(m, keys, pixels=True):
    m.type(keys)
    checks['keyboard_events'] += len(keys)
    if pixels:
        frame(m)


def integrity(m):
    c = m.layout['constants']
    vertices = m.vertices()
    edges = set()
    for i in range(64):
        if m.ram[c['ELIVE'] + i]:
            a, b = m.ram[c['EDGES'] + i * 2:c['EDGES'] + i * 2 + 2]
            expect(a in vertices and b in vertices and a != b, 'edge references')
            key = tuple(sorted((a, b)))
            expect(key not in edges, 'duplicate edge')
            edges.add(key)
    for i in range(32):
        n = m.ram[c['FACES'] + i * 5]
        if n:
            expect(n in (3, 4), 'face arity')
            f = m.ram[c['FACES'] + i * 5 + 1:c['FACES'] + i * 5 + n + 1]
            expect(len(set(f)) == n and all(v in vertices for v in f), 'face references')
            expect(all(tuple(sorted((a, b))) in edges for a, b in zip(f, f[1:] + f[:1])), 'face edges')


def geometry():
    m = Machine()
    m.idle()
    frame(m)
    original = m.snapshot()
    type_keys(m, [127])
    expect(m.snapshot() == original, 'Del with cursor only')
    type_keys(m, [10])
    type_keys(m, 'gx2\n')
    expect(m.vertices()[0] == [-48, -80, -80], 'first relative move')
    type_keys(m, 'gx+2\n')
    expect(m.vertices()[0] == [-16, -80, -80], 'second relative move')
    type_keys(m, 'gy-0.5\n')
    expect(m.vertices()[0] == [-16, -88, -80], 'signed fractional move')
    changed = m.snapshot()
    type_keys(m, 'gx22\n', False)
    expect(m.variable('last_error') == 2 and m.snapshot() == changed, 'range rollback')
    type_keys(m, [27])  # ISA injection, no native Escape event.
    type_keys(m, 'q')
    expect(m.snapshot() == changed and m.ram[m.layout['constants']['SELECT']] == 1, 'q is free')
    type_keys(m, [27])
    expect(not any(m.ram[m.layout['constants']['SELECT']:m.layout['constants']['SELECT'] + 128]), 'Esc clears selection')
    type_keys(m, 'a')
    type_keys(m, 'sx2\n')
    before = m.vertices()
    type_keys(m, 'sx0.5\n')
    expect(all(m.vertices()[i][0] == trunc(before[i][0], 2) + trunc(m.variable('px'), 2) for i in before), 'scale around selection center')
    before = m.vertices()
    pivot = [trunc(sum(v[a] for v in before.values()), len(before)) for a in range(3)]
    type_keys(m, 'sx0.5\n')
    before = m.vertices()
    pivot = [trunc(sum(v[a] for v in before.values()), len(before)) for a in range(3)]
    type_keys(m, 'sx-2\n')
    expect(all(m.vertices()[i][0] == pivot[0] - 2 * (before[i][0] - pivot[0]) for i in before), 'negative scale')
    type_keys(m, 'u')
    expect(m.vertices() == before, 'undo transform')
    # A fresh cube for exact right-angle and fine rotations.
    m = Machine()
    m.idle()
    type_keys(m, 'a')
    before = m.vertices()
    type_keys(m, 'rz90\n')
    expect(m.vertices() == {i: [-p[1], p[0], p[2]] for i, p in before.items()}, 'Z right-angle rotation')
    type_keys(m, 'rz90\n')
    expect(m.vertices() == {i: [-p[0], -p[1], p[2]] for i, p in before.items()}, 'rotation compounds')
    before = m.vertices()
    type_keys(m, 'ry-30.1\n')
    expect(m.variable('tool') == 0 and not m.variable('last_error'), 'fine negative rotation')
    sine = round(256 * math.sin(-30.1 * math.pi / 180))
    cosine = round(256 * math.cos(-30.1 * math.pi / 180))
    expect(m.vertices() == {i: [(p[0] * cosine + p[2] * sine + 128) // 256, p[1], (p[2] * cosine - p[0] * sine + 128) // 256] for i, p in before.items()}, 'independent Q8 fine rotation')
    before = m.vertices()
    type_keys(m, 'gz0.0625\n')
    expect(m.vertices() == {i: [p[0], p[1], p[2] + 1] for i, p in before.items()}, 'exact 1/16 input')
    integrity(m)
    # Input errors retain the model and active tool.
    type_keys(m, 'g', False)
    before = m.snapshot()
    for bad, code in [('x', 1), ('x.', 1), ('x1.23456', 3), ('x999', 2), ('-2', 1), ('x22.0001', 2)]:
        type_keys(m, [8] * m.variable('input_length'), False)
        type_keys(m, bad + '\n', False)
        expect(m.snapshot() == before and m.variable('last_error') == code and m.variable('tool') == 103, ('input', bad))
    for bad in [' ', 'X', 'G', ',', 'q']:
        length = m.variable('input_length')
        type_keys(m, bad, False)
        expect(m.variable('input_length') == length and m.variable('last_error') == 1, ('filter', bad))
    type_keys(m, [8] * m.variable('input_length') + [ord('x')] + [ord('0')] * 8 + [ord('0')], False)
    expect(m.variable('input_length') == 9 and m.variable('last_error') == 1, 'line length')
    type_keys(m, [27])
    expect(m.snapshot() == before, 'cancel typing')
    type_keys(m, 'r' + 'x0.11\n', False)
    expect(m.variable('last_error') == 3 and m.snapshot() == before, 'rotation precision')
    type_keys(m, [27])
    # Navigation and mode changes use screen positions.
    type_keys(m, '1')
    for key in [17, 18, 19, 20]:
        cursor = m.variable('cursor')
        p = projected(m)[cursor]
        type_keys(m, [key])
        q = projected(m)[m.variable('cursor')]
        expect((q[0] <= p[0] if key == 17 else (q[1] <= p[1] if key == 18 else (q[0] >= p[0] if key == 19 else q[1] >= p[1]))), 'arrow direction')
    type_keys(m, [10, 9, 10])
    type_keys(m, '2')
    expect(not any(m.ram[m.layout['constants']['SELECT']:m.layout['constants']['SELECT'] + 128]), 'mode clears every list')
    for keys in ['a', 'gz0.5\n', '3', 'a', 'gx-0.5\n']:
        type_keys(m, keys)
    # Shared vertices move only once even if several selected faces/edges use them.
    expect(all(absolute <= 176 for p in m.vertices().values() for absolute in map(abs, p)), 'coordinate bounds')
    integrity(m)
    print('geometry and input passed', flush=True)


def topology():
    for mode, remaining in [('1', (7, 9, 3)), ('2', (8, 11, 4)), ('3', (8, 12, 5))]:
        m = Machine()
        m.idle()
        before = m.snapshot()
        type_keys(m, mode)
        type_keys(m, [10, 127])
        c = m.layout['constants']
        counts = (len(m.vertices()), sum(bool(v) for v in m.ram[c['ELIVE']:c['ELIVE'] + 64]), sum(bool(m.ram[c['FACES'] + i * 5]) for i in range(32)))
        expect(counts == remaining, ('delete mode', mode, counts))
        integrity(m)
        type_keys(m, 'u')
        expect(m.snapshot() == before, 'undo topology')
    m = Machine()
    m.idle()
    type_keys(m, 'a')
    type_keys(m, [127])
    expect(not m.vertices() and bytes(m.front) == bytes(64) and m.variable('cursor') == -1, 'delete whole model')
    type_keys(m, 'n')
    expect(m.vertices() == {0: [0, 0, 0]}, 'create first vertex in empty model')
    type_keys(m, 'gx-2\n')
    type_keys(m, 'n')
    type_keys(m, 'gx2\n')
    type_keys(m, [9, 10])
    type_keys(m, 'f')
    integrity(m)
    expect(sum(m.ram[m.layout['constants']['ELIVE']:m.layout['constants']['ELIVE'] + 64]) == 1, 'create edge')
    type_keys(m, 'f', False)
    expect(m.variable('last_error') == 6, 'duplicate edge error')
    type_keys(m, 'n')
    type_keys(m, 'gy2\n')
    type_keys(m, [9, 10, 9, 10])
    type_keys(m, 'f')
    integrity(m)
    expect(m.ram[m.layout['constants']['FACES']] == 3, 'create triangle')
    type_keys(m, '3')
    type_keys(m, [10])
    type_keys(m, 'sx0\n')
    integrity(m)
    # Capacity and failed creation, exercised through actual key commands.
    m = Machine()
    m.idle()
    type_keys(m, 'n' * 24, False)
    expect(len(m.vertices()) == 32, 'vertex capacity')
    before = m.snapshot()
    type_keys(m, 'n', False)
    expect(m.variable('last_error') == 5 and m.snapshot() == before, 'capacity is atomic')
    frame(m)
    print('topology and capacity passed', flush=True)


def views():
    m = Machine()
    m.idle()
    for keys in ['+' * 10, 'j', 'i', 'l', 'k', '-' * 13, ' ', '2', 'a', '3', 'a']:
        type_keys(m, keys)
    expect(m.variable('zoom') == 10, 'view reset')
    integrity(m)
    checks['max_stack_bytes'] = m.max_sp
    checks['max_call_stack_bytes'] = m.max_rsp


def main():
    compiled = json.loads((ROOT / '3deditor.compile.json').read_text())
    image = (ROOT / '3deditor.bin').read_bytes()
    expect(not compiled['errors'] and len(image) == compiled['bytes'] <= 32768, 'compile and size')
    arithmetic()
    print('arithmetic passed', flush=True)
    geometry()
    topology()
    views()
    checks.update(program_sha256=hashlib.sha256(image).hexdigest(), bytes=len(image), limit=32768,
                  native_escape_keydown_tested=False, escape_test='ISA code 27 only; native test adapter uses F2',
                  result='passed')
    (ROOT / 'verification.json').write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(checks), flush=True)


if __name__ == '__main__':
    main()
