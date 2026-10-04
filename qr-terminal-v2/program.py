"""QR Terminal v2 source, compiled to Computer v2 instructions by build.py.

This is restricted integer Python syntax for the compiler, not a host program.
KEY/PUTC, bit packing, RS blocks, matrix access and rendering are native opcodes.
"""


def decimal(value):
    leading = 0
    if value >= 100:
        putc(48 + value // 100)
        value = value % 100
        leading = 1
    if value >= 10 or leading:
        putc(48 + value // 10)
    putc(48 + value % 10)


def choice(maximum, maxdigits):
    value = 0
    digits = 0
    text(">")
    while 1:
        key = keycode()
        if key == 27:
            putc(12)
            return 0
        if key == 10:
            if value >= 1 and value <= maximum:
                putc(10)
                return value
            text("\n?\n>")
            value = 0
            digits = 0
        else:
            if key == 8:
                if digits > 0:
                    value = value // 10
                    digits -= 1
                    putc(8)
            else:
                if key >= 48 and key <= 57 and digits < maxdigits:
                    value = value * 10 + key - 48
                    digits += 1
                    putc(key)


def read_input():
    global input_length, input_mode, max_length
    input_length = 0
    fill(INPUT, 768, 0)
    text("Лимит: ")
    decimal(max_length)
    text("\n>")
    while 1:
        key = keycode()
        if key == 27:
            putc(12)
            fill(INPUT, 768, 0)
            input_length = 0
            return 0
        if key == 10:
            if input_length > 0:
                putc(10)
                return 1
        else:
            if key == 8:
                if input_length > 0:
                    input_length -= 1
                    poke8(INPUT + input_length, 0)
                    putc(8)
            else:
                accepted = 0
                if input_mode == 1:
                    accepted = key >= 48 and key <= 57
                if input_mode == 2:
                    accepted = peek8(ALPHABET_MAP + key) != 255
                if input_mode == 3:
                    accepted = key >= 32 and key != 127 and key != 152
                if accepted and input_length < max_length:
                    poke8(INPUT + input_length, key)
                    input_length += 1
                    putc(key)


def append(value, width):
    global bit_length
    bits(value, width)
    bit_length += width


def encode_data():
    global input_length, input_mode, version, data_words, bit_length
    fill(DATA, 384, 0)
    beginbits()
    bit_length = 0
    if input_mode == 1:
        append(1, 4)
        if version < 10:
            append(input_length, 10)
        else:
            append(input_length, 12)
        index = 0
        while index < input_length:
            value = 0
            count = 0
            while count < 3 and index < input_length:
                value = value * 10 + peek8(INPUT + index) - 48
                count += 1
                index += 1
            if count == 3:
                append(value, 10)
            if count == 2:
                append(value, 7)
            if count == 1:
                append(value, 4)
    if input_mode == 2:
        append(2, 4)
        if version < 10:
            append(input_length, 9)
        else:
            append(input_length, 11)
        index = 0
        while index < input_length:
            value = peek8(ALPHABET_MAP + peek8(INPUT + index))
            index += 1
            if index < input_length:
                value = value * 45 + peek8(ALPHABET_MAP + peek8(INPUT + index))
                index += 1
                append(value, 11)
            else:
                append(value, 6)
    if input_mode == 3:
        append(7, 4)
        append(22, 8)
        append(4, 4)
        if version < 10:
            append(input_length, 8)
        else:
            append(input_length, 16)
        index = 0
        while index < input_length:
            append(peek8(INPUT + index), 8)
            index += 1
    remaining = data_words * 8 - bit_length
    if remaining > 4:
        remaining = 4
    if remaining > 0:
        append(0, remaining)
    if (bit_length & 7) != 0:
        append(0, 8 - (bit_length & 7))
    value = 236
    while bit_length < data_words * 8:
        append(value, 8)
        value = value ^ 253


def encode_ecc():
    global profile, block_count, ecc_degree, raw_words
    short_count = peek8(profile + 8)
    short_data = peek8(profile + 9)
    divisor = peek16(profile + 10)
    offset = 0
    block = 0
    while block < block_count:
        length = short_data
        if block >= short_count:
            length += 1
        poke16(BLOCK_INFO + block * 4, offset)
        poke8(BLOCK_INFO + block * 4 + 2, length)
        rsblock(DATA + offset, length, ecc_degree, divisor, ECC + block * ecc_degree)
        offset += length
        block += 1
    output = 0
    index = 0
    while index <= short_data:
        block = 0
        while block < block_count:
            if index < peek8(BLOCK_INFO + block * 4 + 2):
                source = peek16(BLOCK_INFO + block * 4)
                poke8(STREAM + output, peek8(DATA + source + index))
                output += 1
            block += 1
        index += 1
    index = 0
    while index < ecc_degree:
        block = 0
        while block < block_count:
            poke8(STREAM + output, peek8(ECC + block * ecc_degree + index))
            output += 1
            block += 1
        index += 1


def function_module(x, y, dark):
    plot(x, y, 2 | dark)


def finder(cx, cy):
    global size
    dy = -4
    while dy <= 4:
        dx = -4
        while dx <= 4:
            x = cx + dx
            y = cy + dy
            if x >= 0 and x < size and y >= 0 and y < size:
                ax = dx
                ay = dy
                if ax < 0:
                    ax = -ax
                if ay < 0:
                    ay = -ay
                distance = ax
                if ay > distance:
                    distance = ay
                function_module(x, y, distance != 2 and distance != 4)
            dx += 1
        dy += 1


def alignment(cx, cy):
    dy = -2
    while dy <= 2:
        dx = -2
        while dx <= 2:
            dark = 1
            if (dx == -1 or dx == 1) and dy >= -1 and dy <= 1:
                dark = 0
            if (dy == -1 or dy == 1) and dx >= -1 and dx <= 1:
                dark = 0
            function_module(cx + dx, cy + dy, dark)
            dx += 1
        dy += 1


def draw_functions():
    global size, profile, version
    fill(MATRIX, 4096, 0)
    index = 0
    while index < size:
        function_module(6, index, (index & 1) == 0)
        function_module(index, 6, (index & 1) == 0)
        index += 1
    finder(3, 3)
    finder(size - 4, 3)
    finder(3, size - 4)
    count = peek8(profile + 12)
    i = 0
    while i < count:
        j = 0
        while j < count:
            if not ((i == 0 and j == 0) or (i == 0 and j == count - 1) or (i == count - 1 and j == 0)):
                alignment(peek8(profile + 13 + i), peek8(profile + 13 + j))
            j += 1
        i += 1
    format_word = peek16(profile + 16)
    index = 0
    while index < 15:
        dark = (format_word >> index) & 1
        if index < 6:
            function_module(8, index, dark)
        if index == 6:
            function_module(8, 7, dark)
        if index == 7:
            function_module(8, 8, dark)
        if index == 8:
            function_module(7, 8, dark)
        if index >= 9:
            function_module(14 - index, 8, dark)
        if index < 8:
            function_module(size - 1 - index, 8, dark)
        else:
            function_module(8, size - 15 + index, dark)
        index += 1
    function_module(8, size - 8, 1)
    if version >= 7:
        version_lo = peek16(profile + 18)
        version_hi = peek8(profile + 20)
        index = 0
        while index < 18:
            if index < 16:
                dark = (version_lo >> index) & 1
            else:
                dark = (version_hi >> (index - 16)) & 1
            x = size - 11 + index % 3
            y = index // 3
            function_module(x, y, dark)
            function_module(y, x, dark)
            index += 1


def generate():
    global size, raw_words, stage
    stage = 5
    text("Генерация\n")
    encode_data()
    encode_ecc()
    draw_functions()
    place(size, raw_words)
    mask(size)
    stage = 6
    render(size)
    fill(INPUT, 768, 0)
    fill(DATA, 384, 0)
    fill(ECC, 256, 0)
    fill(STREAM, 384, 0)


def main():
    global version, ec_level, input_mode, max_length, input_length
    global profile, size, data_words, raw_words, ecc_degree, block_count, stage
    putc(12)
    while 1:
        input_length = 0
        stage = 1
        text("Версия QR:\n1=21 2=25\n3=29 4=33\n5=37 6=41\n7=45 8=49\n9=53 10=57\n")
        version = choice(10, 2)
        if version != 0:
            stage = 2
            text("Коррекция:\n1 L  7%\n2 M 15%\n3 Q 25%\n4 H 30%\n")
            ec_level = choice(4, 1)
            if ec_level != 0:
                stage = 3
                text("Тип ввода:\n1 Цифры\n2 Алфавит\n3 CP1251\n")
                input_mode = choice(3, 1)
                if input_mode != 0:
                    profile = PROFILES + ((version - 1) * 4 + ec_level - 1) * 32
                    size = peek8(profile + 1)
                    data_words = peek16(profile + 2)
                    raw_words = peek16(profile + 4)
                    ecc_degree = peek8(profile + 6)
                    block_count = peek8(profile + 7)
                    max_length = peek16(profile + 22 + (input_mode - 1) * 2)
                    stage = 4
                    text("QR ")
                    decimal(version)
                    putc(45)
                    putc(peek8(EC_LETTERS + ec_level - 1))
                    putc(10)
                    if read_input():
                        generate()
