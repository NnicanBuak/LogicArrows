import fs from 'node:fs';
import {CPU} from './cpu.mjs';

const fixtures=JSON.parse(fs.readFileSync(process.argv[2]));
const root=new URL('../',import.meta.url);
const layout=JSON.parse(fs.readFileSync(new URL('layout.json',root)));
const cpu=new CPU(fs.readFileSync(new URL('qr_terminal_v2.bin',root)),layout);
const check=(condition,message)=>{if(!condition)throw new Error(message);};
cpu.idle();

// Invalid menu choices and Escape must never enter data input.
cpu.type(Buffer.from('0\n11\n'));
check(cpu.variable('stage')===1,'Invalid version accepted');
cpu.type(Buffer.from('1\n'));
cpu.type(Buffer.from('0\n5\n'));
check(cpu.variable('stage')===2,'Invalid correction accepted');
cpu.press(27);
check(cpu.variable('stage')===1,'Escape from correction failed');
cpu.type(Buffer.from('1\n1\n'));
cpu.type(Buffer.from('0\n4\n'));
check(cpu.variable('stage')===3,'Invalid mode accepted');
cpu.press(27);
check(cpu.variable('stage')===1,'Escape from mode failed');
cpu.select(2,2,3);
cpu.type(Buffer.from('partial'));
cpu.press(27);
check(cpu.variable('stage')===1 && cpu.variable('input_length')===0,'Escape from text failed');
check(cpu.ram.slice(layout.constants.INPUT,layout.constants.INPUT+768).every(v=>v===0),'Escape retained input');

const cases=[];
for(const f of fixtures) {
  const start=cpu.steps;
  cpu.select(f.version,f.level,f.mode);
  check(cpu.variable('stage')===4,`${f.name}: not waiting for input`);
  check(cpu.variable('max_length')===f.capacity,`${f.name}: wrong capacity`);
  const before=cpu.graphics.length;
  cpu.press(10);
  check(cpu.variable('stage')===4 && cpu.graphics.length===before,`${f.name}: empty QR accepted`);
  cpu.type(Buffer.from(f.payload,'base64'));
  check(cpu.variable('input_length')===f.capacity,`${f.name}: maximum input truncated`);
  const saved=Buffer.from(cpu.ram.slice(layout.constants.INPUT,layout.constants.INPUT+f.capacity));
  cpu.type(Buffer.from(f.overflow,'base64'));
  check(cpu.variable('input_length')===f.capacity,`${f.name}: overflow accepted`);
  check(saved.equals(Buffer.from(cpu.ram.slice(layout.constants.INPUT,layout.constants.INPUT+f.capacity))),`${f.name}: overflow changed input`);
  cpu.press(8);
  check(cpu.variable('input_length')===f.capacity-1,`${f.name}: Backspace failed`);
  for(const key of f.invalid) cpu.press(key);
  check(cpu.variable('input_length')===f.capacity-1,`${f.name}: invalid character accepted`);
  cpu.press(saved[saved.length-1]);
  cpu.press(10);
  check(cpu.variable('stage')===1 && cpu.variable('input_length')===0,`${f.name}: selection cycle did not restart`);
  const matrix=cpu.matrix(f.size);
  check(matrix.equals(Buffer.from(f.matrix,'base64')),`${f.name}: QR matrix differs from Nayuki`);
  const graphics=Buffer.from(cpu.graphics.slice(before));
  check(graphics.equals(Buffer.from(f.raster,'base64')),`${f.name}: QR terminal raster differs`);
  for(const [name,length] of [['INPUT',768],['DATA',384],['ECC',256],['STREAM',384]])
    check(cpu.ram.slice(layout.constants[name],layout.constants[name]+length).every(v=>v===0),`${f.name}: ${name} not cleared`);
  check(cpu.maxSP<128 && cpu.maxRSP<128,`${f.name}: stack overflow`);
  cases.push({name:f.name,capacity:f.capacity,steps:cpu.steps-start,graphics_bytes:graphics.length});
  if(cases.length%12===0) console.log(JSON.stringify({completed:cases.length,total:fixtures.length}));
}
const result={cases:cases.length,all_qr_matrices_match:true,all_terminal_rasters_match:true,
  limit:32768,image_bytes:layout.image_bytes,max_stack_bytes:cpu.maxSP,
  max_return_stack_bytes:cpu.maxRSP,steps:cpu.steps,results:cases};
fs.writeFileSync(process.argv[3],JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({passed:cases.length,steps:cpu.steps,stack:cpu.maxSP,calls:cpu.maxRSP}));
