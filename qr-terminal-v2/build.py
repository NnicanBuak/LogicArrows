"""Link QR Terminal v2 into one banked Computer v2 program (maximum 32 KB)."""
import hashlib
import json
import subprocess
from pathlib import Path

from compiler import Compiler, OPS
from runtime import blocks as word_blocks
from native import blocks as qr_blocks
from parameters import ALPHABET, ECC_DEGREES, divisor, field_tables, profiles

ROOT = Path(__file__).resolve().parent
FIELDS = ('ret0_bank ret0_addr ret1_bank ret1_addr ret2_bank ret2_addr ret3_bank ret3_addr '
          'io_ret_bank PC_BANK PC_ADDR SP RSP U0 U1 V0 V1 W0 W1 M0 M1 opcode roll '
          'x0 y0 x1 y1 dx dy sx sy t0 t1 spare0 spare1').split()
QR_FIELDS = ('qptr0 qptr1 qpack qpackn qcount qword0 qword1 qskip qvalue qleft0 qleft1 '
             'qout0 qout1 qcoef0 qcoef1 qdegree qfactor qindex gf_b gf_log qx qy qsize '
             'qright qbit qup qcolumns qbyte qrowbase qextent qwidth qphysicalx').split()

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



def packed(raw):
    """Pack native blocks into 128-byte banks while preserving local branches."""
    units = [[entry] for entry in raw]

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
    raw = [(n, [s.strip() for s in lines if s.strip()], c) for n, lines, c in word_blocks() + qr_blocks()]
    assert set('op_' + n.lower() for n in OPS) <= {n for n, _, _ in raw}
    bybank, banks = packed(raw)
    native_end = (max(bybank) + 1) * 128
    data = bytearray()
    constants = {}

    def reserve(name, length, content=b'', align=False):
        if align:
            data.extend(bytes((-(native_end + len(data))) % 128))
        constants[name] = native_end + len(data)
        if len(content) > length:
            raise ValueError((name, len(content), length))
        data.extend(content)
        data.extend(bytes(length - len(content)))
        return constants[name]

    reserve('DISPATCH', 128, align=True)
    reserve('STACK', 128, align=True)
    reserve('RETURN_STACK', 128, align=True)
    reserve('GLOBAL_WORDS', 1024, align=True)
    reserve('STRINGS', 1024, align=True)
    reserve('INPUT', 768, align=True)
    reserve('DATA', 384, align=True)
    reserve('ECC', 256, align=True)
    reserve('STREAM', 384, align=True)
    reserve('BLOCK_INFO', 128, align=True)
    reserve('MATRIX', 4096, align=True)
    logarithms, exponents = field_tables()
    reserve('LOG', 256, logarithms, align=True)
    reserve('EXP', 512, exponents, align=True)
    alphabet_map = bytearray([255] * 256)
    for i, code in enumerate(ALPHABET):
        alphabet_map[code] = i
    reserve('ALPHABET_MAP', 256, alphabet_map, align=True)
    reserve('EC_LETTERS', 4, b'LMQH')
    divisors = {}
    for degree in sorted({v for row in ECC_DEGREES for v in row}):
        divisors[degree] = reserve('DIVISOR_' + str(degree), degree, divisor(degree))
    profile_data, records = profiles(divisors)
    reserve('PROFILES', len(profile_data), profile_data, align=True)
    reserve('PROGRAM', 0, align=True)
    compiler = Compiler((ROOT / 'program.py').read_text(encoding='utf-8'), constants,
                        constants['GLOBAL_WORDS'], constants['STRINGS'])
    program = compiler.compile(constants['PROGRAM'])
    if len(compiler.strings) > 1024:
        raise ValueError('String memory exceeded')
    offset = constants['STRINGS'] - native_end
    data[offset:offset + len(compiler.strings)] = compiler.strings
    data.extend(program)
    image_bytes = native_end + len(data)
    if image_bytes > 32768:
        raise ValueError(('32 KB exceeded', image_bytes))
    constants.update({name + '_BANK': value // 128 for name, value in list(constants.items())
                      if value % 128 == 0})
    for name in ('DATA', 'STREAM'):
        constants[name + '_LO'] = constants[name] & 255
        constants[name + '_HI'] = constants[name] >> 8
    constants.update(APP_BANK=banks['main'], RS_REGISTER=96)
    fields = {name: 25 + i for i, name in enumerate(FIELDS)}
    fields.update({name: 64 + i for i, name in enumerate(QR_FIELDS)})
    fields['qphysicaly'] = fields['qout0']
    fields['qbank'] = fields['qword0']
    assert len(FIELDS) == 35 and len(QR_FIELDS) == 32

    def expand(bank, name, lines):
        result = []

        def go(target):
            return ['jmp ' + target] if banks[target] in (0, bank) else [
                f'ldi c, {banks[target]}', f'ldi d, {target}', 'jmp set_bank']

        for i, line in enumerate(lines):
            p = line.split()
            if p[0] == 'GO':
                result += go(p[1])
            elif p[0] == 'IF':
                condition, target = p[1:]
                if banks[target] in (0, bank):
                    result.append('j' + condition + ' ' + target)
                else:
                    inverse = dict(z='nz', nz='z', c='nc', nc='c', s='ns', ns='s')[condition]
                    tag = f'bridge_{name}_{i}'
                    result += ['j' + inverse + ' ' + tag] + go(target) + [tag + ':']
            elif p[0] == 'CALL':
                slot, target = p[1:]
                resume = f'resume_{name}_{i}'
                result += [f'ldi c, {bank}', f'st c, ret{slot}_bank', f'ldi d, {resume}',
                           f'st d, ret{slot}_addr'] + go(target) + [resume + ':']
            elif p[0] == 'RETURN':
                result += [f'ld c, ret{p[1]}_bank', f'ld d, ret{p[1]}_addr', 'jmp set_bank']
            elif p[0] in ('READ', 'WRITE', 'READ_REG', 'WRITE_REG'):
                resume = f'io_{name}_{i}'
                result += [f'ldi d, {bank}', 'st d, io_ret_bank']
                if p[0] in ('READ', 'WRITE'):
                    target, address = p[1:]
                    result += [f'ldi c, {target}', f'ldi b, {address}']
                result += [f'ldi d, {resume}', 'jmp ' + ('write_byte' if p[0].startswith('WRITE')
                                                        else 'read_byte'), resume + ':']
            else:
                result.append(line)
        return result

    source = ['; QR Terminal v2 — Computer v2, 32 KB. Generated by build.py.',
              '; CPU computes payload, Reed–Solomon, interleaving, matrix and terminal raster.']
    source += [f'{name} equ {value}' for name, value in {**fields, **constants}.items() if 0 <= value <= 255]
    source += ['start: ldi c, APP_BANK', 'st c, 63', 'jmp main',
               'set_bank: st c, 63', 'jmp d',
               'read_byte: st c, 63', 'ld a, b', 'ld c, io_ret_bank', 'st c, 63', 'jmp d',
               'write_byte: st c, 63', 'st a, b', 'ld c, io_ret_bank', 'st c, 63', 'jmp d',
               'word_workspace db ' + ','.join(['0'] * 35), 'ports db 0,0,1,0',
               'qr_workspace db ' + ','.join(['0'] * 32),
               'rs_register db ' + ','.join(['0'] * 32)]
    layout = {}
    for bank, entries in bybank.items():
        used = 0
        source += ['', f'; Native bank {bank}']
        for name, lines, comment in entries:
            expanded = expand(bank, name, lines)
            layout[name] = dict(bank=bank, address=128 + used, physical=bank * 128 + used)
            source += ['; ' + comment, name + ':']
            for line in expanded:
                if line.endswith(':'):
                    layout[line[:-1]] = dict(bank=bank, address=128 + used, physical=bank * 128 + used)
                source.append(line)
                used += ins_size(line)
        assert used <= 128, (bank, used)
        if used < 128:
            source.append(f'padding{bank} db ' + ','.join(['0'] * (128 - used)))
    dispatch = b''.join(bytes([layout['op_' + name.lower()]['bank'],
                              layout['op_' + name.lower()]['address']]) for name in OPS)
    data[:len(dispatch)] = dispatch
    for offset in range(0, len(data), 128):
        source.append(f'data_{native_end + offset} db ' + ','.join(str(v) for v in data[offset:offset + 128]))
    (ROOT / 'qr_terminal_v2.asm').write_text('\n'.join(source) + '\n', encoding='utf-8')
    metadata = dict(image_bytes=image_bytes, limit=32768, bytecode_bytes=len(program),
                    native_bytes=native_end, constants=constants, variables=compiler.variables,
                    common=fields, blocks=layout, capacities=records,
                    bytecode_labels={name: constants['PROGRAM'] + offset for name, offset in compiler.labels.items()},
                    source_sha256=hashlib.sha256((ROOT / 'program.py').read_bytes()).hexdigest())
    (ROOT / 'layout.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: metadata[k] for k in ['image_bytes', 'bytecode_bytes', 'native_bytes']}))
    subprocess.run(['node', str(ROOT / 'tools/compile.mjs'), str(ROOT / 'qr_terminal_v2.asm')], check=True)
    return metadata


if __name__ == '__main__':
    build()

