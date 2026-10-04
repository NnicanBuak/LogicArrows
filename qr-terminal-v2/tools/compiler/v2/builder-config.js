import { GameMap } from "../arrows.js";

const top = new GameMap("AAADAAAAAAAGCREQACAAMAABAAICAwIEAgUEBgQHAwgBCQEKAQsBDAENAQ4BDwEMAUEBMgIKDSICIwIkAiUCJgInAigCKQIqAisCLAItAi4CLwITAEIBAQAzAxAAQwEOATQBRAQBAAAAAQkPAAEBAQIBAwEEAQUEBgQHAwgBCQEKAQsBDAENAQ4BDwEKDyACIQIiAiMCJAIlAiYCJwIoAikCKgIrAiwCLQIuAi8CAgAAAAEJCAABAQECAQMBBAEFABYAJgA2AAoEIAIhAiICIwIkAg==");
const bottom = new GameMap("AAAEAAAAAAALChKQA5IDlANWAHYChgCWA6YAKAE4AFgBWQNLAywBTANNAz4BTgNPAwkIFAAkA3gAegB7AXwDfQN+A38DDAg0AkQCVABmABcAdwEZAnkDOwEOBGQBdQQmAUcFSQMYEdQB5AH0AcUB1QHlAfUBxgDWAOYA9gDHA9cD5wP3A9gD6AP4AwYAFgISATYAOgEBCUYAtgAYA0gCGgMbAxwDHQIeAx8DEQQnAjcCVwI8AT0BCwNnAikBSgItAw0BCAY5BgQJKgFaASsBWwFcAV0BLgFeAS8BXwEAAAEAABgCBQEGAAcDAQAAAAYBGxADEQISAxMDMwEUAzQBFQI1ARYDFwM3AxgDOAMZAjkDGgM6AxsDOwMcAzwDHQI9Ax4DPgMfAz8DCgwgAUADQQNDAyQBRANFA0YDRwMoAUgDSQMsAQ0BMAFCAwQeUAFRASIBMgFSASMBUwFUAVUBJgFWAScBVwFYAVkBKgFKA1oBKwFLA1sBTANcAU0DXQEuAU4DXgEvAU8DXwEJD3ADcQNyA3MDdAN1A3YDdwN4A3kDegN7A3wDfQN+A38DCwMhAyUDKQMtAxEANgICAAAABgEOEAMwAxECMQMSAzIDUgATA1MDFANUAxUCFgMXAxgDCgEgASQBBAlAA1ABUQAiASMBMwNDATQDNQMmAQkKcANxA3IDcwN0A2UDVgNHAzgDKQMaAAsFIQNEACUDRQI2AicCEQBBAwYAQgM=");
const line = new GameMap("AAADAAAAAAAGCQEAABAABgACABMAEgEMAAMAEAATAQoLBAMFAgYCBwIIAgkCCgILAgwCDQIOAg8CBwAUAQEAAAAACg8AAgECAgIDAgQCBQIGAgcCCAIJAgoCCwIMAg0CDgIPAgIAAAABCgQAAgECAgIDAgQCCQEGABYA");

export const builderConfig = {
    top,
    bottom,
    line,
    rowBytes: 8,  // data bytes on one row of the diskette
    minBytes: 16, // the smallest payload a diskette can carry
    rowPitch: 2,  // map rows taken by one data row
    dataX: 9,     // x of the first data arrow in a row
    cellPitch: 1, // x step between the cells of one byte
    cells: [      // the arrow for each two-bit value of a cell
        { type: 1, rotation: 1, flipped: false },
        { type: 7, rotation: 1, flipped: false },
        { type: 7, rotation: 1, flipped: true },
        { type: 8, rotation: 1, flipped: false }
    ],
    topX: 4,      // x the top cap is pasted at
    lineX: 4,     // x the row separator is pasted at
    lineDy: 1,    // separator y relative to its row: the one below it
    bottomDy: 1,  // bottom cap y = row count * rowPitch + bottomDy
};
