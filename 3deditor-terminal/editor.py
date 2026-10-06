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
        return 72 if a == 0 else 36
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
        cursor = nearest(mode, 72, 36)
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


def tool_limit():
    return 11 if tool == 110 else (22 if tool == 103 else (360 if tool == 114 else 4))


def coordinate_prompt(c, v):
    maximum = tool_limit()
    negative = 1 if v < 0 else 0
    if negative:
        v = -v
    whole = v // 16
    fraction = (v % 16) * 625
    length = 8 + negative + (2 if whole >= 10 else 1) + (3 if maximum >= 100 else (2 if maximum >= 10 else 1))
    factor = 1
    while length > 12:
        factor *= 10
        length -= 1
    putc(c)
    putc(126 if fraction % factor else 61)
    if negative:
        putc(45)
    integer(whole)
    putc(46)
    fraction = (fraction + factor // 2) // factor
    d = 1000 // factor
    while d > 0:
        putc(48 + fraction // d)
        fraction = fraction % d
        d = d // 10
    putc(47)
    integer(maximum)
    putc(10)


def tool_values():
    if tool == 103 or tool == 110:
        coordinate_prompt(88, px)
        coordinate_prompt(89, py)
        coordinate_prompt(90, pz)
    else:
        putc(tool)
        text(": +/-")
        integer(tool_limit())
        putc(10)
        if tool == 115:
            text("all / x/y/z")
        else:
            text("x/y/z")
        text("\nEnter / Esc\n")


def command_prompt():
    putc(tool)
    if input_length == 1:
        putc(58)
        if tool == 115 and peek8(INPUT) == 63:
            text("all")
        else:
            putc(peek8(INPUT))
    else:
        if input_length + input_negative < 10 or (tool == 115 and peek8(INPUT) == 63):
            putc(62)
        if tool != 115 or peek8(INPUT) != 63:
            putc(peek8(INPUT))
        if input_negative:
            putc(45)
        i = 1
        while i < input_length:
            putc(peek8(INPUT + i))
            i += 1


def gizmo_pixel(x, y, color):
    if x >= 0 and x < 66 and y >= 0 and y < 32:
        address = GIZMO_BITMAP + (y // 8) * 66 + x
        bit = 1 << (y % 8)
        if color:
            poke8(address, peek8(address) | bit)
        else:
            poke8(address, peek8(address) & (255 - bit))


def gizmo_line(x, y, tx, ty):
    dx = absolute(tx - x)
    dy = -absolute(ty - y)
    sx = 1 if x < tx else -1
    sy = 1 if y < ty else -1
    e = dx + dy
    while 1:
        gizmo_pixel(x, y, 1)
        if x == tx and y == ty:
            return 0
        twice = e * 2
        if twice >= dy:
            e += dy
            x += sx
        if twice <= dx:
            e += dx
            y += sy


def gizmo_label(a):
    tx = peek8(GIZMO_POINTS + a * 2)
    ty = peek8(GIZMO_POINTS + a * 2 + 1)
    if (tx - 32) * (tx - 32) + (ty - 15) * (ty - 15) < 25:
        poke8(GIZMO_LABELS + a * 2, 255)
        poke8(GIZMO_LABELS + a * 2 + 1, 255)
        return 0
    attempt = 0
    found = 0
    while attempt < 6 and not found:
        right = (tx >= 32) != (attempt % 2 == 1)
        x = tx + (4 if right else -9)
        y = ty - 3 + (8 if attempt // 2 == 1 else (-8 if attempt // 2 == 2 else 0))
        x = 0 if x < 0 else (61 if x > 61 else x)
        y = 0 if y < 0 else (25 if y > 25 else y)
        j = 0
        collision = 0
        i = -1
        while i < 6 and not collision:
            v = -1
            while v < 8 and not collision:
                xx = x + i
                yy = y + v
                if xx >= 0 and xx < 66 and yy >= 0 and yy < 32:
                    if peek8(GIZMO_BITMAP + (yy // 8) * 66 + xx) & (1 << (yy % 8)):
                        collision = 1
                v += 1
            i += 1
        while j < a:
            if absolute(x - peek8(GIZMO_LABELS + j * 2)) < 7 and absolute(y - peek8(GIZMO_LABELS + j * 2 + 1)) < 9:
                collision = 1
            j += 1
        if not collision:
            found = 1
        attempt += 1
    if not found:
        x = 58
        y = 2 + a * 9
    poke8(GIZMO_LABELS + a * 2, x)
    poke8(GIZMO_LABELS + a * 2 + 1, y)
    i = 0
    while i < 5:
        bits = peek8(GIZMO_GLYPHS + a * 5 + i)
        j = 0
        while j < 7:
            gizmo_pixel(x + i, y + j, (bits >> j) & 1)
            j += 1
        i += 1


def gizmo_fraction(value, length):
    result = (absolute(value) + length // 2) // length
    return -result if value < 0 else result


def draw_gizmo():
    i = 0
    while i < 264:
        poke8(GIZMO_BITMAP + i, 0)
        i += 1
    previous_projection = peek8(STATE + 8)
    previous_x = peek8(PROJECT_RESULT)
    previous_y = peek8(PROJECT_RESULT + 1)
    poke8(STATE + 8, 1)
    a = 0
    while a < 3:
        project(24 if a == 0 else 0, 24 if a == 1 else 0, 24 if a == 2 else 0, view_yaw, view_pitch)
        dx = peeks8(PROJECT_RESULT) - 8
        dy = peeks8(PROJECT_RESULT + 1) - 8
        tx = 32 + dx
        ty = 15 + dy
        poke8(GIZMO_POINTS + a * 2, tx)
        poke8(GIZMO_POINTS + a * 2 + 1, ty)
        gizmo_line(32, 15, tx, ty)
        length = absolute(dx) if absolute(dx) > absolute(dy) else absolute(dy)
        if length >= 5:
            bx = tx - gizmo_fraction(dx * 4, length)
            by = ty - gizmo_fraction(dy * 4, length)
            i = -2
            while i <= 2:
                gizmo_line(tx, ty, bx + gizmo_fraction(dy * i, length), by - gizmo_fraction(dx * i, length))
                i += 1
        a += 1
    poke8(STATE + 8, previous_projection)
    poke8(PROJECT_RESULT, previous_x)
    poke8(PROJECT_RESULT + 1, previous_y)
    a = 0
    while a < 3:
        gizmo_label(a)
        a += 1
    # Keep the original 66x32 gizmo; compose its bitmap into the terminal frame.
    row = 0
    while row < 4:
        i = 0
        while i < 66:
            address = TERMINAL_FRAME + row * 256 + 78 + i
            poke8(address, peek8(address) | peek8(GIZMO_BITMAP + row * 66 + i))
            i += 1
        row += 1


def turn_view(k):
    global view_yaw, view_pitch
    if k == 17 or k == 19:
        view_yaw = (view_yaw + (31 if k == 17 else 1)) % 32
    else:
        view_pitch = (view_pitch + (31 if k == 18 else 1)) % 32


def terminal():
    render()
    if not editing:
        if projection:
            text("ORTHO")
        else:
            text("PERSP")
        text(" VIEW\nARROW:TURN +/-:ZOOM\nSPACE:EDIT\nP:PROJ H:AXES")
    elif tool:
        tool_values()
        command_prompt()
    else:
        if projection:
            text("ORTHO")
        else:
            text("PERSP")
        if mode == 1:
            text(" VERTICES\n")
        elif mode == 2:
            text(" EDGES\n")
        else:
            text(" FACES\n")
        text("1:V 2:E 3:F ENT:SELECT\nARROW:MOVE TAB:NEXT\nSPACE:VIEW")


def projection_hint():
    if projection:
        text("ORTHO p h\n")
    else:
        text("PERSP p h\n")


def error(code):
    global last_error
    last_error = code
    render()
    if code == 1:
        text("ERR FORMAT")
    elif code == 2:
        text("ERR RANGE")
    elif code == 3:
        text("PRECISION")
    elif code == 4:
        text("ERR EMPTY")
    elif code == 5:
        text("CAPACITY")
    elif code == 7:
        text("AXIS x/y/z")
    else:
        text("TOPOLOGY")
    text("\n\n\n")


def multiply_divide(value, factor, divisor):
    # Rounded signed value*factor/divisor without a 16-bit product overflow.
    if divisor < 0:
        divisor = -divisor
        factor = -factor
    negative = (value < 0) != (factor < 0)
    value = absolute(value)
    factor = absolute(factor)
    whole = value // divisor
    remainder = value % divisor
    result = 0
    carry = divisor // 2
    while factor:
        if factor & 1:
            result += whole
            carry += remainder
            if carry >= divisor:
                result += 1
                carry -= divisor
        factor = factor >> 1
        whole *= 2
        remainder *= 2
        if remainder >= divisor:
            whole += 1
            remainder -= divisor
    return -result if negative else result


def project_model(i):
    # Keep the mesh's Q4 fractions through camera rotation. Round only at pixels.
    x = vertex_component(i, 0)
    y = vertex_component(i, 1)
    z = vertex_component(i, 2)
    rx = rotate_coordinate(x, z, camera_cos_y, camera_sin_y)
    rz = rotate_coordinate(z, x, camera_cos_y, -camera_sin_y)
    ry = rotate_coordinate(y, rz, camera_cos_p, camera_sin_p)
    depth = 512 + rotate_coordinate(rz, y, camera_cos_p, -camera_sin_p)
    divisor = 640 if projection else depth * 10
    factor = 9 if projection else 72
    poke16(POINTS + i * 4, 72 + multiply_divide(rx * zoom, factor, divisor))
    poke16(POINTS + i * 4 + 2, 36 - multiply_divide(ry * zoom, factor, divisor))
    poke8(POINT_DEPTHS + i, depth // 16)


def terminal_outcode(x, y):
    code = 0
    if x < 0:
        code |= 1
    elif x > 143:
        code |= 2
    if y < 0:
        code |= 4
    elif y > 71:
        code |= 8
    return code


def terminal_line(x, y, tx, ty, color):
    # Clip signed 16-bit endpoints before the native rasterizer reads low bytes.
    start = terminal_outcode(x, y)
    end = terminal_outcode(tx, ty)
    while start or end:
        if start & end:
            return 0
        code = start if start else end
        if code & 8:
            xx = x + multiply_divide(tx - x, 71 - y, ty - y)
            yy = 71
        elif code & 4:
            xx = x + multiply_divide(tx - x, -y, ty - y)
            yy = 0
        elif code & 2:
            yy = y + multiply_divide(ty - y, 143 - x, tx - x)
            xx = 143
        else:
            yy = y + multiply_divide(ty - y, -x, tx - x)
            xx = 0
        if start:
            x = xx
            y = yy
            start = terminal_outcode(x, y)
        else:
            tx = xx
            ty = yy
            end = terminal_outcode(tx, ty)
    if absolute(tx - x) > 120:
        xx = (x + tx) // 2
        yy = (y + ty) // 2
        line(x, y, xx, yy, color)
        line(xx, yy, tx, ty, color)
    else:
        line(x, y, tx, ty, color)


def draw_vertex(i, selected):
    # Camera depth uses the original projection: 32 at the model origin.
    radius = 0 if peek8(POINT_DEPTHS + i) < 24 else 1
    radius += selected
    x = projected_component(i, 0)
    y = projected_component(i, 1)
    row = -radius
    while row <= radius:
        terminal_line(x - radius, y + row, x + radius, y + row, 1)
        row += 1


def draw_edge(a, b, selected):
    x = projected_component(a, 0)
    y = projected_component(a, 1)
    tx = projected_component(b, 0)
    ty = projected_component(b, 1)
    terminal_line(x, y, tx, ty, 1)
    if selected:
        if absolute(tx - x) >= absolute(ty - y):
            terminal_line(x, y - 1, tx, ty - 1, 1)
            terminal_line(x, y + 1, tx, ty + 1, 1)
        else:
            terminal_line(x - 1, y, tx - 1, ty, 1)
            terminal_line(x + 1, y, tx + 1, ty, 1)


def fill_triangle(ax, ay, bx, by, cx, cy):
    # Horizontal spans cover the terminal canvas instead of the LCD's 16x16 scan.
    if ay > by:
        tx = ax
        ty = ay
        ax = bx
        ay = by
        bx = tx
        by = ty
    if by > cy:
        tx = bx
        ty = by
        bx = cx
        by = cy
        cx = tx
        cy = ty
    if ay > by:
        tx = ax
        ty = ay
        ax = bx
        ay = by
        bx = tx
        by = ty
    if cy == ay:
        return 0
    # A nonzero area can wrap to zero in the VM's 16-bit multiplication.
    if (bx - ax) * (cy - ay) == (cx - ax) * (by - ay) and bx - ax == multiply_divide(cx - ax, by - ay, cy - ay):
        return 0
    y = 0 if ay < 0 else ay
    end = 71 if cy > 71 else cy
    while y <= end:
        left = ax + multiply_divide(cx - ax, y - ay, cy - ay)
        if y <= by and by > ay:
            right = ax + multiply_divide(bx - ax, y - ay, by - ay)
        else:
            right = bx + multiply_divide(cx - bx, y - by, cy - by)
        if left > right:
            tx = left
            left = right
            right = tx
        left = 0 if left < 0 else left
        right = 143 if right > 143 else right
        if left <= right:
            split = left + 120 if right - left > 120 else right
            line(left, y, split, y, 2)
            if split < right:
                line(split + 1, y, right, y, 2)
        y += 1


def draw_element(m, i):
    if m == 1:
        draw_vertex(i, 0)
    elif m == 2:
        a = peek8(EDGES + i * 2)
        b = peek8(EDGES + i * 2 + 1)
        draw_edge(a, b, 0)
    else:
        a = peek8(FACES + i * 5 + 1)
        b = peek8(FACES + i * 5 + 2)
        c = peek8(FACES + i * 5 + 3)
        fill_triangle(projected_component(a, 0), projected_component(a, 1), projected_component(b, 0), projected_component(b, 1), projected_component(c, 0), projected_component(c, 1))
        if peek8(FACES + i * 5) == 4:
            b = c
            c = peek8(FACES + i * 5 + 4)
            fill_triangle(projected_component(a, 0), projected_component(a, 1), projected_component(b, 0), projected_component(b, 1), projected_component(c, 0), projected_component(c, 1))
        draw_face_border(i, 0)


def draw_face_border(i, selected):
    n = peek8(FACES + i * 5)
    j = 0
    while j < n:
        a = peek8(FACES + i * 5 + 1 + j)
        b = peek8(FACES + i * 5 + 1 + (j + 1) % n)
        draw_edge(a, b, selected)
        j += 1


def draw_selected(m, i):
    if m == 1:
        draw_vertex(i, 1)
    elif m == 2:
        draw_edge(peek8(EDGES + i * 2), peek8(EDGES + i * 2 + 1), 1)
    else:
        draw_face_border(i, 1)


def render():
    global camera_sin_y, camera_cos_y, camera_sin_p, camera_cos_p
    putc(12)
    poke8(STATE + 8, projection)
    camera_sin_y = peek16(VIEW_SINE + view_yaw * 2)
    camera_cos_y = peek16(VIEW_SINE + ((view_yaw + 8) % 32) * 2)
    camera_sin_p = peek16(VIEW_SINE + view_pitch * 2)
    camera_cos_p = peek16(VIEW_SINE + ((view_pitch + 8) % 32) * 2)
    i = 0
    while i < limit(1):
        if peek8(VLIVE + i):
            project_model(i)
        i += 1
    begin()
    if not editing:
        i = 0
        while i < limit(2):
            if alive(2, i):
                a = peek8(EDGES + i * 2)
                b = peek8(EDGES + i * 2 + 1)
                terminal_line(projected_component(a, 0), projected_component(a, 1),
                     projected_component(b, 0), projected_component(b, 1),
                     1)
            i += 1
    else:
        i = 0
        while i < limit(mode):
            if alive(mode, i):
                draw_element(mode, i)
            i += 1
        i = 0
        while i < limit(mode):
            if alive(mode, i) and peek8(selection_base(mode) + i):
                draw_selected(mode, i)
            i += 1
        if cursor >= 0 and alive(mode, cursor):
            x = center(mode, cursor, 0)
            y = center(mode, cursor, 1)
            terminal_line(x - 4, y, x + 4, y, 1)
            terminal_line(x, y - 4, x, y + 4, 1)
    draw_gizmo()
    present()
    blink(0)


def remember():
    global undo_valid
    copy(UNDO, MESH, MESH_BYTES)
    undo_valid = 1


def fraction_q4(numerator, denominator):
    global fraction_exact
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
    fraction_exact = numerator == 0
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
    if not input_length:
        return 7
    a = peek8(INPUT)
    if a != 120 and a != 121 and a != 122:
        if tool != 115 or a != 63:
            return 7
    if input_length < 2:
        if tool == 110:
            axis = a - 120
            amount = 0
            return 0
        return 1
    axis = 3 if a == 63 else a - 120
    p = 1
    sign = -1 if input_negative else 1
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
        maximum = 11 if tool == 110 else (22 if tool == 103 else 4)
        if whole > maximum or (whole == maximum and fraction):
            return 2
        amount = whole * 16 + fraction_q4(fraction, denominator)
        if tool == 110 and not fraction_exact:
            return 3
        if amount > maximum * 16:
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
                if axis == 0 or axis == 3:
                    x = px + (x - px) * amount // 16
                if axis == 1 or axis == 3:
                    y = py + (y - py) * amount // 16
                if axis == 2 or axis == 3:
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
    poke16(VERTICES + i * 6, px)
    poke16(VERTICES + i * 6 + 2, py)
    poke16(VERTICES + i * 6 + 4, pz)
    poke8(VLIVE + i, 1)
    if i >= limit(1):
        poke8(COUNTS, i + 1)
    clear_selection()
    mode = 1
    cursor = i
    toggle()
    return 0


def create_connection():
    if mode == 2:
        return create_face()
    if mode != 1 or order_count != 2:
        return 6
    a = peek8(ORDER)
    b = peek8(ORDER + 1)
    if edge_index(a, b) >= 0:
        return 6
    e = free_slot(2)
    if e < 0:
        return 5
    remember()
    poke8(EDGES + e * 2, a)
    poke8(EDGES + e * 2 + 1, b)
    poke8(ELIVE + e, 1)
    if e >= limit(2):
        poke8(COUNTS + 1, e + 1)
    return 0


def create_face():
    n = 0
    i = 0
    while i < 32:
        poke8(MARKS + i, 0)
        i += 1
    i = 0
    while i < limit(2):
        if alive(2, i) and peek8(SELECT + 32 + i):
            n += 1
            a = peek8(EDGES + i * 2)
            b = peek8(EDGES + i * 2 + 1)
            poke8(MARKS + a, peek8(MARKS + a) + 1)
            poke8(MARKS + b, peek8(MARKS + b) + 1)
        i += 1
    if n != 3 and n != 4:
        return 6
    count = 0
    start = -1
    i = 0
    while i < 32:
        degree = peek8(MARKS + i)
        if degree:
            if degree != 2:
                return 6
            count += 1
            start = i
        i += 1
    if count != n:
        return 6
    current = start
    previous = -1
    k = 0
    while k < n:
        poke8(ORDER + k, current)
        next_vertex = -1
        i = 0
        while i < limit(2):
            if alive(2, i) and peek8(SELECT + 32 + i):
                a = peek8(EDGES + i * 2)
                b = peek8(EDGES + i * 2 + 1)
                if a == current and b != previous and next_vertex < 0:
                    next_vertex = b
                elif b == current and a != previous and next_vertex < 0:
                    next_vertex = a
            i += 1
        if next_vertex < 0:
            return 6
        previous = current
        current = next_vertex
        k += 1
    if current != start:
        return 6
    i = 0
    while i < limit(3):
        if peek8(FACES + i * 5) == n:
            matches = 0
            k = 0
            while k < n:
                matches += 1 if peek8(MARKS + peek8(FACES + i * 5 + k + 1)) else 0
                k += 1
            if matches == n:
                return 6
        i += 1
    slot = free_slot(3)
    if slot < 0:
        return 5
    remember()
    poke8(FACES + slot * 5, n)
    if slot >= limit(3):
        poke8(COUNTS + 2, slot + 1)
    k = 0
    while k < n:
        poke8(FACES + slot * 5 + k + 1, peek8(ORDER + k))
        k += 1
    return 0


def accept_new_coordinate():
    global new_axis, input_length, input_negative, px, py, pz
    problem = parse()
    if problem:
        return problem
    if new_axis == 0:
        px = amount
    elif new_axis == 1:
        py = amount
    else:
        pz = amount
    new_axis += 1
    if new_axis < 3:
        poke8(INPUT, 120 + new_axis)
        input_length = 1
        input_negative = 0
        return 0
    return new_vertex()


def main():
    global mode, cursor, tool, input_length, last_error, order_count, undo_valid
    global view_yaw, view_pitch, zoom, origin_pivot, px, py, pz, axis, amount
    global editing, new_axis, projection, input_negative
    global gizmo, gizmo_error
    gizmo = 0
    gizmo_error = 0
    editing = 0
    projection = 1
    mode = 1
    cursor = 0
    tool = 0
    input_length = 0
    input_negative = 0
    order_count = 0
    undo_valid = 0
    origin_pivot = 0
    view_yaw = 4
    view_pitch = 3
    zoom = 10
    last_error = 0
    terminal()
    while 1:
        k = keycode()
        if gizmo:
            if k == 27:
                gizmo = 0
                if gizmo_error:
                    error(gizmo_error)
                else:
                    terminal()
            elif not editing and k >= 17 and k <= 20:
                turn_view(k)
                terminal()
        elif k == 104:
            gizmo_error = last_error
            gizmo = 1
            terminal()
        else:
            last_error = 0
            if tool:
                if k == 27:
                    tool = 0
                    input_length = 0
                    terminal()
                elif k == 10 or k == 13:
                    problem = accept_new_coordinate() if tool == 110 else transform()
                    if problem:
                        error(problem)
                    elif tool == 110 and new_axis < 3:
                        terminal()
                    else:
                        tool = 0
                        input_length = 0
                        terminal()
                elif k == 8:
                    if input_length > 1:
                        input_length -= 1
                    else:
                        input_negative = 0
                        if tool != 110:
                            poke8(INPUT, 63)
                    terminal()
                else:
                    if tool != 110 and (k == 120 or k == 121 or k == 122):
                        poke8(INPUT, k)
                        terminal()
                    elif k == 43 or k == 45:
                        input_negative = 1 if k == 45 else 0
                        terminal()
                    elif k == 46 or (k >= 48 and k <= 57):
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
                if k == 32:
                    editing = 1 - editing
                elif k == 112:
                    projection = 1 - projection
                elif not editing:
                    if k >= 17 and k <= 20:
                        turn_view(k)
                    elif k == 43 or k == 61:
                        zoom = 30 if zoom + 2 > 30 else zoom + 2
                    elif k == 45:
                        zoom = 5 if zoom - 2 < 5 else zoom - 2
                elif k >= 49 and k <= 51:
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
                        poke8(INPUT, 63)
                        input_length = 1
                        input_negative = 0
                    else:
                        problem = 4
                elif k == 127:
                    delete_selected()
                elif k == 110:
                    if free_slot(1) < 0:
                        problem = 5
                    else:
                        tool = 110
                        new_axis = 0
                        px = 0
                        py = 0
                        pz = 0
                        poke8(INPUT, 120)
                        input_length = 1
                        input_negative = 0
                elif k == 102:
                    problem = create_connection()
                elif k == 117:
                    if undo_valid:
                        copy(MESH, UNDO, MESH_BYTES)
                        undo_valid = 0
                        clear_selection()
                        cursor = nearest(mode, 72, 36)
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
                elif k == 111:
                    origin_pivot = 1 - origin_pivot
                elif k == 43 or k == 61:
                    zoom += 2
                    if zoom > 30:
                        zoom = 30
                elif k == 45:
                    zoom -= 2
                    if zoom < 5:
                        zoom = 5
                if problem:
                    error(problem)
                else:
                    terminal()
