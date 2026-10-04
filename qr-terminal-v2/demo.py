"""Capture QR Terminal v2 from the repository's actual Computer v2 emulator."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path.insert(0, str(ROOT.parent / 'emulator'))
sys.path.insert(0, str(ROOT / 'tools/oracle'))
from backend import Program
from qrcodegen import QrCode, QrSegment
from verify import raster


def run():
    layout = json.loads((ROOT / 'layout.json').read_text(encoding='utf-8'))
    report = []
    for version, level, message in ((1, 1, 'Привет, QR!'), (10, 4, 'Привет, QR Terminal v2!')):
        start = time.perf_counter()
        program = Program(ROOT / 'qr_terminal_v2.asm', terminal_size=(12, 18))
        assert program.image == (ROOT / 'qr_terminal_v2.bin').read_bytes(), 'Assembler images differ'
        graphics = []
        previous = program.machine.update_ports

        def capture(address, value):
            if address == 61:
                graphics.append(value)
            previous(address, value)

        program.machine.update_ports = capture
        program.idle()
        for code in f'{version}\n{level}\n3\n'.encode('ascii') + message.encode('cp1251') + b'\n':
            program.press(code)
        ecl = [QrCode.Ecc.LOW, QrCode.Ecc.MEDIUM, QrCode.Ecc.QUARTILE, QrCode.Ecc.HIGH][level - 1]
        qr = QrCode.encode_segments([QrSegment.make_eci(22), QrSegment.make_bytes(message.encode('cp1251'))],
                                    ecl, version, version, 0, False)
        base = layout['constants']['MATRIX']
        memory = program.machine.memory
        size = qr.get_size()
        assert all((memory[base + y * 64 + x] & 1) == qr.get_module(x, y)
                   for y in range(size) for x in range(size)), 'Native QR matrix differs'
        assert bytes(graphics) == raster(qr), 'Native terminal raster differs'
        assert program.word(layout['variables']['stage']) == 1, 'Cycle did not restart'
        program.pygame.image.save(program.terminal_surface(scale=4), str(ROOT / f'demo-v{version}.png'))
        report.append(dict(version=version, correction='LMQH'[level - 1],
                           matrix_matches=True, raster_matches=True, cycle_restarted=True,
                           graphics_bytes=len(graphics), seconds=round(time.perf_counter() - start, 2)))
        print(report[-1], flush=True)
    (ROOT / 'native-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    run()
