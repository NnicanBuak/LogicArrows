"""Common desktop launcher for Computer v2 programs, GPL-3.0.

Added 2026-10-04. Run from any directory; source is assembled at launch.
"""
import argparse
from collections import deque
import importlib.util
import json
import os
from pathlib import Path
import time

from backend import Program, load_core
from model_io import export_model, import_model


def choose_file():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    try:
        return filedialog.askopenfilename(title='Открыть программу Computer v2',
                                          filetypes=[('Исходник ASM', '*.asm')])
    finally:
        root.destroy()


class App:
    CELL_W = 24
    CELL_H = 32

    def __init__(self, program=None, model_path=None, terminal_size=None, hide_display=False,
                 terminal_renderer=None):
        self.program = None
        self.model_path = model_path
        self.terminal_size = terminal_size
        self.hide_display = hide_display
        self.renderer_path = terminal_renderer
        self.renderer = None
        self.queue = deque()
        self.running = True
        self.message = 'F4: открыть ASM'
        self.p = load_core().pygame
        width, height = (640, 420)
        if terminal_size:
            terminal_w, terminal_h = terminal_size
            if hide_display:
                width = terminal_w * self.CELL_W + 16
                height = (terminal_h + 1) * self.CELL_H + 95
            else:
                width = max(width, 340 + terminal_w * self.CELL_W + 12)
                height = max(height, 100 + (terminal_h + 1) * self.CELL_H + 90)
        self.window = self.p.display.set_mode((width, height))
        self.font = self.p.font.SysFont('Arial', 15)
        self.p.display.set_caption('Computer v2 — 32 КБ')
        if program:
            self.open(program)

    def open(self, filename):
        try:
            program = Program(filename, self.terminal_size)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.message = str(error).splitlines()[0]
            print(error)
            return False
        self.program = program
        self.renderer = None
        if self.renderer_path:
            try:
                spec = importlib.util.spec_from_file_location('computer_v2_terminal_renderer',
                                                              str(self.renderer_path))
                if spec is None or spec.loader is None:
                    raise ImportError(f'Cannot load renderer: {self.renderer_path}')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.renderer = module.Renderer(program, *self.terminal_size)
            except (OSError, ValueError, AttributeError, TypeError, ImportError) as error:
                self.message = f'Ошибка терминального рендерера: {error}'
                print(error)
                self.program = None
                return False
        self.queue.clear()
        program.machine.pause = False
        self.message = f'{program.path.name} — {len(program.image)} байт / 32 КБ'
        self.p.display.set_caption(f'{program.path.stem} — Computer v2')
        return True

    def handle(self, event):
        p = self.p
        if event.type == p.QUIT:
            self.running = False
            return
        if event.type != p.KEYDOWN:
            return
        if event.key == p.K_F4:
            filename = choose_file()
            if filename:
                self.open(filename)
            return
        program = self.program
        if not program:
            return
        if event.key == p.K_F1:
            program.machine.pause = not program.machine.pause
        elif event.key == p.K_F2:
            self.open(program.path)
        elif event.key == p.K_F3:
            program.machine.pause = True
            program.machine.update([program.single], 60)
        elif event.key in (p.K_F7, p.K_F8):
            speed = program.machine.speed
            program.machine.speed = max(60, speed // 2) if event.key == p.K_F7 else min(3_000_000, speed * 2)
            self.message = f'Скорость: {int(program.machine.speed):,} инструкций/с'
        elif event.key in (p.K_F5, p.K_F6) and program.has_model:
            if not program.variable('gizmo'):
                self.queue.append('save' if event.key == p.K_F5 else 'load')
        else:
            special = {p.K_LEFT: 17, p.K_UP: 18, p.K_RIGHT: 19, p.K_DOWN: 20,
                       p.K_RETURN: 10, p.K_TAB: 9, p.K_BACKSPACE: 8,
                       p.K_DELETE: 127, p.K_ESCAPE: 27}
            if event.key in special:
                self.queue.append(special[event.key])
            elif event.unicode and len(event.unicode) == 1:
                try:
                    self.queue.append(event.unicode.encode('cp1251')[0])
                except UnicodeEncodeError:
                    pass

    def update(self):
        program = self.program
        if not program:
            return
        machine = program.machine
        if program.ready() and self.queue:
            event = self.queue[0]
            if isinstance(event, str):
                action = self.queue.popleft()
                if program.variable('gizmo'):
                    return
                target = self.model_path or program.path.with_name('saved.model.json')
                try:
                    if action == 'save':
                        target.write_text(json.dumps(export_model(program), indent=2) + '\n', encoding='utf-8')
                    else:
                        import_model(program, json.loads(target.read_text(encoding='utf-8')))
                    self.message = ('Сохранено: ' if action == 'save' else 'Загружено: ') + target.name
                except (OSError, ValueError, KeyError, TypeError) as error:
                    self.message = str(error)
            elif not machine.pause:
                machine.memory[62] = self.queue.popleft()
                machine.update([program.single], 60)
        if not machine.stop:
            machine.update([], 60)

    def draw(self):
        p = self.p
        self.window.fill('white')
        if self.program:
            machine = self.program.machine
            machine.update_display()
            if self.renderer:
                self.renderer.refresh()
            if not self.hide_display:
                self.window.blit(p.transform.scale(machine.display, (320, 320)), (8, 8))
            terminal_x, terminal_y = ((8, 8) if self.hide_display else (340, 100))
            self.window.blit(self.program.terminal_surface(), (terminal_x, terminal_y))
            if self.terminal_size:
                terminal_w, terminal_h = self.terminal_size
                input_y = terminal_y + terminal_h * self.CELL_H
                if self.renderer:
                    line = self.program.terminal_line_surface(self.renderer.status, scale=4)
                    self.window.blit(line, (terminal_x, input_y))
                else:
                    p.draw.rect(self.window, (0, 0, 0),
                                (terminal_x, input_y, terminal_w * self.CELL_W, 2))
                    cursor_x = terminal_x + min(machine.console_index, terminal_w - 1) * self.CELL_W
                    p.draw.rect(self.window, (0, 0, 0), (cursor_x, input_y + 3, self.CELL_W, 3))
            if machine.enable_indicator and not self.hide_display:
                value = machine.indicator_b1 | (machine.indicator_b2 << 8)
                if machine.enable_indicator == 2 and value & 32768:
                    value -= 65536
                indicator_y = (270 if not self.terminal_size else
                               terminal_y + (self.terminal_size[1] + 1) * self.CELL_H + 4)
                self.window.blit(self.font.render(str(value), True, 'black'), (340, indicator_y))
            status_y = max(374, self.window.get_height() - 46)
            if self.program.has_model:
                self.window.blit(self.font.render('F5: сохранить модель JSON   F6: загрузить', True, 'black'),
                                 (12, status_y - 24))
        status = self.message
        if self.program and self.program.machine.pause:
            status = 'Пауза — ' + status
        if self.program and self.program.machine.stop:
            status = 'Программа остановлена — ' + status
        status_y = max(374, self.window.get_height() - 46)
        self.window.blit(self.font.render(status[:120], True, 'black'), (12, status_y))
        hints = 'F1: пауза   F2: заново   F3: шаг   F4: открыть   F7/F8: скорость'
        self.window.blit(self.font.render(hints, True, 'black'), (12, status_y + 22))
        p.display.flip()


def main(argv=None):
    def terminal_size(value):
        try:
            width, height = (int(part) for part in value.lower().split('x', 1))
        except (ValueError, TypeError):
            raise argparse.ArgumentTypeError('use WIDTHxHEIGHT, for example 24x9')
        if width < 1 or height < 1:
            raise argparse.ArgumentTypeError('terminal dimensions must be positive')
        return width, height

    parser = argparse.ArgumentParser(description='Общий эмулятор Computer v2 с 32 КБ памяти')
    parser.add_argument('program', nargs='?', type=Path, help='Исходник программы .asm')
    parser.add_argument('--model', type=Path, help='Файл модели JSON для F5/F6 в 3DEditor')
    parser.add_argument('--terminal-size', type=terminal_size, metavar='WIDTHxHEIGHT',
                        help='Размер терминала в символах; нижняя строка ввода добавляется отдельно')
    parser.add_argument('--hide-display', action='store_true',
                        help='Не показывать дисплей 16×16; терминал занимает основную область окна')
    parser.add_argument('--terminal-renderer', type=Path,
                        help='Плагин высокоразрешённого рендеринга для терминальных графических символов')
    parser.add_argument('--frames', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--headless', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.headless:
        os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    app = App(args.program, args.model, args.terminal_size, args.hide_display, args.terminal_renderer)
    count = 0
    try:
        while app.running and (args.frames is None or count < args.frames):
            for event in app.p.event.get():
                app.handle(event)
            app.update()
            app.draw()
            count += 1
            time.sleep(0.001)
    finally:
        app.p.quit()


if __name__ == '__main__':
    main()
