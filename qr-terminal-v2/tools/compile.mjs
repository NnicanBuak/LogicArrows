// Official Computer v2 assembler, with the user-requested 32768-byte profile.
import fs from 'node:fs';
import path from 'node:path';
import {createCompiler} from './compiler/asm.js';
import {Args,commands,instructions,registers,keywords} from './compiler/v2/reference.js';
import {buildDiskette} from './compiler/builder.js';
import {builderConfig} from './compiler/v2/builder-config.js';

const filename = path.resolve(process.argv[2]);
const Compiler = createCompiler({Args, commands, instructions, registers, keywords,
  memorySize:32768,
  byteAddress:offset => offset < 256 ? offset : (offset & 0xFF) | 0x80,
  trackLineOffsets:true});
const compiler = new Compiler(fs.readFileSync(filename, 'utf8'));
compiler.compile();
if (compiler.errors.length) {
  console.error(JSON.stringify(compiler.errors, null, 2));
  process.exit(1);
}
const base = filename.replace(/\.asm$/i, '');
fs.writeFileSync(base + '.bin', Buffer.from(compiler.bytes));
fs.writeFileSync(base + '.diskette.txt', buildDiskette([...compiler.bytes], builderConfig) + '\n');
fs.writeFileSync(base + '.compile.json', JSON.stringify({bytes:compiler.bytes.length,
  limit:32768, free:32768-compiler.bytes.length, errors:[], names:compiler.names},null,2) + '\n');
console.log(JSON.stringify({bytes:compiler.bytes.length, limit:32768, errors:[]}));
