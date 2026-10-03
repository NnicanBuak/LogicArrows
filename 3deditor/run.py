"""Launch the compiled 3DEditor in a compact desktop window."""
import argparse
from collections import deque
import json
from pathlib import Path
import time

from native import Native, ROOT
from model_io import export_model, import_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, default=ROOT / 'saved.model.json')
    args = parser.parse_args()
    native = Native()
    p = native.pygame
    window = p.display.set_mode((640, 390))
    p.display.set_caption('3DEditor')
    font = p.font.SysFont('Arial', 16)
    queue = deque()
    pending_save = False
    pending_load = False
    running = True
    message = 'F5 save JSON   F6 load JSON'
    special = {p.K_LEFT: 17, p.K_UP: 18, p.K_RIGHT: 19, p.K_DOWN: 20,
               p.K_RETURN: 10, p.K_TAB: 9, p.K_BACKSPACE: 8,
               p.K_DELETE: 127, p.K_ESCAPE: 27}
    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False
            elif event.type == p.KEYDOWN:
                if event.key == p.K_F5:
                    pending_save = True
                elif event.key == p.K_F6:
                    pending_load = True
                elif event.key in special:
                    queue.append(special[event.key])
                elif event.unicode and len(event.unicode) == 1 and ord(event.unicode) < 256:
                    queue.append(ord(event.unicode))
        if native.ready():
            native.machine.pause = True
            if pending_save:
                try:
                    args.model.write_text(json.dumps(export_model(native), indent=2) + '\n', encoding='utf-8')
                    message = 'Saved: ' + args.model.name
                except OSError as e:
                    message = str(e)
                pending_save = False
            if pending_load:
                try:
                    import_model(native, json.loads(args.model.read_text(encoding='utf-8')))
                    message = 'Loaded: ' + args.model.name
                except (OSError, ValueError, KeyError, TypeError) as e:
                    message = str(e)
                pending_load = False
            if queue:
                code = queue.popleft()
                event = native.event(code)
                native.machine.update([event], 60)
                if code == 27:
                    native.machine.memory[62] = 27
                # Move past the wait-loop condition even when readiness was
                # observed between its read and conditional jump.
                for _ in range(4):
                    native.machine.update([native.single], 60)
        native.machine.pause = False
        native.machine.update([], 60)
        native.machine.update_display()
        window.fill('white')
        window.blit(p.transform.scale(native.machine.display, (320, 320)), (8, 8))
        window.blit(native.terminal_surface(), (340, 100))
        window.blit(font.render(message[:75], True, 'black'), (12, 351))
        p.display.flip()
        time.sleep(0.001)
    p.quit()


if __name__ == '__main__':
    main()
