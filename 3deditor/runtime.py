"""Native Computer v2 runtime and unmodified 3DGraphics API dependencies."""
from compiler import OPS


def blocks():
    result = []

    def b(name, code):
        result.append((name, code.strip().splitlines(), '3DEditor native runtime'))

    def go():
        return 'GO vm_dispatch'

    def push():
        return 'CALL 2 vm_push\n' + go()

    def zero():
        return 'clr a\nst a, U1'

    def neg(lo, hi):
        return f'ld a, {lo}\nneg a\nst a, {lo}\nld a, {hi}\nldi b, 0\nsbb b, a\nst b, {hi}'

    b('main', '''
ldi a, PROGRAM_BANK
st a, PC_BANK
ldi a, 128
st a, PC_ADDR
clr a
st a, SP
st a, RSP
st a, 62
ld a, 62
GO vm_dispatch
''')
    b('vm_fetch', '''
ld c, PC_BANK
ld b, PC_ADDR
READ_REG
st a, t1
ld b, PC_ADDR
inc b
st b, PC_ADDR
IF nz vm_fetch_done
ldi b, 128
st b, PC_ADDR
ld b, PC_BANK
inc b
st b, PC_BANK
vm_fetch_done:
ld a, t1
RETURN 3
''')
    b('vm_immediate', '''
CALL 3 vm_fetch
st a, M0
CALL 3 vm_fetch
st a, M1
RETURN 1
''')
    b('vm_address', '''
ld a, M1
shl a
mov c, a
ld b, M0
shl b
IF nc vm_address_low
inc c
vm_address_low:
ld b, M0
test c
IF nz vm_address_banked
test b
IF ns vm_address_done
vm_address_banked:
ldi a, 128
or b, a
vm_address_done:
RETURN 3
''')
    # Memory helpers inline the calculation to leave slot 3 free for callers.
    address = '''
ld a, M1
shl a
mov c, a
ld b, M0
shl b
IF nc {name}_low
inc c
{name}_low:
ld b, M0
test c
IF nz {name}_banked
test b
IF ns {name}_done
{name}_banked:
ldi a, 128
or b, a
{name}_done:
'''
    b('vm_read', address.format(name='vm_read') + 'READ_REG\nRETURN 3')
    b('vm_write', 'st a, t0\n' + address.format(name='vm_write') + 'ld a, t0\nWRITE_REG\nRETURN 3')
    b('vm_increment_address', '''
ld a, M0
inc a
st a, M0
IF nz vm_increment_done
ld a, M1
inc a
st a, M1
vm_increment_done:
RETURN 3
''')
    b('vm_pop', '''
ld b, SP
dec b
dec b
st b, SP
ldi a, 128
add b, a
ld c, STACK_BANK_CONST
READ_REG
st a, U0
ld b, SP
ldi a, 129
add b, a
ld c, STACK_BANK_CONST
READ_REG
st a, U1
RETURN 2
''')
    b('vm_push', '''
ld b, SP
ldi a, 128
add b, a
ld c, STACK_BANK_CONST
ld a, U0
WRITE_REG
ld b, SP
ldi a, 129
add b, a
ld c, STACK_BANK_CONST
ld a, U1
WRITE_REG
ld a, SP
inc a
inc a
st a, SP
RETURN 2
''')
    # Bank numbers are constants; use ldi in the stack helpers.
    for i, (name, lines, comment) in enumerate(result):
        result[i] = name, [line.replace('ld c, STACK_BANK_CONST', 'ldi c, STACK_BANK') for line in lines], comment
    b('vm_dispatch', '''
CALL 3 vm_fetch
dec a
shl a
ldi b, 128
add b, a
st b, opcode
ldi c, DISPATCH_BANK
READ_REG
st a, x0
ld b, opcode
inc b
ldi c, DISPATCH_BANK
READ_REG
mov d, a
ld c, x0
GO set_bank
''')
    b('vm_operands', '''
CALL 2 vm_pop
ld a, U0
st a, V0
ld a, U1
st a, V1
CALL 2 vm_pop
RETURN 1
''')
    b('op_const', 'CALL 1 vm_immediate\nld a, M0\nst a, U0\nld a, M1\nst a, U1\n' + push())
    b('op_get', 'CALL 1 vm_immediate\nGO vm_load_word')
    b('op_load16', 'CALL 2 vm_pop\nld a, U0\nst a, M0\nld a, U1\nst a, M1\nGO vm_load_word')
    b('vm_load_word', '''
CALL 3 vm_read
st a, U0
CALL 3 vm_increment_address
CALL 3 vm_read
st a, U1
''' + push())
    for name, signed in [('load8', False), ('loads', True)]:
        b('op_' + name, '''
CALL 2 vm_pop
ld a, U0
st a, M0
ld a, U1
st a, M1
CALL 3 vm_read
st a, U0
clr b
''' + (f'test a\nIF ns {name}_positive\ndec b\n{name}_positive:\n' if signed else '') + 'st b, U1\n' + push())
    b('op_set', 'CALL 1 vm_immediate\nCALL 2 vm_pop\nGO vm_store_word')
    for name, size in [('store8', 1), ('store16', 2)]:
        b('op_' + name, '''
CALL 1 vm_operands
ld a, U0
st a, M0
ld a, U1
st a, M1
ld a, V0
st a, U0
ld a, V1
st a, U1
''' + ('ld a, U0\nCALL 3 vm_write\n' + go() if size == 1 else 'GO vm_store_word'))
    b('vm_store_word', 'ld a, U0\nCALL 3 vm_write\nCALL 3 vm_increment_address\nld a, U1\nCALL 3 vm_write\n' + go())
    for name, low, high in [('add', 'add', 'adc'), ('sub', 'sub', 'sbb'), ('and', 'and', 'and'), ('or', 'or', 'or'), ('xor', 'xor', 'xor')]:
        b('op_' + name, f'CALL 1 vm_operands\nld a, U0\nld b, V0\n{low} a, b\nst a, U0\nld a, U1\nld b, V1\n{high} a, b\nst a, U1\n' + push())
    b('op_neg', 'CALL 2 vm_pop\n' + neg('U0', 'U1') + '\n' + push())
    b('op_not', '''
CALL 2 vm_pop
ld a, U0
ld b, U1
or a, b
ldi a, 0
IF nz not_done
inc a
not_done:
st a, U0
''' + zero() + '\n' + push())
    b('op_eq', '''
CALL 1 vm_operands
ld a, U0
ld b, V0
xor a, b
st a, W0
ld a, U1
ld b, V1
xor a, b
ld b, W0
or a, b
ldi a, 0
IF nz eq_done
inc a
eq_done:
st a, U0
''' + zero() + '\n' + push())
    b('op_lt', '''
CALL 1 vm_operands
ld a, U1
ld b, V1
xor a, b
IF s lt_opposite
ld a, U1
sub a, b
IF c lt_yes
IF nz lt_no
ld a, U0
ld b, V0
sub a, b
IF c lt_yes
GO lt_no
lt_opposite:
ld a, U1
test a
IF s lt_yes
lt_no:
clr a
GO lt_done
lt_yes:
ldi a, 1
lt_done:
st a, U0
''' + zero() + '\n' + push())
    for name, low, high in [('shl', 'shl', 'rcl'), ('shr', 'rcr', 'sar')]:
        shift = f'ld a, U0\n{low} a\nst a, U0\nld a, U1\n{high} a\nst a, U1' if name == 'shl' else f'ld a, U1\n{high} a\nst a, U1\nld a, U0\n{low} a\nst a, U0'
        b('op_' + name, 'CALL 1 vm_operands\nld a, V0\ntest a\nIF z ' + name + '_done\n' + name + '_loop:\n' + shift + f'\nld a, V0\ndec a\nst a, V0\nIF nz {name}_loop\n{name}_done:\n' + push())
    b('op_mul', '''
CALL 1 vm_operands
clr a
st a, W0
st a, W1
ldi a, 16
st a, roll
mul16_loop:
ld a, V1
shr a
st a, V1
ld a, V0
rcr a
st a, V0
IF nc mul16_skip
ld a, W0
ld b, U0
add a, b
st a, W0
ld a, W1
ld b, U1
adc a, b
st a, W1
mul16_skip:
ld a, U0
shl a
st a, U0
ld a, U1
rcl a
st a, U1
ld a, roll
dec a
st a, roll
IF nz mul16_loop
ld a, W0
st a, U0
ld a, W1
st a, U1
''' + push())
    b('op_div', 'clr a\nst a, opcode\nGO vm_divide')
    b('op_mod', 'ldi a, 1\nst a, opcode\nGO vm_divide')
    b('vm_divide', '''
CALL 1 vm_operands
ld a, U1
st a, sx
ld b, V1
xor a, b
st a, sy
ld a, U1
test a
IF ns div_u_positive
''' + neg('U0', 'U1') + '''
div_u_positive:
ld a, V1
test a
IF ns div_v_positive
''' + neg('V0', 'V1') + '''
div_v_positive:
clr a
st a, W0
st a, W1
ldi a, 16
st a, roll
GO vm_division_loop
''')
    b('vm_division_loop', '''
ld a, U0
shl a
st a, U0
ld a, U1
rcl a
st a, U1
ld a, W0
rcl a
st a, W0
ld a, W1
rcl a
st a, W1
ld b, V1
sub a, b
IF c div_skip
IF nz div_subtract
ld a, W0
ld b, V0
sub a, b
IF c div_skip
div_subtract:
ld a, W0
ld b, V0
sub a, b
st a, W0
ld a, W1
ld b, V1
sbb a, b
st a, W1
ld a, U0
inc a
st a, U0
div_skip:
ld a, roll
dec a
st a, roll
IF nz vm_division_loop
GO vm_division_done
''')
    b('vm_division_done', '''
ld a, opcode
test a
IF z div_quotient
ld a, W0
st a, U0
ld a, W1
st a, U1
ld a, sx
GO div_sign
div_quotient:
ld a, sy
div_sign:
test a
IF ns div_finish
''' + neg('U0', 'U1') + '\ndiv_finish:\n' + push())
    b('op_drop', 'CALL 2 vm_pop\n' + go())
    b('op_dup', 'CALL 2 vm_pop\nCALL 2 vm_push\n' + push())
    b('op_jmp', 'CALL 1 vm_immediate\nGO vm_jump')
    b('op_jz', '''
CALL 1 vm_immediate
CALL 2 vm_pop
ld a, U0
ld b, U1
or a, b
IF z vm_jump
''' + go())
    b('vm_jump', '''
ld a, M1
shl a
st a, PC_BANK
ld a, M0
shl a
IF nc jump_low
ld a, PC_BANK
inc a
st a, PC_BANK
jump_low:
ld a, M0
ldi b, 128
or a, b
st a, PC_ADDR
''' + go())
    b('op_call', '''
CALL 1 vm_immediate
ld b, RSP
ldi a, 128
add b, a
ldi c, RETURN_STACK_BANK
ld a, PC_BANK
WRITE_REG
ld b, RSP
ldi a, 129
add b, a
ldi c, RETURN_STACK_BANK
ld a, PC_ADDR
WRITE_REG
ld a, RSP
inc a
inc a
st a, RSP
GO vm_jump
''')
    b('op_ret', '''
ld b, RSP
dec b
dec b
st b, RSP
ldi a, 128
add b, a
ldi c, RETURN_STACK_BANK
READ_REG
st a, PC_BANK
ld b, RSP
ldi a, 129
add b, a
ldi c, RETURN_STACK_BANK
READ_REG
st a, PC_ADDR
''' + go())
    b('op_key', '''
READ CONTEXT_BANK CTX_BLINK_ACTIVE
st a, dx
clr a
st a, ret0_bank
st a, ret0_addr
ldi a, 2
st a, dy
vm_key_wait:
ld a, 62
test a
IF nz vm_key_ready
ld a, dx
test a
IF z vm_key_wait
ld a, ret0_addr
inc a
st a, ret0_addr
IF nz vm_key_wait
ld a, ret0_bank
inc a
st a, ret0_bank
IF nz vm_key_wait
ld a, dy
dec a
st a, dy
IF nz vm_key_wait
ldi a, 2
st a, dy
CALL 1 vm_blink
GO vm_key_wait
vm_key_ready:
st a, U0
''' + zero() + '\n' + push())
    # Slot 0 is free while KEY waits: its two return bytes count idle polls.
    # Both frames are cached by render(). No API calls or device-mode writes
    # are needed here, so a key arriving during the copy remains in port 62.
    # Clear blue before adding red, and red before adding blue. A selected
    # cursor must not transiently turn purple while the LCD planes change.
    b('vm_blink', '''
READ CONTEXT_BANK CTX_BLINK_PHASE
ldi b, 1
xor a, b
st a, sy
WRITE CONTEXT_BANK CTX_BLINK_PHASE
ldi a, 160
ldi b, 96
ld c, sy
test c
IF nz vm_blink_source
ldi a, 192
ldi b, 64
vm_blink_source:
st a, x0
st b, y0
ldi a, 64
st a, x1
vm_blink_loop:
ldi c, BLINK_FRAMES_BANK
ld b, x0
READ_REG
ld b, y0
st a, b
ld a, x0
inc a
st a, x0
ld a, y0
inc a
IF ns vm_blink_dest
ldi a, 128
st a, x0
ldi a, 64
vm_blink_dest:
st a, y0
ld a, x1
dec a
st a, x1
IF nz vm_blink_loop
RETURN 1
''')
    b('op_blink', '''
CALL 2 vm_pop
ld a, U0
WRITE CONTEXT_BANK CTX_BLINK_ACTIVE
ldi a, 1
WRITE CONTEXT_BANK CTX_BLINK_PHASE
''' + go())
    b('op_putc', '''
CALL 2 vm_pop
ldi a, 49
st a, 62
ld a, 62
ld a, U0
st a, 60
ldi a, 48
st a, 62
ld a, 62
''' + go())
    b('op_text', '''
CALL 1 vm_immediate
ldi a, 49
st a, 62
ld a, 62
text_loop:
CALL 3 vm_read
test a
IF z text_done
st a, 60
CALL 3 vm_increment_address
GO text_loop
text_done:
ldi a, 48
st a, 62
ld a, 62
''' + go())
    b('op_copy', '''
CALL 2 vm_pop
ld a, U0
st a, dx
ld a, U1
st a, dy
CALL 2 vm_pop
ld a, U0
st a, x0
ld a, U1
st a, y0
CALL 2 vm_pop
ld a, U0
st a, x1
ld a, U1
st a, y1
GO vm_copy_loop
''')
    b('vm_copy_loop', '''
ld a, dx
ld b, dy
or a, b
IF z vm_dispatch
ld a, x0
st a, M0
ld a, y0
st a, M1
CALL 3 vm_read
st a, sx
CALL 3 vm_increment_address
ld a, M0
st a, x0
ld a, M1
st a, y0
ld a, x1
st a, M0
ld a, y1
st a, M1
ld a, sx
CALL 3 vm_write
CALL 3 vm_increment_address
ld a, M0
st a, x1
ld a, M1
st a, y1
ld a, dx
ldi b, 1
sub a, b
st a, dx
ld a, dy
ldi b, 0
sbb a, b
st a, dy
GO vm_copy_loop
''')
    # API overwrites its COMMON scratch variables. Preserve the VM's PC/stacks.
    for name, action in [('save', 'WRITE'), ('restore', 'READ')]:
        code = []
        for offset, field in enumerate(['PC_BANK', 'PC_ADDR', 'SP', 'RSP']):
            code += [f'ld a, {field}', f'WRITE CONTEXT_BANK CTX{offset}'] if action == 'WRITE' else [f'READ CONTEXT_BANK CTX{offset}', f'st a, {field}']
        b('vm_' + name, '\n'.join(code) + '\nRETURN 3')
    for name, api in [('begin', 'gfx_begin'), ('present', 'gfx_present')]:
        b('op_' + name, f'CALL 3 vm_save\nCALL 0 {api}\nCALL 3 vm_restore\nld a, 62\n' + go())
    # Pop via U into scratch that vm_pop itself does not modify. Set wx/wy last.
    for name, fields, api, slot in [('pixel', ['color', 'y0', 'x0'], 'gfx_pixel', 2),
                                   ('line', ['color', 'y1', 'x1', 'y0', 'x0'], 'gfx_line', 1),
                                   ('triangle', ['color', 'dy', 'dx', 'y1', 'x1', 'y0', 'x0'], 'gfx_triangle', 1)]:
        code = []
        for field in fields:
            code += ['CALL 2 vm_pop', 'ld a, U0', f'st a, {field}']
        if name == 'pixel':
            code += ['ld a, x0', 'st a, wx', 'ld a, y0', 'st a, wy']
        code += ['CALL 3 vm_save', f'CALL {slot} {api}', 'CALL 3 vm_restore', go()]
        # Larger triangle wrapper needs two banks.
        if name == 'triangle':
            b('op_triangle', '\n'.join(code[:15]) + '\nGO vm_triangle_args')
            b('vm_triangle_args', '\n'.join(code[15:]))
        else:
            b('op_' + name, '\n'.join(code))
    b('op_project', '''
CALL 2 vm_pop
ld a, U0
st a, pitch
CALL 2 vm_pop
ld a, U0
st a, yaw
CALL 2 vm_pop
ld a, U0
st a, dx
CALL 2 vm_pop
ld a, U0
st a, y0
CALL 2 vm_pop
ld a, U0
st a, x0
GO vm_project_args
''')
    b('vm_project_args', '''
ld a, x0
st a, wx
ld a, y0
st a, wy
ld a, dx
st a, wz
clr a
st a, roll
CALL 3 vm_save
CALL 1 gfx_project_vertex
ld a, wx
WRITE CONTEXT_BANK CTX4
ld a, wy
WRITE CONTEXT_BANK CTX5
ld a, wz
WRITE CONTEXT_BANK CTX6
ld a, depth
WRITE CONTEXT_BANK CTX7
CALL 3 vm_restore
''' + go())
    b('gfx_begin', '''
clr a
st a, 62
ldi b, 64
ldi c, 64
editor_begin_loop:
st a, b
inc b
dec c
IF nz editor_begin_loop
RETURN 0
''')
    b('gfx_present', '''
ldi a, 48
st a, 62
ldi b, 64
ldi d, 64
editor_present_loop:
ld a, b
st a, b
inc b
dec d
IF nz editor_present_loop
RETURN 0
''')
    assert set('op_' + n.lower() for n in OPS) <= {entry[0] for entry in result}
    return result
