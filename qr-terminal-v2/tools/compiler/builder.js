import { GameMap } from "./arrows.js";

export function buildDiskette(bytes, config) {
    const { top, bottom, line, rowBytes, minBytes, rowPitch, dataX, cellPitch, cells,
        topX, lineX, lineDy, bottomDy } = config;
    const gameMap = new GameMap();

    let byteCount = bytes.length;

    if (byteCount < minBytes)
        bytes.push(...Array(minBytes - byteCount).fill(0));
    else if (byteCount % rowBytes != 0)
        bytes.push(...Array(rowBytes - byteCount % rowBytes).fill(0));

    byteCount = bytes.length;
    const rowCount = byteCount / rowBytes;

    for (let row = 0; row < rowCount - 1; ++row)
        gameMap.paste(line, lineX, row * rowPitch + 3 + lineDy);
    gameMap.paste(top, topX, 0);
    gameMap.paste(bottom, 0, rowCount * rowPitch + bottomDy);

    const bitsPerCell = Math.log2(cells.length);
    const cellsPerByte = 8 / bitsPerCell;
    const mask = cells.length - 1;

    for (let row = 0; row < rowCount; ++row) {
        let bytes_row = bytes.splice(0, rowBytes);
        let y = row * rowPitch + 3;

        for (let i = 0; i < rowBytes; ++i) {
            let byte = bytes_row.at(i);
            let x = i * cellsPerByte * cellPitch + dataX;

            for (let j = 0; j < cellsPerByte; ++j) {
                const cell = cells[byte & mask];
                gameMap.setArrow(x + j * cellPitch, y, cell.type, cell.rotation, cell.flipped);
                byte >>= bitsPerCell;
            }
        }
    }

    return gameMap.save();
}
