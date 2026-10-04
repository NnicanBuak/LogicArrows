const CHUNK_SIZE = 16;

class Arrow {
    type = 0;
    rotation = 0;
    flipped = false;
}

class Chunk {
    arrows = new Array(CHUNK_SIZE ** 2).fill().map(() => new Arrow());

    constructor(x, y) {
        this.x = x;
        this.y = y;
    }

    getArrow(x, y) {
        return this.arrows[x + y * 16];
    }

    getArrowTypes() {
        const arrowTypes = new Set();
        for (const arrow of this.arrows)
            if (arrow.type !== 0)
                arrowTypes.add(arrow.type);
        return Array.from(arrowTypes);
    }
}

export class GameMap {
    chunks = [];
    chunkColumns = new Map();
    filledArrows = null;

    constructor(save) {
        if (save)
            this.load(save);
    }

    setArrow(x, y, type, rotation, flipped) {
        this.filledArrows = null;
        Object.assign(this.getArrow(x, y), { type, rotation, flipped });
    }

    getArrow(x, y) {
        const chunk = this.getChunkByArrowCoordinates(x, y);
        return chunk.getArrow(x - chunk.x * CHUNK_SIZE, y - chunk.y * CHUNK_SIZE);
    }

    getChunkByArrowCoordinates(x, y) {
        const negativeCorrectionX = x < 0 ? 1 : 0;
        const negativeCorrectionY = y < 0 ? 1 : 0;
        const chunkX = ~~((x + negativeCorrectionX) / CHUNK_SIZE) - negativeCorrectionX;
        const chunkY = ~~((y + negativeCorrectionY) / CHUNK_SIZE) - negativeCorrectionY;
        return this.getChunk(chunkX, chunkY);
    }

    getChunk(x, y) {
        let column = this.chunkColumns.get(x);
        if (!column) {
            column = new Map();
            this.chunkColumns.set(x, column);
        }
        let chunk = column.get(y);
        if (!chunk) {
            chunk = new Chunk(x, y);
            this.chunks.push(chunk);
            column.set(y, chunk);
        }
        return chunk;
    }

    getFilledArrows() {
        if (!this.filledArrows) {
            this.filledArrows = [];
            for (const chunk of this.chunks)
                for (let i = 0; i < CHUNK_SIZE; ++i)
                    for (let j = 0; j < CHUNK_SIZE; ++j) {
                        const arrow = chunk.arrows[i + j * CHUNK_SIZE];
                        if (arrow.type !== 0)
                            this.filledArrows.push({ x: chunk.x * CHUNK_SIZE + i, y: chunk.y * CHUNK_SIZE + j, arrow });
                    }
        }
        return this.filledArrows;
    }

    paste(map, x, y) {
        for (const filled of map.getFilledArrows())
            this.setArrow(filled.x + x, filled.y + y, filled.arrow.type, filled.arrow.rotation, filled.arrow.flipped);
    }

    load(save) {
        this.filledArrows = null;
        const buffer = atob(save).split("").map((c) => c.charCodeAt(0));

        if (buffer.length < 4)
            return;
        let index = 0;
        let version = buffer[index++];
        version |= buffer[index++] << 8;
        if (version !== 0)
            throw new Error("Unsupported save version");
        let chunksCount = buffer[index++];
        chunksCount |= buffer[index++] << 8;
        for (let i = 0; i < chunksCount; i++) {
            let chunkX = buffer[index++];
            chunkX |= (buffer[index++] & 0x7F) << 8;
            if ((buffer[index - 1] & 0x80) !== 0)
                chunkX = -chunkX;
            let chunkY = buffer[index++];
            chunkY |= (buffer[index++] & 0x7F) << 8;
            if ((buffer[index - 1] & 0x80) !== 0)
                chunkY = -chunkY;
            const arrowsTypesCount = buffer[index++] + 1;
            const chunk = this.getChunk(chunkX, chunkY);
            for (let j = 0; j < arrowsTypesCount; j++) {
                const type = buffer[index++];
                const typeCount = buffer[index++] + 1;
                for (let k = 0; k < typeCount; k++) {
                    const position = buffer[index++];
                    const rotation = buffer[index++];
                    const arrow = chunk.getArrow(position & 0xF, position >> 4);
                    arrow.type = type;
                    arrow.rotation = rotation & 0x3;
                    arrow.flipped = (rotation & 0x4) !== 0;
                }
            }
        }
    }

    save() {
        const buffer = [];
        buffer.push(0, 0);
        buffer.push(this.chunks.length & 0xFF, (this.chunks.length >> 8) & 0xFF);
        this.chunks.forEach((chunk) => {
            const arrowsTypes = chunk.getArrowTypes();
            const chunkBytesX = [
                Math.abs(chunk.x) & 0xFF,
                (Math.abs(chunk.x) >> 8) & 0xFF,
            ];
            const chunkBytesY = [
                Math.abs(chunk.y) & 0xFF,
                (Math.abs(chunk.y) >> 8) & 0xFF,
            ];
            if (chunk.x < 0)
                chunkBytesX[1] |= 0x80;
            else
                chunkBytesX[1] &= 0x7F;
            if (chunk.y < 0)
                chunkBytesY[1] |= 0x80;
            else
                chunkBytesY[1] &= 0x7F;
            buffer.push(...chunkBytesX);
            buffer.push(...chunkBytesY);
            buffer.push(arrowsTypes.length - 1);
            arrowsTypes.forEach((type) => {
                buffer.push(type);
                buffer.push(0);
                const typesCountIndex = buffer.length - 1;
                let typeCount = 0;
                for (let i = 0; i < CHUNK_SIZE; i++) {
                    for (let j = 0; j < CHUNK_SIZE; j++) {
                        const arrow = chunk.getArrow(i, j);
                        if (arrow.type === type) {
                            const position = i | (j << 4);
                            const rotation = arrow.rotation | ((arrow.flipped ? 1 : 0) << 2);
                            buffer.push(position);
                            buffer.push(rotation);
                            typeCount++;
                        }
                    }
                }
                buffer[typesCountIndex] = typeCount - 1;
            });
        });

        let binary = "";
        const bytes = new Uint8Array(buffer);
        const length = bytes.byteLength;
        for (let i = 0; i < length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
}
