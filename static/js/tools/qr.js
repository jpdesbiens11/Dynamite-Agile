/* QR code, made in the page (0.60.30, D-O-038): the link of a page as a QR code, to carry it from a computer to a phone
   (scan, then share from the phone). No library, no network: ISO/IEC 18004, byte mode, error correction level M,
   versions 1 to 15 (up to 412 bytes -- every address of the tool), the mask with the lowest penalty.
   DA.qr(text) -> {size, dark(x, y)}; DA.qrCanvas(text, px) -> a <canvas> with the quiet zone (4 modules). */
(function () {
  "use strict";

  /* EC level M, per version: [EC codewords per block, blocks of group 1, data codewords, blocks of group 2, data codewords] */
  const BLOCKS = [null, [10, 1, 16, 0, 0], [16, 1, 28, 0, 0], [26, 1, 44, 0, 0], [18, 2, 32, 0, 0], [24, 2, 43, 0, 0],
    [16, 4, 27, 0, 0], [18, 4, 31, 0, 0], [22, 2, 38, 2, 39], [22, 3, 36, 2, 37], [26, 4, 43, 1, 44], [30, 1, 50, 4, 51],
    [22, 6, 36, 2, 37], [22, 8, 37, 1, 38], [24, 4, 40, 5, 41], [24, 5, 41, 5, 42]];
  const ALIGN = [null, [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50],
    [6, 30, 54], [6, 32, 58], [6, 34, 62], [6, 26, 46, 66], [6, 26, 48, 70]];

  function mul(x, y) {  // GF(256), polynomial 0x11D
    let z = 0;
    for (let i = 7; i >= 0; i--) {
      z = (z << 1) ^ ((z >>> 7) * 0x11d);
      z ^= ((y >>> i) & 1) * x;
    }
    return z & 0xff;
  }

  function divisor(degree) {
    const out = new Array(degree).fill(0);
    out[degree - 1] = 1;
    let root = 1;
    for (let i = 0; i < degree; i++) {
      for (let j = 0; j < degree; j++) {
        out[j] = mul(out[j], root);
        if (j + 1 < degree) out[j] ^= out[j + 1];
      }
      root = mul(root, 0x02);
    }
    return out;
  }

  function remainder(data, div) {
    const out = new Array(div.length).fill(0);
    data.forEach((b) => {
      const factor = b ^ out.shift();
      out.push(0);
      div.forEach((d, i) => { out[i] ^= mul(d, factor); });
    });
    return out;
  }

  function utf8(text) {
    return Array.from(new TextEncoder().encode(text));
  }

  function codewords(bytes) {
    let version = 0;
    for (let v = 1; v <= 15; v++) {
      const b = BLOCKS[v];
      const capacity = (b[1] * b[2] + b[3] * b[4]) * 8;
      if (4 + (v < 10 ? 8 : 16) + bytes.length * 8 <= capacity) { version = v; break; }
    }
    if (!version) throw new Error("Lien trop long pour un code QR.");
    const [ec, n1, d1, n2, d2] = BLOCKS[version];
    const capacity = (n1 * d1 + n2 * d2) * 8;
    const bits = [];
    const put = (value, len) => { for (let i = len - 1; i >= 0; i--) bits.push((value >>> i) & 1); };
    put(4, 4);
    put(bytes.length, version < 10 ? 8 : 16);
    bytes.forEach((b) => put(b, 8));
    put(0, Math.min(4, capacity - bits.length));
    put(0, (8 - (bits.length % 8)) % 8);
    for (let pad = 0xec; bits.length < capacity; pad ^= 0xec ^ 0x11) put(pad, 8);
    const data = [];
    for (let i = 0; i < bits.length; i += 8) data.push(bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
    const blocks = [];
    const div = divisor(ec);
    let k = 0;
    for (let i = 0; i < n1 + n2; i++) {
      const len = i < n1 ? d1 : d2;
      const block = data.slice(k, k + len);
      k += len;
      blocks.push({ data: block, ec: remainder(block, div) });
    }
    const out = [];
    for (let i = 0; i < Math.max(d1, d2); i++) blocks.forEach((b) => { if (i < b.data.length) out.push(b.data[i]); });
    for (let i = 0; i < ec; i++) blocks.forEach((b) => out.push(b.ec[i]));
    return { version, out };
  }

  function build(version) {
    const size = version * 4 + 17;
    const dark = Array.from({ length: size }, () => new Array(size).fill(false));
    const fixed = Array.from({ length: size }, () => new Array(size).fill(false));
    const set = (x, y, on) => { dark[y][x] = on; fixed[y][x] = true; };
    for (let i = 0; i < size; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
    [[3, 3], [size - 4, 3], [3, size - 4]].forEach(([cx, cy]) => {
      for (let dy = -4; dy <= 4; dy++) {
        for (let dx = -4; dx <= 4; dx++) {
          const x = cx + dx, y = cy + dy, d = Math.max(Math.abs(dx), Math.abs(dy));
          if (x >= 0 && x < size && y >= 0 && y < size) set(x, y, d !== 2 && d !== 4);
        }
      }
    });
    const pos = ALIGN[version], last = pos.length - 1;
    pos.forEach((ax, i) => pos.forEach((ay, j) => {
      if ((i === 0 && j === 0) || (i === 0 && j === last) || (i === last && j === 0)) return;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) set(ax + dx, ay + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }));
    if (version >= 7) {
      let rem = version;
      for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1f25);
      const bits = (version << 12) | rem;
      for (let i = 0; i < 18; i++) {
        const on = ((bits >>> i) & 1) === 1, a = size - 11 + (i % 3), b = Math.floor(i / 3);
        set(a, b, on);
        set(b, a, on);
      }
    }
    format(dark, fixed, size, 0);  // reserves the format areas
    return { size, dark, fixed };
  }

  function format(dark, fixed, size, mask) {
    const data = mask;  // level M: format bits 00
    let rem = data;
    for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
    const bits = ((data << 10) | rem) ^ 0x5412;
    const bit = (i) => ((bits >>> i) & 1) === 1;
    const set = (x, y, on) => { dark[y][x] = on; fixed[y][x] = true; };
    for (let i = 0; i <= 5; i++) set(8, i, bit(i));
    set(8, 7, bit(6));
    set(8, 8, bit(7));
    set(7, 8, bit(8));
    for (let i = 9; i < 15; i++) set(14 - i, 8, bit(i));
    for (let i = 0; i < 8; i++) set(size - 1 - i, 8, bit(i));
    for (let i = 8; i < 15; i++) set(8, size - 15 + i, bit(i));
    set(8, size - 8, true);
  }

  const MASKS = [(x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
    (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => ((x * y) % 2) + ((x * y) % 3) === 0,
    (x, y) => (((x * y) % 2) + ((x * y) % 3)) % 2 === 0, (x, y) => (((x + y) % 2) + ((x * y) % 3)) % 2 === 0];

  function penalty(dark, size) {
    let score = 0;
    const line = (get) => {
      for (let a = 0; a < size; a++) {
        let run = 1;
        const cells = [];
        for (let b = 0; b < size; b++) cells.push(get(a, b));
        for (let b = 1; b <= size; b++) {
          if (b < size && cells[b] === cells[b - 1]) { run++; continue; }
          if (run >= 5) score += run - 2;
          run = 1;
        }
        const s = cells.map((c) => (c ? "1" : "0")).join("");
        score += 40 * ((s.match(/(?=10111010000)/g) || []).length + (s.match(/(?=00001011101)/g) || []).length);
      }
    };
    line((a, b) => dark[a][b]);
    line((a, b) => dark[b][a]);
    let count = 0;
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (dark[y][x]) count++;
        if (x < size - 1 && y < size - 1) {
          const c = dark[y][x];
          if (dark[y][x + 1] === c && dark[y + 1][x] === c && dark[y + 1][x + 1] === c) score += 3;
        }
      }
    }
    return score + 10 * Math.floor(Math.abs(count * 20 - size * size * 10) / (size * size));
  }

  function qr(text) {
    const { version, out } = codewords(utf8(text));
    const base = build(version);
    const size = base.size;
    const placed = base.dark.map((row) => row.slice());
    let i = 0;
    for (let right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let vert = 0; vert < size; vert++) {
        for (let j = 0; j < 2; j++) {
          const x = right - j, up = ((right + 1) & 2) === 0, y = up ? size - 1 - vert : vert;
          if (!base.fixed[y][x] && i < out.length * 8) {
            placed[y][x] = ((out[i >>> 3] >>> (7 - (i & 7))) & 1) === 1;
            i++;
          }
        }
      }
    }
    let best = null;
    MASKS.forEach((fn, m) => {
      const dark = placed.map((row, y) => row.map((on, x) => (base.fixed[y][x] ? on : on !== fn(x, y))));
      const fixed = base.fixed.map((row) => row.slice());
      format(dark, fixed, size, m);
      const score = penalty(dark, size);
      if (!best || score < best.score) best = { score, dark };
    });
    return { size, version, dark: (x, y) => best.dark[y][x] };
  }

  function canvas(text, px) {
    const code = qr(text);
    const n = code.size + 8;
    const scale = Math.max(2, Math.floor((px || 200) / n));
    const node = document.createElement("canvas");
    node.width = node.height = n * scale;
    const g = node.getContext("2d");
    g.fillStyle = "#fff";
    g.fillRect(0, 0, node.width, node.height);
    g.fillStyle = "#000";
    for (let y = 0; y < code.size; y++) {
      for (let x = 0; x < code.size; x++) if (code.dark(x, y)) g.fillRect((x + 4) * scale, (y + 4) * scale, scale, scale);
    }
    return node;
  }

  if (typeof window !== "undefined" && window.DA) Object.assign(window.DA, { qr, qrCanvas: canvas });
  if (typeof module !== "undefined") module.exports = { qr };
})();
