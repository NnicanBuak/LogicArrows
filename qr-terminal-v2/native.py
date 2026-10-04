"""Native QR hot loops: bit packing, Reed–Solomon, placement and terminal output.

All of these blocks are linked as Computer v2 instructions. No host-side QR
generation is used by the program.
"""


def blocks():
    result = []

    def b(name, code):
        result.append((name, code.strip().splitlines(), 'QR Terminal v2 native QR engine'))

    dispatch = 'GO vm_dispatch'

    b('op_fill', '''
CALL 2 vm_pop
ld a, U0
st a, qvalue
CALL 2 vm_pop
ld a, U0
st a, qleft0
ld a, U1
st a, qleft1
CALL 2 vm_pop
ld a, U0
st a, M0
ld a, U1
st a, M1
fill_loop:
ld a, qleft0
ld b, qleft1
or a, b
IF z vm_dispatch
ld a, qvalue
CALL 3 vm_write
CALL 3 vm_increment_address
ld a, qleft0
ldi b, 1
sub a, b
st a, qleft0
ld a, qleft1
ldi b, 0
sbb a, b
st a, qleft1
GO fill_loop
''')

    b('op_beginbits', '''
ldi a, DATA_LO
st a, qptr0
ldi a, DATA_HI
st a, qptr1
clr a
st a, qpack
st a, qpackn
''' + dispatch)

    b('op_bits', '''
CALL 2 vm_pop
ld a, U0
st a, qcount
CALL 2 vm_pop
ld a, U0
st a, qword0
ld a, U1
st a, qword1
ldi a, 16
ld b, qcount
sub a, b
st a, qskip
IF z bits_emit
bits_shift:
ld a, qword0
shl a
st a, qword0
ld a, qword1
rcl a
st a, qword1
ld a, qskip
dec a
st a, qskip
IF nz bits_shift
GO bits_emit
''')
    b('bits_emit', '''
ld a, qcount
test a
IF z vm_dispatch
ld a, qword0
shl a
st a, qword0
ld a, qword1
rcl a
st a, qword1
ld a, qpack
rcl a
st a, qpack
ld a, qpackn
inc a
st a, qpackn
ldi b, 8
xor b, a
IF nz bits_next
ld a, qptr0
st a, M0
ld a, qptr1
st a, M1
ld a, qpack
CALL 3 vm_write
CALL 3 vm_increment_address
ld a, M0
st a, qptr0
ld a, M1
st a, qptr1
clr a
st a, qpack
st a, qpackn
bits_next:
ld a, qcount
dec a
st a, qcount
GO bits_emit
''')

    # RS(data pointer, data length, ECC degree, divisor pointer, output pointer).
    b('op_rsblock', '''
CALL 2 vm_pop
ld a, U0
st a, qout0
ld a, U1
st a, qout1
CALL 2 vm_pop
ld a, U0
st a, qcoef0
ld a, U1
st a, qcoef1
CALL 2 vm_pop
ld a, U0
st a, qdegree
CALL 2 vm_pop
ld a, U0
st a, qleft0
CALL 2 vm_pop
ld a, U0
st a, qptr0
ld a, U1
st a, qptr1
clr a
ldi b, RS_REGISTER
ldi c, 31
rs_clear:
st a, b
inc b
dec c
IF nz rs_clear
GO rs_outer
''')
    b('rs_outer', '''
ld a, qptr0
st a, M0
ld a, qptr1
st a, M1
CALL 3 vm_read
ld b, RS_REGISTER
xor a, b
st a, qfactor
CALL 3 vm_increment_address
ld a, M0
st a, qptr0
ld a, M1
st a, qptr1
ld a, qcoef0
st a, M0
ld a, qcoef1
st a, M1
clr a
st a, qindex
GO rs_inner
''')
    b('rs_inner', '''
CALL 3 vm_read
ld b, qfactor
CALL 1 gf_multiply
ld b, qindex
ldi c, RS_REGISTER+1
add b, c
ld c, b
xor a, c
dec b
st a, b
CALL 3 vm_increment_address
ld a, qindex
inc a
st a, qindex
ld b, qdegree
xor b, a
IF nz rs_inner
ld a, qleft0
dec a
st a, qleft0
IF nz rs_outer
ld a, qout0
st a, M0
ld a, qout1
st a, M1
clr a
st a, qindex
GO rs_output
''')
    b('rs_output', '''
ld b, qindex
ldi c, RS_REGISTER
add b, c
ld a, b
CALL 3 vm_write
CALL 3 vm_increment_address
ld a, qindex
inc a
st a, qindex
ld b, qdegree
xor b, a
IF nz rs_output
''' + dispatch)

    # Preserve M0/M1 so the caller's divisor pointer survives multiplication.
    b('gf_multiply', '''
test a
IF z gf_zero
test b
IF z gf_zero
st b, gf_b
mov b, a
shl a
ldi c, LOG_BANK
IF nc gf_first_low
inc c
gf_first_low:
ldi a, 128
or b, a
READ_REG
st a, gf_log
ld b, gf_b
mov a, b
shl a
ldi c, LOG_BANK
IF nc gf_second_low
inc c
gf_second_low:
ldi a, 128
or b, a
READ_REG
ld b, gf_log
add a, b
ldi c, EXP_BANK
IF nc gf_exp_low
inc c
inc c
gf_exp_low:
mov b, a
shl a
IF nc gf_exp_bank
inc c
gf_exp_bank:
ldi a, 128
or b, a
READ_REG
RETURN 1
gf_zero:
clr a
RETURN 1
''')

    # Matrix uses one byte per module, 64-byte row pitch: bit 0 is color;
    # bit 1 marks a function module. The 4 KB region is bank-aligned.
    b('qr_address', '''
ld a, qy
shr a
ldi c, MATRIX_BANK
add c, a
ld a, qy
ldi b, 1
and a, b
shr a
ldi b, 128
IF nc qr_address_x
ldi b, 192
qr_address_x:
ld a, qx
add b, a
st c, qbank
RETURN 0
''')
    b('qr_get', 'CALL 0 qr_address\nld c, qbank\nREAD_REG\nRETURN 1')
    b('qr_set', 'st a, qvalue\nCALL 0 qr_address\nld c, qbank\nld a, qvalue\nWRITE_REG\nRETURN 1')
    b('op_plot', '''
CALL 2 vm_pop
ld a, U0
st a, qvalue
CALL 2 vm_pop
ld a, U0
st a, qy
CALL 2 vm_pop
ld a, U0
st a, qx
ld a, qvalue
CALL 1 qr_set
''' + dispatch)
    b('op_tile', '''
CALL 2 vm_pop
ld a, U0
st a, qy
CALL 2 vm_pop
ld a, U0
st a, qx
CALL 1 qr_get
st a, U0
clr a
st a, U1
CALL 2 vm_push
''' + dispatch)

    b('op_place', '''
CALL 2 vm_pop
ld a, U0
st a, qleft0
ld a, U1
st a, qleft1
CALL 2 vm_pop
ld a, U0
st a, qsize
dec a
st a, qright
ldi a, STREAM_LO
st a, qptr0
ldi a, STREAM_HI
st a, qptr1
ldi a, 128
st a, qbit
ldi a, 1
st a, qup
GO place_pair
''')
    b('place_pair', '''
ld a, qright
ldi b, 6
xor b, a
IF nz place_pair_ready
dec a
st a, qright
place_pair_ready:
ld a, qsize
dec a
ld b, qup
test b
IF nz place_row_start
clr a
place_row_start:
st a, qy
GO place_row
''')
    b('place_row', '''
ld a, qright
st a, qx
ldi a, 2
st a, qcolumns
GO place_module
''')
    b('place_module', '''
CALL 1 qr_get
ldi b, 2
and a, b
IF nz place_next
ld a, qleft0
ld b, qleft1
or a, b
IF z place_next
ld a, qbit
ldi b, 128
xor b, a
IF nz place_color
ld a, qptr0
st a, M0
ld a, qptr1
st a, M1
CALL 3 vm_read
st a, qbyte
CALL 3 vm_increment_address
ld a, M0
st a, qptr0
ld a, M1
st a, qptr1
place_color:
ld a, qbyte
ld b, qbit
and a, b
ldi a, 0
IF z place_write
inc a
place_write:
CALL 1 qr_set
ld a, qbit
shr a
st a, qbit
IF nz place_next
ldi a, 128
st a, qbit
ld a, qleft0
ldi b, 1
sub a, b
st a, qleft0
ld a, qleft1
ldi b, 0
sbb a, b
st a, qleft1
GO place_next
''')
    b('place_next', '''
ld a, qx
dec a
st a, qx
ld a, qcolumns
dec a
st a, qcolumns
IF nz place_module
ld a, qy
ld b, qup
test b
IF z place_down
test a
IF z place_end_pair
dec a
st a, qy
GO place_row
place_down:
inc a
st a, qy
ld b, qsize
xor b, a
IF nz place_row
GO place_end_pair
''')
    b('place_end_pair', '''
ld a, qup
ldi b, 1
xor a, b
st a, qup
ld a, qright
ldi b, 2
sub a, b
st a, qright
IF c vm_dispatch
IF z vm_dispatch
GO place_pair
''')

    # Fixed mask 0 is a valid QR mask. It is also used by the 1 KB version.
    b('op_mask', '''
CALL 2 vm_pop
ld a, U0
st a, qsize
clr a
st a, qy
mask_row:
clr a
st a, qx
mask_column:
ld a, qx
ld b, qy
add a, b
shr a
IF c mask_next
CALL 1 qr_get
ldi b, 2
and b, a
IF nz mask_next
ldi b, 1
xor a, b
CALL 1 qr_set
mask_next:
ld a, qx
inc a
st a, qx
ld b, qsize
xor b, a
IF nz mask_column
ld a, qy
inc a
st a, qy
ld b, qsize
xor b, a
IF nz mask_row
''' + dispatch)

    # Render 4-module quiet zone, then complete the final 6x8 glyphs with white.
    # No terminal scroll markers or separator strips enter the coordinate map.
    b('op_render', '''
CALL 2 vm_pop
ld a, U0
st a, qsize
ldi b, 8
add a, b
st a, qextent
clr a
render_width:
ldi b, 6
add a, b
ld b, qextent
sub b, a
IF c render_width_ready
IF z render_width_ready
GO render_width
render_width_ready:
st a, qwidth
clr a
st a, qrowbase
GO render_row
''')
    b('render_row', '''
clr a
st a, qphysicalx
GO render_column
''')
    b('render_column', '''
clr a
st a, qpack
ldi a, 1
st a, qbit
ld a, qrowbase
st a, qphysicaly
GO render_pixel
''')
    b('render_pixel', '''
ld a, qphysicalx
ldi b, 4
sub a, b
IF c render_blank
st a, qx
ld b, qsize
sub a, b
IF nc render_blank
ld a, qphysicaly
ldi b, 4
sub a, b
IF c render_blank
st a, qy
ld b, qsize
sub a, b
IF nc render_blank
CALL 1 qr_get
shr a
IF nc render_blank
ld a, qpack
ld b, qbit
or a, b
st a, qpack
render_blank:
ld a, qphysicaly
inc a
st a, qphysicaly
ld a, qbit
shl a
st a, qbit
IF nz render_pixel
GO render_emit
''')
    b('render_emit', '''
ld a, qpack
st a, 61
ld a, qphysicalx
inc a
st a, qphysicalx
ld b, qwidth
xor b, a
IF nz render_column
ldi a, 10
st a, 60
ld a, qrowbase
ldi b, 8
add a, b
st a, qrowbase
ld b, qextent
sub a, b
IF c render_row
''' + dispatch)
    return result
