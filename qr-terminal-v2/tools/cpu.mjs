// Headless Computer v2 ISA harness for verification, not a program runtime.
// The generated ASM image performs every step of QR generation itself.
export class CPU {
  constructor(image, layout) {
    this.ram = new Uint8Array(32768);
    this.ram.set(image);
    this.layout = layout;
    this.r = new Uint8Array(4);
    this.ip = 0;
    this.bank = 1;
    this.z = this.s = this.c = this.o = 0;
    this.key = 0;
    this.devices = 0;
    this.steps = 0;
    this.text = [];
    this.graphics = [];
    this.maxSP = this.maxRSP = 0;
    const lengths = {STACK:128, RETURN_STACK:128, GLOBAL_WORDS:1024, INPUT:768,
      DATA:384, ECC:256, STREAM:384, BLOCK_INFO:128, MATRIX:4096};
    this.writable = Object.entries(lengths).map(([n,len]) => [layout.constants[n],layout.constants[n]+len]);
  }
  physical(a) { return a < 128 ? a : this.bank * 128 + (a & 127); }
  read(a) {
    if (a === 62) { const k=this.key; this.key=0; return k; }
    return this.ram[this.physical(a)];
  }
  write(a, v) {
    v &= 255;
    const p=this.physical(a);
    if (p < 25 || (p >= 128 && !this.writable.some(([lo,hi]) => p>=lo && p<hi)))
      throw new Error(`Write outside RAM: ${p}, bank ${this.bank}, IP ${this.ip}`);
    this.ram[p]=v;
    if(a===63) this.bank=v || 1;
    if(a===62) this.devices=v;
    if(a===60 && (this.devices & 1)) this.text.push(v);
    if(a===61) this.graphics.push(v);
    if(a===this.layout.common.SP) this.maxSP=Math.max(this.maxSP,v);
    if(a===this.layout.common.RSP) this.maxRSP=Math.max(this.maxRSP,v);
  }
  fetch() { const v=this.ram[this.physical(this.ip)]; this.ip=(this.ip+1)&255; return v; }
  zs(v) { this.z=v===0?1:0; this.s=v>>>7; }
  step() {
    this.steps++;
    const op=this.fetch(), x=op&3, y=(op&15)>>>2, h=op>>>4;
    if(op===0) return;
    if(op===1 || op===2) throw new Error(`Unexpected halt ${op}`);
    if(op===3) { this.ip=this.fetch(); return; }
    if(op>=4 && op<=7) { this.ip=this.r[x]; return; }
    if(op>=8 && op<=15) {
      const a=this.fetch(), f=[this.z,this.s,this.c,this.o][x];
      if(op<=11 ? f : !f) this.ip=a;
      return;
    }
    if(op>=16 && op<=47) {
      const f=[this.z,this.s,this.c,this.o][x];
      if(op<=31 ? f : !f) this.ip=this.r[y];
      return;
    }
    if(h===3) { this.write(x===y?this.fetch():this.r[y],this.r[x]); return; }
    if(h===4) { this.r[x]=this.read(this.r[y]); return; }
    if(op>=80 && op<=83) { this.r[x]=this.read(this.fetch()); return; }
    if(op>=84 && op<=87) { this.r[x]=this.fetch(); return; }
    let a=this.r[x], b=this.r[y], v, t;
    if(h>=6 && h<=13) {
      if(x===y) {
        if(h===6) v=(a+1)&255;
        if(h===7) v=(a-1)&255;
        if(h===8) v=a^255;
        if(h===9) {v=(-a)&255; this.c=a!==0?1:0; this.o=a===128?1:0;}
        if(h===10) {this.r[x]=0; return;}
        if(h===11) {this.zs(a); return;}
        if(h===12) {v=((a<<1)|this.c)&255; this.c=a>>>7;}
        if(h===13) {v=(a>>>1)|(this.c<<7); this.c=a&1;}
      } else {
        if(h===6 || h===8) {
          t=a+b+(h===8?this.c:0); v=t&255; this.c=t>255?1:0;
          this.o=((~(a^b)&(a^v))&128)?1:0;
        }
        if(h===7 || h===9) {
          t=a-b-(h===9?this.c:0); v=t&255; this.c=t<0?1:0;
          this.o=(((a^b)&(a^v))&128)?1:0;
        }
        if(h===10) {this.r[x]=b; return;}
        if(h===11) v=a&b;
        if(h===12) v=a|b;
        if(h===13) v=a^b;
      }
    } else if(op>=224 && op<=235) {
      if(op<228) {v=(a<<1)&255; this.c=a>>>7;}
      else {v=(a>>>1)|(op>=232?(a&128):0); this.c=a&1;}
    } else throw new Error(`Invalid opcode ${op}`);
    this.r[x]=v; this.zs(v);
  }
  at(name) { const p=this.layout.blocks[name]; return this.bank===p.bank && this.ip===p.address; }
  idle(limit=80000000) {
    const end=this.steps+limit;
    while(!this.at('vm_key_wait')) {
      if(this.steps>=end) throw new Error(`Timeout ${this.bank}:${this.ip}`);
      this.step();
    }
  }
  press(code) { this.idle(); this.key=code; this.step(); this.idle(); }
  type(bytes) { for(const k of bytes) this.press(k); }
  word(address) { return this.ram[address] | (this.ram[address+1]<<8); }
  variable(name) { return this.word(this.layout.variables[name]); }
  select(version, level, mode) {
    this.type(Buffer.from(`${version}\n${level}\n${mode}\n`));
  }
  matrix(size) {
    const a=this.layout.constants.MATRIX, result=[];
    for(let y=0;y<size;y++) for(let x=0;x<size;x++) result.push(this.ram[a+y*64+x]&1);
    return Buffer.from(result);
  }
}
