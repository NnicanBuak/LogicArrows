"""Extract an unchanged Life cell from the public map's native save."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "ArrowsHDL" / "src"))
from arrowasm import decode, disassemble, encode, lower, parse
from arrow_layout import destinations
from mapdata import read_map, write_json, write_map

API = "https://logic-arrows.io/api/mapguest"
ORIGIN = (110, 76)
HEIGHT = 20


def crop(cells, origin, width, height=HEIGHT):
    ox, oy = origin
    return {(x-ox, y-oy): cell for (x, y), cell in cells.items()
            if ox <= x < ox+width and oy <= y < oy+height}


def preview(cells, width, path):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    size, left, top = 30, 45, 65
    image = Image.new("RGB", (width*size+70, HEIGHT*size+100), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 17)
    draw.text((left, 15), f"map-life: {width} x {HEIGHT}, {len(cells)} arrows", font=font, fill="#1e293b")
    for x in range(width+1):
        draw.line((left+x*size, top, left+x*size, top+HEIGHT*size), fill="#e7eaf0")
    for y in range(HEIGHT+1):
        draw.line((left, top+y*size, left+width*size, top+y*size), fill="#e7eaf0")
    for x in range(0, width, 5):
        draw.text((left+x*size+5, top-25), str(x), font=font, fill="#64748b")
    for y in range(0, HEIGHT, 5):
        draw.text((12, top+y*size+4), str(y), font=font, fill="#64748b")
    sprites = {}
    for (x, y), cell in cells.items():
        token = (cell.type, cell.rotation, cell.mirrored)
        if token not in sprites:
            sprite = Image.open(ROOT / f"ArrowsHDL/assets/sprites/arrow{cell.type}.png").convert("RGBA")
            if cell.mirrored:
                sprite = ImageOps.mirror(sprite)
            sprites[token] = sprite.rotate(-90*cell.rotation).resize((size-4, size-4), Image.Resampling.LANCZOS)
        if cell.type == 24:
            draw.rectangle((left+x*size+1, top+y*size+1, left+(x+1)*size-1, top+(y+1)*size-1), fill="#fff0d5")
        image.paste(sprites[token], (left+x*size+2, top+y*size+2), sprites[token])
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Download the current public map")
    args = parser.parse_args()
    reference = HERE / "reference"
    reference.mkdir(exist_ok=True)
    snapshot = reference / "mapguest.json"
    if args.refresh or not snapshot.exists():
        request = Request(API, data=b'{"id":"life"}', headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            snapshot.write_bytes(response.read())
    document = json.loads(snapshot.read_text(encoding="utf-8-sig"))
    original = document["data"]
    (reference / "original.save.txt").write_text(original+"\n", encoding="ascii")
    cells = decode(original)
    output = HERE / "build"
    output.mkdir(exist_ok=True)
    tile, single = crop(cells, ORIGIN, 40), crop(cells, ORIGIN, 20)

    checks = {"native_save_roundtrip": True, "json_roundtrip": True, "assembly_roundtrip": True}
    for stem, selection, width in (("life-cell", single, 20), ("life-repeat", tile, 40)):
        write_map(output, stem, selection)
        assembly = disassemble(selection)
        (output / f"{stem}.arrowasm").write_text(assembly, encoding="utf-8")
        assert decode(encode(selection)) == selection
        assert read_map(output / f"{stem}.map.json") == selection
        assert lower(parse(assembly)) == selection
        preview(selection, width, output / f"{stem}.preview.png")

    # Check every slot of the same phase in the repeated field, including holes.
    exact = []
    different = []
    for y in range(36, 317, 20):
        for x in range(30, 311, 40):
            position = [x, y]
            (exact if crop(cells, position, 40) == tile else different).append(position)
    periods = {}
    for axis, maximum in ((0, 80), (1, 40)):
        periods["x" if axis == 0 else "y"] = next(
            shift for shift in range(1, maximum+1)
            if crop(cells, (ORIGIN[0] + (shift if axis == 0 else 0),
                            ORIGIN[1] + (shift if axis == 1 else 0)), 40) == tile)
    assert periods == {"x": 40, "y": 20}, periods
    assert len(exact) >= 4
    checks["periods"] = periods
    checks["single_cell_repeated_right"] = crop(cells, (150, 76), 20) == single
    checks["single_cell_repeated_below"] = crop(cells, (110, 96), 20) == single
    assert checks["single_cell_repeated_right"] and checks["single_cell_repeated_below"]

    # Preserve the original contacts, rather than inventing ports on the crop.
    selected_global = {(x+ORIGIN[0], y+ORIGIN[1]) for x, y in single}
    links = []
    for p, cell in cells.items():
        for q in destinations(p, cell):
            if q in cells and ((p in selected_global) != (q in selected_global)):
                links.append({"kind": "signal", "direction": "out" if p in selected_global else "in",
                              "from": [p[0]-ORIGIN[0], p[1]-ORIGIN[1]],
                              "to": [q[0]-ORIGIN[0], q[1]-ORIGIN[1]]})
        if cell.type == 5:
            dx, dy = 0, 1
            for _ in range(cell.rotation):
                dx, dy = -dy, dx
            q = p[0]+dx, p[1]+dy
            if q in cells and ((p in selected_global) != (q in selected_global)):
                links.append({"kind": "detector_observation", "detector": [p[0]-ORIGIN[0], p[1]-ORIGIN[1]],
                              "observed": [q[0]-ORIGIN[0], q[1]-ORIGIN[1]]})
    write_json(output / "life-cell.connections.json", {"coordinates": "relative to crop origin", "links": links})
    report = {
        "source_url": "https://logic-arrows.io/map-life", "api_url": API,
        "map_id": document["id"], "map_version": document["version"],
        "extracted_utc": datetime.now(timezone.utc).isoformat(),
        "source_save_sha256": hashlib.sha256(original.encode("ascii")).hexdigest(),
        "source_cells": len(cells), "crop_origin": list(ORIGIN),
        "single_cell": {"width": 20, "height": 20, "cells": len(single),
                        "types": dict(sorted(Counter(v.type for v in single.values()).items()))},
        "repeat_tile": {"width": 40, "height": 20, "cells": len(tile), "game_cells": 2},
        "checks": checks, "exact_repeat_origins": exact, "different_repeat_origins": different,
        "external_signal_links": sum(link["kind"] == "signal" for link in links),
        "external_detector_observations": sum(link["kind"] == "detector_observation" for link in links),
        "simulation_performed": False,
    }
    write_json(output / "extraction.report.json", report)
    print(json.dumps({"cell": report["single_cell"], "repeat": report["repeat_tile"],
                      "checks": checks, "exact_repeats": len(exact),
                      "external_links": len(links)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
