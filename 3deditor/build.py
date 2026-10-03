"""Link 3DEditor, its word runtime, and the required 3DGraphics API functions."""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / 'graphics3d' / 'src'))
sys.path.insert(0, str(REPO / 'graphics3d' / 'tools'))
from engine import api_blocks
from compiler import Compiler, OPS
from runtime import blocks

FIELDS = ('ret0_bank ret0_addr ret1_bank ret1_addr ret2_bank ret2_addr ret3_bank ret3_addr '
          'io_ret_bank ptr_bank ptr_addr vertex_count edge_count yaw pitch roll out_bank out_addr '
          'wx wy wz ru rv angle t0 t1 x0 y0 x1 y1 dx dy sx sy err mask color').split()
ALIASES = dict(signs='mask', mul_sign='err', depth='angle', PC_BANK='ptr_bank', PC_ADDR='ptr_addr',
               SP='vertex_count', RSP='edge_count', U0='wx', U1='wy', V0='wz', V1='ru',
               W0='rv', W1='angle', M0='out_bank', M1='out_addr', opcode='yaw')


def ins_size(line):
    p = line.replace(',', ' ').split()
    if line.endswith(':') or not p or p[0].startswith(';'):
        return 0
    if p[0] == 'db':
        return len(p) - 1
    if p[0] == 'ldi':
        return 2
    if p[0] in ('ld', 'st') or p[0].startswith('j'):
        return 1 if p[-1] in ('a', 'b', 'c', 'd') else 2
    return 1


def dependencies():
    raw = api_blocks()
    owners = {}
    for name, lines, comment in raw:
        owners[name] = name
        for line in lines:
            if line.endswith(':'):
                owners[line[:-1]] = name
    wanted = {'gfx_project_vertex', 'gfx_pixel', 'gfx_line', 'gfx_triangle', 'pixel_masks', 'triangle_registers'}
    changed = True
    while changed:
        changed = False
        for name, lines, comment in raw:
            if name in wanted:
                for line in lines:
                    p = line.split()
                    if p and p[0] in ('GO', 'IF', 'CALL') and p[-1] in owners:
                        target = owners[p[-1]]
                        if target not in wanted:
                            wanted.add(target)
                            changed = True
    return [(n, list(s), '3DGraphics API: ' + n) for n, s, c in raw if n in wanted]


def packed(raw):
    """Deterministic first-fit; whole API units retain their adjacent tables."""
    units = []
    for name, lines, comment in raw:
        if name in ('pixel_masks', 'triangle_registers'):
            host = 'gfx_pixel' if name == 'pixel_masks' else 'triangle_load0'
            next(u for u in units if u[0][0] == host).append((name, lines, comment))
        else:
            units.append([(name, lines, comment)])

    def owner_map():
        result = {'set_bank': -1, 'read_byte': -1, 'write_byte': -1}
        for i, entries in enumerate(units):
            for name, lines, _ in entries:
                result[name] = i
                result.update({s[:-1]: i for s in lines if s.endswith(':')})
        return result

    def cost(i, others, owner):
        size = 0
        for _, lines, _ in units[i]:
            for s in lines:
                p = s.split()
                if p[0] in ('GO', 'IF', 'CALL'):
                    internal = owner[p[-1]] in others
                    size += (10 if p[0] == 'CALL' else 2) + (0 if internal else (6 if p[0] == 'IF' else 4))
                elif p[0] == 'RETURN':
                    size += 6
                elif p[0] in ('READ', 'WRITE'):
                    size += 12
                elif p[0] in ('READ_REG', 'WRITE_REG'):
                    size += 8
                else:
                    size += ins_size(s)
        return size

    # Split only runtime functions as needed. An explicit GO connects the chunks.
    serial = 0
    while True:
        owner = owner_map()
        oversized = next((i for i in range(len(units)) if cost(i, {i}, owner) > 128), None)
        if oversized is None:
            break
        name, lines, comment = units[oversized][0]
        if comment.startswith('3DGraphics'):
            raise ValueError((name, cost(oversized, {oversized}, owner)))
        serial += 1
        split = len(lines) // 2
        tail = f'native_continuation_{serial}'
        units[oversized] = [(name, lines[:split] + ['GO ' + tail], comment)]
        units.append([(tail, lines[split:], comment)])
    owner = owner_map()
    groups = []
    for i in sorted(range(len(units)), key=lambda i: -cost(i, {i}, owner)):
        choices = []
        for bank, group in enumerate(groups):
            candidate = set(group) | {i}
            size = sum(cost(j, candidate, owner) for j in candidate)
            if size <= 128:
                choices.append((size, bank))
        if choices:
            groups[max(choices)[1]].append(i)
        else:
            groups.append([i])
    bybank = {b: [e for i in group for e in units[i]] for b, group in enumerate(groups, 1)}
    banks = {'set_bank': 0, 'read_byte': 0, 'write_byte': 0}
    for bank, entries in bybank.items():
        for name, lines, _ in entries:
            banks[name] = bank
            banks.update({s[:-1]: bank for s in lines if s.endswith(':')})
    return bybank, banks


def build():
    raw = [(n, [s.strip() for s in lines if s.strip()], c) for n, lines, c in blocks() + dependencies()]
    bybank, banks = packed(raw)
    native_end = (max(bybank) + 1) * 128
    next_address = native_end
    data = bytearray()
    constants = {}

    def reserve(name, length, content=b'', align=False):
        nonlocal next_address
        if align:
            padding = (-next_address) % 128
            next_address += padding
            data.extend(b'\0' * padding)
        constants[name] = next_address
        data.extend(content + b'\0' * (length - len(content)))
        next_address += length
        return constants[name]

    reserve('DISPATCH', 128, align=True)
    reserve('STACK', 128, align=True)
    reserve('RETURN_STACK', 128, align=True)
    reserve('CONTEXT', 128, align=True)
    state = bytearray(128)
    state[8] = 1
    for phase in range(1, 8):
        coefficient = math.sin(phase * math.tau / 32)
        bits = [round(m * coefficient) - round((m - 1) * coefficient) for m in range(1, 33)]
        state[23 + (phase - 1) * 4:27 + (phase - 1) * 4] = bytes(sum(bits[i + j] << j for j in range(8)) for i in range(0, 32, 8))
    reserve('STATE', 128, state, align=True)
    reserve('TRI_STATE', 128, align=True)
    reserve('GLOBAL_WORDS', 1024, align=True)
    reserve('STRINGS', 1024, align=True)
    mesh_start = next_address
    reserve('COUNTS', 3, bytes([8, 12, 6]))
    vertices = [[80 if i & bit else -80 for bit in (1, 2, 4)] for i in range(8)]
    reserve('VERTICES', 192, b''.join((v & 65535).to_bytes(2, 'little') for p in vertices for v in p))
    reserve('VLIVE', 32, bytes([1] * 8))
    edges = [(i, i ^ bit) for bit in (1, 2, 4) for i in range(8) if not i & bit]
    reserve('EDGES', 128, bytes(v for edge in edges for v in edge))
    reserve('ELIVE', 64, bytes([1] * 12))
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    reserve('FACES', 160, bytes(v for face in faces for v in [4] + face))
    constants.update(MESH=mesh_start, MESH_BYTES=next_address - mesh_start)
    reserve('SELECT', 128)
    reserve('ORDER', 32)
    reserve('MARKS', 32)
    reserve('POINTS', 128)
    reserve('TRIAL', 192)
    reserve('UNDO', constants['MESH_BYTES'])
    reserve('BASE_MASK', 32)
    reserve('SELECT_MASK', 32)
    reserve('BLINK_FRAMES', 128, align=True)
    constants['STEADY_FRAME'] = constants['BLINK_FRAMES'] + 64
    reserve('INPUT', 16)
    reserve('SINE', 7200, b''.join((round(256 * math.sin(i * math.tau / 3600)) & 65535).to_bytes(2, 'little') for i in range(3600)))
    reserve('PROGRAM', 0, align=True)
    constants['PROJECT_RESULT'] = constants['CONTEXT'] + 4
    constants['BLINK_PHASE'] = constants['CONTEXT'] + 8
    constants['BLINK_ACTIVE'] = constants['CONTEXT'] + 9
    compiler = Compiler((ROOT / 'editor.py').read_text(encoding='utf-8'), constants,
                        constants['GLOBAL_WORDS'], constants['STRINGS'])
    program = compiler.compile(constants['PROGRAM'])
    assert len(compiler.strings) <= 1024
    data[constants['STRINGS'] - native_end:constants['STRINGS'] - native_end + len(compiler.strings)] = compiler.strings
    data.extend(program)
    image_bytes = native_end + len(data)
    assert image_bytes <= 32768, (image_bytes, len(program), len(compiler.variables))
    constants.update({k + '_BANK': constants[k] // 128 for k in ['DISPATCH', 'STACK', 'RETURN_STACK', 'CONTEXT', 'STATE', 'TRI_STATE', 'BLINK_FRAMES', 'PROGRAM']})
    constants.update({f'CTX{i}': 128 + i for i in range(8)})
    constants.update(CTX_BLINK_PHASE=136, CTX_BLINK_ACTIVE=137)
    constants.update(LUT_BASE=constants['STATE_BANK'], LUT_ADDR=151, CAMERA_DISTANCE=32,
                     STATE_TX=140, STATE_TY=141, STATE_TZ=142, STATE_PROJECTION=136,
                     TRI_STATE_END=140, VERTEX_BASE=1, APP_BANK=banks['main'])
    constants.update({f'TRI_STATE{i}': 128 + i for i in range(12)})
    fields = {n: 25 + i for i, n in enumerate(FIELDS)}
    fields.update({n: fields[v] for n, v in ALIASES.items()})

    def expand(bank, name, lines):
        result = []

        def go(target):
            return ['jmp ' + target] if banks[target] in (0, bank) else [f'ldi c, {banks[target]}', f'ldi d, {target}', 'jmp set_bank']

        for i, line in enumerate(lines):
            p = line.split()
            if p[0] == 'GO':
                result += go(p[1])
            elif p[0] == 'IF':
                condition, target = p[1:]
                if banks[target] in (0, bank):
                    result += ['j' + condition + ' ' + target]
                else:
                    inverse = dict(z='nz', nz='z', c='nc', nc='c', s='ns', ns='s')[condition]
                    tag = f'bridge_{name}_{i}'
                    result += ['j' + inverse + ' ' + tag] + go(target) + [tag + ':']
            elif p[0] == 'CALL':
                slot, target = p[1:]
                resume = f'resume_{name}_{i}'
                result += [f'ldi c, {bank}', f'st c, ret{slot}_bank', f'ldi d, {resume}', f'st d, ret{slot}_addr'] + go(target) + [resume + ':']
            elif p[0] == 'RETURN':
                result += [f'ld c, ret{p[1]}_bank', f'ld d, ret{p[1]}_addr', 'jmp set_bank']
            elif p[0] in ('READ', 'WRITE', 'READ_REG', 'WRITE_REG'):
                resume = f'io_{name}_{i}'
                result += [f'ldi d, {bank}', 'st d, io_ret_bank']
                if p[0] in ('READ', 'WRITE'):
                    target, address = p[1:]
                    result += [f'{"ldi" if target in constants else "ld"} c, {target}', f'{"ldi" if address in constants else "ld"} b, {address}']
                result += [f'ldi d, {resume}', 'jmp ' + ('write_byte' if p[0].startswith('WRITE') else 'read_byte'), resume + ':']
            else:
                result.append(line)
        return result

    source = ['; 3DEditor: 32 KB Computer v2. Generated by build.py.']
    source += [f'{name} equ {value}' for name, value in {**fields, **constants}.items() if 0 <= value <= 255]
    source += ['start: ldi c, APP_BANK', 'st c, 63', 'jmp main',
               'set_bank: st c, 63', 'jmp d',
               'read_byte: st c, 63', 'ld a, b', 'ld c, io_ret_bank', 'st c, 63', 'jmp d',
               'write_byte: st c, 63', 'st a, b', 'ld c, io_ret_bank', 'st c, 63', 'jmp d',
               'globals db ' + ','.join(['0'] * 37), 'ports db 0,0', 'screen db ' + ','.join(['0'] * 64)]
    layout = {}
    for bank, entries in bybank.items():
        used = 0
        source += ['', f'; Native bank {bank}']
        for name, lines, comment in entries:
            expanded = expand(bank, name, lines)
            layout[name] = dict(bank=bank, address=128 + used, physical=bank * 128 + used)
            source += ['; ' + comment]
            if expanded[0].startswith('db '):
                source += [name + ' ' + expanded[0]]
            else:
                source += [name + ':']
                for line in expanded:
                    if line.endswith(':'):
                        layout[line[:-1]] = dict(bank=bank, address=128 + used, physical=bank * 128 + used)
                    source.append(line)
                    used += ins_size(line)
                continue
            used += sum(ins_size(line) for line in expanded)
        assert used <= 128, (bank, used)
        source += [f'padding{bank} db ' + ','.join(['0'] * (128 - used))] if used < 128 else []
    dispatch = b''.join(bytes([layout['op_' + name.lower()]['bank'], layout['op_' + name.lower()]['address']]) for name in OPS)
    data[:len(dispatch)] = dispatch
    for offset in range(0, len(data), 128):
        source += [f'data_{native_end + offset} db ' + ','.join(str(v) for v in data[offset:offset + 128])]
    (ROOT / '3deditor.asm').write_text('\n'.join(source) + '\n', encoding='utf-8')
    metadata = dict(image_bytes=image_bytes, limit=32768, bytecode_bytes=len(program),
                    native_bytes=native_end, constants=constants, variables=compiler.variables,
                    common=fields, blocks=layout, bytecode_labels={n: constants['PROGRAM'] + a for n, a in compiler.labels.items()},
                    library_source_sha256=hashlib.sha256((REPO / 'graphics3d/src/engine.py').read_bytes()).hexdigest(),
                    max_vertices=32, max_edges=64, max_faces=32, coordinate_fraction_bits=4,
                    coordinate_limit=11, frame_buffer=64, frame_buffer_bytes=64,
                    blink_half_period_polls=131072)
    (ROOT / 'layout.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: metadata[k] for k in ['image_bytes', 'bytecode_bytes', 'native_bytes']}))
    return metadata


if __name__ == '__main__':
    build()
