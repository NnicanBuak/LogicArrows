// Decode the actual LogicArrows diskette map back into payload bytes.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {GameMap} from '../graphics3d/vendor/compiler/arrows.js';
import {builderConfig as config} from '../graphics3d/vendor/compiler/v2/builder-config.js';

const image = fs.readFileSync(new URL('./3deditor.bin', import.meta.url));
const map = new GameMap(fs.readFileSync(new URL('./3deditor.diskette.txt', import.meta.url), 'utf8').trim());
const paddedBytes = Math.ceil(image.length / config.rowBytes) * config.rowBytes;
const decoded = Buffer.alloc(paddedBytes);
for (let i = 0; i < paddedBytes; i++) {
  const row = Math.floor(i / config.rowBytes);
  for (let cell = 0; cell < 4; cell++) {
    const arrow = map.getArrow(config.dataX + (i % config.rowBytes) * 4 + cell,
                               row * config.rowPitch + 3);
    const value = config.cells.findIndex(c => c.type === arrow.type &&
      c.rotation === arrow.rotation && c.flipped === arrow.flipped);
    if (value < 0) throw new Error('Invalid diskette cell at byte ' + i);
    decoded[i] |= value << (2 * cell);
  }
}
if (!decoded.subarray(0, image.length).equals(image) ||
    decoded.subarray(image.length).some(v => v !== 0)) {
  throw new Error('Diskette payload differs from the compiled image');
}
const result = {result:'passed', bytes:image.length, padded_bytes:paddedBytes,
  program_sha256:crypto.createHash('sha256').update(image).digest('hex')};
fs.writeFileSync(new URL('./diskette-verification.json', import.meta.url), JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
