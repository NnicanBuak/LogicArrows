; ##################################################################################################
; ##                 3DGraphics — API для Computer v2, профиль эмулятора 32 КБ                 ##
; ##################################################################################################
; Вершины преобразует CPU; LUT содержат только умножение и деление.
; Три цветных состояния и белый фон; CPU сортирует треугольники от дальних к ближним.
; Демо: вращение X/Y/Z, масштаб координат ×1…×2…×1 за 256 кадров.
; Модель: crystal; режим: wireframe. Образ превышает 1 КБ.

ret0_bank           equ 25
ret0_addr           equ 26
ret1_bank           equ 27
ret1_addr           equ 28
ret2_bank           equ 29
ret2_addr           equ 30
ret3_bank           equ 31
ret3_addr           equ 32
io_ret_bank         equ 33
ptr_bank            equ 34
ptr_addr            equ 35
vertex_count        equ 36
edge_count          equ 37
yaw                 equ 38
pitch               equ 39
roll                equ 40
out_bank            equ 41
out_addr            equ 42
wx                  equ 43
wy                  equ 44
wz                  equ 45
ru                  equ 46
rv                  equ 47
angle               equ 48
t0                  equ 49
t1                  equ 50
x0                  equ 51
y0                  equ 52
x1                  equ 53
y1                  equ 54
dx                  equ 55
dy                  equ 56
sx                  equ 57
sy                  equ 58
err                 equ 59
mask                equ 60
color               equ 61
signs               equ 60
mul_sign            equ 59
depth               equ 48
BUFFER_BASE         equ 65
VERTEX_BASE         equ 67
MODEL_BASE          equ 69
LUT_BASE            equ 70
PROJECTION_BASE     equ 102
CAMERA_DISTANCE     equ 32
MAX_VERTICES        equ 6
MAX_TRIANGLES       equ 0
STATE_BANK          equ 66
TRI_BUFFER_BASE     equ 68
STATE_PHASE         equ 128
STATE_SCALE         equ 129
STATE_TRI_TOTAL     equ 130
STATE_CACHE_BANK    equ 131
STATE_CACHE_ADDR    equ 132
STATE_BEST_BANK     equ 133
STATE_BEST_ADDR     equ 134
STATE_CULL          equ 135
TRI_STATE0          equ 228
TRI_STATE1          equ 229
TRI_STATE2          equ 230
TRI_STATE3          equ 231
TRI_STATE4          equ 232
TRI_STATE5          equ 233
TRI_STATE6          equ 234
TRI_STATE7          equ 235
TRI_STATE8          equ 236
TRI_STATE9          equ 237
TRI_STATE10         equ 238
TRI_STATE11         equ 239

;===================================================================================================
; Общая область памяти
;===================================================================================================
start:              ldi c, 1
                    st c, 0x3F
                    jmp main
set_bank:           st c, 0x3F
                    jmp d
read_byte:          st c, 0x3F
                    ld a, b
                    ld c, io_ret_bank
                    st c, 0x3F
                    jmp d
write_byte:         st c, 0x3F
                    st a, b
                    ld c, io_ret_bank
                    st c, 0x3F
                    jmp d
globals db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
ports db 0,0
screen db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #1
;===================================================================================================

; Демонстрация полного API: вращение всех осей и масштаб ×1…×2.
main:
                    ldi a, 48
                    st a, 0x3E
                    ldi c, 2
                    ldi d, frame_start
                    jmp set_bank
padding1 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #2
;===================================================================================================

; Все оси меняются постепенно: Y=n/4, X=n/2, Z=3n/4, по модулю 32.
frame_start:
                    ldi d, 2
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_PHASE
                    ldi d, io_frame_start_0
                    jmp read_byte
io_frame_start_0:
                    shr a
                    shr a
                    ldi b, 31
                    and a, b
                    st a, yaw
                    ldi d, 2
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_PHASE
                    ldi d, io_frame_start_6
                    jmp read_byte
io_frame_start_6:
                    shr a
                    ldi b, 31
                    and a, b
                    st a, pitch
                    ldi d, 2
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_PHASE
                    ldi d, io_frame_start_11
                    jmp read_byte
io_frame_start_11:
                    mov b, a
                    shl a
                    add a, b
                    shr a
                    shr a
                    ldi b, 31
                    and a, b
                    st a, roll
                    ldi c, 3
                    ldi d, frame_scale
                    jmp set_bank
padding2 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #3
;===================================================================================================

; Полный цикл ×2 → ×1 → ×2 за 256 кадров, как у демонстрации 1K.
frame_scale:
                    ldi d, 3
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_PHASE
                    ldi d, io_frame_scale_0
                    jmp read_byte
io_frame_scale_0:
                    ldi b, 128
                    sub a, b
                    jns scale_phase_positive
                    neg a
scale_phase_positive:
                    shr a
                    shr a
                    ldi b, 32
                    add a, b
                    ldi d, 3
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_SCALE
                    ldi d, io_frame_scale_10
                    jmp write_byte
io_frame_scale_10:
                    ldi c, 4
                    ldi d, frame_draw
                    jmp set_bank
padding3 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #4
;===================================================================================================

; Построить модель в скрытом кадре и вывести все 64 готовых байта.
frame_draw:
                    ldi c, 4
                    st c, ret0_bank
                    ldi d, resume_frame_draw_0
                    st d, ret0_addr
                    ldi c, 65
                    ldi d, gfx_begin
                    jmp set_bank
resume_frame_draw_0:
                    ldi a, MODEL_BASE
                    st a, ptr_bank
                    ldi a, 128
                    st a, ptr_addr
                    ldi c, 4
                    st c, ret0_bank
                    ldi d, resume_frame_draw_5
                    st d, ret0_addr
                    ldi c, 41
                    ldi d, gfx_draw_mesh
                    jmp set_bank
resume_frame_draw_5:
                    ldi c, 4
                    st c, ret0_bank
                    ldi d, resume_frame_draw_6
                    st d, ret0_addr
                    ldi c, 65
                    ldi d, gfx_present
                    jmp set_bank
resume_frame_draw_6:
                    ldi c, 5
                    ldi d, frame_advance
                    jmp set_bank
padding4 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #5
;===================================================================================================

; Следующая фаза 0…255; кадры 0 и 128 имеют одинаковый ракурс и вдвое разные XYZ.
frame_advance:
frame_complete:
                    ldi d, 5
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_PHASE
                    ldi d, io_frame_advance_1
                    jmp read_byte
io_frame_advance_1:
                    inc a
                    ldi d, 5
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_PHASE
                    ldi d, io_frame_advance_3
                    jmp write_byte
io_frame_advance_3:
                    ldi c, 2
                    ldi d, frame_start
                    jmp set_bank
padding5 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #6
;===================================================================================================

; Прочитать следующий байт модели; переходить через границы банков.
gfx_read_next:
                    ldi d, 6
                    st d, io_ret_bank
                    ld c, ptr_bank
                    ld b, ptr_addr
                    ldi d, io_gfx_read_next_0
                    jmp read_byte
io_gfx_read_next_0:
                    ld b, ptr_addr
                    inc b
                    st b, ptr_addr
                    jnz read_next_done
                    ldi b, 128
                    st b, ptr_addr
                    ld b, ptr_bank
                    inc b
                    st b, ptr_bank
read_next_done:
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding6 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #7
;===================================================================================================

; Записать следующий байт в буфер экранных вершин.
gfx_write_next:
                    ldi d, 7
                    st d, io_ret_bank
                    ld c, out_bank
                    ld b, out_addr
                    ldi d, io_gfx_write_next_0
                    jmp write_byte
io_gfx_write_next_0:
                    ld b, out_addr
                    inc b
                    st b, out_addr
                    jnz write_next_done
                    ldi b, 128
                    st b, out_addr
                    ld b, out_bank
                    inc b
                    st b, out_bank
write_next_done:
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding7 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #8
;===================================================================================================

; Прочитать следующий байт экранной вершины.
gfx_read_output:
                    ldi d, 8
                    st d, io_ret_bank
                    ld c, out_bank
                    ld b, out_addr
                    ldi d, io_gfx_read_output_0
                    jmp read_byte
io_gfx_read_output_0:
                    ld b, out_addr
                    inc b
                    st b, out_addr
                    jnz read_output_done
                    ldi b, 128
                    st b, out_addr
                    ld b, out_bank
                    inc b
                    st b, out_bank
read_output_done:
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding8 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #9
;===================================================================================================

; Повернуть пару ru/rv на angle: u=cos*u+sin*v, v=cos*v-sin*u.
gfx_rotate_pair:
                    ld c, angle
                    ldi a, LUT_BASE
                    add c, a
                    ld b, ru
                    ldi a, 63
                    and b, a
                    ldi a, 192
                    add b, a
                    ldi d, 9
                    st d, io_ret_bank
                    ldi d, io_gfx_rotate_pair_8
                    jmp read_byte
io_gfx_rotate_pair_8:
                    st a, t0
                    ld c, angle
                    ldi a, LUT_BASE
                    add c, a
                    ld b, rv
                    ldi a, 63
                    and b, a
                    ldi a, 128
                    add b, a
                    ldi d, 9
                    st d, io_ret_bank
                    ldi d, io_gfx_rotate_pair_18
                    jmp read_byte
io_gfx_rotate_pair_18:
                    st a, t1
                    ld c, angle
                    ldi a, LUT_BASE
                    add c, a
                    ld b, rv
                    ldi a, 63
                    and b, a
                    ldi a, 192
                    add b, a
                    ldi d, 9
                    st d, io_ret_bank
                    ldi d, io_gfx_rotate_pair_28
                    jmp read_byte
io_gfx_rotate_pair_28:
                    st a, rv
                    ld c, angle
                    ldi a, LUT_BASE
                    add c, a
                    ld b, ru
                    ldi a, 63
                    and b, a
                    ldi a, 128
                    add b, a
                    ldi d, 9
                    st d, io_ret_bank
                    ldi d, io_gfx_rotate_pair_38
                    jmp read_byte
io_gfx_rotate_pair_38:
                    st a, ru
                    ld a, t0
                    ld b, t1
                    add a, b
                    st a, t0
                    ld a, rv
                    ld b, ru
                    sub a, b
                    st a, rv
                    ld a, t0
                    st a, ru
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding9 db 0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #10
;===================================================================================================

; Вращение вокруг Y, затем X. Координаты модели имеют радиус не более 20.
gfx_project_vertex:
                    ld a, wx
                    st a, ru
                    ld a, wz
                    st a, rv
                    ld a, yaw
                    st a, angle
                    ldi c, 10
                    st c, ret2_bank
                    ldi d, resume_gfx_project_vertex_6
                    st d, ret2_addr
                    ldi c, 9
                    ldi d, gfx_rotate_pair
                    jmp set_bank
resume_gfx_project_vertex_6:
                    ld a, ru
                    st a, wx
                    ld a, rv
                    st a, wz
                    ld a, wy
                    st a, ru
                    ld a, wz
                    st a, rv
                    ld a, pitch
                    st a, angle
                    ldi c, 10
                    st c, ret2_bank
                    ldi d, resume_gfx_project_vertex_17
                    st d, ret2_addr
                    ldi c, 9
                    ldi d, gfx_rotate_pair
                    jmp set_bank
resume_gfx_project_vertex_17:
                    ld a, ru
                    st a, wy
                    ld a, rv
                    st a, wz
                    ldi c, 11
                    ldi d, project_roll
                    jmp set_bank
padding10 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #11
;===================================================================================================

; Вращение вокруг Z; ближняя/дальняя плоскости камеры — z=8 и z=63.
project_roll:
                    ld a, wx
                    st a, ru
                    ld a, wy
                    st a, rv
                    ld a, roll
                    st a, angle
                    ldi c, 11
                    st c, ret2_bank
                    ldi d, resume_project_roll_6
                    st d, ret2_addr
                    ldi c, 9
                    ldi d, gfx_rotate_pair
                    jmp set_bank
resume_project_roll_6:
                    ld a, ru
                    st a, wx
                    ld a, rv
                    st a, wy
                    ld a, wz
                    ldi b, CAMERA_DISTANCE
                    add a, b
                    st a, wz
                    st a, depth
                    ldi b, 8
                    sub a, b
                    jnc bridge_project_roll_18
                    ldi c, 13
                    ldi d, project_invisible
                    jmp set_bank
bridge_project_roll_18:
                    ldi b, 56
                    sub a, b
                    jc bridge_project_roll_21
                    ldi c, 13
                    ldi d, project_invisible
                    jmp set_bank
bridge_project_roll_21:
                    ldi c, 12
                    ldi d, project_perspective
                    jmp set_bank
padding11 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #12
;===================================================================================================

; Перспектива x=8+16*x/z, y=8-16*y/z; таблица деления содержит числа, не кадры.
project_perspective:
                    ld c, wz
                    ldi a, 8
                    sub c, a
                    shr c
                    ldi a, PROJECTION_BASE
                    add c, a
                    ld b, wz
                    ldi a, 1
                    and b, a
                    shl b
                    shl b
                    shl b
                    shl b
                    shl b
                    shl b
                    ld a, wx
                    ldi d, 63
                    and a, d
                    add b, a
                    ldi a, 128
                    add b, a
                    ldi d, 12
                    st d, io_ret_bank
                    ldi d, io_project_perspective_21
                    jmp read_byte
io_project_perspective_21:
                    st a, wx
                    ld c, wz
                    ldi a, 8
                    sub c, a
                    shr c
                    ldi a, PROJECTION_BASE
                    add c, a
                    ld b, wz
                    ldi a, 1
                    and b, a
                    shl b
                    shl b
                    shl b
                    shl b
                    shl b
                    shl b
                    ld a, wy
                    neg a
                    ldi d, 63
                    and a, d
                    add b, a
                    ldi a, 128
                    add b, a
                    ldi d, 12
                    st d, io_ret_bank
                    ldi d, io_project_perspective_45
                    jmp read_byte
io_project_perspective_45:
                    st a, wy
                    ldi a, 1
                    st a, wz
                    ld c, ret1_bank
                    ld d, ret1_addr
                    jmp set_bank
padding12 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #13
;===================================================================================================

; Пометить вершину вне диапазона глубины; инцидентные примитивы пропускаются.
project_invisible:
                    clr a
                    st a, wz
                    ld c, ret1_bank
                    ld d, ret1_addr
                    jmp set_bank
padding13 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #14
;===================================================================================================

; A — индекс; вернуть x/y/видимость и глубину из четырёхбайтовой экранной вершины.
gfx_get_vertex:
                    mov b, a
                    ldi c, 31
                    and b, c
                    shl b
                    shl b
                    ldi c, 128
                    add b, c
                    st b, out_addr
                    shr a
                    shr a
                    shr a
                    shr a
                    shr a
                    ldi c, VERTEX_BASE
                    add a, c
                    st a, out_bank
                    ldi c, 14
                    st c, ret2_bank
                    ldi d, resume_gfx_get_vertex_16
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_gfx_get_vertex_16:
                    st a, wx
                    ldi c, 14
                    st c, ret2_bank
                    ldi d, resume_gfx_get_vertex_18
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_gfx_get_vertex_18:
                    st a, wy
                    ldi c, 14
                    st c, ret2_bank
                    ldi d, resume_gfx_get_vertex_20
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_gfx_get_vertex_20:
                    st a, wz
                    ldi c, 14
                    st c, ret2_bank
                    ldi d, resume_gfx_get_vertex_22
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_gfx_get_vertex_22:
                    st a, depth
                    ld c, ret1_bank
                    ld d, ret1_addr
                    jmp set_bank
padding14 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #15
;===================================================================================================

; wx/wy — пиксель; color=0 белый, 1 красный, 2 синий, 3 фиолетовый.
gfx_pixel:
                    ld a, wx
                    ld b, wy
                    or a, b
                    ldi b, 240
                    and a, b
                    jz bridge_gfx_pixel_5
                    ldi c, 16
                    ldi d, pixel_done
                    jmp set_bank
bridge_gfx_pixel_5:
                    ld b, wy
                    shl b
                    ld a, wx
                    mov c, a
                    shr a
                    shr a
                    shr a
                    add b, a
                    ldi a, 128
                    add b, a
                    st b, ru
                    mov a, c
                    ldi b, 7
                    and a, b
                    ldi b, pixel_masks
                    add a, b
                    ld a, a
                    st a, mask
                    ldi d, 15
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ld b, ru
                    ldi d, io_gfx_pixel_24
                    jmp read_byte
io_gfx_pixel_24:
                    st a, t0
                    ld a, color
                    ldi b, 1
                    and a, b
                    ld a, t0
                    ld b, mask
                    jnz pixel_red_set
                    not b
                    and a, b
                    jmp pixel_red_write
pixel_red_set:
                    or a, b
pixel_red_write:
                    ldi d, 15
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ld b, ru
                    ldi d, io_gfx_pixel_38
                    jmp write_byte
io_gfx_pixel_38:
                    ld a, ru
                    ldi b, 32
                    add a, b
                    st a, ru
                    ldi c, 16
                    ldi d, pixel_blue
                    jmp set_bank

; Маски пикселей; старший бит слева.
pixel_masks db 128,64,32,16,8,4,2,1
padding15 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #16
;===================================================================================================

; Записать второй цветовой слой; оба слоя заменяют цвет, а не накапливают его.
pixel_blue:
                    ldi d, 16
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ld b, ru
                    ldi d, io_pixel_blue_0
                    jmp read_byte
io_pixel_blue_0:
                    st a, t0
                    ld a, color
                    ldi b, 2
                    and a, b
                    ld a, t0
                    ld b, mask
                    jnz pixel_blue_set
                    not b
                    and a, b
                    jmp pixel_blue_write
pixel_blue_set:
                    or a, b
pixel_blue_write:
                    ldi d, 16
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ld b, ru
                    ldi d, io_pixel_blue_14
                    jmp write_byte
io_pixel_blue_14:
pixel_done:
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding16 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #17
;===================================================================================================

; Цветная линия Брезенхэма; экран отсекается проверкой координат каждого пикселя.
gfx_line:
                    ld a, x1
                    ld b, x0
                    sub a, b
                    ldi b, 1
                    jns full_x_positive
                    neg a
                    neg b
full_x_positive:
                    st a, dx
                    st b, sx
                    ld a, y1
                    ld b, y0
                    sub a, b
                    ldi b, 1
                    jns full_y_positive
                    neg a
                    neg b
full_y_positive:
                    st a, dy
                    st b, sy
                    ld a, dx
                    ld b, dy
                    sub a, b
                    ldi b, 0
                    jnc line_x_major
                    inc b
                    ld a, dy
                    jmp line_major_ready
line_x_major:
                    ld a, dx
line_major_ready:
                    st b, angle
                    inc a
                    st a, x1
                    dec a
                    dec a
                    sar a
                    st a, err
                    ldi c, 18
                    ldi d, line_pixel
                    jmp set_bank
padding17 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #18
;===================================================================================================

; X — главная ось; ошибка сохраняет правило выбора пикселя исходного растеризатора.
line_pixel:
                    ld a, x0
                    st a, wx
                    ld a, y0
                    st a, wy
                    ldi c, 18
                    st c, ret2_bank
                    ldi d, resume_line_pixel_4
                    st d, ret2_addr
                    ldi c, 15
                    ldi d, gfx_pixel
                    jmp set_bank
resume_line_pixel_4:
                    ld a, x1
                    dec a
                    st a, x1
                    jnz bridge_line_pixel_8
                    ldi c, 19
                    ldi d, line_done
                    jmp set_bank
bridge_line_pixel_8:
                    ld a, angle
                    test a
                    jz bridge_line_pixel_11
                    ldi c, 19
                    ldi d, line_step_y
                    jmp set_bank
bridge_line_pixel_11:
                    ld a, x0
                    ld b, sx
                    add a, b
                    st a, x0
                    ld a, err
                    ld b, dy
                    sub a, b
                    st a, err
                    jns line_pixel
                    ld b, dx
                    add a, b
                    st a, err
                    ld a, y0
                    ld b, sy
                    add a, b
                    st a, y0
                    jmp line_pixel
padding18 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #19
;===================================================================================================

; Y — главная ось; координаты -54...70 допустимы при разности не более 127.
line_step_y:
                    ld a, y0
                    ld b, sy
                    add a, b
                    st a, y0
                    ld a, err
                    ld b, dx
                    sub a, b
                    st a, err
                    js bridge_line_step_y_8
                    ldi c, 18
                    ldi d, line_pixel
                    jmp set_bank
bridge_line_step_y_8:
                    ld b, dy
                    add a, b
                    st a, err
                    ld a, x0
                    ld b, sx
                    add a, b
                    st a, x0
                    ldi c, 18
                    ldi d, line_pixel
                    jmp set_bank
line_done:
                    ld c, ret1_bank
                    ld d, ret1_addr
                    jmp set_bank
padding19 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #20
;===================================================================================================

; Знаковое умножение ru*rv: t1:t0 — 16-битный результат, без аппаратного MUL.
gfx_mul16:
                    ld a, ru
                    ld b, rv
                    xor a, b
                    st a, mul_sign
                    ld c, ru
                    test c
                    jns mul_u_positive
                    neg c
mul_u_positive:
                    ld b, rv
                    test b
                    jns mul_v_positive
                    neg b
mul_v_positive:
                    clr d
                    clr a
                    st a, t0
                    st a, t1
mul_loop:
                    shr b
                    jnc mul_skip
                    ld a, t0
                    add a, c
                    st a, t0
                    ld a, t1
                    adc a, d
                    st a, t1
mul_skip:
                    shl c
                    rcl d
                    test b
                    jnz mul_loop
                    ld a, mul_sign
                    test a
                    jns mul_done
                    ld a, t0
                    neg a
                    st a, t0
                    ld a, t1
                    ldi b, 0
                    sbb b, a
                    st b, t1
mul_done:
                    ld c, ret3_bank
                    ld d, ret3_addr
                    jmp set_bank
padding20 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #21
;===================================================================================================

; Определитель первого ребра и третьей вершины; нулевая площадь не заполняется.
triangle_area:
                    ld a, x1
                    ld b, x0
                    sub a, b
                    st a, ru
                    ld a, wy
                    ld b, y0
                    sub a, b
                    st a, rv
                    ldi c, 21
                    st c, ret3_bank
                    ldi d, resume_triangle_area_8
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_area_8:
                    ld a, t0
                    st a, sx
                    ld a, t1
                    st a, sy
                    ld a, y1
                    ld b, y0
                    sub a, b
                    st a, ru
                    ld a, wx
                    ld b, x0
                    sub a, b
                    st a, rv
                    ldi c, 21
                    st c, ret3_bank
                    ldi d, resume_triangle_area_21
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_area_21:
                    ld a, sx
                    ld b, t0
                    sub a, b
                    st a, sx
                    ld a, sy
                    ld b, t1
                    sbb a, b
                    st a, sy
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding21 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #22
;===================================================================================================

; Проверить текущие 16-битные значения рёбер; умножения в цикле нет.
triangle_inside:
                    clr a
                    st a, signs
                    ldi c, 23
                    ldi d, triangle_sign0
                    jmp set_bank
padding22 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #23
;===================================================================================================

; Оба ненулевых знака одновременно означают точку вне треугольника.
triangle_sign0:
                    ld a, y0
                    test a
                    js triangle_negative0
                    ld b, x0
                    or a, b
                    jnz bridge_triangle_sign0_5
                    ldi c, 24
                    ldi d, triangle_sign1
                    jmp set_bank
bridge_triangle_sign0_5:
                    ld a, signs
                    ldi b, 2
                    jmp triangle_sign_record0
triangle_negative0:
                    ld a, signs
                    ldi b, 1
triangle_sign_record0:
                    or a, b
                    st a, signs
                    ldi b, 3
                    xor a, b
                    jnz bridge_triangle_sign0_17
                    ldi c, 27
                    ldi d, triangle_inside_no
                    jmp set_bank
bridge_triangle_sign0_17:
                    ldi c, 24
                    ldi d, triangle_sign1
                    jmp set_bank
padding23 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #24
;===================================================================================================

; Оба ненулевых знака одновременно означают точку вне треугольника.
triangle_sign1:
                    ld a, y1
                    test a
                    js triangle_negative1
                    ld b, x1
                    or a, b
                    jnz bridge_triangle_sign1_5
                    ldi c, 25
                    ldi d, triangle_sign2
                    jmp set_bank
bridge_triangle_sign1_5:
                    ld a, signs
                    ldi b, 2
                    jmp triangle_sign_record1
triangle_negative1:
                    ld a, signs
                    ldi b, 1
triangle_sign_record1:
                    or a, b
                    st a, signs
                    ldi b, 3
                    xor a, b
                    jnz bridge_triangle_sign1_17
                    ldi c, 27
                    ldi d, triangle_inside_no
                    jmp set_bank
bridge_triangle_sign1_17:
                    ldi c, 25
                    ldi d, triangle_sign2
                    jmp set_bank
padding24 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #25
;===================================================================================================

; Оба ненулевых знака одновременно означают точку вне треугольника.
triangle_sign2:
                    ld a, dy
                    test a
                    js triangle_negative2
                    ld b, dx
                    or a, b
                    jnz bridge_triangle_sign2_5
                    ldi c, 26
                    ldi d, triangle_inside_yes
                    jmp set_bank
bridge_triangle_sign2_5:
                    ld a, signs
                    ldi b, 2
                    jmp triangle_sign_record2
triangle_negative2:
                    ld a, signs
                    ldi b, 1
triangle_sign_record2:
                    or a, b
                    st a, signs
                    ldi b, 3
                    xor a, b
                    jnz bridge_triangle_sign2_17
                    ldi c, 27
                    ldi d, triangle_inside_no
                    jmp set_bank
bridge_triangle_sign2_17:
                    ldi c, 26
                    ldi d, triangle_inside_yes
                    jmp set_bank
padding25 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #26
;===================================================================================================

; Точка внутри или на границе треугольника.
triangle_inside_yes:
                    ldi a, 1
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding26 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #27
;===================================================================================================

; Точка вне треугольника.
triangle_inside_no:
                    clr a
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding27 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #28
;===================================================================================================

; Вычислить определитель ребра в точке (0,0) один раз.
triangle_init0:
                    ld a, x1
                    ld b, x0
                    sub a, b
                    st a, ru
                    ld a, wy
                    ld b, y0
                    sub a, b
                    st a, rv
                    ldi c, 28
                    st c, ret3_bank
                    ldi d, resume_triangle_init0_8
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_init0_8:
                    ld a, t0
                    st a, sx
                    ld a, t1
                    st a, sy
                    ld a, y1
                    ld b, y0
                    sub a, b
                    st a, ru
                    ld a, wx
                    ld b, x0
                    sub a, b
                    st a, rv
                    ldi c, 28
                    st c, ret3_bank
                    ldi d, resume_triangle_init0_21
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_init0_21:
                    ld a, sx
                    ld b, t0
                    sub a, b
                    st a, sx
                    ld a, sy
                    ld b, t1
                    sbb a, b
                    st a, sy
                    ld a, sx
                    ldi d, 28
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE0
                    ldi d, io_triangle_init0_31
                    jmp write_byte
io_triangle_init0_31:
                    ld a, sy
                    ldi d, 28
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE1
                    ldi d, io_triangle_init0_33
                    jmp write_byte
io_triangle_init0_33:
                    ldi c, 29
                    ldi d, triangle_coeff0
                    jmp set_bank
padding28 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #29
;===================================================================================================

; Сохранить шаг ребра по X и Y; порядок обхода вершин может быть любым.
triangle_coeff0:
                    ld a, y0
                    ld b, y1
                    sub a, b
                    ldi d, 29
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE6
                    ldi d, io_triangle_coeff0_3
                    jmp write_byte
io_triangle_coeff0_3:
                    ld a, x1
                    ld b, x0
                    sub a, b
                    ldi d, 29
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE9
                    ldi d, io_triangle_coeff0_7
                    jmp write_byte
io_triangle_coeff0_7:
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding29 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #30
;===================================================================================================

; Вычислить определитель ребра в точке (0,0) один раз.
triangle_init1:
                    ld a, dx
                    ld b, x1
                    sub a, b
                    st a, ru
                    ld a, wy
                    ld b, y1
                    sub a, b
                    st a, rv
                    ldi c, 30
                    st c, ret3_bank
                    ldi d, resume_triangle_init1_8
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_init1_8:
                    ld a, t0
                    st a, sx
                    ld a, t1
                    st a, sy
                    ld a, dy
                    ld b, y1
                    sub a, b
                    st a, ru
                    ld a, wx
                    ld b, x1
                    sub a, b
                    st a, rv
                    ldi c, 30
                    st c, ret3_bank
                    ldi d, resume_triangle_init1_21
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_init1_21:
                    ld a, sx
                    ld b, t0
                    sub a, b
                    st a, sx
                    ld a, sy
                    ld b, t1
                    sbb a, b
                    st a, sy
                    ld a, sx
                    ldi d, 30
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE2
                    ldi d, io_triangle_init1_31
                    jmp write_byte
io_triangle_init1_31:
                    ld a, sy
                    ldi d, 30
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE3
                    ldi d, io_triangle_init1_33
                    jmp write_byte
io_triangle_init1_33:
                    ldi c, 31
                    ldi d, triangle_coeff1
                    jmp set_bank
padding30 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #31
;===================================================================================================

; Сохранить шаг ребра по X и Y; порядок обхода вершин может быть любым.
triangle_coeff1:
                    ld a, y1
                    ld b, dy
                    sub a, b
                    ldi d, 31
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE7
                    ldi d, io_triangle_coeff1_3
                    jmp write_byte
io_triangle_coeff1_3:
                    ld a, dx
                    ld b, x1
                    sub a, b
                    ldi d, 31
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE10
                    ldi d, io_triangle_coeff1_7
                    jmp write_byte
io_triangle_coeff1_7:
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding31 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #32
;===================================================================================================

; Вычислить определитель ребра в точке (0,0) один раз.
triangle_init2:
                    ld a, x0
                    ld b, dx
                    sub a, b
                    st a, ru
                    ld a, wy
                    ld b, dy
                    sub a, b
                    st a, rv
                    ldi c, 32
                    st c, ret3_bank
                    ldi d, resume_triangle_init2_8
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_init2_8:
                    ld a, t0
                    st a, sx
                    ld a, t1
                    st a, sy
                    ld a, y0
                    ld b, dy
                    sub a, b
                    st a, ru
                    ld a, wx
                    ld b, dx
                    sub a, b
                    st a, rv
                    ldi c, 32
                    st c, ret3_bank
                    ldi d, resume_triangle_init2_21
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_triangle_init2_21:
                    ld a, sx
                    ld b, t0
                    sub a, b
                    st a, sx
                    ld a, sy
                    ld b, t1
                    sbb a, b
                    st a, sy
                    ld a, sx
                    ldi d, 32
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE4
                    ldi d, io_triangle_init2_31
                    jmp write_byte
io_triangle_init2_31:
                    ld a, sy
                    ldi d, 32
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE5
                    ldi d, io_triangle_init2_33
                    jmp write_byte
io_triangle_init2_33:
                    ldi c, 33
                    ldi d, triangle_coeff2
                    jmp set_bank
padding32 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #33
;===================================================================================================

; Сохранить шаг ребра по X и Y; порядок обхода вершин может быть любым.
triangle_coeff2:
                    ld a, dy
                    ld b, y0
                    sub a, b
                    ldi d, 33
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE8
                    ldi d, io_triangle_coeff2_3
                    jmp write_byte
io_triangle_coeff2_3:
                    ld a, x0
                    ld b, dx
                    sub a, b
                    ldi d, 33
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE11
                    ldi d, io_triangle_coeff2_7
                    jmp write_byte
io_triangle_coeff2_7:
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding33 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #34
;===================================================================================================

; Загрузить значения и приращения в рабочие переменные COMMON.
triangle_load0:
                    ldi d, 34
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE0
                    ldi d, io_triangle_load0_0
                    jmp read_byte
io_triangle_load0_0:
                    st a, x0
                    ldi d, 34
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE1
                    ldi d, io_triangle_load0_2
                    jmp read_byte
io_triangle_load0_2:
                    st a, y0
                    ldi d, 34
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE2
                    ldi d, io_triangle_load0_4
                    jmp read_byte
io_triangle_load0_4:
                    st a, x1
                    ldi d, 34
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE3
                    ldi d, io_triangle_load0_6
                    jmp read_byte
io_triangle_load0_6:
                    st a, y1
                    ldi d, 34
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE4
                    ldi d, io_triangle_load0_8
                    jmp read_byte
io_triangle_load0_8:
                    st a, dx
                    ldi d, 34
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE5
                    ldi d, io_triangle_load0_10
                    jmp read_byte
io_triangle_load0_10:
                    st a, dy
                    ldi c, 35
                    ldi d, triangle_load1
                    jmp set_bank
padding34 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #35
;===================================================================================================

; Загрузить значения и приращения в рабочие переменные COMMON.
triangle_load1:
                    ldi d, 35
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE6
                    ldi d, io_triangle_load1_0
                    jmp read_byte
io_triangle_load1_0:
                    st a, sx
                    ldi d, 35
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE7
                    ldi d, io_triangle_load1_2
                    jmp read_byte
io_triangle_load1_2:
                    st a, sy
                    ldi d, 35
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE8
                    ldi d, io_triangle_load1_4
                    jmp read_byte
io_triangle_load1_4:
                    st a, err
                    ldi d, 35
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE9
                    ldi d, io_triangle_load1_6
                    jmp read_byte
io_triangle_load1_6:
                    st a, ret3_bank
                    ldi d, 35
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE10
                    ldi d, io_triangle_load1_8
                    jmp read_byte
io_triangle_load1_8:
                    st a, ret3_addr
                    ldi d, 35
                    st d, io_ret_bank
                    ldi c, BUFFER_BASE
                    ldi b, TRI_STATE11
                    ldi d, io_triangle_load1_10
                    jmp read_byte
io_triangle_load1_10:
                    st a, angle
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding35 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #36
;===================================================================================================

; Прибавить три знаковых приращения к 16-битным определителям.
triangle_advance_x:
                    ld a, x0
                    ld b, sx
                    ldi c, 0
                    test b
                    jns advance_x_0
                    dec c
advance_x_0:
                    add a, b
                    st a, x0
                    ld a, y0
                    adc a, c
                    st a, y0
                    ld a, x1
                    ld b, sy
                    ldi c, 0
                    test b
                    jns advance_x_1
                    dec c
advance_x_1:
                    add a, b
                    st a, x1
                    ld a, y1
                    adc a, c
                    st a, y1
                    ld a, dx
                    ld b, err
                    ldi c, 0
                    test b
                    jns advance_x_2
                    dec c
advance_x_2:
                    add a, b
                    st a, dx
                    ld a, dy
                    adc a, c
                    st a, dy
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding36 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #37
;===================================================================================================

; Прибавить три знаковых приращения к 16-битным определителям.
triangle_advance_y:
                    ld a, x0
                    ld b, ret3_bank
                    ldi c, 0
                    test b
                    jns advance_y_0
                    dec c
advance_y_0:
                    add a, b
                    st a, x0
                    ld a, y0
                    adc a, c
                    st a, y0
                    ld a, x1
                    ld b, ret3_addr
                    ldi c, 0
                    test b
                    jns advance_y_1
                    dec c
advance_y_1:
                    add a, b
                    st a, x1
                    ld a, y1
                    adc a, c
                    st a, y1
                    ld a, dx
                    ld b, angle
                    ldi c, 0
                    test b
                    jns advance_y_2
                    dec c
advance_y_2:
                    add a, b
                    st a, dx
                    ld a, dy
                    adc a, c
                    st a, dy
                    ld c, ret2_bank
                    ld d, ret2_addr
                    jmp set_bank
padding37 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #38
;===================================================================================================

; Подготовить рёбра треугольника x0/y0, x1/y1, dx/dy; нулевая площадь пропускается.
gfx_triangle:
                    ld a, dx
                    st a, wx
                    ld a, dy
                    st a, wy
                    ldi c, 38
                    st c, ret2_bank
                    ldi d, resume_gfx_triangle_4
                    st d, ret2_addr
                    ldi c, 21
                    ldi d, triangle_area
                    jmp set_bank
resume_gfx_triangle_4:
                    ld a, sx
                    ld b, sy
                    or a, b
                    jnz bridge_gfx_triangle_8
                    ldi c, 40
                    ldi d, triangle_done
                    jmp set_bank
bridge_gfx_triangle_8:
                    clr a
                    st a, wx
                    st a, wy
                    ldi c, 38
                    st c, ret2_bank
                    ldi d, resume_gfx_triangle_12
                    st d, ret2_addr
                    ldi c, 28
                    ldi d, triangle_init0
                    jmp set_bank
resume_gfx_triangle_12:
                    ldi c, 38
                    st c, ret2_bank
                    ldi d, resume_gfx_triangle_13
                    st d, ret2_addr
                    ldi c, 30
                    ldi d, triangle_init1
                    jmp set_bank
resume_gfx_triangle_13:
                    ldi c, 38
                    st c, ret2_bank
                    ldi d, resume_gfx_triangle_14
                    st d, ret2_addr
                    ldi c, 32
                    ldi d, triangle_init2
                    jmp set_bank
resume_gfx_triangle_14:
                    ldi c, 38
                    st c, ret2_bank
                    ldi d, resume_gfx_triangle_15
                    st d, ret2_addr
                    ldi c, 34
                    ldi d, triangle_load0
                    jmp set_bank
resume_gfx_triangle_15:
                    ldi c, 39
                    ldi d, triangle_scan
                    jmp set_bank
padding38 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #39
;===================================================================================================

; Заполнять треугольник; во внутреннем цикле только сложения, проверки и запись цвета.
triangle_scan:
triangle_pixel:
                    ldi c, 39
                    st c, ret2_bank
                    ldi d, resume_triangle_scan_1
                    st d, ret2_addr
                    ldi c, 22
                    ldi d, triangle_inside
                    jmp set_bank
resume_triangle_scan_1:
                    test a
                    jz triangle_advance
                    ldi c, 39
                    st c, ret2_bank
                    ldi d, resume_triangle_scan_4
                    st d, ret2_addr
                    ldi c, 15
                    ldi d, gfx_pixel
                    jmp set_bank
resume_triangle_scan_4:
triangle_advance:
                    ld a, wx
                    inc a
                    st a, wx
                    ldi b, 16
                    xor a, b
                    jnz bridge_triangle_scan_11
                    ldi c, 40
                    ldi d, triangle_row
                    jmp set_bank
bridge_triangle_scan_11:
                    ldi c, 39
                    st c, ret2_bank
                    ldi d, resume_triangle_scan_12
                    st d, ret2_addr
                    ldi c, 36
                    ldi d, triangle_advance_x
                    jmp set_bank
resume_triangle_scan_12:
                    jmp triangle_pixel
padding39 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #40
;===================================================================================================

; Вернуть определители к началу строки и сдвинуть их на следующую строку.
triangle_row:
                    ld a, wy
                    inc a
                    st a, wy
                    ldi b, 16
                    xor a, b
                    jz triangle_done
                    clr a
                    st a, wx
                    ld a, sx
                    neg a
                    st a, sx
                    ld a, sy
                    neg a
                    st a, sy
                    ld a, err
                    neg a
                    st a, err
                    ldi a, 15
                    st a, mask
triangle_rewind:
                    ldi c, 40
                    st c, ret2_bank
                    ldi d, resume_triangle_row_20
                    st d, ret2_addr
                    ldi c, 36
                    ldi d, triangle_advance_x
                    jmp set_bank
resume_triangle_row_20:
                    ld a, mask
                    dec a
                    st a, mask
                    jnz triangle_rewind
                    ld a, sx
                    neg a
                    st a, sx
                    ld a, sy
                    neg a
                    st a, sy
                    ld a, err
                    neg a
                    st a, err
                    ldi c, 40
                    st c, ret2_bank
                    ldi d, resume_triangle_row_34
                    st d, ret2_addr
                    ldi c, 37
                    ldi d, triangle_advance_y
                    jmp set_bank
resume_triangle_row_34:
                    ldi c, 39
                    ldi d, triangle_pixel
                    jmp set_bank
triangle_done:
                    ld c, ret1_bank
                    ld d, ret1_addr
                    jmp set_bank
padding40 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #41
;===================================================================================================

; ptr_bank/ptr_addr — заголовок V,E,T; затем XYZ, рёбра с цветом, треугольники с цветом.
gfx_draw_mesh:
                    ldi c, 41
                    st c, ret2_bank
                    ldi d, resume_gfx_draw_mesh_0
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_gfx_draw_mesh_0:
                    st a, vertex_count
                    ldi c, 41
                    st c, ret2_bank
                    ldi d, resume_gfx_draw_mesh_2
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_gfx_draw_mesh_2:
                    st a, edge_count
                    ldi c, 41
                    st c, ret2_bank
                    ldi d, resume_gfx_draw_mesh_4
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_gfx_draw_mesh_4:
                    ldi d, 41
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_TRI_TOTAL
                    ldi d, io_gfx_draw_mesh_5
                    jmp write_byte
io_gfx_draw_mesh_5:
                    ldi a, VERTEX_BASE
                    st a, out_bank
                    ldi a, 128
                    st a, out_addr
                    ldi c, 42
                    ldi d, mesh_vertex
                    jmp set_bank
padding41 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #42
;===================================================================================================

; Прочитать XYZ и выполнить вращение с перспективой.
mesh_vertex:
                    ldi c, 42
                    st c, ret2_bank
                    ldi d, resume_mesh_vertex_0
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_vertex_0:
                    st a, wx
                    ldi c, 42
                    st c, ret2_bank
                    ldi d, resume_mesh_vertex_2
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_vertex_2:
                    st a, wy
                    ldi c, 42
                    st c, ret2_bank
                    ldi d, resume_mesh_vertex_4
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_vertex_4:
                    st a, wz
                    ldi c, 42
                    st c, ret1_bank
                    ldi d, resume_mesh_vertex_6
                    st d, ret1_addr
                    ldi c, 45
                    ldi d, gfx_scale_vertex
                    jmp set_bank
resume_mesh_vertex_6:
                    ldi c, 42
                    st c, ret1_bank
                    ldi d, resume_mesh_vertex_7
                    st d, ret1_addr
                    ldi c, 10
                    ldi d, gfx_project_vertex
                    jmp set_bank
resume_mesh_vertex_7:
                    ldi c, 43
                    ldi d, mesh_store_vertex
                    jmp set_bank
padding42 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #43
;===================================================================================================

; CPU вычисляет каждую экранную вершину один раз; результат — x/y/видимость/глубина.
mesh_store_vertex:
                    ld a, wx
                    ldi c, 43
                    st c, ret2_bank
                    ldi d, resume_mesh_store_vertex_1
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_store_vertex_1:
                    ld a, wy
                    ldi c, 43
                    st c, ret2_bank
                    ldi d, resume_mesh_store_vertex_3
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_store_vertex_3:
                    ld a, wz
                    ldi c, 43
                    st c, ret2_bank
                    ldi d, resume_mesh_store_vertex_5
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_store_vertex_5:
                    ld a, depth
                    ldi c, 43
                    st c, ret2_bank
                    ldi d, resume_mesh_store_vertex_7
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_store_vertex_7:
                    ld a, vertex_count
                    dec a
                    st a, vertex_count
                    jz bridge_mesh_store_vertex_11
                    ldi c, 42
                    ldi d, mesh_vertex
                    jmp set_bank
bridge_mesh_store_vertex_11:
                    ld a, edge_count
                    test a
                    jnz bridge_mesh_store_vertex_14
                    ldi c, 49
                    ldi d, mesh_faces_begin
                    jmp set_bank
bridge_mesh_store_vertex_14:
                    ldi c, 44
                    ldi d, mesh_edge
                    jmp set_bank
padding43 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #44
;===================================================================================================

; Цвет — третий байт ребра; вершины вне диапазона глубины не соединяются.
mesh_edge:
                    ldi c, 44
                    st c, ret2_bank
                    ldi d, resume_mesh_edge_0
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_edge_0:
                    ldi c, 44
                    st c, ret1_bank
                    ldi d, resume_mesh_edge_1
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_edge_1:
                    ld a, wx
                    st a, x0
                    ld a, wy
                    st a, y0
                    ld a, wz
                    st a, signs
                    ldi c, 44
                    st c, ret2_bank
                    ldi d, resume_mesh_edge_8
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_edge_8:
                    ldi c, 44
                    st c, ret1_bank
                    ldi d, resume_mesh_edge_9
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_edge_9:
                    ld a, wx
                    st a, x1
                    ld a, wy
                    st a, y1
                    ldi c, 44
                    st c, ret2_bank
                    ldi d, resume_mesh_edge_14
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_edge_14:
                    st a, color
                    ld a, signs
                    ld b, wz
                    and a, b
                    jz mesh_edge_next
                    ldi c, 44
                    st c, ret1_bank
                    ldi d, resume_mesh_edge_20
                    st d, ret1_addr
                    ldi c, 17
                    ldi d, gfx_line
                    jmp set_bank
resume_mesh_edge_20:
mesh_edge_next:
                    ld a, edge_count
                    dec a
                    st a, edge_count
                    jnz mesh_edge
                    ldi c, 49
                    ldi d, mesh_faces_begin
                    jmp set_bank
padding44 db 0,0

;===================================================================================================
; Банк памяти #45
;===================================================================================================

; Масштабирование XYZ: знаковое 16-битное произведение, коэффициент Q5 32…64 = ×1…×2.
gfx_scale_vertex:
                    ld a, wx
                    st a, ru
                    ldi d, 45
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_SCALE
                    ldi d, io_gfx_scale_vertex_2
                    jmp read_byte
io_gfx_scale_vertex_2:
                    st a, rv
                    ldi c, 45
                    st c, ret3_bank
                    ldi d, resume_gfx_scale_vertex_4
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_gfx_scale_vertex_4:
                    ld a, t0
                    ld b, t1
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    st a, wx
                    ldi c, 46
                    ldi d, scale_vertex1
                    jmp set_bank
padding45 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #46
;===================================================================================================

; Масштабирование XYZ: знаковое 16-битное произведение, коэффициент Q5 32…64 = ×1…×2.
scale_vertex1:
                    ld a, wy
                    st a, ru
                    ldi d, 46
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_SCALE
                    ldi d, io_scale_vertex1_2
                    jmp read_byte
io_scale_vertex1_2:
                    st a, rv
                    ldi c, 46
                    st c, ret3_bank
                    ldi d, resume_scale_vertex1_4
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_scale_vertex1_4:
                    ld a, t0
                    ld b, t1
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    st a, wy
                    ldi c, 47
                    ldi d, scale_vertex2
                    jmp set_bank
padding46 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #47
;===================================================================================================

; Масштабирование XYZ: знаковое 16-битное произведение, коэффициент Q5 32…64 = ×1…×2.
scale_vertex2:
                    ld a, wz
                    st a, ru
                    ldi d, 47
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_SCALE
                    ldi d, io_scale_vertex2_2
                    jmp read_byte
io_scale_vertex2_2:
                    st a, rv
                    ldi c, 47
                    st c, ret3_bank
                    ldi d, resume_scale_vertex2_4
                    st d, ret3_addr
                    ldi c, 20
                    ldi d, gfx_mul16
                    jmp set_bank
resume_scale_vertex2_4:
                    ld a, t0
                    ld b, t1
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    sar b
                    rcr a
                    st a, wz
                    ld c, ret1_bank
                    ld d, ret1_addr
                    jmp set_bank
padding47 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #48
;===================================================================================================

; A — масштаб Q5; сохранить коэффициент до рисования модели.
gfx_set_scale:
                    ldi d, 48
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_SCALE
                    ldi d, io_gfx_set_scale_0
                    jmp write_byte
io_gfx_set_scale_0:
                    ld c, ret1_bank
                    ld d, ret1_addr
                    jmp set_bank
padding48 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #49
;===================================================================================================

; Подготовить пятибайтовые записи треугольников: сумма глубин, цвет, три индекса.
mesh_faces_begin:
                    ldi d, 49
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_TRI_TOTAL
                    ldi d, io_mesh_faces_begin_0
                    jmp read_byte
io_mesh_faces_begin_0:
                    test a
                    jnz bridge_mesh_faces_begin_2
                    ldi c, 64
                    ldi d, mesh_done
                    jmp set_bank
bridge_mesh_faces_begin_2:
                    st a, vertex_count
                    ldi a, TRI_BUFFER_BASE
                    ldi d, 49
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_CACHE_BANK
                    ldi d, io_mesh_faces_begin_5
                    jmp write_byte
io_mesh_faces_begin_5:
                    ldi a, 128
                    ldi d, 49
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_CACHE_ADDR
                    ldi d, io_mesh_faces_begin_7
                    jmp write_byte
io_mesh_faces_begin_7:
                    ldi c, 50
                    ldi d, mesh_cache_face0
                    jmp set_bank
padding49 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #50
;===================================================================================================

; Прочитать индекс и добавить глубину камеры; сохранить общую видимость.
mesh_cache_face0:
                    ldi c, 50
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_face0_0
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_cache_face0_0:
                    st a, x0
                    ldi c, 50
                    st c, ret1_bank
                    ldi d, resume_mesh_cache_face0_2
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_cache_face0_2:
                    ld a, wz
                    st a, signs
                    ld a, depth
                    st a, dx
                    ldi c, 51
                    ldi d, mesh_cache_face1
                    jmp set_bank
padding50 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #51
;===================================================================================================

; Прочитать индекс и добавить глубину камеры; сохранить общую видимость.
mesh_cache_face1:
                    ldi c, 51
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_face1_0
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_cache_face1_0:
                    st a, y0
                    ldi c, 51
                    st c, ret1_bank
                    ldi d, resume_mesh_cache_face1_2
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_cache_face1_2:
                    ld a, wz
                    ld b, signs
                    and a, b
                    st a, signs
                    ld a, depth
                    ld b, dx
                    add a, b
                    st a, dx
                    ldi c, 52
                    ldi d, mesh_cache_face2
                    jmp set_bank
padding51 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #52
;===================================================================================================

; Прочитать индекс и добавить глубину камеры; сохранить общую видимость.
mesh_cache_face2:
                    ldi c, 52
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_face2_0
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_cache_face2_0:
                    st a, x1
                    ldi c, 52
                    st c, ret1_bank
                    ldi d, resume_mesh_cache_face2_2
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_cache_face2_2:
                    ld a, wz
                    ld b, signs
                    and a, b
                    st a, signs
                    ld a, depth
                    ld b, dx
                    add a, b
                    st a, dx
                    ldi c, 53
                    ldi d, mesh_cache_color
                    jmp set_bank
padding52 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #53
;===================================================================================================

; Нулевая глубина записи означает невидимый или уже нарисованный треугольник.
mesh_cache_color:
                    ldi c, 53
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_color_0
                    st d, ret2_addr
                    ldi c, 6
                    ldi d, gfx_read_next
                    jmp set_bank
resume_mesh_cache_color_0:
                    st a, color
                    ld a, signs
                    test a
                    jnz mesh_cache_visible
                    clr a
                    st a, dx
mesh_cache_visible:
                    ldi d, 53
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_CACHE_BANK
                    ldi d, io_mesh_cache_color_8
                    jmp read_byte
io_mesh_cache_color_8:
                    st a, out_bank
                    ldi d, 53
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_CACHE_ADDR
                    ldi d, io_mesh_cache_color_10
                    jmp read_byte
io_mesh_cache_color_10:
                    st a, out_addr
                    ldi c, 54
                    ldi d, mesh_cache_write0
                    jmp set_bank
padding53 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #54
;===================================================================================================

; Сохранить ключ глубины, цвет и первый индекс в рабочем буфере.
mesh_cache_write0:
                    ld a, dx
                    ldi c, 54
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_write0_1
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_cache_write0_1:
                    ld a, color
                    ldi c, 54
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_write0_3
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_cache_write0_3:
                    ld a, x0
                    ldi c, 54
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_write0_5
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_cache_write0_5:
                    ldi c, 55
                    ldi d, mesh_cache_write1
                    jmp set_bank
padding54 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #55
;===================================================================================================

; Продолжить буфер через границу банка и обработать следующий треугольник.
mesh_cache_write1:
                    ld a, y0
                    ldi c, 55
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_write1_1
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_cache_write1_1:
                    ld a, x1
                    ldi c, 55
                    st c, ret2_bank
                    ldi d, resume_mesh_cache_write1_3
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_cache_write1_3:
                    ld a, out_bank
                    ldi d, 55
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_CACHE_BANK
                    ldi d, io_mesh_cache_write1_5
                    jmp write_byte
io_mesh_cache_write1_5:
                    ld a, out_addr
                    ldi d, 55
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_CACHE_ADDR
                    ldi d, io_mesh_cache_write1_7
                    jmp write_byte
io_mesh_cache_write1_7:
                    ld a, vertex_count
                    dec a
                    st a, vertex_count
                    jz bridge_mesh_cache_write1_11
                    ldi c, 50
                    ldi d, mesh_cache_face0
                    jmp set_bank
bridge_mesh_cache_write1_11:
                    ldi c, 56
                    ldi d, mesh_sort_start
                    jmp set_bank
padding55 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #56
;===================================================================================================

; Каждый кадр сортируется заново по текущим координатам камеры.
mesh_sort_start:
                    ldi d, 56
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_TRI_TOTAL
                    ldi d, io_mesh_sort_start_0
                    jmp read_byte
io_mesh_sort_start_0:
                    st a, vertex_count
                    ldi c, 57
                    ldi d, mesh_select
                    jmp set_bank
padding56 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #57
;===================================================================================================

; Найти максимальную сумму глубин среди ещё не нарисованных треугольников.
mesh_select:
                    clr a
                    st a, dx
                    ldi d, 57
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_TRI_TOTAL
                    ldi d, io_mesh_select_2
                    jmp read_byte
io_mesh_select_2:
                    st a, edge_count
                    ldi a, TRI_BUFFER_BASE
                    st a, out_bank
                    ldi a, 128
                    st a, out_addr
                    ldi c, 58
                    ldi d, mesh_scan
                    jmp set_bank
padding57 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #58
;===================================================================================================

; При равной глубине сохранять исходный порядок; ближние записи не заменяют дальнюю.
mesh_scan:
                    ld a, out_bank
                    st a, x0
                    ld a, out_addr
                    st a, y0
                    ldi c, 58
                    st c, ret2_bank
                    ldi d, resume_mesh_scan_4
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_mesh_scan_4:
                    ld b, dx
                    sub b, a
                    jc bridge_mesh_scan_7
                    ldi c, 59
                    ldi d, mesh_scan_next
                    jmp set_bank
bridge_mesh_scan_7:
                    st a, dx
                    ld a, x0
                    ldi d, 58
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_BEST_BANK
                    ldi d, io_mesh_scan_10
                    jmp write_byte
io_mesh_scan_10:
                    ld a, y0
                    ldi d, 58
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_BEST_ADDR
                    ldi d, io_mesh_scan_12
                    jmp write_byte
io_mesh_scan_12:
                    ldi c, 59
                    ldi d, mesh_scan_next
                    jmp set_bank
padding58 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #59
;===================================================================================================

; Пропустить четыре поля записи; указатель корректно пересекает границы 128-байтовых банков.
mesh_scan_next:
                    ld a, out_addr
                    ldi b, 4
                    add a, b
                    jnc mesh_scan_no_wrap
                    ldi b, 128
                    add a, b
                    ld b, out_bank
                    inc b
                    st b, out_bank
mesh_scan_no_wrap:
                    st a, out_addr
                    ld a, edge_count
                    dec a
                    st a, edge_count
                    jz bridge_mesh_scan_next_14
                    ldi c, 58
                    ldi d, mesh_scan
                    jmp set_bank
bridge_mesh_scan_next_14:
                    ld a, dx
                    test a
                    jnz bridge_mesh_scan_next_17
                    ldi c, 64
                    ldi d, mesh_done
                    jmp set_bank
bridge_mesh_scan_next_17:
                    ldi c, 60
                    ldi d, mesh_selected
                    jmp set_bank
padding59 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #60
;===================================================================================================

; Пометить выбранную запись как нарисованную и прочитать её цвет и индексы.
mesh_selected:
                    ldi d, 60
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_BEST_BANK
                    ldi d, io_mesh_selected_0
                    jmp read_byte
io_mesh_selected_0:
                    st a, out_bank
                    ldi d, 60
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_BEST_ADDR
                    ldi d, io_mesh_selected_2
                    jmp read_byte
io_mesh_selected_2:
                    st a, out_addr
                    clr a
                    ldi c, 60
                    st c, ret2_bank
                    ldi d, resume_mesh_selected_5
                    st d, ret2_addr
                    ldi c, 7
                    ldi d, gfx_write_next
                    jmp set_bank
resume_mesh_selected_5:
                    ldi c, 60
                    st c, ret2_bank
                    ldi d, resume_mesh_selected_6
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_mesh_selected_6:
                    st a, color
                    ldi c, 60
                    st c, ret2_bank
                    ldi d, resume_mesh_selected_8
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_mesh_selected_8:
                    st a, dx
                    ldi c, 61
                    ldi d, mesh_selected_indices
                    jmp set_bank
padding60 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #61
;===================================================================================================

; Первый индекс преобразовать в экранную вершину после чтения всей записи.
mesh_selected_indices:
                    ldi c, 61
                    st c, ret2_bank
                    ldi d, resume_mesh_selected_indices_0
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_mesh_selected_indices_0:
                    st a, dy
                    ldi c, 61
                    st c, ret2_bank
                    ldi d, resume_mesh_selected_indices_2
                    st d, ret2_addr
                    ldi c, 8
                    ldi d, gfx_read_output
                    jmp set_bank
resume_mesh_selected_indices_2:
                    st a, sx
                    ld a, dx
                    ldi c, 61
                    st c, ret1_bank
                    ldi d, resume_mesh_selected_indices_5
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_selected_indices_5:
                    ld a, wx
                    st a, x0
                    ld a, wy
                    st a, y0
                    ldi c, 62
                    ldi d, mesh_selected_vertex1
                    jmp set_bank
padding61 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #62
;===================================================================================================

; Получить три экранные вершины выбранного треугольника.
mesh_selected_vertex1:
                    ld a, dy
                    ldi c, 62
                    st c, ret1_bank
                    ldi d, resume_mesh_selected_vertex1_1
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_selected_vertex1_1:
                    ld a, wx
                    st a, x1
                    ld a, wy
                    st a, y1
                    ld a, sx
                    ldi c, 62
                    st c, ret1_bank
                    ldi d, resume_mesh_selected_vertex1_7
                    st d, ret1_addr
                    ldi c, 14
                    ldi d, gfx_get_vertex
                    jmp set_bank
resume_mesh_selected_vertex1_7:
                    ld a, wx
                    st a, dx
                    ld a, wy
                    st a, dy
                    ldi c, 63
                    ldi d, mesh_selected_cull
                    jmp set_bank
padding62 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #63
;===================================================================================================

; При включённом отсечении пропустить обратные и вырожденные грани; затем рисовать от дальних к ближним.
mesh_selected_cull:
                    ldi d, 63
                    st d, io_ret_bank
                    ldi c, STATE_BANK
                    ldi b, STATE_CULL
                    ldi d, io_mesh_selected_cull_0
                    jmp read_byte
io_mesh_selected_cull_0:
                    test a
                    jz mesh_selected_draw
                    ld a, dx
                    st a, wx
                    ld a, dy
                    st a, wy
                    ldi c, 63
                    st c, ret2_bank
                    ldi d, resume_mesh_selected_cull_7
                    st d, ret2_addr
                    ldi c, 21
                    ldi d, triangle_area
                    jmp set_bank
resume_mesh_selected_cull_7:
                    ld a, sy
                    test a
                    jns bridge_mesh_selected_cull_10
                    ldi c, 64
                    ldi d, mesh_selected_next
                    jmp set_bank
bridge_mesh_selected_cull_10:
                    ld b, sx
                    or a, b
                    jnz bridge_mesh_selected_cull_13
                    ldi c, 64
                    ldi d, mesh_selected_next
                    jmp set_bank
bridge_mesh_selected_cull_13:
mesh_selected_draw:
                    ldi c, 63
                    st c, ret1_bank
                    ldi d, resume_mesh_selected_cull_15
                    st d, ret1_addr
                    ldi c, 38
                    ldi d, gfx_triangle
                    jmp set_bank
resume_mesh_selected_cull_15:
                    ldi c, 64
                    ldi d, mesh_selected_next
                    jmp set_bank
padding63 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #64
;===================================================================================================

; Завершить модель после всех видимых треугольников.
mesh_selected_next:
                    ld a, vertex_count
                    dec a
                    st a, vertex_count
                    jz bridge_mesh_selected_next_3
                    ldi c, 57
                    ldi d, mesh_select
                    jmp set_bank
bridge_mesh_selected_next_3:
mesh_done:
                    ld c, ret0_bank
                    ld d, ret0_addr
                    jmp set_bank
padding64 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #65
;===================================================================================================

; Два скрытых цветовых слоя по 32 байта.
backbuffer db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

; Очистить оба слоя скрытого кадра.
gfx_begin:
                    clr a
                    ldi b, 128
                    ldi c, 64
begin_loop:
                    st a, b
                    inc b
                    dec c
                    jnz begin_loop
                    ld c, ret0_bank
                    ld d, ret0_addr
                    jmp set_bank

; Скопировать все 64 байта на цветной экран; обновление последовательное.
gfx_present:
                    ldi b, 128
                    ldi c, 64
                    ldi d, 64
present_loop:
                    ld a, b
                    st a, c
                    inc b
                    inc c
                    dec d
                    jnz present_loop
                    ld c, ret0_bank
                    ld d, ret0_addr
                    jmp set_bank

; Выравнивание состояния треугольника.
state_alignment db 0

; Начальные определители и приращения рёбер.
triangle_state db 0,0,0,0,0,0,0,0,0,0,0,0
padding65 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #66: graphics_state
;===================================================================================================
graphics_state66 db 0,32,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #67: projected_vertices
;===================================================================================================
projected_vertices67 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #68: triangle_cache
;===================================================================================================
triangle_cache68 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #69: model
;===================================================================================================
model69 db 6,24,0,251,0,251,5,0,251,5,0,5,251,0,5,0,7,0,0,249,0,0,1,1,1,4,1,4,0,1,1,0,2,0,5,2,5,1,2,1,2,2,2,4,2,4,1,2,2,1,3,1,5,3,5,2,3,2,3,3,3,4,3,4,2,3,3,2,1,2,5,1,5,3,1,3,0,1,0,4,1,4,3,1,0,3,2,3,5,2,5,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #70: rotation_lut
;===================================================================================================
rotation_lut70 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,224,225,226,227,228,229,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255

;===================================================================================================
; Банк памяти #71: rotation_lut
;===================================================================================================
rotation_lut71 db 0,0,0,1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,6,6,6,250,250,250,250,251,251,251,251,251,252,252,252,252,252,252,253,253,253,253,253,254,254,254,254,254,255,255,255,255,255,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,26,27,28,29,30,225,226,227,228,229,230,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255

;===================================================================================================
; Банк памяти #72: rotation_lut
;===================================================================================================
rotation_lut72 db 0,0,1,1,2,2,2,3,3,3,4,4,5,5,5,6,6,7,7,7,8,8,8,9,9,10,10,10,11,11,11,12,244,244,245,245,245,246,246,246,247,247,248,248,248,249,249,249,250,250,251,251,251,252,252,253,253,253,254,254,254,255,255,0,0,1,2,3,4,5,6,6,7,8,9,10,11,12,13,14,15,16,17,18,18,19,20,21,22,23,24,25,26,27,28,29,226,227,228,229,230,231,232,233,234,235,236,237,238,238,239,240,241,242,243,244,245,246,247,248,249,250,250,251,252,253,254,255

;===================================================================================================
; Банк памяти #73: rotation_lut
;===================================================================================================
rotation_lut73 db 0,1,1,2,2,3,3,4,4,5,6,6,7,7,8,8,9,9,10,11,11,12,12,13,13,14,14,15,16,16,17,17,238,239,239,240,240,241,242,242,243,243,244,244,245,245,246,247,247,248,248,249,249,250,250,251,252,252,253,253,254,254,255,255,0,1,2,2,3,4,5,6,7,7,8,9,10,11,12,12,13,14,15,16,17,17,18,19,20,21,22,22,23,24,25,26,229,230,231,232,233,234,234,235,236,237,238,239,239,240,241,242,243,244,244,245,246,247,248,249,249,250,251,252,253,254,254,255

;===================================================================================================
; Банк памяти #74: rotation_lut
;===================================================================================================
rotation_lut74 db 0,1,1,2,3,4,4,5,6,6,7,8,8,9,10,11,11,12,13,13,14,15,16,16,17,18,18,19,20,21,21,22,233,234,235,235,236,237,238,238,239,240,240,241,242,243,243,244,245,245,246,247,248,248,249,250,250,251,252,252,253,254,255,255,0,1,1,2,3,4,4,5,6,6,7,8,8,9,10,11,11,12,13,13,14,15,16,16,17,18,18,19,20,21,21,22,233,234,235,235,236,237,238,238,239,240,240,241,242,243,243,244,245,245,246,247,248,248,249,250,250,251,252,252,253,254,255,255

;===================================================================================================
; Банк памяти #75: rotation_lut
;===================================================================================================
rotation_lut75 db 0,1,2,2,3,4,5,6,7,7,8,9,10,11,12,12,13,14,15,16,17,17,18,19,20,21,22,22,23,24,25,26,229,230,231,232,233,234,234,235,236,237,238,239,239,240,241,242,243,244,244,245,246,247,248,249,249,250,251,252,253,254,254,255,0,1,1,2,2,3,3,4,4,5,6,6,7,7,8,8,9,9,10,11,11,12,12,13,13,14,14,15,16,16,17,17,238,239,239,240,240,241,242,242,243,243,244,244,245,245,246,247,247,248,248,249,249,250,250,251,252,252,253,253,254,254,255,255

;===================================================================================================
; Банк памяти #76: rotation_lut
;===================================================================================================
rotation_lut76 db 0,1,2,3,4,5,6,6,7,8,9,10,11,12,13,14,15,16,17,18,18,19,20,21,22,23,24,25,26,27,28,29,226,227,228,229,230,231,232,233,234,235,236,237,238,238,239,240,241,242,243,244,245,246,247,248,249,250,250,251,252,253,254,255,0,0,1,1,2,2,2,3,3,3,4,4,5,5,5,6,6,7,7,7,8,8,8,9,9,10,10,10,11,11,11,12,244,244,245,245,245,246,246,246,247,247,248,248,248,249,249,249,250,250,251,251,251,252,252,253,253,253,254,254,254,255,255,0

;===================================================================================================
; Банк памяти #77: rotation_lut
;===================================================================================================
rotation_lut77 db 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,26,27,28,29,30,225,226,227,228,229,230,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255,0,0,0,1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,6,6,6,250,250,250,250,251,251,251,251,251,252,252,252,252,252,252,253,253,253,253,253,254,254,254,254,254,255,255,255,255,255,0,0

;===================================================================================================
; Банк памяти #78: rotation_lut
;===================================================================================================
rotation_lut78 db 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,224,225,226,227,228,229,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #79: rotation_lut
;===================================================================================================
rotation_lut79 db 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,26,27,28,29,30,225,226,227,228,229,230,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255,0,0,0,255,255,255,255,255,254,254,254,254,254,253,253,253,253,253,252,252,252,252,252,252,251,251,251,251,251,250,250,250,6,6,6,6,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,3,2,2,2,2,2,1,1,1,1,1,0,0

;===================================================================================================
; Банк памяти #80: rotation_lut
;===================================================================================================
rotation_lut80 db 0,1,2,3,4,5,6,6,7,8,9,10,11,12,13,14,15,16,17,18,18,19,20,21,22,23,24,25,26,27,28,29,226,227,228,229,230,231,232,233,234,235,236,237,238,238,239,240,241,242,243,244,245,246,247,248,249,250,250,251,252,253,254,255,0,0,255,255,254,254,254,253,253,253,252,252,251,251,251,250,250,249,249,249,248,248,248,247,247,246,246,246,245,245,245,244,12,12,11,11,11,10,10,10,9,9,8,8,8,7,7,7,6,6,5,5,5,4,4,3,3,3,2,2,2,1,1,0

;===================================================================================================
; Банк памяти #81: rotation_lut
;===================================================================================================
rotation_lut81 db 0,1,2,2,3,4,5,6,7,7,8,9,10,11,12,12,13,14,15,16,17,17,18,19,20,21,22,22,23,24,25,26,229,230,231,232,233,234,234,235,236,237,238,239,239,240,241,242,243,244,244,245,246,247,248,249,249,250,251,252,253,254,254,255,0,255,255,254,254,253,253,252,252,251,250,250,249,249,248,248,247,247,246,245,245,244,244,243,243,242,242,241,240,240,239,239,18,17,17,16,16,15,14,14,13,13,12,12,11,11,10,9,9,8,8,7,7,6,6,5,4,4,3,3,2,2,1,1

;===================================================================================================
; Банк памяти #82: rotation_lut
;===================================================================================================
rotation_lut82 db 0,1,1,2,3,4,4,5,6,6,7,8,8,9,10,11,11,12,13,13,14,15,16,16,17,18,18,19,20,21,21,22,233,234,235,235,236,237,238,238,239,240,240,241,242,243,243,244,245,245,246,247,248,248,249,250,250,251,252,252,253,254,255,255,0,255,255,254,253,252,252,251,250,250,249,248,248,247,246,245,245,244,243,243,242,241,240,240,239,238,238,237,236,235,235,234,23,22,21,21,20,19,18,18,17,16,16,15,14,13,13,12,11,11,10,9,8,8,7,6,6,5,4,4,3,2,1,1

;===================================================================================================
; Банк памяти #83: rotation_lut
;===================================================================================================
rotation_lut83 db 0,1,1,2,2,3,3,4,4,5,6,6,7,7,8,8,9,9,10,11,11,12,12,13,13,14,14,15,16,16,17,17,238,239,239,240,240,241,242,242,243,243,244,244,245,245,246,247,247,248,248,249,249,250,250,251,252,252,253,253,254,254,255,255,0,255,254,254,253,252,251,250,249,249,248,247,246,245,244,244,243,242,241,240,239,239,238,237,236,235,234,234,233,232,231,230,27,26,25,24,23,22,22,21,20,19,18,17,17,16,15,14,13,12,12,11,10,9,8,7,7,6,5,4,3,2,2,1

;===================================================================================================
; Банк памяти #84: rotation_lut
;===================================================================================================
rotation_lut84 db 0,0,1,1,2,2,2,3,3,3,4,4,5,5,5,6,6,7,7,7,8,8,8,9,9,10,10,10,11,11,11,12,244,244,245,245,245,246,246,246,247,247,248,248,248,249,249,249,250,250,251,251,251,252,252,253,253,253,254,254,254,255,255,0,0,255,254,253,252,251,250,250,249,248,247,246,245,244,243,242,241,240,239,238,238,237,236,235,234,233,232,231,230,229,228,227,30,29,28,27,26,25,24,23,22,21,20,19,18,18,17,16,15,14,13,12,11,10,9,8,7,6,6,5,4,3,2,1

;===================================================================================================
; Банк памяти #85: rotation_lut
;===================================================================================================
rotation_lut85 db 0,0,0,1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,6,6,6,250,250,250,250,251,251,251,251,251,252,252,252,252,252,252,253,253,253,253,253,254,254,254,254,254,255,255,255,255,255,0,0,0,255,254,253,252,251,250,249,248,247,246,245,244,243,242,241,240,239,238,237,236,235,234,233,232,231,230,230,229,228,227,226,31,30,29,28,27,26,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1

;===================================================================================================
; Банк памяти #86: rotation_lut
;===================================================================================================
rotation_lut86 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,255,254,253,252,251,250,249,248,247,246,245,244,243,242,241,240,239,238,237,236,235,234,233,232,231,230,229,228,227,226,225,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1

;===================================================================================================
; Банк памяти #87: rotation_lut
;===================================================================================================
rotation_lut87 db 0,0,0,255,255,255,255,255,254,254,254,254,254,253,253,253,253,253,252,252,252,252,252,252,251,251,251,251,251,250,250,250,6,6,6,6,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,3,2,2,2,2,2,1,1,1,1,1,0,0,0,255,254,253,252,251,250,249,248,247,246,245,244,243,242,241,240,239,238,237,236,235,234,233,232,231,230,230,229,228,227,226,31,30,29,28,27,26,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1

;===================================================================================================
; Банк памяти #88: rotation_lut
;===================================================================================================
rotation_lut88 db 0,0,255,255,254,254,254,253,253,253,252,252,251,251,251,250,250,249,249,249,248,248,248,247,247,246,246,246,245,245,245,244,12,12,11,11,11,10,10,10,9,9,8,8,8,7,7,7,6,6,5,5,5,4,4,3,3,3,2,2,2,1,1,0,0,255,254,253,252,251,250,250,249,248,247,246,245,244,243,242,241,240,239,238,238,237,236,235,234,233,232,231,230,229,228,227,30,29,28,27,26,25,24,23,22,21,20,19,18,18,17,16,15,14,13,12,11,10,9,8,7,6,6,5,4,3,2,1

;===================================================================================================
; Банк памяти #89: rotation_lut
;===================================================================================================
rotation_lut89 db 0,255,255,254,254,253,253,252,252,251,250,250,249,249,248,248,247,247,246,245,245,244,244,243,243,242,242,241,240,240,239,239,18,17,17,16,16,15,14,14,13,13,12,12,11,11,10,9,9,8,8,7,7,6,6,5,4,4,3,3,2,2,1,1,0,255,254,254,253,252,251,250,249,249,248,247,246,245,244,244,243,242,241,240,239,239,238,237,236,235,234,234,233,232,231,230,27,26,25,24,23,22,22,21,20,19,18,17,17,16,15,14,13,12,12,11,10,9,8,7,7,6,5,4,3,2,2,1

;===================================================================================================
; Банк памяти #90: rotation_lut
;===================================================================================================
rotation_lut90 db 0,255,255,254,253,252,252,251,250,250,249,248,248,247,246,245,245,244,243,243,242,241,240,240,239,238,238,237,236,235,235,234,23,22,21,21,20,19,18,18,17,16,16,15,14,13,13,12,11,11,10,9,8,8,7,6,6,5,4,4,3,2,1,1,0,255,255,254,253,252,252,251,250,250,249,248,248,247,246,245,245,244,243,243,242,241,240,240,239,238,238,237,236,235,235,234,23,22,21,21,20,19,18,18,17,16,16,15,14,13,13,12,11,11,10,9,8,8,7,6,6,5,4,4,3,2,1,1

;===================================================================================================
; Банк памяти #91: rotation_lut
;===================================================================================================
rotation_lut91 db 0,255,254,254,253,252,251,250,249,249,248,247,246,245,244,244,243,242,241,240,239,239,238,237,236,235,234,234,233,232,231,230,27,26,25,24,23,22,22,21,20,19,18,17,17,16,15,14,13,12,12,11,10,9,8,7,7,6,5,4,3,2,2,1,0,255,255,254,254,253,253,252,252,251,250,250,249,249,248,248,247,247,246,245,245,244,244,243,243,242,242,241,240,240,239,239,18,17,17,16,16,15,14,14,13,13,12,12,11,11,10,9,9,8,8,7,7,6,6,5,4,4,3,3,2,2,1,1

;===================================================================================================
; Банк памяти #92: rotation_lut
;===================================================================================================
rotation_lut92 db 0,255,254,253,252,251,250,250,249,248,247,246,245,244,243,242,241,240,239,238,238,237,236,235,234,233,232,231,230,229,228,227,30,29,28,27,26,25,24,23,22,21,20,19,18,18,17,16,15,14,13,12,11,10,9,8,7,6,6,5,4,3,2,1,0,0,255,255,254,254,254,253,253,253,252,252,251,251,251,250,250,249,249,249,248,248,248,247,247,246,246,246,245,245,245,244,12,12,11,11,11,10,10,10,9,9,8,8,8,7,7,7,6,6,5,5,5,4,4,3,3,3,2,2,2,1,1,0

;===================================================================================================
; Банк памяти #93: rotation_lut
;===================================================================================================
rotation_lut93 db 0,255,254,253,252,251,250,249,248,247,246,245,244,243,242,241,240,239,238,237,236,235,234,233,232,231,230,230,229,228,227,226,31,30,29,28,27,26,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0,0,0,255,255,255,255,255,254,254,254,254,254,253,253,253,253,253,252,252,252,252,252,252,251,251,251,251,251,250,250,250,6,6,6,6,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,3,2,2,2,2,2,1,1,1,1,1,0,0

;===================================================================================================
; Банк памяти #94: rotation_lut
;===================================================================================================
rotation_lut94 db 0,255,254,253,252,251,250,249,248,247,246,245,244,243,242,241,240,239,238,237,236,235,234,233,232,231,230,229,228,227,226,225,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

;===================================================================================================
; Банк памяти #95: rotation_lut
;===================================================================================================
rotation_lut95 db 0,255,254,253,252,251,250,249,248,247,246,245,244,243,242,241,240,239,238,237,236,235,234,233,232,231,230,230,229,228,227,226,31,30,29,28,27,26,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0,0,0,1,1,1,1,1,2,2,2,2,2,3,3,3,3,3,4,4,4,4,4,4,5,5,5,5,5,6,6,6,250,250,250,250,251,251,251,251,251,252,252,252,252,252,252,253,253,253,253,253,254,254,254,254,254,255,255,255,255,255,0,0

;===================================================================================================
; Банк памяти #96: rotation_lut
;===================================================================================================
rotation_lut96 db 0,255,254,253,252,251,250,250,249,248,247,246,245,244,243,242,241,240,239,238,238,237,236,235,234,233,232,231,230,229,228,227,30,29,28,27,26,25,24,23,22,21,20,19,18,18,17,16,15,14,13,12,11,10,9,8,7,6,6,5,4,3,2,1,0,0,1,1,2,2,2,3,3,3,4,4,5,5,5,6,6,7,7,7,8,8,8,9,9,10,10,10,11,11,11,12,244,244,245,245,245,246,246,246,247,247,248,248,248,249,249,249,250,250,251,251,251,252,252,253,253,253,254,254,254,255,255,0

;===================================================================================================
; Банк памяти #97: rotation_lut
;===================================================================================================
rotation_lut97 db 0,255,254,254,253,252,251,250,249,249,248,247,246,245,244,244,243,242,241,240,239,239,238,237,236,235,234,234,233,232,231,230,27,26,25,24,23,22,22,21,20,19,18,17,17,16,15,14,13,12,12,11,10,9,8,7,7,6,5,4,3,2,2,1,0,1,1,2,2,3,3,4,4,5,6,6,7,7,8,8,9,9,10,11,11,12,12,13,13,14,14,15,16,16,17,17,238,239,239,240,240,241,242,242,243,243,244,244,245,245,246,247,247,248,248,249,249,250,250,251,252,252,253,253,254,254,255,255

;===================================================================================================
; Банк памяти #98: rotation_lut
;===================================================================================================
rotation_lut98 db 0,255,255,254,253,252,252,251,250,250,249,248,248,247,246,245,245,244,243,243,242,241,240,240,239,238,238,237,236,235,235,234,23,22,21,21,20,19,18,18,17,16,16,15,14,13,13,12,11,11,10,9,8,8,7,6,6,5,4,4,3,2,1,1,0,1,1,2,3,4,4,5,6,6,7,8,8,9,10,11,11,12,13,13,14,15,16,16,17,18,18,19,20,21,21,22,233,234,235,235,236,237,238,238,239,240,240,241,242,243,243,244,245,245,246,247,248,248,249,250,250,251,252,252,253,254,255,255

;===================================================================================================
; Банк памяти #99: rotation_lut
;===================================================================================================
rotation_lut99 db 0,255,255,254,254,253,253,252,252,251,250,250,249,249,248,248,247,247,246,245,245,244,244,243,243,242,242,241,240,240,239,239,18,17,17,16,16,15,14,14,13,13,12,12,11,11,10,9,9,8,8,7,7,6,6,5,4,4,3,3,2,2,1,1,0,1,2,2,3,4,5,6,7,7,8,9,10,11,12,12,13,14,15,16,17,17,18,19,20,21,22,22,23,24,25,26,229,230,231,232,233,234,234,235,236,237,238,239,239,240,241,242,243,244,244,245,246,247,248,249,249,250,251,252,253,254,254,255

;===================================================================================================
; Банк памяти #100: rotation_lut
;===================================================================================================
rotation_lut100 db 0,0,255,255,254,254,254,253,253,253,252,252,251,251,251,250,250,249,249,249,248,248,248,247,247,246,246,246,245,245,245,244,12,12,11,11,11,10,10,10,9,9,8,8,8,7,7,7,6,6,5,5,5,4,4,3,3,3,2,2,2,1,1,0,0,1,2,3,4,5,6,6,7,8,9,10,11,12,13,14,15,16,17,18,18,19,20,21,22,23,24,25,26,27,28,29,226,227,228,229,230,231,232,233,234,235,236,237,238,238,239,240,241,242,243,244,245,246,247,248,249,250,250,251,252,253,254,255

;===================================================================================================
; Банк памяти #101: rotation_lut
;===================================================================================================
rotation_lut101 db 0,0,0,255,255,255,255,255,254,254,254,254,254,253,253,253,253,253,252,252,252,252,252,252,251,251,251,251,251,250,250,250,6,6,6,6,5,5,5,5,5,4,4,4,4,4,4,3,3,3,3,3,2,2,2,2,2,1,1,1,1,1,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,26,27,28,29,30,225,226,227,228,229,230,230,231,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255

;===================================================================================================
; Банк памяти #102: projection_lut
;===================================================================================================
projection_lut102 db 8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,62,64,66,68,70,200,202,204,206,208,210,212,214,216,218,220,222,224,226,228,230,232,234,236,238,240,242,244,246,248,250,252,254,0,2,4,6,8,10,12,13,15,17,19,20,22,24,26,28,29,31,33,35,36,38,40,42,44,45,47,49,51,52,54,56,58,60,61,63,207,209,211,212,214,216,218,220,221,223,225,227,228,230,232,234,236,237,239,241,243,244,246,248,250,252,253,255,1,3,4,6

;===================================================================================================
; Банк памяти #103: projection_lut
;===================================================================================================
projection_lut103 db 8,10,11,13,14,16,18,19,21,22,24,26,27,29,30,32,34,35,37,38,40,42,43,45,46,48,50,51,53,54,56,58,213,214,216,218,219,221,222,224,226,227,229,230,232,234,235,237,238,240,242,243,245,246,248,250,251,253,254,0,2,3,5,6,8,9,11,12,14,15,17,18,20,21,23,24,25,27,28,30,31,33,34,36,37,39,40,41,43,44,46,47,49,50,52,53,217,219,220,222,223,225,226,228,229,231,232,233,235,236,238,239,241,242,244,245,247,248,249,251,252,254,255,1,2,4,5,7

;===================================================================================================
; Банк памяти #104: projection_lut
;===================================================================================================
projection_lut104 db 8,9,11,12,13,15,16,17,19,20,21,23,24,25,27,28,29,31,32,33,35,36,37,39,40,41,43,44,45,47,48,49,221,223,224,225,227,228,229,231,232,233,235,236,237,239,240,241,243,244,245,247,248,249,251,252,253,255,0,1,3,4,5,7,8,9,10,12,13,14,15,17,18,19,20,22,23,24,25,26,28,29,30,31,33,34,35,36,38,39,40,41,42,44,45,46,225,226,227,228,230,231,232,233,234,236,237,238,239,241,242,243,244,246,247,248,249,250,252,253,254,255,1,2,3,4,6,7

;===================================================================================================
; Банк памяти #105: projection_lut
;===================================================================================================
projection_lut105 db 8,9,10,11,13,14,15,16,17,18,19,21,22,23,24,25,26,27,29,30,31,32,33,34,35,37,38,39,40,41,42,43,227,229,230,231,232,233,234,235,237,238,239,240,241,242,243,245,246,247,248,249,250,251,253,254,255,0,1,2,3,5,6,7,8,9,10,11,12,13,14,15,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,33,34,35,36,37,38,39,40,41,230,231,232,233,234,235,236,237,238,239,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255,1,2,3,4,5,6,7

;===================================================================================================
; Банк памяти #106: projection_lut
;===================================================================================================
projection_lut106 db 8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,232,233,234,235,236,237,238,239,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,32,33,34,35,36,37,234,235,236,237,238,239,240,240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255,0,0,1,2,3,4,5,6,7

;===================================================================================================
; Банк памяти #107: projection_lut
;===================================================================================================
projection_lut107 db 8,9,10,11,12,12,13,14,15,16,17,18,19,20,20,21,22,23,24,25,26,27,28,28,29,30,31,32,33,34,35,36,236,236,237,238,239,240,241,242,243,244,244,245,246,247,248,249,250,251,252,252,253,254,255,0,1,2,3,4,4,5,6,7,8,9,10,11,11,12,13,14,15,16,16,17,18,19,20,21,21,22,23,24,25,26,27,27,28,29,30,31,32,32,33,34,237,238,239,240,240,241,242,243,244,245,245,246,247,248,249,250,251,251,252,253,254,255,0,0,1,2,3,4,5,5,6,7

;===================================================================================================
; Банк памяти #108: projection_lut
;===================================================================================================
projection_lut108 db 8,9,10,10,11,12,13,14,14,15,16,17,18,18,19,20,21,22,22,23,24,25,26,26,27,28,29,30,30,31,32,33,238,239,240,241,242,242,243,244,245,246,246,247,248,249,250,250,251,252,253,254,254,255,0,1,2,2,3,4,5,6,6,7,8,9,10,10,11,12,13,13,14,15,16,16,17,18,19,19,20,21,22,22,23,24,25,26,26,27,28,29,29,30,31,32,240,240,241,242,243,243,244,245,246,246,247,248,249,250,250,251,252,253,253,254,255,0,0,1,2,3,3,4,5,6,6,7

;===================================================================================================
; Банк памяти #109: projection_lut
;===================================================================================================
projection_lut109 db 8,9,9,10,11,12,12,13,14,15,15,16,17,17,18,19,20,20,21,22,23,23,24,25,25,26,27,28,28,29,30,31,241,241,242,243,244,244,245,246,247,247,248,249,249,250,251,252,252,253,254,255,255,0,1,1,2,3,4,4,5,6,7,7,8,9,9,10,11,11,12,13,14,14,15,16,16,17,18,18,19,20,21,21,22,23,23,24,25,25,26,27,27,28,29,30,242,242,243,244,245,245,246,247,247,248,249,249,250,251,251,252,253,254,254,255,0,0,1,2,2,3,4,5,5,6,7,7

;===================================================================================================
; Банк памяти #110: projection_lut
;===================================================================================================
projection_lut110 db 8,9,9,10,11,11,12,13,13,14,15,15,16,17,17,18,19,19,20,21,21,22,23,23,24,25,25,26,27,27,28,29,243,243,244,245,245,246,247,247,248,249,249,250,251,251,252,253,253,254,255,255,0,1,1,2,3,3,4,5,5,6,7,7,8,9,9,10,11,11,12,12,13,14,14,15,16,16,17,18,18,19,20,20,21,21,22,23,23,24,25,25,26,27,27,28,244,244,245,245,246,247,247,248,249,249,250,251,251,252,252,253,254,254,255,0,0,1,2,2,3,4,4,5,5,6,7,7

;===================================================================================================
; Банк памяти #111: projection_lut
;===================================================================================================
projection_lut111 db 8,9,9,10,10,11,12,12,13,14,14,15,15,16,17,17,18,18,19,20,20,21,22,22,23,23,24,25,25,26,26,27,244,245,246,246,247,247,248,249,249,250,250,251,252,252,253,254,254,255,255,0,1,1,2,2,3,4,4,5,6,6,7,7,8,9,9,10,10,11,12,12,13,13,14,15,15,16,16,17,17,18,19,19,20,20,21,22,22,23,23,24,25,25,26,26,245,246,246,247,247,248,249,249,250,250,251,252,252,253,253,254,255,255,0,0,1,1,2,3,3,4,4,5,6,6,7,7

;===================================================================================================
; Банк памяти #112: projection_lut
;===================================================================================================
projection_lut112 db 8,9,9,10,10,11,11,12,13,13,14,14,15,15,16,17,17,18,18,19,19,20,21,21,22,22,23,23,24,25,25,26,246,246,247,247,248,249,249,250,250,251,251,252,253,253,254,254,255,255,0,1,1,2,2,3,3,4,5,5,6,6,7,7,8,9,9,10,10,11,11,12,12,13,14,14,15,15,16,16,17,17,18,18,19,20,20,21,21,22,22,23,23,24,25,25,246,247,247,248,249,249,250,250,251,251,252,252,253,254,254,255,255,0,0,1,1,2,2,3,4,4,5,5,6,6,7,7

;===================================================================================================
; Банк памяти #113: projection_lut
;===================================================================================================
projection_lut113 db 8,9,9,10,10,11,11,12,12,13,13,14,14,15,15,16,17,17,18,18,19,19,20,20,21,21,22,22,23,23,24,25,247,247,248,249,249,250,250,251,251,252,252,253,253,254,254,255,255,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,9,9,10,10,11,11,12,12,13,13,14,14,15,15,16,16,17,17,18,18,19,19,20,20,21,21,22,22,23,23,24,247,248,249,249,250,250,251,251,252,252,253,253,254,254,255,255,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7

;===================================================================================================
; Банк памяти #114: projection_lut
;===================================================================================================
projection_lut114 db 8,8,9,10,10,10,11,12,12,12,13,14,14,14,15,16,16,16,17,18,18,18,19,20,20,20,21,22,22,22,23,24,248,248,249,250,250,250,251,252,252,252,253,254,254,254,255,0,0,0,1,2,2,2,3,4,4,4,5,6,6,6,7,8,8,8,9,9,10,10,11,11,12,12,13,13,14,14,15,15,16,16,17,17,18,18,19,19,20,20,21,21,22,22,23,23,248,249,249,250,250,251,251,252,252,253,253,254,254,255,255,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8

;===================================================================================================
; Банк памяти #115: projection_lut
;===================================================================================================
projection_lut115 db 8,8,9,9,10,10,11,11,12,12,13,13,14,14,15,15,16,16,16,17,17,18,18,19,19,20,20,21,21,22,22,23,249,249,250,250,251,251,252,252,253,253,254,254,255,255,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,8,9,9,10,10,11,11,12,12,13,13,13,14,14,15,15,16,16,17,17,18,18,19,19,19,20,20,21,21,22,22,249,250,250,251,251,252,252,253,253,253,254,254,255,255,0,0,1,1,2,2,3,3,3,4,4,5,5,6,6,7,7,8

;===================================================================================================
; Банк памяти #116: projection_lut
;===================================================================================================
projection_lut116 db 8,8,9,9,10,10,11,11,12,12,12,13,13,14,14,15,15,16,16,16,17,17,18,18,19,19,20,20,20,21,21,22,250,250,251,251,252,252,252,253,253,254,254,255,255,0,0,0,1,1,2,2,3,3,4,4,4,5,5,6,6,7,7,8,8,8,9,9,10,10,11,11,11,12,12,13,13,14,14,14,15,15,16,16,17,17,18,18,18,19,19,20,20,21,21,21,250,251,251,251,252,252,253,253,254,254,254,255,255,0,0,1,1,2,2,2,3,3,4,4,5,5,5,6,6,7,7,8

;===================================================================================================
; Банк памяти #117: projection_lut
;===================================================================================================
projection_lut117 db 8,8,9,9,10,10,11,11,11,12,12,13,13,13,14,14,15,15,16,16,16,17,17,18,18,19,19,19,20,20,21,21,251,251,251,252,252,253,253,253,254,254,255,255,0,0,0,1,1,2,2,3,3,3,4,4,5,5,5,6,6,7,7,8,8,8,9,9,10,10,10,11,11,12,12,13,13,13,14,14,15,15,15,16,16,17,17,17,18,18,19,19,19,20,20,21,251,251,252,252,253,253,253,254,254,255,255,255,0,0,1,1,1,2,2,3,3,3,4,4,5,5,6,6,6,7,7,8

;===================================================================================================
; Банк памяти #118: projection_lut
;===================================================================================================
projection_lut118 db 8,8,9,9,10,10,10,11,11,12,12,12,13,13,14,14,14,15,15,16,16,16,17,17,18,18,18,19,19,20,20,20,251,252,252,252,253,253,254,254,254,255,255,0,0,0,1,1,2,2,2,3,3,4,4,4,5,5,6,6,6,7,7,8,8,8,9,9,10,10,10,11,11,12,12,12,13,13,13,14,14,15,15,15,16,16,17,17,17,18,18,19,19,19,20,20,252,252,252,253,253,253,254,254,255,255,255,0,0,1,1,1,2,2,3,3,3,4,4,4,5,5,6,6,6,7,7,8

;===================================================================================================
; Банк памяти #119: projection_lut
;===================================================================================================
projection_lut119 db 8,8,9,9,10,10,10,11,11,11,12,12,13,13,13,14,14,14,15,15,16,16,16,17,17,18,18,18,19,19,19,20,252,252,253,253,253,254,254,254,255,255,0,0,0,1,1,2,2,2,3,3,3,4,4,5,5,5,6,6,6,7,7,8,8,8,9,9,9,10,10,11,11,11,12,12,12,13,13,14,14,14,15,15,15,16,16,17,17,17,18,18,18,19,19,20,252,252,253,253,254,254,254,255,255,255,0,0,1,1,1,2,2,2,3,3,4,4,4,5,5,5,6,6,7,7,7,8

;===================================================================================================
; Банк памяти #120: projection_lut
;===================================================================================================
projection_lut120 db 8,8,9,9,9,10,10,11,11,11,12,12,12,13,13,13,14,14,15,15,15,16,16,16,17,17,17,18,18,19,19,19,252,253,253,253,254,254,255,255,255,0,0,0,1,1,1,2,2,3,3,3,4,4,4,5,5,5,6,6,7,7,7,8,8,8,9,9,9,10,10,10,11,11,12,12,12,13,13,13,14,14,14,15,15,15,16,16,17,17,17,18,18,18,19,19,253,253,253,254,254,254,255,255,255,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,6,6,6,7,7,7,8

;===================================================================================================
; Банк памяти #121: projection_lut
;===================================================================================================
projection_lut121 db 8,8,9,9,9,10,10,10,11,11,11,12,12,13,13,13,14,14,14,15,15,15,16,16,16,17,17,17,18,18,18,19,253,253,254,254,254,255,255,255,0,0,0,1,1,1,2,2,2,3,3,3,4,4,5,5,5,6,6,6,7,7,7,8,8,8,9,9,9,10,10,10,11,11,11,12,12,12,13,13,13,14,14,14,15,15,15,16,16,17,17,17,18,18,18,19,253,253,254,254,254,255,255,255,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7,7,8

;===================================================================================================
; Банк памяти #122: projection_lut
;===================================================================================================
projection_lut122 db 8,8,9,9,9,10,10,10,11,11,11,12,12,12,13,13,13,14,14,14,15,15,15,16,16,16,17,17,17,18,18,18,253,254,254,254,255,255,255,0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7,7,8,8,8,9,9,9,10,10,10,11,11,11,12,12,12,13,13,13,14,14,14,15,15,15,16,16,16,16,17,17,17,18,18,254,254,254,255,255,255,0,0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7,7,8

;===================================================================================================
; Банк памяти #123: projection_lut
;===================================================================================================
projection_lut123 db 8,8,9,9,9,10,10,10,11,11,11,12,12,12,12,13,13,13,14,14,14,15,15,15,16,16,16,17,17,17,18,18,254,254,254,255,255,255,0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,4,5,5,5,6,6,6,7,7,7,8,8,8,9,9,9,10,10,10,11,11,11,11,12,12,12,13,13,13,14,14,14,15,15,15,16,16,16,16,17,17,17,18,254,254,255,255,255,0,0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,5,6,6,6,7,7,7,8

;===================================================================================================
; Банк памяти #124: projection_lut
;===================================================================================================
projection_lut124 db 8,8,9,9,9,10,10,10,10,11,11,11,12,12,12,13,13,13,14,14,14,14,15,15,15,16,16,16,17,17,17,18,254,254,255,255,255,0,0,0,1,1,1,2,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,6,7,7,7,8,8,8,9,9,9,10,10,10,10,11,11,11,12,12,12,13,13,13,13,14,14,14,15,15,15,16,16,16,16,17,17,17,254,255,255,255,0,0,0,0,1,1,1,2,2,2,3,3,3,3,4,4,4,5,5,5,6,6,6,6,7,7,7,8

;===================================================================================================
; Банк памяти #125: projection_lut
;===================================================================================================
projection_lut125 db 8,8,9,9,9,9,10,10,10,11,11,11,12,12,12,12,13,13,13,14,14,14,15,15,15,15,16,16,16,17,17,17,255,255,255,255,0,0,0,1,1,1,1,2,2,2,3,3,3,4,4,4,4,5,5,5,6,6,6,7,7,7,7,8,8,8,9,9,9,9,10,10,10,11,11,11,11,12,12,12,13,13,13,14,14,14,14,15,15,15,16,16,16,16,17,17,255,255,255,0,0,0,0,1,1,1,2,2,2,2,3,3,3,4,4,4,5,5,5,5,6,6,6,7,7,7,7,8

;===================================================================================================
; Банк памяти #126: projection_lut
;===================================================================================================
projection_lut126 db 8,8,9,9,9,9,10,10,10,11,11,11,11,12,12,12,13,13,13,13,14,14,14,15,15,15,15,16,16,16,17,17,255,255,255,0,0,0,1,1,1,1,2,2,2,3,3,3,3,4,4,4,5,5,5,5,6,6,6,7,7,7,7,8,8,8,9,9,9,9,10,10,10,11,11,11,11,12,12,12,12,13,13,13,14,14,14,14,15,15,15,16,16,16,16,17,255,255,0,0,0,0,1,1,1,2,2,2,2,3,3,3,4,4,4,4,5,5,5,5,6,6,6,7,7,7,7,8

;===================================================================================================
; Банк памяти #127: projection_lut
;===================================================================================================
projection_lut127 db 8,8,9,9,9,9,10,10,10,10,11,11,11,12,12,12,12,13,13,13,14,14,14,14,15,15,15,15,16,16,16,17,255,255,0,0,0,1,1,1,1,2,2,2,2,3,3,3,4,4,4,4,5,5,5,6,6,6,6,7,7,7,7,8,8,8,9,9,9,9,10,10,10,10,11,11,11,12,12,12,12,13,13,13,13,14,14,14,15,15,15,15,16,16,16,16,255,0,0,0,0,1,1,1,1,2,2,2,3,3,3,3,4,4,4,4,5,5,5,6,6,6,6,7,7,7,7,8

;===================================================================================================
; Банк памяти #128: projection_lut
;===================================================================================================
projection_lut128 db 8,8,9,9,9,9,10,10,10,10,11,11,11,11,12,12,12,13,13,13,13,14,14,14,14,15,15,15,15,16,16,16,255,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,8,8,8,9,9,9,9,10,10,10,10,11,11,11,11,12,12,12,12,13,13,13,14,14,14,14,15,15,15,15,16,16,16,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,8

;===================================================================================================
; Банк памяти #129: projection_lut
;===================================================================================================
projection_lut129 db 8,8,9,9,9,9,10,10,10,10,11,11,11,11,12,12,12,12,13,13,13,13,14,14,14,14,15,15,15,15,16,16,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,8,8,8,9,9,9,9,10,10,10,10,11,11,11,11,12,12,12,12,13,13,13,13,14,14,14,14,15,15,15,15,16,16,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,8
