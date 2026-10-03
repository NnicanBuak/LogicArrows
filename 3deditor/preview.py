"""Capture the actual native LCD/terminal, with a tutorial-style key overlay."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from native import Native, ROOT
from machine import Machine
from verify import frame

LABELS = {17: '←', 18: '↑', 19: '→', 20: '↓', 10: 'Enter', 9: 'Tab',
          27: 'Esc', 127: 'Del', 8: '⌫'}
# Sequential input, no simultaneous keys. F2 forwards 27 only in this test.
SEQUENCE = [[10], [9], [10], list(map(ord, 'gx2\n')), list(map(ord, 'rz30\n')),
            list(map(ord, 'sx2\n')), list(map(ord, 'sx0.5\n')), [27],
            list(map(ord, '2')), [10], [19], list(map(ord, 'gz-1\n')),
            list(map(ord, '3')), [10], [9], list(map(ord, 'sy0.5\n')),
            list(map(ord, '++j++i++l++k++')), list(map(ord, '1a')), [127]]


def main():
    native = Native(headless=True)
    native.idle()
    check = Machine()
    check.idle()
    fonts = [Path('C:/Windows/Fonts/seguisym.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    font_path = next(p for p in fonts if p.exists())
    font = ImageFont.truetype(str(font_path), 25)
    frames, durations, events = [], [], []

    def capture(key=None, duration=180):
        # Every displayed pixel and character comes from the native emulator.
        p = native.pygame
        native.machine.update_display()
        display = Image.frombytes('RGB', (512, 512), p.image.tobytes(native.machine.display, 'RGB'))
        terminal = native.terminal_surface(scale=3)
        console = Image.frombytes('RGB', terminal.get_size(), p.image.tobytes(terminal, 'RGB'))
        canvas = Image.new('RGB', (384, 558), 'white')
        canvas.paste(display.resize((384, 384), Image.Resampling.NEAREST), (0, 0))
        canvas.paste(console, ((384 - console.width) // 2, 396))
        if key is not None:
            label = LABELS.get(key, chr(key))
            draw = ImageDraw.Draw(canvas)
            w = max(45, int(draw.textlength(label, font=font)) + 22)
            draw.rounded_rectangle(((384 - w) // 2, 514, (384 + w) // 2, 551), 7, fill='#24262b')
            draw.text((192, 532), label, font=font, fill='white', anchor='mm')
        frames.append(canvas)
        durations.append(duration)

    capture(duration=1300)
    for stage in SEQUENCE:
        for code in stage:
            native.press(code, testing=True)
            check.type([code])
            assert native.snapshot() == check.snapshot(), ('native geometry', code)
            assert native.displayed() == bytes(check.front), ('native pixels', code)
            for field in ['mode', 'cursor', 'tool', 'input_length', 'zoom', 'last_error']:
                assert native.variable(field) == check.variable(field), ('native state', code, field)
            frame(check)
            events.append(code)
            capture(code, 400)
            capture(duration=120)
            print(f'key {len(events)}: code {code}', flush=True)
        durations[-1] += 500
    assert native.displayed() == bytes(64) and not check.vertices()
    assert native.variable('zoom') == 30
    assert not any(event['key'] == native.pygame.K_ESCAPE for event in native.native_events)
    durations[-1] += 1500
    frames[0].save(ROOT / 'preview.png')
    frames[0].save(ROOT / 'preview.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=True)
    with Image.open(ROOT / 'preview.gif') as gif:
        assert gif.info['loop'] == 0
        metadata = dict(program_sha256=hashlib.sha256((ROOT / '3deditor.bin').read_bytes()).hexdigest(),
                        source='unmodified Computer v2 emulator executing ASM; LCD and terminal captured directly',
                        frames=gif.n_frames, duration_ms=sum(durations), native_keyboard_events=len(events),
                        escape_test_adapter='F2 -> 27; no native Escape KEYDOWN',
                        final_display_empty=True, zoom_maximum=3, canvas_size=[384, 558],
                        geometry_and_pixels_match_independent_checks=True, keys=events)
    (ROOT / 'preview.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: metadata[k] for k in ['frames', 'duration_ms', 'native_keyboard_events']}), flush=True)


if __name__ == '__main__':
    main()
