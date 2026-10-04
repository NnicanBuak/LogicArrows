"""Build-time QR Model 2 tables for versions 1–10.

ECC degrees/block counts: Project Nayuki (MIT), QR-Code-generator/python,
https://github.com/nayuki/QR-Code-generator/blob/master/python/qrcodegen.py
Capacity reference: https://www.qrcode.com/en/about/versionPage/versionPage1_10.html
"""

ECC_DEGREES = (
    (7, 10, 15, 20, 26, 18, 20, 24, 30, 18),
    (10, 16, 26, 18, 24, 16, 18, 22, 22, 26),
    (13, 22, 18, 26, 18, 24, 18, 22, 20, 24),
    (17, 28, 22, 16, 22, 28, 26, 26, 24, 28),
)
BLOCK_COUNTS = (
    (1, 1, 1, 1, 1, 2, 2, 2, 2, 4),
    (1, 1, 1, 2, 2, 4, 4, 4, 5, 5),
    (1, 1, 2, 2, 4, 4, 6, 6, 8, 8),
    (1, 1, 2, 4, 4, 4, 5, 6, 8, 8),
)
ALPHABET = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'


def raw_codewords(version):
    bits = (16 * version + 128) * version + 64
    if version >= 2:
        alignments = version // 7 + 2
        bits -= (25 * alignments - 10) * alignments - 55
        if version >= 7:
            bits -= 36
    return bits // 8


def capacity(data_words, version, mode):
    count_bits = ((10, 12), (9, 11), (8, 16))[mode - 1][version >= 10]
    overhead = 4 + count_bits + (12 if mode == 3 else 0)
    count = 0
    while True:
        n = count + 1
        bits = ((n // 3) * 10 + (0, 4, 7)[n % 3] if mode == 1 else
                (n // 2) * 11 + (n % 2) * 6 if mode == 2 else n * 8)
        if overhead + bits > data_words * 8 or n >= (1 << count_bits):
            return count
        count = n


def gf_mul(x, y):
    result = 0
    for _ in range(8):
        if y & 1:
            result ^= x
        y >>= 1
        x <<= 1
        if x & 256:
            x ^= 0x11D
    return result


def divisor(degree):
    coefficients = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for i in range(degree):
            coefficients[i] = gf_mul(coefficients[i], root)
            if i + 1 < degree:
                coefficients[i] ^= coefficients[i + 1]
        root = gf_mul(root, 2)
    return bytes(coefficients)


def field_tables():
    logarithms = bytearray(256)
    exponents = bytearray(512)
    value = 1
    for i in range(255):
        exponents[i] = value
        logarithms[value] = i
        value = gf_mul(value, 2)
    for i in range(255, 512):
        exponents[i] = exponents[i - 255]
    return logarithms, exponents


def bch(value, shifts, polynomial):
    remainder = value
    for _ in range(shifts):
        remainder = (remainder << 1) ^ ((remainder >> (shifts - 1)) * polynomial)
    return (value << shifts) | remainder


def profiles(divisors):
    data = bytearray()
    records = []
    for version in range(1, 11):
        size = version * 4 + 17
        positions = [] if version == 1 else ([6, size - 7] if version < 7 else [6, size // 2, size - 7])
        for level, letter in enumerate('LMQH'):
            degree = ECC_DEGREES[level][version - 1]
            blocks = BLOCK_COUNTS[level][version - 1]
            raw = raw_codewords(version)
            words = raw - degree * blocks
            row = bytearray(32)
            row[:2] = bytes([version, size])
            row[2:4] = words.to_bytes(2, 'little')
            row[4:6] = raw.to_bytes(2, 'little')
            row[6:10] = bytes([degree, blocks, blocks - raw % blocks, raw // blocks - degree])
            row[10:12] = divisors[degree].to_bytes(2, 'little')
            row[12] = len(positions)
            row[13:13 + len(positions)] = bytes(positions)
            row[16:18] = (bch((1, 0, 3, 2)[level] << 3, 10, 0x537) ^ 0x5412).to_bytes(2, 'little')
            row[18:21] = bch(version, 12, 0x1F25).to_bytes(3, 'little')
            limits = [capacity(words, version, mode) for mode in (1, 2, 3)]
            for i, n in enumerate(limits):
                row[22 + i * 2:24 + i * 2] = n.to_bytes(2, 'little')
            data.extend(row)
            records.append(dict(version=version, size=size, correction=letter, data_codewords=words,
                                raw_codewords=raw, ecc_degree=degree, blocks=blocks,
                                numeric=limits[0], alphanumeric=limits[1], cp1251=limits[2]))
    return data, records
