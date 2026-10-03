; 3DViewer — клавиатурный куб для Computer v2, не более 1024 байт.
; Стрелки: yaw/pitch; + или =: больше; -: меньше; Del: удалить; пробел: вернуть куб.

yaw equ 7
pitch equ 8
scale equ 9
syaw equ 10
cyaw equ 11
spitch equ 12
bxx equ 13
bxz equ 14
byx equ 15
byy equ 16
byz equ 17
vertex equ 18
pxsum equ 19
pysum equ 20
rx equ 21
ep equ 22
base equ 23
x0 equ 24
y0 equ 25
x1 equ 26
y1 equ 27
dx equ 28
dy equ 29
sy equ 30
err equ 31
e2 equ 32
ret_bank equ 33
ret_addr equ 34
scale_sign equ 35
model_deleted equ 60
masks equ 36
points equ 44

start: ldi c, 1
ldi d, frame_start
set_bank: st c, 63
jmp d
globals db 4,3,10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
pixel_masks db 128,64,32,16,8,4,2,1
vertex_cache db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
common_spare db 0,0
ports db 0,0
screen db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

; Банк #1
; Сохранить прежний экран; очистить LCD RAM и получить sin/cos двух углов.
frame_start:
clr a
st a, 62
ldi b, 64
ldi c, 64
clear_loop:
st a, b
inc b
dec c
jnz clear_loop
ld b, yaw
ldi c, sine
add b, c
ld a, b
st a, syaw
shl a
shl a
shl a
st a, bxz
ldi a, 8
add b, a
ld a, b
st a, cyaw
shl a
shl a
shl a
st a, bxx
ld b, pitch
ldi c, sine
add b, c
ld a, b
st a, spitch
ldi a, 8
add b, a
ld a, b
shl a
shl a
shl a
st a, byy
ldi c, 6
ldi d, basis_y
jmp set_bank
; 32 коэффициента Q3 и 8 повторов для cos без дополнительного обёртывания.
sine db 0,2,3,4,6,7,7,8,8,8,7,7,6,4,3,2,0,254,253,252,250,249,249,248,248,248,249,249,250,252,253,254,0,2,3,4,6,7,7,8
; После удаления игнорировать управление; пробел восстанавливает исходный куб.
no_model:
ldi b, 32
xor a, b
jnz resume_no_model_2
ldi c, 5
ldi d, reset_model
jmp set_bank
resume_no_model_2:
ldi c, 5
ldi d, key_loop
jmp set_bank
padding1 db 0,0,0,0,0,0,0,0,0,0,0,0

; Банк #2
; Три бита номера вершины выбирают знаки X/Y/Z; каждую вершину вычислить один раз.
vertex_begin:
ld a, bxx
ld b, byx
ld c, vertex
shr c
jc x_positive
neg a
neg b
x_positive:
st a, pxsum
st b, pysum
ld a, byy
shr c
jc y_positive
neg a
y_positive:
ld b, pysum
add b, a
st b, pysum
ld a, bxz
ld b, byz
shr c
jc z_positive
neg a
neg b
z_positive:
ld c, pysum
add b, c
st b, pysum
ld c, pxsum
add a, c
ldi c, 2
st c, ret_bank
ldi d, resume_vertex_begin_30
st d, ret_addr
ldi c, 6
ldi d, project_coordinate
jmp set_bank
resume_vertex_begin_30:
st a, rx
ld a, pysum
ldi c, 2
st c, ret_bank
ldi d, resume_vertex_begin_33
st d, ret_addr
ldi c, 6
ldi d, project_coordinate
jmp set_bank
resume_vertex_begin_33:
ldi c, 3
ldi d, vertex_store
jmp set_bank
; scale=5…30: шаг ×0,2 с ограничением на ×3; базовая половина стороны 2,5 пикселя.
scale_up:
ld a, scale
ldi b, 30
mov c, a
sub c, b
jnz resume_scale_up_4
ldi c, 5
ldi d, key_loop
jmp set_bank
resume_scale_up_4:
inc a
mov c, a
sub c, b
jz scale_up_store
inc a
scale_up_store:
st a, scale
ldi c, 1
ldi d, frame_start
jmp set_bank
padding2 db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0

; Банк #3
; Сохранить XY в общей памяти; после восьми вершин начать обход 12 рёбер.
vertex_store:
ld b, vertex
shl b
ldi c, points
add b, c
ld c, rx
st c, b
inc b
st a, b
ld a, vertex
inc a
st a, vertex
ldi b, 8
xor a, b
jz resume_vertex_store_13
ldi c, 2
ldi d, vertex_begin
jmp set_bank
resume_vertex_store_13:
ldi a, edges
st a, ep
ldi a, 64
st a, base
ldi c, 7
ldi d, edge_begin
jmp set_bank
; Брезенхэм: знаковые XY могут выходить за экран; упорядочить концы по X и вычислить ошибку.
line_start:
ld a, x1
ld b, x0
sub a, b
jns x_forward
neg a
ld c, x0
ld d, x1
st d, x0
st c, x1
ld c, y0
ld d, y1
st d, y0
st c, y1
x_forward:
st a, dx
ld a, y1
ld b, y0
sub a, b
ldi b, 1
jns y_forward
neg a
neg b
y_forward:
st a, dy
st b, sy
ld a, dx
ld b, dy
sub a, b
st a, err
ldi c, 4
ldi d, line_loop
jmp set_bank
; Del (0x7F): убрать модель из сцены и опубликовать пустой цветной кадр.
delete_model:
ldi a, 1
st a, model_deleted
clr a
st a, 62
ldi b, 64
ldi c, 64
delete_clear_loop:
st a, b
inc b
dec c
jnz delete_clear_loop
ldi c, 4
ldi d, frame_ready
jmp set_bank
padding3 db 0,0,0,0,0,0,0,0,0,0,0

; Банк #4
; Рисовать только пиксели 0…15 по обеим осям; идти по всему ребру без подгонки масштаба.
line_loop:
ld a, x0
ldi b, 16
sub a, b
jnc skip_pixel
ld a, y0
ldi b, 16
sub a, b
jnc skip_pixel
ld a, x0
mov b, a
shr a
shr a
shr a
ld c, y0
shl c
add c, a
ld a, base
add c, a
mov a, b
ldi d, 7
and a, d
ldi d, masks
add a, d
ld a, a
ld b, c
or a, b
line_pixel_store:
st a, c
skip_pixel:
ld a, x0
ld b, x1
xor a, b
jnz line_step
ld a, y0
ld b, y1
xor a, b
jnz resume_line_loop_36
ldi c, 7
ldi d, edge_done
jmp set_bank
resume_line_loop_36:
line_step:
ld a, err
shl a
st a, e2
ld b, dy
neg b
sub a, b
js skip_x
ld a, err
ld b, dy
sub a, b
st a, err
ld a, x0
inc a
st a, x0
skip_x:
ld a, dx
ld b, e2
sub a, b
js line_loop
ld a, err
ld b, dx
add a, b
st a, err
ld a, y0
ld b, sy
add a, b
st a, y0
jmp line_loop
; Включить дисплей и опубликовать LCD RAM; ждать клавишу без автоматической анимации.
frame_ready:
ldi a, 48
st a, 62
ldi b, 64
ldi c, 64
publish_loop:
ld a, b
st a, b
inc b
dec c
jnz publish_loop
frame_presented:
ldi c, 5
ldi d, key_loop
jmp set_bank
padding4 db 0,0,0,0

; Банк #5
; 0x11/12/13/14: чётный индекс — yaw, нечётный — pitch; один шаг равен 11,25°.
key_loop:
ld a, 62
test a
jz key_loop
mov d, a
ld b, model_deleted
test b
jz resume_key_loop_6
ldi c, 1
ldi d, no_model
jmp set_bank
resume_key_loop_6:
ldi b, 17
sub a, b
jc other_keys
mov c, a
ldi b, 4
sub c, b
jnc other_keys
ldi b, yaw
shr a
jnc axis_selected
inc b
axis_selected:
ld c, b
shr a
jc rotate_positive
dec c
jmp rotation_store
rotate_positive:
inc c
rotation_store:
ldi d, 31
and c, d
st c, b
ldi c, 1
ldi d, frame_start
jmp set_bank
; Del удаляет модель; плюс/равно и минус меняют масштаб; пробел возвращает куб.
other_keys:
mov a, d
ldi b, 127
xor a, b
jnz resume_other_keys_3
ldi c, 3
ldi d, delete_model
jmp set_bank
resume_other_keys_3:
mov a, d
ldi b, 43
xor a, b
jnz resume_other_keys_7
ldi c, 2
ldi d, scale_up
jmp set_bank
resume_other_keys_7:
mov a, d
ldi b, 61
xor a, b
jnz resume_other_keys_11
ldi c, 2
ldi d, scale_up
jmp set_bank
resume_other_keys_11:
mov a, d
ldi b, 45
xor a, b
jnz resume_other_keys_15
ldi c, 6
ldi d, scale_down
jmp set_bank
resume_other_keys_15:
mov a, d
ldi b, 32
xor a, b
jnz key_loop
reset_model:
clr a
st a, model_deleted
ldi a, 4
st a, yaw
ldi a, 3
st a, pitch
ldi a, 10
st a, scale
ldi c, 1
ldi d, frame_start
jmp set_bank
padding5 db 0

; Банк #6
; Проекция базиса куба: Y = -sin(yaw)*sin(pitch)*X + cos(pitch)*Y + cos(yaw)*sin(pitch)*Z.
basis_y:
ld a, syaw
ld b, spitch
ldi c, 6
st c, ret_bank
ldi d, resume_basis_y_2
st d, ret_addr
jmp multiply
resume_basis_y_2:
neg a
st a, byx
ld a, cyaw
ld b, spitch
ldi c, 6
st c, ret_bank
ldi d, resume_basis_y_7
st d, ret_addr
jmp multiply
resume_basis_y_7:
st a, byz
clr a
st a, vertex
ldi c, 2
ldi d, vertex_begin
jmp set_bank
; Знаковое произведение двух коэффициентов -8…8; результат помещается в байт.
multiply:
mov d, a
clr a
test d
jz multiply_done
jns multiply_loop
neg d
neg b
multiply_loop:
add a, b
dec d
jnz multiply_loop
multiply_done:
ld c, ret_bank
ld d, ret_addr
jmp set_bank
; 16-битное произведение коэффициента на scale; деление на 256 и центр +8. scale=10 — ×1.
project_coordinate:
st a, scale_sign
mov b, a
test b
jns scale_absolute
neg b
scale_absolute:
ld d, scale
clr a
clr c
scale_loop:
add a, b
jnc scale_no_carry
inc c
scale_no_carry:
dec d
jnz scale_loop
ld b, scale_sign
test b
jns scale_finish
not c
neg a
jc scale_finish
inc c
scale_finish:
mov a, c
ldi b, 8
add a, b
ld c, ret_bank
ld d, ret_addr
jmp set_bank
; Уменьшать на ×0,2; последний шаг доводит до ×0,5, дальнейший минус игнорируется.
scale_down:
ld a, scale
ldi b, 5
mov c, a
sub c, b
jnz resume_scale_down_4
ldi c, 5
ldi d, key_loop
jmp set_bank
resume_scale_down_4:
dec a
mov c, a
sub c, b
jz scale_down_store
dec a
scale_down_store:
st a, scale
ldi c, 1
ldi d, frame_start
jmp set_bank
padding6 db 0

; Банк #7
; Взять две готовые вершины; чередовать синий и красный слой для соседних рёбер.
edge_begin:
ld b, ep
ld a, b
shl a
ldi c, points
add a, c
mov c, a
ld a, c
st a, x0
inc c
ld a, c
st a, y0
inc b
ld a, b
shl a
ldi c, points
add a, c
mov c, a
ld a, c
st a, x1
inc c
ld a, c
st a, y1
inc b
st b, ep
ld a, base
ldi b, 32
xor a, b
st a, base
ldi c, 3
ldi d, line_start
jmp set_bank
; Следующее ребро; после 12 рёбер вывести готовый кадр.
edge_done:
ld a, ep
ldi b, edges_end
xor a, b
jnz edge_begin
ldi c, 4
ldi d, frame_ready
jmp set_bank
; 12 рёбер куба: соседние вершины отличаются одним битом.
edges db 0,1,2,3,4,5,6,7,0,2,1,3,4,6,5,7,0,4,1,5,2,6,3,7
edges_end:
