"""Render a minimal keyboard demo from actual Computer v2 emulator frames."""
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DISPLAY_SIZE = 384
CANVAS_SIZE = (DISPLAY_SIZE, DISPLAY_SIZE + 48)
COLORS = [(255, 255, 255), (255, 0, 0), (76, 128, 255), (165, 64, 128)]
KEY_LABELS = {0x11: "←", 0x12: "↑", 0x13: "→", 0x14: "↓",
              ord("+"): "+", ord("-"): "−", ord(" "): "Space"}
TIMING_MULTIPLIER = 2
SEQUENCE = [(ord("+"), 10), (0x13, 8), (ord("-"), 5),
            (0x12, 8), (ord("+"), 5), (0x11, 8),
            (ord("-"), 8), (0x14, 8), (ord("+"), 8)]


def render_preview(displayed, press, read_state, output=ROOT):
    """Only the 16×16 display and a pulsing keycap; reset closes the loop."""
    fonts = [Path("C:/Windows/Fonts/seguisym.ttf"),
             Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
             Path("C:/Windows/Fonts/arial.ttf")]
    font_path = next((path for path in fonts if path.exists()), None)
    key_font = ImageFont.truetype(str(font_path), 30) if font_path else ImageFont.load_default(size=30)
    frames, durations, events, stages = [], [], [], []

    def capture(key=None, duration=70):
        pixels = displayed()
        assert len(pixels) == 64
        assert any(pixels), "The cube must remain visible throughout the demo"
        screen = Image.new("RGB", (16, 16), "white")
        for y in range(16):
            for x in range(16):
                address, mask = 2 * y + x // 8, 128 >> (x % 8)
                color = int(bool(pixels[address] & mask)) + 2 * int(bool(pixels[address + 32] & mask))
                screen.putpixel((x, y), COLORS[color])
        frame = Image.new("RGB", CANVAS_SIZE, "white")
        frame.paste(screen.resize((DISPLAY_SIZE, DISPLAY_SIZE), Image.Resampling.NEAREST), (0, 0))
        if key is not None:
            # The keycap sits below the raster, leaving every LCD pixel visible.
            draw = ImageDraw.Draw(frame)
            width = max(48, int(draw.textlength(KEY_LABELS[key], font=key_font)) + 22)
            left = (DISPLAY_SIZE - width) // 2
            top = DISPLAY_SIZE + 6
            draw.rounded_rectangle((left, top, left + width, top + 35), radius=7,
                                   fill="#24262b", outline="#454850", width=1)
            draw.text((DISPLAY_SIZE // 2, top + 16), KEY_LABELS[key],
                      fill="white", font=key_font, anchor="mm")
        frames.append(frame)
        durations.append(duration)

    # A new loop starts at the same state as launching the program.
    press(ord(" "))
    assert any(displayed())
    assert read_state() == dict(yaw=4, pitch=3, scale=10)
    capture(duration=650)
    for key, count in SEQUENCE:
        for _ in range(count):
            press(key)
            events.append(key)
            capture(key, 140)
            capture(duration=60)
        durations[-1] += 300
        state = read_state()
        stages.append(dict(key=KEY_LABELS[key], code=key, count=count,
                           scale=state["scale"] / 10,
                           yaw=state["yaw"], pitch=state["pitch"]))

    assert stages[0]["scale"] == 3 and stages[-1]["scale"] == 3
    assert {stage["code"] for stage in stages if 17 <= stage["code"] <= 20} == {17, 18, 19, 20}

    # Hold maximum zoom, then reset the view for a seamless loop.
    durations[-1] += 650
    capture(ord(" "), 180)
    press(ord(" "))
    events.append(ord(" "))
    assert read_state() == dict(yaw=4, pitch=3, scale=10)
    capture(ord(" "), 420)
    capture(duration=650)
    assert frames[-1].tobytes() == frames[0].tobytes(), "The loop must end at its initial view"
    durations = [duration * TIMING_MULTIPLIER for duration in durations]

    output.mkdir(parents=True, exist_ok=True)
    frames[0].save(output / "preview.png")
    frames[0].save(output / "preview.gif", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=True)
    with Image.open(output / "preview.gif") as gif:
        assert gif.info["loop"] == 0 and gif.size == CANVAS_SIZE
        encoded_duration = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            encoded_duration += gif.info["duration"]
        assert encoded_duration == sum(durations)
        assert gif.convert("RGB").tobytes() == frames[0].tobytes()
        encoded_frames = gif.n_frames
    metadata = dict(
        program_sha256=hashlib.sha256((output / "3dviewer.bin").read_bytes()).hexdigest(),
        source="unmodified native emulator after KEYDOWN events",
        display_resolution=[16, 16], canvas_size=list(CANVAS_SIZE),
        source_frames=len(frames), encoded_frames=encoded_frames,
        duration_ms=sum(durations), loop=0, keyboard_events=len(events),
        timing_multiplier=TIMING_MULTIPLIER, playback_speed=1 / TIMING_MULTIPLIER,
        key_press_ms=140 * TIMING_MULTIPLIER, key_release_ms=60 * TIMING_MULTIPLIER,
        maximum_zoom=3, maximum_zoom_reached=True,
        zoom_step=0.2,
        all_arrow_directions=True, rotation_alternates_with_zoom=True, stages=stages,
        sequence=[dict(key=KEY_LABELS[key], code=key, count=count) for key, count in SEQUENCE]
                 + [dict(key="Space", code=32, count=1)],
        key_overlay_only=True, overlay_covers_display=False, final_display_empty=False,
        final_view_reset=True, cube_visible_in_all_frames=True, delete_key_shown=False,
    )
    (output / "preview.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main():
    import sys
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
    vendor = ROOT.parent / "graphics3d/vendor/emulator"
    sys.path.insert(0, str(vendor))
    os.chdir(vendor)
    import pygame
    from emulator import Emulator

    layout = json.loads((ROOT / "layout.json").read_text(encoding="utf-8"))
    compiled = json.loads((ROOT / "3dviewer.compile.json").read_text(encoding="utf-8"))
    machine = Emulator()
    machine.filename = str(ROOT / "3dviewer.asm")
    machine.load()
    assert not machine.compilation_error
    single_step = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3, unicode="")

    def until_input():
        for _ in range(100000):
            if machine.bank == layout["banks"]["key_loop"] and machine.index == compiled["names"]["key_loop"]:
                return
            machine.update([single_step], 60)
        raise AssertionError("Preview emulator did not return to the input loop")

    keys = {
        0x11: (pygame.K_LEFT, ""), 0x12: (pygame.K_UP, ""),
        0x13: (pygame.K_RIGHT, ""), 0x14: (pygame.K_DOWN, ""),
        ord("+"): (pygame.K_EQUALS, "+"), ord("-"): (pygame.K_MINUS, "-"),
        ord(" "): (pygame.K_SPACE, " "),
    }

    def press(code):
        key, text = keys[code]
        machine.update([pygame.event.Event(pygame.KEYDOWN, key=key, unicode=text), single_step], 60)
        until_input()
        if machine.memory[62]:
            machine.update([single_step], 60)
            until_input()

    def displayed():
        result = bytearray(64)
        for y in range(16):
            for x in range(16):
                for plane in range(2):
                    if machine.colors[x][y][plane]:
                        result[32 * plane + 2 * y + x // 8] |= 128 >> (x % 8)
        return bytes(result)

    def read_state():
        return {name: machine.memory[layout["variables"][name]]
                for name in ("yaw", "pitch", "scale")}

    until_input()
    metadata = render_preview(displayed, press, read_state)
    report_path = ROOT / "verification.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["sha256"] == metadata["program_sha256"]
        report.update(preview_frames=metadata["source_frames"], preview_source=metadata["source"])
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pygame.quit()
    print(json.dumps(dict(frames=metadata["source_frames"],
                          duration_ms=metadata["duration_ms"], loop=0, final_view_reset=True)))


if __name__ == "__main__":
    main()
