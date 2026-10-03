"""Verify independent geometry, keyboard behavior and the unmodified emulator.

Uses the local Computer v2 dependencies in graphics3d/vendor; see README.md.
Run build.py and the official 1 KB compiler before this script.
"""
import hashlib
import itertools
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT.parent / "graphics3d/vendor"
layout = json.loads((ROOT / "layout.json").read_text(encoding="utf-8"))
compiled = json.loads((ROOT / "3dviewer.compile.json").read_text(encoding="utf-8"))
image = (ROOT / "3dviewer.bin").read_bytes()
assert len(image) == layout["image_bytes"] == compiled["bytes"] <= 1024
assert not compiled["errors"] and compiled["limit"] == 1024
V = layout["variables"]
STATE_NAMES = ("yaw", "pitch", "scale")
SINE = [round(8 * math.sin(i * math.tau / 32)) for i in range(32)]
assert layout["sine"] == SINE


def vertices(yaw, pitch, scale):
    sy, cy = SINE[yaw], SINE[(yaw + 8) % 32]
    sp, cp = SINE[pitch], SINE[(pitch + 8) % 32]
    result = []
    for index in range(8):
        x, y, z = (1 if index & bit else -1 for bit in (1, 2, 4))
        horizontal = 8 * (x * cy + z * sy)
        vertical = -x * sy * sp + 8 * y * cp + z * cy * sp
        assert -128 <= horizontal <= 127 and -128 <= vertical <= 127
        point = (8 + horizontal * scale // 256, 8 + vertical * scale // 256)
        assert all(-128 <= coordinate <= 127 for coordinate in point), (yaw, pitch, scale, point)
        result.append(point)
    return result


def reference(state):
    points = vertices(*state)
    frame = bytearray(64)
    edges = [(i, i ^ bit) for bit in (1, 2, 4) for i in range(8) if not i & bit]
    assert edges == [tuple(e) for e in layout["edges"]]
    for index, (a, b) in enumerate(edges):
        (x, y), (end_x, end_y) = points[a], points[b]
        if x > end_x:
            x, y, end_x, end_y = end_x, end_y, x, y
        dx, dy = abs(end_x - x), abs(end_y - y)
        step_y = 1 if y < end_y else -1
        error = dx - dy
        plane = 32 if index % 2 == 0 else 0
        while True:
            if 0 <= x < 16 and 0 <= y < 16:
                frame[plane + 2 * y + x // 8] |= 128 >> (x % 8)
            if (x, y) == (end_x, end_y):
                break
            doubled = error * 2
            # The byte CPU uses signs for these two Bresenham comparisons.
            assert all(-128 <= value <= 127 for value in
                       (error, doubled, doubled + dy, dx - doubled)), state
            if doubled >= -dy:
                error -= dy
                x += 1
            if doubled <= dx:
                error += dx
                y += step_y
    return bytes(frame)


def transition(state, key):
    yaw, pitch, scale = state
    if key == ord(" "):
        return 4, 3, 10
    if key == 0x11:
        yaw = (yaw - 1) % 32
    elif key == 0x13:
        yaw = (yaw + 1) % 32
    elif key == 0x12:
        pitch = (pitch - 1) % 32
    elif key == 0x14:
        pitch = (pitch + 1) % 32
    elif key in (ord("+"), ord("=")):
        scale = min(30, scale + 2)
    elif key == ord("-"):
        scale = max(5, scale - 2)
    return yaw, pitch, scale


# Geometry may extend past the viewport; all arithmetic must still fit a byte.
clipped_states = 0
coordinate_min, coordinate_max = 127, -128
for state in itertools.product(range(32), range(32), range(5, 31)):
    coordinates = [v for point in vertices(*state) for v in point]
    coordinate_min = min(coordinate_min, *coordinates)
    coordinate_max = max(coordinate_max, *coordinates)
    clipped_states += any(v < 0 or v >= 16 for v in coordinates)
    reference(state)
zoom_bounds = {}
for scale in (10, 20, 30):
    points = vertices(4, 3, scale)
    zoom_bounds[str(scale / 10)] = [min(p[0] for p in points), min(p[1] for p in points),
                                   max(p[0] for p in points), max(p[1] for p in points)]
assert zoom_bounds["3.0"][0] < zoom_bounds["2.0"][0] < zoom_bounds["1.0"][0]
assert zoom_bounds["3.0"][2] > zoom_bounds["2.0"][2] > zoom_bounds["1.0"][2]
assert zoom_bounds["2.0"][1] < 0 and zoom_bounds["3.0"][1] < zoom_bounds["2.0"][1]
print(f"Geometry: 26624 states; {clipped_states} extend past 16x16; all raster arithmetic is safe.", flush=True)

sys.path.insert(0, str(VENDOR / "cpu_model"))
from debug_cpu import CPU


class CheckedCPU(CPU):
    def __init__(self):
        super().__init__(image)
        self.max_address = 0
        self.visible_writes = []

    def physical(self, address):
        physical = super().physical(address)
        assert 0 <= physical < 1024, physical
        self.max_address = max(self.max_address, physical)
        return physical

    def write(self, address, value):
        assert address in set(V.values()) or layout["points"] <= address < layout["points"] + 16 or 62 <= address < 128, ("write to read-only memory", address)
        if self.bank == layout["banks"]["line_pixel_store"] and self.ip == compiled["names"]["line_pixel_store"] + 1:
            assert 64 <= address < 128, ("LCD pixel escaped viewport", address)
        if 64 <= address < 128 and self.devices & 16:
            self.visible_writes.append((address, value & 255))
        return super().write(address, value)


def at(machine, name):
    return machine.bank == layout["banks"][name] and machine.ip == compiled["names"][name]


def assert_frame(machine, state):
    expected = reference(state)
    assert bytes(machine.ram[64:128]) == expected, ("CPU pixels", state)
    assert bytes(machine.ram[layout["points"]:layout["points"] + 16]) == bytes(v & 255 for p in vertices(*state) for v in p), ("CPU vertices", state)
    assert machine.devices == 48
    return expected


cpu = CheckedCPU()
cpu.until(lambda m: at(m, "key_loop"))
assert_frame(cpu, (4, 3, 10))
frame_counts = []
states = [(y, p, (y + 3 * p) % 26 + 5) for y in range(32) for p in range(32)]
states += [(y, p, 30) for y in range(32) for p in range(32)]
states += [(y, p, s) for y, p in [(0, 0), (4, 3), (12, 28), (28, 20)] for s in range(5, 31)]
for state in states:
    for name, value in zip(("yaw", "pitch", "scale"), state):
        cpu.ram[V[name]] = value
    cpu.bank, cpu.ip = layout["banks"]["frame_start"], compiled["names"]["frame_start"]
    old_screen = bytes(cpu.screen)
    cpu.visible_writes = []
    before = cpu.steps
    cpu.until(lambda m: at(m, "frame_ready"))
    assert bytes(cpu.screen) == old_screen and cpu.devices == 0
    cpu.until(lambda m: at(m, "key_loop"))
    expected = assert_frame(cpu, state)
    assert cpu.visible_writes == list(enumerate(expected, 64)), ("publish sequence", state)
    frame_counts.append(cpu.steps - before)

# Use actual input-port reads, including every byte outside the command set.
keys = [0x11] * 32 + [0x13] * 32 + [0x12] * 32 + [0x14] * 32
keys += [ord("+")] * 40 + [ord("-")] * 40 + [ord("=")] * 40 + [ord(" ")]
keys += list(range(256))
delete_noop_keys = []
for resize, count in ((ord("-"), 25), (ord("+"), 25), (0x13, 7)):
    delete_noop_keys += [ord(" ")] + [resize] * count + [0x7F]
    delete_noop_keys += [0x11, 0x12, 0x13, 0x14, ord("+"), ord("="), ord("-"), 0x7F, ord("a"), ord(" ")]
keys += delete_noop_keys
state = tuple(cpu.ram[V[name]] for name in STATE_NAMES)
cpu_delete_events = 0
for key in keys:
    before_state, before_frame = state, bytes(cpu.ram[64:128])
    state = transition(state, key)
    cpu.keys = [key]
    cpu.step()
    cpu.until(lambda m: at(m, "key_loop") and not m.keys)
    assert tuple(cpu.ram[V[name]] for name in STATE_NAMES) == state, ("CPU key", key)
    assert_frame(cpu, state)
    if key == 0x7F:
        assert state == before_state and bytes(cpu.ram[64:128]) == before_frame, "Del must leave the viewer unchanged"
        cpu_delete_events += 1
snapshot = bytes(cpu.ram)
for _ in range(3000):
    cpu.step()
assert bytes(cpu.ram) == snapshot, "Idle input loop modifies memory"
print(f"CPU: {len(states)} frames and {len(keys)} keyboard events match independent math.", flush=True)

os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
sys.path.insert(0, str(VENDOR / "emulator"))
os.chdir(VENDOR / "emulator")
import pygame
from emulator import Emulator
from compiler import compile as native_compile

native_image, log, error = native_compile((ROOT / "3dviewer.asm").read_text(encoding="utf-8"))
assert not error, log
assert bytes(native_image) == image, "Official and native compiler disagree"


class Native(Emulator):
    def __init__(self):
        super().__init__()
        self.filename = str(ROOT / "3dviewer.asm")
        self.load()
        assert not self.compilation_error
        self.steps = 0
        self.max_address = 0
        self.visible_writes = []

    def read(self, address):
        physical = address if address < 128 else address + (self.bank - 1) * 128
        assert 0 <= physical < 1024
        self.max_address = max(self.max_address, physical)
        return super().read(address)

    def write(self, address, value):
        assert address in set(V.values()) or layout["points"] <= address < layout["points"] + 16 or 62 <= address < 128, ("native write to read-only memory", address)
        physical = address if address < 128 else address + (self.bank - 1) * 128
        assert 0 <= physical < 1024
        self.max_address = max(self.max_address, physical)
        if 64 <= address < 128 and self.enable_display:
            self.visible_writes.append((address, value))
        return super().write(address, value)

    def step(self, event=None):
        self.steps += 1
        events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3, unicode="")]
        if event is not None:
            events.insert(0, event)
        self.update(events, 60)

    def at(self, name):
        return self.bank == layout["banks"][name] and self.index == compiled["names"][name]

    def until(self, name):
        for _ in range(100000):
            if self.at(name):
                return
            self.step()
        raise AssertionError(("Native timeout", name, self.bank, self.index))

    def displayed(self):
        result = bytearray(64)
        for y in range(16):
            for x in range(16):
                for plane in range(2):
                    if self.colors[x][y][plane]:
                        result[32 * plane + 2 * y + x // 8] |= 128 >> (x % 8)
        return bytes(result)


native = Native()
native.until("key_loop")
assert native.displayed() == reference((4, 3, 10))
native_states = [(y, p, s) for y, p in [(0, 0), (4, 3), (8, 8), (20, 28), (31, 31)] for s in range(5, 31)]
for state in native_states:
    for name, value in zip(("yaw", "pitch", "scale"), state):
        native.memory[V[name]] = value
    native.bank, native.index = layout["banks"]["frame_start"], compiled["names"]["frame_start"]
    old_screen = native.displayed()
    native.visible_writes = []
    native.until("frame_ready")
    assert native.displayed() == old_screen and native.enable_display == 0
    native.until("key_loop")
    expected = reference(state)
    assert native.displayed() == expected, ("Native pixels", state)
    assert native.visible_writes == list(enumerate(expected, 64))

KEYS = {
    0x11: (pygame.K_LEFT, ""), 0x12: (pygame.K_UP, ""),
    0x13: (pygame.K_RIGHT, ""), 0x14: (pygame.K_DOWN, ""),
    ord("+"): (pygame.K_EQUALS, "+"), ord("="): (pygame.K_EQUALS, "="),
    ord("-"): (pygame.K_MINUS, "-"), ord(" "): (pygame.K_SPACE, " "),
    0x7F: (pygame.K_DELETE, chr(127)),
}


def native_press(code):
    key, text = KEYS.get(code, (pygame.K_a, chr(code)))
    native.step(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=text))
    assert native.memory[62] == 0, "Input port not reset after reading"
    native.until("key_loop")
    # This emulator also exposes the last display-control write to the next read.
    # Drain that ignored code (0x30) before checking the steady idle state.
    if native.memory[62]:
        native.step()
        native.until("key_loop")


state = tuple(native.memory[V[n]] for n in STATE_NAMES)
native_keys = [0x11] * 32 + [0x13] * 32 + [0x12] * 32 + [0x14] * 32
native_keys += [ord("+")] * 40 + [ord("-")] * 40 + [ord("=")] * 40 + [ord(" "), ord("a"), ord("Я")]
native_keys += delete_noop_keys
native_delete_events = 0
for key in native_keys:
    before_state, before_frame = state, native.displayed()
    state = transition(state, key)
    native_press(key)
    assert tuple(native.memory[V[n]] for n in STATE_NAMES) == state, ("Native key", key)
    assert native.displayed() == reference(state)
    assert native.memory[62] == 0, "Input loop did not settle"
    if key == 0x7F:
        assert state == before_state and native.displayed() == before_frame, "Native Del must leave the viewer unchanged"
        native_delete_events += 1

# Shift and Ctrl by themselves are ignored by the unmodified emulator.
for key in (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LCTRL, pygame.K_RCTRL):
    native.step(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=""))
    native.until("key_loop")
    assert native.memory[62] == 0 and native.displayed() == reference(state)
print(f"Native: {len(native_states)} frames and {len(native_keys)} real KEYDOWN events match.", flush=True)

# Generate the same minimal preview as the standalone preview.py command.
from preview import render_preview
preview = render_preview(native.displayed, native_press,
                         lambda: {name: native.memory[V[name]] for name in STATE_NAMES}, ROOT)

report = dict(
    image_bytes=len(image), free_bytes=1024-len(image), limit=1024,
    sha256=hashlib.sha256(image).hexdigest(),
    official_compiler_matches_native=True, geometry_states=32*32*26,
    cpu_frames=len(states), cpu_keyboard_events=len(keys), cpu_pixel_mismatches=0,
    native_frames=len(native_states), native_keyboard_events=len(native_keys), native_pixel_mismatches=0,
    idle_memory_unchanged=True, frame_hidden_until_ready=True,
    complete_frame_publish=True, all_states_fit_screen=False,
    viewport_clipping=True, fit_to_screen=False, clipped_geometry_states=clipped_states,
    projected_coordinate_range=[coordinate_min, coordinate_max],
    initial_view_zoom_bounds=zoom_bounds, pixel_writes_inside_lcd=True,
    scale_limits=[0.5, 3], initial_scale=1, scale_step=0.2,
    scale_boundary_clamping=True, scale_levels=26, rotation_steps=32,
    ignored_delete_key_code=127, delete_key_ignored=True, delete_noop_scenarios=3,
    cpu_delete_key_events=cpu_delete_events, native_delete_key_events=native_delete_events,
    controls_work_after_delete_key=True, space_resets_view=True,
    cpu_max_address=cpu.max_address, native_max_address=native.max_address,
    instructions_per_frame_min=min(frame_counts), instructions_per_frame_max=max(frame_counts),
    preview_source=preview["source"], preview_frames=preview["source_frames"],
)
(ROOT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
pygame.quit()
print(json.dumps(report, ensure_ascii=False), flush=True)
