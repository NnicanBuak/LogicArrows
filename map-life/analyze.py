"""Reproducible native-circuit experiments; never overwrite production exports."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "minesweeper-v1"), str(ROOT / "ArrowsHDL/src")]
from arrowasm import Cell, disassemble, encode
from mapdata import read_map, write_json
from runner import simulate

OUT = HERE / "build/analysis"


def run(cells, frames, inputs, probes):
    report = simulate(cells, dict(ticks=sum(frames), frame_ticks=frames,
        inputs=[dict(at=list(p), values=v) for p, v in inputs],
        expect=[], observe=[list(p) for p in probes]), optimize_cycles=False)
    return [o["values"] for o in report["observations"]]


def export(name, cells):
    (OUT / (name + ".save.txt")).write_text(encode(cells) + "\n", encoding="ascii")
    (OUT / (name + ".arrowasm")).write_text(disassemble(cells), encoding="utf-8")


def life_counter(original):
    points = ((2,3),(3,3),(4,3),(5,3),(6,3),(7,3),(8,3),(8,2),(9,3),(10,3))
    cells = {p: original[p] for p in points}
    cells[1,3] = Cell(22,1)
    frames = [20] + [d for _ in range(8) for d in (1,24)]
    samples = run(cells, frames, [((1,3), [0]+[v for _ in range(8) for v in (1,0)])],
                  [(3,3),(6,3),(9,3)])
    rows = [[v[k] for v in samples] for k in [0]+list(range(2,len(frames),2))]
    expected = [[n&1, (n>>1)&1, int(n>=4)] for n in range(9)]
    assert rows == expected, (rows, expected)
    export("life-counter-isolated", cells)
    return dict(passed=True, pulse_width=1, gap_ticks=24, count_states=rows,
                state_meaning=["bit0", "bit1", "at_least_four"],
                original_arrows=10, fixture_arrows=1)


def life_rule(original):
    points = ((3,4),(3,5),(5,5),(7,5),(9,5),(6,4),(7,4),(8,4),
              (9,4),(11,3),(11,4),(11,5),(11,6))
    cells = {p: original[p] for p in points}
    fixtures = dict(b0=((3,3),0), b1=((6,3),0), overflow=((9,3),2),
                    alive=((7,6),0), clock=((11,2),2))
    for p, rotation in fixtures.values():
        cells[p] = Cell(22,rotation)
    cases = [(n,a) for n in range(9) for a in range(2)]
    frames = [d for _ in cases for d in (40,1,40)]
    values = {key: [] for key in fixtures}
    for n, alive in cases:
        word = dict(b0=n&1, b1=(n>>1)&1, overflow=int(n>=4), alive=alive)
        for key in values:
            values[key].extend([0,1,0] if key == "clock" else [word[key]]*3)
    samples = run(cells, frames, [(fixtures[k][0], v) for k,v in values.items()], [(11,6)])
    actual = samples[0][2::3]
    expected = [int(n==3 or (n==2 and alive)) for n,alive in cases]
    assert actual == expected, (actual, expected)
    export("life-rule-isolated", cells)
    return dict(passed=True, cases=18, actual=actual, expected=expected,
                equation="bit1 AND NOT at_least_four AND (bit0 OR alive)")


def serial_counter():
    # Extend the actual Life ripple topology to four exact binary bits.
    # This isolated component needs one-tick input pulses and initialization.
    cells = {(x,0): Cell(19,1) for x in (3,6,9,12)}
    cells.update({(x,0): Cell(16,1) for x in (4,7,10)})
    cells.update({(x,0): Cell(12,1) for x in (2,5,8)})
    cells[11,0] = Cell(1,1)
    cells[1,0] = Cell(22,1)
    frames, values, expected = [32], [0], [0]
    total = 0
    for mask in range(256):
        for bit in range(8):
            pulse = (mask>>bit)&1
            frames.extend((1,32)); values.extend((pulse,0))
            total += pulse
            expected.append(total%16)
    samples = run(cells, frames, [((1,0), values)], [(x,0) for x in (3,6,9,12)])
    actual = [sum(v[k]<<j for j,v in enumerate(samples))
              for k in [0]+list(range(2,len(frames),2))]
    assert actual == expected
    export("binary-counter4-prototype", cells)
    return dict(passed=True, masks=256, pulse_slots=2048, checked_words=len(actual),
                core_arrows=11, core_width=11, core_height=1, registers=4,
                carry_gates=3, pulse_width=1, gap_ticks=32,
                limitation="No reset, serializer, output fanout or board integration included; tested modulo 16.")


def metrics():
    mine = ROOT / "minesweeper-v1/build"
    cells = read_map(mine / "cell.save.txt")
    nets = json.loads((mine / "cell.nets.json").read_text(encoding="utf-8"))
    layout = json.loads((mine / "cell.layout.json").read_text(encoding="utf-8"))
    graph = json.loads((mine / "cell.logic.json").read_text(encoding="utf-8"))
    assert nets["map_hash"] == layout["map_hash"]
    return dict(side=layout["side"], arrows=len(cells),
                wires=nets["wire_arrows"], nets=nets["net_count"],
                wire_fraction=nets["wire_arrows"]/len(cells),
                saved_graph_nodes=len(graph["nodes"]), map_hash=layout["map_hash"],
                arrow_types=dict(sorted(Counter(c.type for c in cells.values()).items())),
                lower_bound_arrows_to_remove_for_64=len(cells)-64*64,
                caution="Saved graph is older than current snap.py; physical export metrics refer to the saved cell only.")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = read_map(HERE / "build/life-cell.map.json")
    save = (HERE / "reference/original.save.txt").read_text(encoding="ascii").strip()
    result = dict(source_save_sha256=hashlib.sha256(save.encode("ascii")).hexdigest(),
                  life_types=dict(sorted(Counter(c.type for c in original.values()).items())),
                  life_counter=life_counter(original), life_rule=life_rule(original),
                  binary_counter4=serial_counter(), minesweeper=metrics(),
                  full_life_board_simulated=False, browser_simulated=False,
                  simulation_profile="GraphDLC-01232bd")
    write_json(OUT / "logic-analysis.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
