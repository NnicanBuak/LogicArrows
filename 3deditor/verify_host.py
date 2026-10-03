"""Additional axis/selection checks and real headless F5/F6 launcher roundtrip."""
import hashlib
import json
import math
import sys

from machine import Machine, ROOT
from native import Native
from model_io import export_model, import_model, encode_model
from verify import frame


def main():
    m = Machine()
    m.idle()
    m.type('a')
    before = m.vertices()
    m.type('rx45.3\n')
    sine, cosine = round(256 * math.sin(math.radians(45.3))), round(256 * math.cos(math.radians(45.3)))
    assert m.vertices() == {i: [p[0], (p[1] * cosine - p[2] * sine + 128) // 256,
                                  (p[1] * sine + p[2] * cosine + 128) // 256] for i, p in before.items()}
    frame(m)
    m.type('2a')
    before = m.vertices()
    m.type('gz0.125\n')
    assert m.vertices() == {i: [p[0], p[1], p[2] + 2] for i, p in before.items()}, 'Shared edge vertices must move once'
    m.type('3a')
    before = m.vertices()
    m.type('gx-0.0625\n')
    assert m.vertices() == {i: [p[0] - 1, p[1], p[2]] for i, p in before.items()}, 'Shared face vertices must move once'
    frame(m)
    native = Native(headless=True)
    native.idle()
    original = export_model(native)
    # Invalid imports are atomic, including unrepresentable fractions and edges.
    for bad in [dict(original, vertices=[[12, 0, 0]]),
                dict(original, vertices=[[0.01, 0, 0]]),
                dict(original, edges=[[0, 99]]),
                dict(original, edges=original['edges'] + [original['edges'][0]])]:
        before = native.snapshot()
        try:
            import_model(native, bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid JSON accepted')
        assert native.snapshot() == before
    fixture = ROOT.parent / 'work/3deditor-qa/roundtrip.model.json'
    fixture.parent.mkdir(parents=True, exist_ok=True)
    import run
    run.Native = lambda: native
    p = native.pygame
    batches = iter([[p.event.Event(p.KEYDOWN, key=p.K_F5, unicode='')],
                    [p.event.Event(p.KEYDOWN, key=p.K_F6, unicode='')],
                    [p.event.Event(p.QUIT)]])
    previous_get, previous_argv = p.event.get, sys.argv
    p.event.get = lambda: next(batches, [])
    sys.argv = ['run.py', '--model', str(fixture)]
    try:
        run.main()
    finally:
        p.event.get, sys.argv = previous_get, previous_argv
    assert json.loads(fixture.read_text(encoding='utf-8')) == original
    assert export_model(native) == original
    assert native.variable('tool') == 0 and native.variable('undo_valid') == 0
    result = dict(result='passed', program_sha256=hashlib.sha256((ROOT / '3deditor.bin').read_bytes()).hexdigest(),
                  x_axis_rotation=True, common_edge_vertices_once=True, common_face_vertices_once=True,
                  invalid_json_atomic=True, launcher_f5_f6_roundtrip=True, native_escape_keydown_tested=False)
    (ROOT / 'host-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
