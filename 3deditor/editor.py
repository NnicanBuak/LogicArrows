"""Build-time source of 3DEditor. Compiled to bytecode in the ASM disk image.

Integers are signed 16-bit; division truncates toward zero on the target.
Only the named native intrinsics are provided by the machine runtime.
"""


def absolute(v):
    return -v if v < 0 else v


def clear_selection():
    global order_count
    i = 0
    while i < 128:
        poke8(SELECT + i, 0)
        i += 1
    order_count = 0


def limit(m):
    return peek8(COUNTS + m - 1)


def alive(m, i):
    if i < 0:
        return 0
    if m == 1:
        return peek8(VLIVE + i)
    if m == 2:
        return peek8(ELIVE + i)
    return peek8(FACES + i * 5)


def selection_base(m):
    return SELECT if m == 1 else (SELECT + 32 if m == 2 else SELECT + 96)


def vertex_component(i, a):
    return peek16(VERTICES + i * 6 + a * 2)


def projected_component(i, a):
    return peek16(POINTS + i * 4 + a * 2)


def center(m, i, a):
    if i < 0:
        return 8
    if m == 1:
        return projected_component(i, a)
    if m == 2:
        v = peek8(EDGES + i * 2)
        w = peek8(EDGES + i * 2 + 1)
        return (projected_component(v, a) + projected_component(w, a)) // 2
    n = peek8(FACES + i * 5)
    k = 0
    total = 0
    while k < n:
        total += projected_component(peek8(FACES + i * 5 + k + 1), a)
        k += 1
    return total // n


def nearest(m, x, y):
    i = 0
    best = -1
    score = 32767
    while i < limit(m):
        if alive(m, i):
            d = absolute(center(m, i, 0) - x) + absolute(center(m, i, 1) - y)
            if d < score:
                best = i
                score = d
        i += 1
    return best


def navigate(k):
    global cursor
    if cursor < 0:
        cursor = nearest(mode, 8, 8)
        return 0
    x = center(mode, cursor, 0)
    y = center(mode, cursor, 1)
    best = cursor
    score = 32767
    i = 0
    while i < limit(mode):
        if alive(mode, i):
            dx = center(mode, i, 0) - x
            dy = center(mode, i, 1) - y
            forward = -dx if k == 17 else (dx if k == 19 else (-dy if k == 18 else dy))
            sideways = absolute(dy) if k == 17 or k == 19 else absolute(dx)
            if forward > 0:
                d = forward + sideways * 3
                if d < score:
                    best = i
                    score = d
        i += 1
    cursor = best


def cycle():
    global cursor
    n = limit(mode)
    i = 1
    while i <= n:
        candidate = (cursor + i) % n
        if alive(mode, candidate):
            cursor = candidate
            return 0
        i += 1
    cursor = -1


def toggle():
    global order_count
    if cursor < 0:
        return 0
    address = selection_base(mode) + cursor
    selected = peek8(address)
    poke8(address, 1 - selected)
    if mode == 1:
        if not selected:
            poke8(ORDER + order_count, cursor)
            order_count += 1
        else:
            i = 0
            while i < order_count:
                if peek8(ORDER + i) == cursor:
                    j = i
                    while j + 1 < order_count:
                        poke8(ORDER + j, peek8(ORDER + j + 1))
                        j += 1
                    order_count -= 1
                    return 0
                i += 1


def mark_vertices():
    i = 0
    while i < 32:
        poke8(MARKS + i, 0)
        i += 1
    i = 0
    while i < limit(mode):
        if alive(mode, i) and peek8(selection_base(mode) + i):
            if mode == 1:
                poke8(MARKS + i, 1)
            elif mode == 2:
                poke8(MARKS + peek8(EDGES + i * 2), 1)
                poke8(MARKS + peek8(EDGES + i * 2 + 1), 1)
            else:
                k = 0
                while k < peek8(FACES + i * 5):
                    poke8(MARKS + peek8(FACES + i * 5 + k + 1), 1)
                    k += 1
        i += 1
    total = 0
    i = 0
    while i < 32:
        total += peek8(MARKS + i)
        i += 1
    return total


def pivot():
    global px, py, pz
    n = mark_vertices()
    px = 0
    py = 0
    pz = 0
    if n == 0 or origin_pivot:
        return n
    i = 0
    while i < 32:
        if peek8(MARKS + i):
            px += vertex_component(i, 0)
            py += vertex_component(i, 1)
            pz += vertex_component(i, 2)
        i += 1
    px = px // n
    py = py // n
    pz = pz // n
    return n


def integer(v):
    if v < 0:
        putc(45)
        v = -v
    d = 10000
    started = 0
    while d > 0:
        digit = v // d
        if digit or started or d == 1:
            putc(48 + digit)
            started = 1
        v = v % d
        d = d // 10


def fixed(v):
    if v < 0:
        putc(45)
        v = -v
    integer(v // 16)
    putc(46)
    fraction = (v % 16) * 625
    d = 1000
    while d > 0:
        putc(48 + fraction // d)
        fraction = fraction % d
        d = d // 10


def terminal():
    putc(12)
    if tool:
        putc(88)
        putc(61)
        fixed(px)
        putc(10)
        putc(89)
        putc(61)
        fixed(py)
        putc(10)
        putc(90)
        putc(61)
        fixed(pz)
        putc(10)
        putc(tool)
        putc(62)
        i = 0
        while i < input_length:
            putc(peek8(INPUT + i))
            i += 1
    else:
        text("3DEditor\n")
        putc(86 if mode == 1 else (69 if mode == 2 else 70))
        putc(35)
        integer(cursor)
        text(" SEL:")
        n = 0
        i = 0
        while i < limit(mode):
            n += peek8(selection_base(mode) + i)
            i += 1
        integer(n)
        putc(10)
        text("P:")
        if origin_pivot:
            text("ORIGIN\n")
        else:
            text("CENTER\n")
        text("g r s / Del")


def error(code):
    global last_error
    last_error = code
    putc(12)
    if code == 1:
        text("ERR FORMAT\n")
    elif code == 2:
        text("ERR RANGE\n")
    elif code == 3:
        text("ERR PRECISION\n")
    elif code == 4:
        text("ERR EMPTY\n")
    elif code == 5:
        text("ERR CAPACITY\n")
    else:
        text("ERR TOPOLOGY\n")
    if tool:
        putc(tool)
        putc(62)
        i = 0
        while i < input_length:
            putc(peek8(INPUT + i))
            i += 1


def draw_element(m, i):
    if m == 1:
        pixel(projected_component(i, 0), projected_component(i, 1), 3)
    elif m == 2:
        a = peek8(EDGES + i * 2)
        b = peek8(EDGES + i * 2 + 1)
        line(projected_component(a, 0), projected_component(a, 1), projected_component(b, 0), projected_component(b, 1), 3)
    else:
        a = peek8(FACES + i * 5 + 1)
        b = peek8(FACES + i * 5 + 2)
        c = peek8(FACES + i * 5 + 3)
        triangle(projected_component(a, 0), projected_component(a, 1), projected_component(b, 0), projected_component(b, 1), projected_component(c, 0), projected_component(c, 1), 3)
        if peek8(FACES + i * 5) == 4:
            b = c
            c = peek8(FACES + i * 5 + 4)
            triangle(projected_component(a, 0), projected_component(a, 1), projected_component(b, 0), projected_component(b, 1), projected_component(c, 0), projected_component(c, 1), 3)


def render():
    i = 0
    while i < limit(1):
        if peek8(VLIVE + i):
            project(vertex_component(i, 0) // 16, vertex_component(i, 1) // 16, vertex_component(i, 2) // 16, view_yaw, view_pitch)
            x = 8 + (peeks8(PROJECT_RESULT) - 8) * zoom // 10
            y = 8 + (peeks8(PROJECT_RESULT + 1) - 8) * zoom // 10
            poke16(POINTS + i * 4, x)
            poke16(POINTS + i * 4 + 2, y)
        i += 1
    begin()
    i = 0
    while i < limit(mode):
        if alive(mode, i):
            draw_element(mode, i)
        i += 1
    copy(BASE_MASK, 64, 32)
    begin()
    i = 0
    while i < limit(mode):
        if alive(mode, i) and peek8(selection_base(mode) + i):
            draw_element(mode, i)
        i += 1
    copy(SELECT_MASK, 64, 32)
    begin()
    if cursor >= 0 and alive(mode, cursor):
        draw_element(mode, cursor)
    i = 0
    while i < 32:
        current = peek8(64 + i)
        selected = peek8(SELECT_MASK + i)
        base = peek8(BASE_MASK + i) & ~(selected | current)
        poke8(64 + i, base | current)
        poke8(96 + i, base | (selected & ~current))
        i += 1
    present()


def remember():
    global undo_valid
    copy(UNDO, MESH, MESH_BYTES)
    undo_valid = 1


def fraction_q4(numerator, denominator):
    # Four binary fraction digits; intermediate values stay below 20000.
    result = 0
    i = 0
    while i < 4:
        numerator *= 2
        result *= 2
        if numerator >= denominator:
            numerator -= denominator
            result += 1
        i += 1
    if numerator * 2 >= denominator:
        result += 1
    return result


def rotate_coordinate(a, b, c, d):
    # Exact rounded (a*c+b*d)/256 without overflowing a signed 16-bit word.
    major = (a >> 4) * c + (b >> 4) * d
    minor = (major & 15) * 16 + (a & 15) * c + (b & 15) * d
    return (major >> 4) + ((minor + 128) >> 8)


def parse():
    global axis, amount
    if input_length < 2:
        return 1
    a = peek8(INPUT)
    if a != 120 and a != 121 and a != 122:
        return 1
    axis = a - 120
    p = 1
    sign = 1
    a = peek8(INPUT + p)
    if a == 43 or a == 45:
        sign = -1 if a == 45 else 1
        p += 1
    digits = 0
    whole = 0
    while p < input_length and peek8(INPUT + p) >= 48 and peek8(INPUT + p) <= 57:
        whole = whole * 10 + peek8(INPUT + p) - 48
        digits += 1
        p += 1
        if whole > 360 or digits > 3:
            return 2
    if not digits:
        return 1
    fraction = 0
    denominator = 1
    decimals = 0
    if p < input_length:
        if peek8(INPUT + p) != 46:
            return 1
        p += 1
        while p < input_length and peek8(INPUT + p) >= 48 and peek8(INPUT + p) <= 57:
            if decimals == 4:
                return 3
            fraction = fraction * 10 + peek8(INPUT + p) - 48
            denominator *= 10
            decimals += 1
            p += 1
        if not decimals:
            return 1
    if p != input_length:
        return 1
    if tool == 114:
        if decimals > 1 and fraction % (denominator // 10):
            return 3
        amount = whole * 10 + (fraction // (denominator // 10) if decimals else 0)
        if amount > 3600:
            return 2
    else:
        maximum = 22 if tool == 103 else 4
        if whole > maximum or (whole == maximum and fraction):
            return 2
        amount = whole * 16 + fraction_q4(fraction, denominator)
        if amount > (352 if tool == 103 else 64):
            return 2
    amount *= sign
    return 0


def transform():
    problem = parse()
    if problem:
        return problem
    copy(TRIAL, VERTICES, 192)
    angle = amount % 3600
    if angle < 0:
        angle += 3600
    sine = peek16(SINE + angle * 2)
    cosine = peek16(SINE + ((angle + 900) % 3600) * 2)
    i = 0
    while i < 32:
        if peek8(MARKS + i):
            x = vertex_component(i, 0)
            y = vertex_component(i, 1)
            z = vertex_component(i, 2)
            if tool == 103:
                if axis == 0:
                    x += amount
                elif axis == 1:
                    y += amount
                else:
                    z += amount
            elif tool == 115:
                if axis == 0:
                    x = px + (x - px) * amount // 16
                elif axis == 1:
                    y = py + (y - py) * amount // 16
                else:
                    z = pz + (z - pz) * amount // 16
            else:
                if axis == 0:
                    a = y - py
                    b = z - pz
                    y = py + rotate_coordinate(a, b, cosine, -sine)
                    z = pz + rotate_coordinate(a, b, sine, cosine)
                elif axis == 1:
                    a = z - pz
                    b = x - px
                    z = pz + rotate_coordinate(a, b, cosine, -sine)
                    x = px + rotate_coordinate(a, b, sine, cosine)
                else:
                    a = x - px
                    b = y - py
                    x = px + rotate_coordinate(a, b, cosine, -sine)
                    y = py + rotate_coordinate(a, b, sine, cosine)
            if absolute(x) > 176 or absolute(y) > 176 or absolute(z) > 176:
                return 2
            poke16(TRIAL + i * 6, x)
            poke16(TRIAL + i * 6 + 2, y)
            poke16(TRIAL + i * 6 + 4, z)
        i += 1
    remember()
    copy(VERTICES, TRIAL, 192)
    return 0


def edge_index(a, b):
    i = 0
    while i < limit(2):
        if peek8(ELIVE + i):
            v = peek8(EDGES + i * 2)
            w = peek8(EDGES + i * 2 + 1)
            if (v == a and w == b) or (v == b and w == a):
                return i
        i += 1
    return -1


def delete_selected():
    global cursor
    if not mark_vertices():
        return 0
    x = center(mode, cursor, 0)
    y = center(mode, cursor, 1)
    remember()
    i = 0
    while i < limit(mode):
        if peek8(selection_base(mode) + i):
            poke8((VLIVE if mode == 1 else (ELIVE if mode == 2 else FACES)) + i * (5 if mode == 3 else 1), 0)
        i += 1
    i = 0
    while i < limit(2):
        if peek8(ELIVE + i):
            if not peek8(VLIVE + peek8(EDGES + i * 2)) or not peek8(VLIVE + peek8(EDGES + i * 2 + 1)):
                poke8(ELIVE + i, 0)
        i += 1
    i = 0
    while i < limit(3):
        n = peek8(FACES + i * 5)
        k = 0
        while k < n:
            a = peek8(FACES + i * 5 + k + 1)
            b = peek8(FACES + i * 5 + (k + 1) % n + 1)
            if not peek8(VLIVE + a) or edge_index(a, b) < 0:
                poke8(FACES + i * 5, 0)
            k += 1
        i += 1
    clear_selection()
    cursor = nearest(mode, x, y)


def free_slot(m):
    i = 0
    while i < (64 if m == 2 else 32):
        if not alive(m, i):
            return i
        i += 1
    return -1


def new_vertex():
    global cursor, mode, order_count
    i = free_slot(1)
    if i < 0:
        return 5
    remember()
    poke16(VERTICES + i * 6, 0)
    poke16(VERTICES + i * 6 + 2, 0)
    poke16(VERTICES + i * 6 + 4, 0)
    poke8(VLIVE + i, 1)
    if i >= limit(1):
        poke8(COUNTS, i + 1)
    clear_selection()
    mode = 1
    cursor = i
    toggle()
    return 0


def create_connection():
    if mode != 1 or order_count < 2 or order_count > 4:
        return 6
    if order_count > 2:
        slot = free_slot(3)
        if slot < 0:
            return 5
        # Reject an existing face with the same set of vertices.
        i = 0
        while i < limit(3):
            if peek8(FACES + i * 5) == order_count:
                k = 0
                matches = 0
                while k < order_count:
                    matches += peek8(SELECT + peek8(FACES + i * 5 + k + 1))
                    k += 1
                if matches == order_count:
                    return 6
            i += 1
    else:
        if edge_index(peek8(ORDER), peek8(ORDER + 1)) >= 0:
            return 6
    needed = 0
    k = 0
    while k < (1 if order_count == 2 else order_count):
        a = peek8(ORDER + k)
        b = peek8(ORDER + (k + 1) % order_count)
        if edge_index(a, b) < 0:
            needed += 1
        k += 1
    available = 0
    i = 0
    while i < 64:
        available += 1 if not peek8(ELIVE + i) else 0
        i += 1
    if available < needed:
        return 5
    remember()
    k = 0
    while k < (1 if order_count == 2 else order_count):
        a = peek8(ORDER + k)
        b = peek8(ORDER + (k + 1) % order_count)
        if edge_index(a, b) < 0:
            e = free_slot(2)
            poke8(EDGES + e * 2, a)
            poke8(EDGES + e * 2 + 1, b)
            poke8(ELIVE + e, 1)
            if e >= limit(2):
                poke8(COUNTS + 1, e + 1)
        k += 1
    if order_count > 2:
        poke8(FACES + slot * 5, order_count)
        if slot >= limit(3):
            poke8(COUNTS + 2, slot + 1)
        k = 0
        while k < order_count:
            poke8(FACES + slot * 5 + k + 1, peek8(ORDER + k))
            k += 1
    return 0


def main():
    global mode, cursor, tool, input_length, last_error, order_count, undo_valid
    global view_yaw, view_pitch, zoom, origin_pivot, px, py, pz, axis, amount
    mode = 1
    cursor = 0
    tool = 0
    input_length = 0
    order_count = 0
    undo_valid = 0
    origin_pivot = 0
    view_yaw = 4
    view_pitch = 3
    zoom = 10
    last_error = 0
    render()
    terminal()
    while 1:
        k = keycode()
        last_error = 0
        if tool:
            if k == 27:
                tool = 0
                input_length = 0
                terminal()
            elif k == 10 or k == 13:
                problem = transform()
                if problem:
                    error(problem)
                else:
                    tool = 0
                    input_length = 0
                    render()
                    terminal()
            elif k == 8:
                if input_length:
                    input_length -= 1
                terminal()
            else:
                if k == 120 or k == 121 or k == 122 or k == 43 or k == 45 or k == 46 or (k >= 48 and k <= 57):
                    if input_length < 9:
                        poke8(INPUT + input_length, k)
                        input_length += 1
                        terminal()
                    else:
                        error(1)
                else:
                    error(1)
        else:
            problem = 0
            if k >= 49 and k <= 51:
                x = center(mode, cursor, 0)
                y = center(mode, cursor, 1)
                clear_selection()
                mode = k - 48
                cursor = nearest(mode, x, y)
            elif k >= 17 and k <= 20:
                navigate(k)
            elif k == 9:
                cycle()
            elif k == 10 or k == 13:
                toggle()
            elif k == 27:
                clear_selection()
            elif k == 103 or k == 114 or k == 115:
                if pivot():
                    tool = k
                    input_length = 0
                else:
                    problem = 4
            elif k == 127:
                delete_selected()
            elif k == 110:
                problem = new_vertex()
            elif k == 102:
                problem = create_connection()
            elif k == 117:
                if undo_valid:
                    copy(MESH, UNDO, MESH_BYTES)
                    undo_valid = 0
                    clear_selection()
                    cursor = nearest(mode, 8, 8)
            elif k == 97:
                clear_selection()
                i = 0
                while i < limit(mode):
                    if alive(mode, i):
                        poke8(selection_base(mode) + i, 1)
                        if mode == 1:
                            poke8(ORDER + order_count, i)
                            order_count += 1
                    i += 1
            elif k == 112:
                origin_pivot = 1 - origin_pivot
            elif k == 106 or k == 108:
                view_yaw = (view_yaw + (31 if k == 106 else 1)) % 32
            elif k == 105 or k == 107:
                view_pitch = (view_pitch + (31 if k == 105 else 1)) % 32
            elif k == 43 or k == 61:
                zoom += 2
                if zoom > 30:
                    zoom = 30
            elif k == 45:
                zoom -= 2
                if zoom < 5:
                    zoom = 5
            elif k == 32:
                view_yaw = 4
                view_pitch = 3
                zoom = 10
            render()
            if problem:
                error(problem)
            else:
                terminal()
