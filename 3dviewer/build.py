"""Build 3DViewer: an interactive cube for the 1 KB Computer v2."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SINE = [round(8 * math.sin(i * math.tau / 32)) for i in range(32)]
EDGES = [(i, i ^ bit) for bit in (1, 2, 4) for i in range(8) if not i & bit]
VARIABLES = "yaw pitch scale syaw cyaw spitch bxx bxz byx byy byz vertex pxsum pysum rx ep base x0 y0 x1 y1 dx dy sy err e2 ret_bank ret_addr scale_sign".split()
BLOCKS = []


def block(bank, name, code, comment):
    BLOCKS.append((bank, name, code.strip().splitlines(), comment))


block(1, "frame_start", """
clr a
st a, 62
ldi b, 64
ldi c, 64
clear_loop:
st a, b
inc b
dec c
IF nz clear_loop
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
GO basis_y
""", "Сохранить прежний экран; очистить LCD RAM и получить sin/cos двух углов.")
block(1, "sine", ["db " + ",".join(str(v & 255) for v in SINE + SINE[:8])][0],
      "32 коэффициента Q3 и 8 повторов для cos без дополнительного обёртывания.")

block(6, "basis_y", """
ld a, syaw
ld b, spitch
CALL multiply
neg a
st a, byx
ld a, cyaw
ld b, spitch
CALL multiply
st a, byz
clr a
st a, vertex
GO vertex_begin
""", "Проекция базиса куба: Y = -sin(yaw)*sin(pitch)*X + cos(pitch)*Y + cos(yaw)*sin(pitch)*Z.")
block(6, "multiply", """
mov d, a
clr a
test d
IF z multiply_done
IF ns multiply_loop
neg d
neg b
multiply_loop:
add a, b
dec d
IF nz multiply_loop
multiply_done:
RETURN
""", "Знаковое произведение двух коэффициентов -8…8; результат помещается в байт.")
block(6, "project_coordinate", """
st a, scale_sign
mov b, a
test b
IF ns scale_absolute
neg b
scale_absolute:
ld d, scale
clr a
clr c
scale_loop:
add a, b
IF nc scale_no_carry
inc c
scale_no_carry:
dec d
IF nz scale_loop
ld b, scale_sign
test b
IF ns scale_finish
not c
neg a
IF c scale_finish
inc c
scale_finish:
mov a, c
ldi b, 8
add a, b
RETURN
""", "16-битное произведение коэффициента на scale; деление на 256 и центр +8. scale=10 — ×1.")

block(2, "vertex_begin", """
ld a, bxx
ld b, byx
ld c, vertex
shr c
IF c x_positive
neg a
neg b
x_positive:
st a, pxsum
st b, pysum
ld a, byy
shr c
IF c y_positive
neg a
y_positive:
ld b, pysum
add b, a
st b, pysum
ld a, bxz
ld b, byz
shr c
IF c z_positive
neg a
neg b
z_positive:
ld c, pysum
add b, c
st b, pysum
ld c, pxsum
add a, c
CALL project_coordinate
st a, rx
ld a, pysum
CALL project_coordinate
GO vertex_store
""", "Три бита номера вершины выбирают знаки X/Y/Z; каждую вершину вычислить один раз.")
block(3, "vertex_store", """
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
IF nz vertex_begin
ldi a, edges
st a, ep
ldi a, 64
st a, base
GO edge_begin
""", "Сохранить XY в общей памяти; после восьми вершин начать обход 12 рёбер.")

block(7, "edge_begin", """
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
GO line_start
""", "Взять две готовые вершины; чередовать синий и красный слой для соседних рёбер.")
block(7, "edge_done", """
ld a, ep
ldi b, edges_end
xor a, b
IF nz edge_begin
GO frame_ready
""", "Следующее ребро; после 12 рёбер вывести готовый кадр.")
block(7, "edges", "db " + ",".join(str(v) for edge in EDGES for v in edge) + "\nedges_end:",
      "12 рёбер куба: соседние вершины отличаются одним битом.")

block(3, "line_start", """
ld a, x1
ld b, x0
sub a, b
IF ns x_forward
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
IF ns y_forward
neg a
neg b
y_forward:
st a, dy
st b, sy
ld a, dx
ld b, dy
sub a, b
st a, err
GO line_loop
""", "Брезенхэм: знаковые XY могут выходить за экран; упорядочить концы по X и вычислить ошибку.")
block(4, "line_loop", """
ld a, x0
ldi b, 16
sub a, b
IF nc skip_pixel
ld a, y0
ldi b, 16
sub a, b
IF nc skip_pixel
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
IF nz line_step
ld a, y0
ld b, y1
xor a, b
IF z edge_done
line_step:
ld a, err
shl a
st a, e2
ld b, dy
neg b
sub a, b
IF s skip_x
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
IF s line_loop
ld a, err
ld b, dx
add a, b
st a, err
ld a, y0
ld b, sy
add a, b
st a, y0
GO line_loop
""", "Рисовать только пиксели 0…15 по обеим осям; идти по всему ребру без подгонки масштаба.")
block(4, "frame_ready", """
ldi a, 48
st a, 62
ldi b, 64
ldi c, 64
publish_loop:
ld a, b
st a, b
inc b
dec c
IF nz publish_loop
frame_presented:
GO key_loop
""", "Включить дисплей и опубликовать LCD RAM; ждать клавишу без автоматической анимации.")

block(5, "key_loop", """
ld a, 62
test a
IF z key_loop
mov d, a
ld b, model_deleted
test b
IF nz no_model
ldi b, 17
sub a, b
IF c other_keys
mov c, a
ldi b, 4
sub c, b
IF nc other_keys
ldi b, yaw
shr a
IF nc axis_selected
inc b
axis_selected:
ld c, b
shr a
IF c rotate_positive
dec c
GO rotation_store
rotate_positive:
inc c
rotation_store:
ldi d, 31
and c, d
st c, b
GO frame_start
""", "0x11/12/13/14: чётный индекс — yaw, нечётный — pitch; один шаг равен 11,25°.")
block(5, "other_keys", """
mov a, d
ldi b, 127
xor a, b
IF z delete_model
mov a, d
ldi b, 43
xor a, b
IF z scale_up
mov a, d
ldi b, 61
xor a, b
IF z scale_up
mov a, d
ldi b, 45
xor a, b
IF z scale_down
mov a, d
ldi b, 32
xor a, b
IF nz key_loop
reset_model:
clr a
st a, model_deleted
ldi a, 4
st a, yaw
ldi a, 3
st a, pitch
ldi a, 10
st a, scale
GO frame_start
""", "Del удаляет модель; плюс/равно и минус меняют масштаб; пробел возвращает куб.")
block(2, "scale_up", """
ld a, scale
ldi b, 30
mov c, a
sub c, b
IF z key_loop
inc a
mov c, a
sub c, b
IF z scale_up_store
inc a
scale_up_store:
st a, scale
GO frame_start
""", "scale=5…30: шаг ×0,2 с ограничением на ×3; базовая половина стороны 2,5 пикселя.")
block(6, "scale_down", """
ld a, scale
ldi b, 5
mov c, a
sub c, b
IF z key_loop
dec a
mov c, a
sub c, b
IF z scale_down_store
dec a
scale_down_store:
st a, scale
GO frame_start
""", "Уменьшать на ×0,2; последний шаг доводит до ×0,5, дальнейший минус игнорируется.")

block(1, "no_model", """
ldi b, 32
xor a, b
IF z reset_model
GO key_loop
""", "После удаления игнорировать управление; пробел восстанавливает исходный куб.")
block(3, "delete_model", """
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
IF nz delete_clear_loop
GO frame_ready
""", "Del (0x7F): убрать модель из сцены и опубликовать пустой цветной кадр.")


def size(line):
    if line.endswith(":"):
        return 0
    parts = line.replace(",", " ").split()
    if parts[0] == "db":
        return len(parts) - 1
    return 1 if all(v in "abcd" for v in parts[1:]) else 2


def build():
    banks = {"set_bank": 0}
    for bank, name, lines, _ in BLOCKS:
        banks[name] = bank
        banks.update({line[:-1]: bank for line in lines if line.endswith(":")})

    def expand(bank, name, lines):
        result = []

        def go(target):
            if banks[target] in (0, bank):
                return ["jmp " + target]
            return [f"ldi c, {banks[target]}", f"ldi d, {target}", "jmp set_bank"]

        for i, line in enumerate(lines):
            p = line.split()
            resume = f"resume_{name}_{i}"
            if p[0] == "GO":
                result += go(p[1])
            elif p[0] == "IF":
                condition, target = p[1:]
                if banks[target] in (0, bank):
                    result += ["j" + condition + " " + target]
                else:
                    inverse = {"z": "nz", "nz": "z", "s": "ns", "ns": "s", "c": "nc", "nc": "c"}[condition]
                    result += ["j" + inverse + " " + resume] + go(target) + [resume + ":"]
            elif p[0] == "CALL":
                result += [f"ldi c, {bank}", "st c, ret_bank", f"ldi d, {resume}", "st d, ret_addr"]
                result += go(p[1]) + [resume + ":"]
            elif p[0] == "RETURN":
                result += ["ld c, ret_bank", "ld d, ret_addr", "jmp set_bank"]
            else:
                result.append(line)
        return result

    addresses = {name: 7 + i for i, name in enumerate(VARIABLES)}
    masks = 7 + len(VARIABLES)
    points = masks + 8
    assert points + 16 < 62
    addresses["model_deleted"] = points + 16
    source = ["; 3DViewer — клавиатурный куб для Computer v2, не более 1024 байт.",
              "; Стрелки: yaw/pitch; + или =: больше; -: меньше; Del: удалить; пробел: вернуть куб.", ""]
    source += [f"{name} equ {address}" for name, address in addresses.items()]
    source += [f"masks equ {masks}", f"points equ {points}", "",
               "start: ldi c, 1", "ldi d, frame_start", "set_bank: st c, 63", "jmp d"]
    initial = {"yaw": 4, "pitch": 3, "scale": 10, "model_deleted": 0}
    source += ["globals db " + ",".join(str(initial.get(name, 0)) for name in VARIABLES),
               "pixel_masks db 128,64,32,16,8,4,2,1",
               "vertex_cache db " + ",".join(["0"] * 16)]
    source += ["common_spare db " + ",".join(["0"] * (62 - points - 16)),
               "ports db 0,0", "screen db " + ",".join(["0"] * 64)]
    usage, entries = {}, {}
    for bank in range(1, 8):
        source += ["", f"; Банк #{bank}"]
        used = 0
        for bn, name, lines, comment in BLOCKS:
            if bn != bank:
                continue
            expanded = expand(bank, name, lines)
            count = sum(size(line) for line in expanded)
            entries[name] = dict(bank=bank, address=128 + used, size=count)
            source += ["; " + comment]
            source += [name + " " + expanded[0]] + expanded[1:] if expanded[0].startswith("db ") else [name + ":"] + expanded
            used += count
        usage[bank] = used
        if used > 128:
            raise ValueError(f"Банк {bank}: {used}/128 байт; " + str({n: b["size"] for n, b in entries.items() if b["bank"] == bank}))
        if bank < 7 and used < 128:
            source += [f"padding{bank} db " + ",".join(["0"] * (128 - used))]
    image_bytes = 7 * 128 + usage[7]
    assert image_bytes <= 1024
    (ROOT / "3dviewer.asm").write_text("\n".join(source) + "\n", encoding="utf-8")
    layout = dict(image_bytes=image_bytes, limit=1024, free_bytes=1024-image_bytes,
                  variables=addresses, blocks=entries, banks=banks, code_bank_sizes=usage,
                  sine=SINE, edges=EDGES, points=points, initial=initial,
                  scale=dict(minimum=0.5, maximum=3, initial=1, step=0.2,
                             encoding_units_per_one=10, base_radius=2.5,
                             projection_divisor=256, fit_to_screen=False,
                             clamp_last_step_at_boundary=True),
                  viewport=dict(width=16, height=16, clipping="per raster pixel"),
                  model_lifecycle=dict(delete_key=127, restore_key=32,
                                       controls_ignored_while_deleted=True))
    (ROOT / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(bytes=image_bytes, banks=usage)))


if __name__ == "__main__":
    build()
