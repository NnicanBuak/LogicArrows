"""Verify every version/correction/mode at capacity against independent QR output."""
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/oracle'))
from qrcodegen import DataTooLongError, QrCode, QrSegment


def raster(qr):
    size = qr.get_size()
    extent = size + 8
    width = (extent + 5) // 6 * 6
    output = bytearray()
    for base in range(0, extent, 8):
        for x in range(width):
            output.append(sum(int(qr.get_module(x - 4, base + bit - 4)) << bit for bit in range(8)))
    return output


def segment(payload, mode):
    if mode == 1:
        return [QrSegment.make_numeric(payload.decode('ascii'))]
    if mode == 2:
        return [QrSegment.make_alphanumeric(payload.decode('ascii'))]
    return [QrSegment.make_eci(22), QrSegment.make_bytes(payload)]


def verify():
    layout = json.loads((ROOT / 'layout.json').read_text(encoding='utf-8'))
    image = (ROOT / 'qr_terminal_v2.bin').read_bytes()
    assert len(image) == layout['image_bytes'] <= 32768
    patterns = [b'01234567890123456789', b'HELLO QR 123 $%*+-./:', 'Привет, QR! Ёё: 123.'.encode('cp1251')]
    levels = [QrCode.Ecc.LOW, QrCode.Ecc.MEDIUM, QrCode.Ecc.QUARTILE, QrCode.Ecc.HIGH]
    fixtures = []
    for record in layout['capacities']:
        version = record['version']
        level = 'LMQH'.index(record['correction'])
        for mode, field in enumerate(('numeric', 'alphanumeric', 'cp1251'), 1):
            capacity = record[field]
            pattern = patterns[mode - 1]
            payload = (pattern * (capacity // len(pattern) + 1))[:capacity]
            qr = QrCode.encode_segments(segment(payload, mode), levels[level], version, version, 0, False)
            try:
                QrCode.encode_segments(segment(payload + pattern[:1], mode), levels[level], version, version, 0, False)
            except DataTooLongError:
                pass
            else:
                raise AssertionError((record, mode, 'capacity too small'))
            matrix = bytes(qr.get_module(x, y) for y in range(record['size']) for x in range(record['size']))
            encoded = lambda value: base64.b64encode(value).decode('ascii')
            invalid = ([65, 32, 127, 152, 17, 9] if mode == 1 else
                       [97, 192, 127, 152, 17, 9] if mode == 2 else [31, 127, 152, 17, 9])
            fixtures.append(dict(name=f'v{version}-{record["correction"]}-mode{mode}',
                                 version=version, level=level + 1, mode=mode, size=record['size'],
                                 capacity=capacity, payload=encoded(payload), overflow=encoded(pattern[:3]),
                                 invalid=invalid, matrix=encoded(matrix), raster=encoded(raster(qr))))
    with tempfile.TemporaryDirectory(prefix='qr-terminal-v2-') as temporary:
        inputs = Path(temporary) / 'fixtures.json'
        inputs.write_text(json.dumps(fixtures), encoding='utf-8')
        subprocess.run(['node', str(ROOT / 'tools/verify.mjs'), str(inputs), str(ROOT / 'verification.json')], check=True)


if __name__ == '__main__':
    verify()
