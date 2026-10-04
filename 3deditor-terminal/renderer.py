"""Render the 3DEditor mesh directly into 24x9 terminal bitmap glyphs."""
import json
import math
from pathlib import Path
import time


WIDTH, HEIGHT = 24 * 6, 9 * 8
CHAR_W, CHAR_H = 6, 8


class Renderer:
    def __init__(self, program, columns=24, rows=9):
        if (columns, rows) != (24, 9):
            raise ValueError('3DEditor Terminal uses a 24x9 pixel-glyph frame')
        self.program = program
        self.machine = program.machine
        self.pygame = program.pygame
        self.machine.terminal_frame_mode = True
        self.machine.enable_console = 1
        self.constants = dict(program.profile['constants'])
        layout_path = Path(__file__).resolve().parent.parent / '3deditor' / 'layout.json'
        layout = json.loads(layout_path.read_text(encoding='utf-8'))
        self.constants.update(layout['constants'])
        self.variables = dict(program.profile['variables'])
        self.variables.update(layout['variables'])
        self.status = ''
        self._fingerprint = None
        self._blink = -1

    def word(self, address):
        value = self.machine.memory[address] | (self.machine.memory[address + 1] << 8)
        return value - 65536 if value & 32768 else value

    def value(self, name):
        return self.word(self.variables[name])

    def fingerprint(self):
        c = self.constants
        v = self.variables
        mem = self.machine.memory
        mesh = bytes(mem[c['MESH']:c['MESH'] + c['MESH_BYTES']])
        select = bytes(mem[c['SELECT']:c['SELECT'] + 128])
        state = tuple(self.word(v[name]) for name in
                      ('cursor', 'editing', 'mode', 'projection', 'view_yaw', 'view_pitch', 'zoom', 'tool', 'gizmo'))
        blink = int(time.monotonic() * 2) & 1
        return mesh, select, state, blink

    def mesh(self):
        c, mem = self.constants, self.machine.memory
        counts = mem[c['COUNTS']:c['COUNTS'] + 3]
        vertices, edges, faces = {}, [], []
        for i in range(counts[0]):
            if mem[c['VLIVE'] + i]:
                base = c['VERTICES'] + i * 6
                vertices[i] = [self.word(base + axis * 2) / 16 for axis in range(3)]
        for i in range(counts[1]):
            if mem[c['ELIVE'] + i]:
                edges.append((i, mem[c['EDGES'] + i * 2], mem[c['EDGES'] + i * 2 + 1]))
        for i in range(counts[2]):
            base = c['FACES'] + i * 5
            n = mem[base]
            if n in (3, 4):
                faces.append((i, tuple(mem[base + 1:base + 1 + n])))
        return vertices, edges, faces

    def project(self, point):
        yaw = self.value('view_yaw') * math.tau / 32
        pitch = self.value('view_pitch') * math.tau / 32
        x, y, z = point
        x, z = math.cos(yaw) * x + math.sin(yaw) * z, math.cos(yaw) * z - math.sin(yaw) * x
        y, z = math.cos(pitch) * y + math.sin(pitch) * z, math.cos(pitch) * z - math.sin(pitch) * y
        zoom = self.value('zoom') / 10
        if self.value('projection'):
            sx, sy = x / 2, -y / 2
        else:
            depth = 32 + z
            if depth <= 1:
                return None
            sx, sy = 16 * x / depth, -16 * y / depth
        scale = 4.5 * zoom
        return (self._round(WIDTH / 2 + sx * scale),
                self._round(HEIGHT / 2 + sy * scale))

    @staticmethod
    def _round(value):
        return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)

    def render(self):
        p = self.pygame
        frame = p.Surface((WIDTH, HEIGHT))
        frame.fill((255, 255, 255))
        vertices, edges, faces = self.mesh()
        points = {i: self.project(point) for i, point in vertices.items()}
        mode = self.value('mode')
        editing = bool(self.value('editing'))
        cursor = self.value('cursor')
        selection_base = self.constants['SELECT'] + (0 if mode == 1 else 32 if mode == 2 else 96)
        selected = lambda index: bool(self.machine.memory[selection_base + index])
        count = self.machine.memory[self.constants['COUNTS'] + mode - 1]
        active_cursor = editing and 0 <= cursor < count
        if active_cursor:
            alive_base = self.constants['VLIVE'] if mode == 1 else self.constants['ELIVE']
            if mode in (1, 2):
                active_cursor = bool(self.machine.memory[alive_base + cursor])
            else:
                active_cursor = bool(self.machine.memory[self.constants['FACES'] + cursor * 5])
        cursor_visible = active_cursor and ((int(time.monotonic() * 2) & 1) == 0)

        if editing and mode == 3:
            for index, face in faces:
                polygon = [points[v] for v in face if v in points and points[v] is not None]
                if len(polygon) == len(face):
                    if selected(index):
                        p.draw.polygon(frame, (208, 208, 208), polygon)
                    self.hatch_polygon(frame, polygon, 3 if selected(index) else 6)
                    p.draw.polygon(frame, (48, 48, 48), polygon, 1)

        for index, a, b in edges:
            if a not in points or b not in points or points[a] is None or points[b] is None:
                continue
            if editing and mode == 1:
                continue
            if editing and mode == 3:
                continue
            width = 2 if editing and mode == 2 and selected(index) else 1
            if not editing and index % 2 == 0:
                # Different edge cadence preserves the viewer's alternating line cue in monochrome.
                self.dashed_line(frame, points[a], points[b])
            else:
                p.draw.line(frame, (24, 24, 24), points[a], points[b], width)

        if editing and mode == 1:
            for index, point in points.items():
                if point is not None:
                    p.draw.circle(frame, (24, 24, 24), (self._round(point[0]), self._round(point[1])),
                                  3 if selected(index) else 2, 1 if selected(index) else 0)

        if active_cursor and cursor_visible:
            if mode == 1 and cursor in points and points[cursor] is not None:
                q = points[cursor]
                p.draw.circle(frame, (0, 0, 0), (self._round(q[0]), self._round(q[1])), 5, 1)
            elif mode == 2:
                edge = next((item for item in edges if item[0] == cursor), None)
                if edge and edge[1] in points and edge[2] in points:
                    p.draw.line(frame, (0, 0, 0), points[edge[1]], points[edge[2]], 3)
            elif mode == 3:
                face = next((item for item in faces if item[0] == cursor), None)
                if face:
                    poly = [points[i] for i in face[1] if i in points and points[i] is not None]
                    if len(poly) == len(face[1]):
                        p.draw.polygon(frame, (0, 0, 0), poly, 2)
        if self.value('gizmo'):
            self.draw_gizmo(frame)
        return frame

    def draw_gizmo(self, frame):
        yaw = self.value('view_yaw') * math.tau / 32
        pitch = self.value('view_pitch') * math.tau / 32
        base = (WIDTH - 24, HEIGHT - 22)
        labels = ('X', 'Y', 'Z')
        for axis, vector in enumerate(((1, 0, 0), (0, 1, 0), (0, 0, 1))):
            x, y, z = vector
            x, z = math.cos(yaw) * x + math.sin(yaw) * z, math.cos(yaw) * z - math.sin(yaw) * x
            y, z = math.cos(pitch) * y + math.sin(pitch) * z, math.cos(pitch) * z - math.sin(pitch) * y
            dx, dy = x / 2, -y / 2
            length = max(abs(dx), abs(dy), 0.01)
            end = (base[0] + self._round(dx * 15 / length),
                   base[1] + self._round(dy * 15 / length))
            self.pygame.draw.line(frame, (0, 0, 0), base, end, 1)
            font = self.pygame.font.Font(None, 13)
            label = font.render(labels[axis], False, (0, 0, 0))
            frame.blit(label, (end[0] - 3, end[1] - 5))

    def dashed_line(self, surface, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        steps = max(1, int(max(abs(dx), abs(dy))))
        for n in range(0, steps, 4):
            end = min(n + 2, steps)
            self.pygame.draw.line(surface, (24, 24, 24),
                                  (self._round(a[0] + dx * n / steps), self._round(a[1] + dy * n / steps)),
                                  (self._round(a[0] + dx * end / steps), self._round(a[1] + dy * end / steps)))

    def hatch_polygon(self, surface, polygon, spacing):
        low = max(0, min(point[1] for point in polygon))
        high = min(HEIGHT - 1, max(point[1] for point in polygon))
        for y in range(low, high + 1, spacing):
            crossings = []
            for i, (x1, y1) in enumerate(polygon):
                x2, y2 = polygon[(i + 1) % len(polygon)]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    crossings.append(round(x1 + (y - y1) * (x2 - x1) / (y2 - y1)))
            crossings.sort()
            for i in range(0, len(crossings) - 1, 2):
                left = max(0, crossings[i])
                right = min(WIDTH - 1, crossings[i + 1])
                if left <= right:
                    self.pygame.draw.line(surface, (32, 32, 32), (left, y), (right, y))

    def encode_and_write(self, frame):
        machine = self.machine
        machine.enable_console = 1
        machine.write(0x3C, 0x0C)
        pixels = self.pygame.image.tostring(frame, 'RGB')
        for row in range(9):
            for cell_x in range(24):
                for column in range(6):
                    value = 0
                    x = cell_x * CHAR_W + column
                    for ybit in range(CHAR_H):
                        y = row * CHAR_H + ybit
                        if pixels[(y * WIDTH + x) * 3] < 128:
                            value |= 1 << ybit
                    machine.write(0x3D, value)

    def make_status(self):
        editing = bool(self.value('editing'))
        mode = self.value('mode')
        projection = 'ORTHO' if self.value('projection') else 'PERSP'
        tool = self.value('tool')
        errors = {1: 'ERR FORMAT', 2: 'ERR RANGE', 3: 'PRECISION', 4: 'ERR EMPTY',
                  5: 'CAPACITY', 6: 'TOPOLOGY', 7: 'AXIS x/y/z'}
        error = errors.get(self.value('last_error'))
        if error:
            return error + ' ENTER'
        if self.value('gizmo'):
            return 'GIZMO ARROWS ESC'
        if tool:
            names = {103: 'M', 114: 'R', 115: 'S', 110: 'N'}
            c = self.constants
            length = max(0, min(12, self.value('input_length')))
            command = bytes(self.machine.memory[c['INPUT']:c['INPUT'] + length]).decode('ascii', 'ignore')
            return f'{names.get(tool, "E")}:{command[:10]} ENT OK ESC'
        if not editing:
            return f'VIEW {projection} ARW +/- SPACE'
        names = {1: 'VERTICES', 2: 'EDGES', 3: 'FACES'}
        return f'EDIT {names.get(mode, "MODEL")} ENTER TAB'

    def refresh(self):
        fingerprint = self.fingerprint()
        self.status = self.make_status()
        if fingerprint == self._fingerprint:
            return
        self._fingerprint = fingerprint
        self.encode_and_write(self.render())
