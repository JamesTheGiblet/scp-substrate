// The cube field: one big cube, holding clusters, holding cubes, holding lenses.
// Canvas 2D with its own small 3D maths, so the page needs no network.
(() => {
  const canvas = document.getElementById("field");
  const ctx = canvas.getContext("2d");
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const RGB = {
    FACT: [84, 146, 240], COUNTER: [240, 104, 96], OPINION: [242, 178, 52],
    FICTION: [168, 132, 238], CONTEXT: [62, 190, 180], HUMAN: [94, 198, 112],
  };
  const SIDES = [
    ["FACT", [4, 5, 6, 7]], ["CONTEXT", [1, 0, 3, 2]], ["COUNTER", [5, 1, 2, 6]],
    ["FICTION", [0, 4, 7, 3]], ["HUMAN", [7, 6, 2, 3]], ["OPINION", [0, 1, 5, 4]],
  ];
  const CORNERS = [[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]];
  const EDGES = [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  const OUT = { FACT: [0,0,1], CONTEXT: [0,0,-1], COUNTER: [1,0,0], FICTION: [-1,0,0], HUMAN: [0,1,0], OPINION: [0,-1,0] };
  const NAMES = { HUMAN: "YOU" };

  const hash = text => [...text].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7);
  const rand = (seed, n) => { const x = Math.sin(seed * 12.9898 + n * 78.233) * 43758.5453; return x - Math.floor(x); };
  const add = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k];
  const mix = (a, b, t) => a + (b - a) * t;

  // --- the world -----------------------------------------------------------
  const groupNames = [...new Set(CUBES.map(c => c.group))].sort((a, b) =>
    (a === "Project claims" ? "" : a).localeCompare(b === "Project claims" ? "" : b));

  function topicOf(c, peers) {
    const count = t => peers.filter(p => p.tags.includes(t)).length;
    const usable = c.tags.filter(t => count(t) >= 2 && count(t) < peers.length);
    usable.sort((a, b) => count(b) - count(a) || a.localeCompare(b));
    return usable[0] || c.tags[0] || "other";
  }

  const clusters = [], nodes = [];
  const focus = { cluster: null, node: null, lens: null };
  groupNames.forEach((group, g) => {
    const peers = CUBES.filter(c => c.group === group);
    const angle = (g / groupNames.length) * Math.PI * 2;
    const home = groupNames.length > 1 ? [Math.cos(angle) * 640, 0, Math.sin(angle) * 640] : [0, 0, 0];
    const topics = [...new Set(peers.map(c => topicOf(c, peers)))].sort();
    topics.forEach((topic, t) => {
      // Spread topics evenly over a sphere around the group's home
      const y = 1 - (2 * (t + .5)) / topics.length, r = Math.sqrt(1 - y * y), a = t * 2.399963;
      const cluster = { group, topic, home: add(home, [Math.cos(a) * r * 340, y * 290, Math.sin(a) * r * 340]),
                        nodes: [], c: [0, 0, 0], half: 40 };
      clusters.push(cluster);
      peers.filter(c => topicOf(c, peers) === topic).forEach((c, i) => {
        const seed = hash(c.id);
        const node = {
          c, cluster, seed, sats: [], open: 0, hover: 0, r: 11 + c.score * 6,
          p: add(cluster.home, [rand(seed, 1) * 80 - 40, rand(seed, 2) * 80 - 40, rand(seed, 3) * 80 - 40]),
          v: [0, 0, 0], ry: rand(seed, 4) * 6, rx: rand(seed, 5) * 6, spin: .1 + rand(seed, 6) * .2,
        };
        node.sats = [...LENSES, "HUMAN"].map(lens => ({ node, lens, ry: rand(seed, 7), p: node.p }));
        cluster.nodes.push(node);
        nodes.push(node);
      });
    });
  });

  // Each cube's own place on a shell, used while its cluster is open
  const shell = cl => {
    const count = cl.nodes.length;
    cl.spread = 60 + count * 24;
    cl.nodes.forEach((n, i) => {
      const y = count > 1 ? 1 - (2 * i) / (count - 1) : 0, r = Math.sqrt(1 - y * y), a = i * 2.399963;
      n.slot = [Math.cos(a) * r * cl.spread, y * cl.spread * .75, Math.sin(a) * r * cl.spread];
    });
  };
  clusters.forEach(shell);

  const links = [], byId = Object.fromEntries(nodes.map(n => [n.c.id, n]));
  const link = (a, b, kind) => {
    if (a !== b && !links.some(l => (l.a === a && l.b === b) || (l.a === b && l.b === a)))
      links.push({ a, b, kind, seed: rand(a.seed, b.seed % 97) });
  };
  clusters.forEach(cl => cl.nodes.forEach((n, i) => {
    if (cl.nodes.length > 1) link(n, cl.nodes[(i + 1) % cl.nodes.length], "topic");
    if (cl.nodes.length > 4) link(n, cl.nodes[(i + 2) % cl.nodes.length], "topic");
  }));
  nodes.forEach(n => {
    n.c.neighbours.forEach(id => byId[id] && link(n, byId[id], "neighbour"));
    if (n.c.contradicts && byId[n.c.contradicts]) link(n, byId[n.c.contradicts], "contra");
    const other = nodes.find(m => m.cluster !== n.cluster && m.c.group === n.c.group
      && m.c.tags.some(t => n.c.tags.includes(t) && t !== "pca9685" && t !== "hardware"));
    if (other) link(n, other, "bridge");
  });

  const tagClusters = [...clusters], tagHome = new Map(nodes.map(n => [n, n.cluster]));
  const tagLinks = [...links];
  let mode = "TAGS";

  function physics(dt, time) {
    for (const n of nodes) {
      const open = focus.cluster === n.cluster;
      const pull = open ? add(n.cluster.home, n.slot) : n.cluster.home;
      const grip = open ? 7 : n.fresh > 0 ? 2.4 : .3;
      for (let k = 0; k < 3; k++) {
        n.v[k] += (pull[k] - n.p[k]) * grip * dt;
        if (!calm) n.v[k] += Math.sin(time * .35 + n.seed + k * 2) * 9 * dt;
      }
    }
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      const d = [a.p[0] - b.p[0], a.p[1] - b.p[1], a.p[2] - b.p[2]];
      const dist = Math.max(Math.hypot(...d), 1);
      if (dist > 240) continue;
      const force = 13000 / (dist * dist) * dt;
      for (let k = 0; k < 3; k++) { a.v[k] += d[k] / dist * force; b.v[k] -= d[k] / dist * force; }
    }
    for (const l of links) {
      if (l.kind === "bridge" || l.a.cluster !== l.b.cluster) continue;
      const d = [l.b.p[0] - l.a.p[0], l.b.p[1] - l.a.p[1], l.b.p[2] - l.a.p[2]];
      const pull = (Math.hypot(...d) - 110) * .28 * dt / Math.max(Math.hypot(...d), 1);
      for (let k = 0; k < 3; k++) { l.a.v[k] += d[k] * pull; l.b.v[k] -= d[k] * pull; }
    }
    for (const n of nodes) for (let k = 0; k < 3; k++) {
      n.v[k] *= Math.pow(.2, dt);
      n.p[k] += n.v[k] * dt;
    }
  }
  for (let i = 0; i < 500; i++) physics(.03, i * .03);

  const box = list => {
    const lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    list.forEach(n => n.p.forEach((v, k) => { lo[k] = Math.min(lo[k], v); hi[k] = Math.max(hi[k], v); }));
    return { c: lo.map((v, k) => (v + hi[k]) / 2), half: Math.max(...lo.map((v, k) => (hi[k] - v) / 2)) + 30 };
  };
  const tagGroups = groupNames.map(name => ({ name, list: nodes.filter(n => n.c.group === name), c: [0,0,0], half: 100 }));
  let groups = tagGroups;
  const world = { c: [0, 0, 0], half: 300 };
  const fitBoxes = () => {
    clusters.forEach(cl => Object.assign(cl, box(cl.nodes)));
    groups.forEach(g => { const b = box(g.list); g.c = b.c; g.half = b.half + 26; });
    Object.assign(world, box(nodes)); world.half += 46;
  };
  fitBoxes();

  // Regroup the same cubes; they fly to their new homes
  function applyMode(next, keep) {
    mode = next;
    const kept = keep ? focus.node : null;
    focus.cluster = focus.node = focus.lens = null;
    clusters.length = 0;
    links.length = 0;
    let reach = 900;
    if (next === "TAGS") {
      clusters.push(...tagClusters);
      links.push(...tagLinks);
      nodes.forEach(n => { n.cluster = tagHome.get(n); });
      groups = tagGroups;
    } else {
      const data = MODES[next], count = data.clusters.length;
      reach = 330 + count * 34;
      data.clusters.forEach((entry, i) => {
        const y = count > 1 ? 1 - (2 * i + 1) / count : 0, r = Math.sqrt(1 - y * y), a = i * 2.399963;
        const cl = { group: "", topic: entry.name, home: [Math.cos(a) * r * reach, y * reach * .8, Math.sin(a) * r * reach],
                     nodes: entry.members.map(id => byId[id]), c: [0, 0, 0], half: 40 };
        cl.nodes.forEach(n => { n.cluster = cl; });
        clusters.push(cl);
      });
      data.links.forEach(l => links.push({ a: byId[l.a], b: byId[l.b], kind: "lens", lens: l.lens,
                                           term: l.term, seed: rand(byId[l.a].seed, byId[l.b].seed % 97) }));
      groups = [];
    }
    clusters.forEach(shell);
    fitBoxes();
    world.half = Math.max(world.half, reach + 120);
    if (kept) {
      focus.node = kept;
      focus.cluster = kept.cluster;
      fillPanel(kept);
      setCrumbs();
    } else if (panelReady && !keep) goHome();
    else if (panelReady) setCrumbs();
  }
  let panelReady = false;

  // New data from the server. Unknown cubes fly in from outside the big cube.
  function update(cubes, modes, flyId) {
    CUBES.length = 0;
    CUBES.push(...cubes);
    Object.keys(MODES).forEach(k => delete MODES[k]);
    Object.assign(MODES, modes);
    for (const c of cubes) {
      const known = byId[c.id];
      if (known) {
        known.c = c;
        known.r = 11 + c.score * 6;
        continue;
      }
      const seed = hash(c.id);
      const a = rand(seed, 1) * 6.28, far = world.half * 2.1;
      const home = tagClusters.find(cl => c.tags.includes(cl.topic)) || tagClusters[0];
      const n = { c, cluster: home, seed, sats: [], open: 0, hover: 0, r: 11 + c.score * 6, trail: [],
                  p: add(world.c, [Math.cos(a) * far, -far * .5, Math.sin(a) * far]), v: [0, 0, 0],
                  ry: rand(seed, 4) * 6, rx: rand(seed, 5) * 6, spin: .3 };
      n.sats = [...LENSES, "HUMAN"].map(lens => ({ node: n, lens, ry: rand(seed, 7), p: n.p }));
      home.nodes.push(n);
      tagHome.set(n, home);
      nodes.push(n);
      byId[c.id] = n;
      tagGroups.forEach(g => { if (g.name === c.group) g.list.push(n); });
    }
    tagClusters.forEach(shell);
    applyMode(MODES[mode] || mode === "TAGS" ? mode : "ALL", true);
    if (byId[flyId]) { byId[flyId].fresh = 7; byId[flyId].trail = byId[flyId].trail || []; }
    draw();
    renderStats();
  }

  // --- camera --------------------------------------------------------------
  const cam = { yaw: .6, pitch: .34, dist: 1300, t: [...world.c], toDist: 1300 };
  let W = 0, H = 0, F = 800;
  const view = { filter: "all", query: "" };

  function project(p) {
    const x = p[0] - cam.t[0], y = p[1] - cam.t[1], z = p[2] - cam.t[2];
    const cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
    const x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
    const y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    const d = cam.dist + z2;
    if (d < 24) return null;
    const k = F / d;
    return { x: mid() + x1 * k, y: H / 2 + y2 * k, d, k };
  }
  const mid = () => W / 2 - (focus.node && W > 760 ? Math.min(W * .16, 205) : 0);
  const fog = d => Math.max(.1, Math.min(1, 1.5 - d / (cam.dist * 2.1)));

  function matches(c) {
    if (view.filter === "attested" && c.status !== "attested") return false;
    if (view.filter === "needs" && c.status === "attested") return false;
    if (!view.query) return true;
    const text = [c.id, c.content, ...Object.values(c.faces).map(f => f ? f.content : "")].join(" ").toLowerCase();
    return text.includes(view.query);
  }

  function drawCube(item) {
    const { p, size, ry, rx, faces, alpha } = item;
    const cy = Math.cos(ry), sy = Math.sin(ry), cx = Math.cos(rx), sx = Math.sin(rx);
    const pts = CORNERS.map(([a, b, c]) => {
      const x = a * cy + c * sy, z = -a * sy + c * cy, y = b * cx - z * sx, zz = b * sx + z * cx;
      return project(add(p, [x, y, zz], size));
    });
    if (pts.some(q => !q)) return;
    for (const [lens, idx] of SIDES) {
      const q = idx.map(i => pts[i]);
      const area = (q[1].x - q[0].x) * (q[2].y - q[0].y) - (q[1].y - q[0].y) * (q[2].x - q[0].x);
      if (area <= 0) continue;
      const light = .62 + .38 * Math.min(1, Math.abs(area) / (size * size * q[0].k * q[0].k * 4));
      ctx.beginPath();
      q.forEach((v, i) => i ? ctx.lineTo(v.x, v.y) : ctx.moveTo(v.x, v.y));
      ctx.closePath();
      const face = faces[lens];
      if (face) {
        const [r, g, b] = RGB[lens];
        const dim = face === "unread" ? .62 : 1;
        ctx.globalAlpha = alpha;
        ctx.fillStyle = `rgb(${r * light * dim | 0},${g * light * dim | 0},${b * light * dim | 0})`;
        ctx.fill();
        ctx.strokeStyle = "rgba(255,255,255,.28)";
        ctx.lineWidth = .7;
        ctx.stroke();
      } else {
        ctx.globalAlpha = alpha * .9;
        ctx.fillStyle = "rgba(120,135,165,.07)";
        ctx.fill();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = "rgba(170,185,215,.55)";
        ctx.lineWidth = .8;
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }
    ctx.globalAlpha = 1;
  }

  function wire(c, half, rgb, alpha) {
    const pts = CORNERS.map(v => project(add(c, v, half)));
    ctx.strokeStyle = `rgba(${rgb},${alpha})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (const [a, b] of EDGES) {
      if (!pts[a] || !pts[b]) continue;
      ctx.moveTo(pts[a].x, pts[a].y);
      ctx.lineTo(pts[b].x, pts[b].y);
    }
    ctx.stroke();
  }

  function glow(q, radius, rgb, alpha) {
    const g = ctx.createRadialGradient(q.x, q.y, 0, q.x, q.y, radius);
    g.addColorStop(0, `rgba(${rgb},${alpha})`);
    g.addColorStop(1, `rgba(${rgb},0)`);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(q.x, q.y, radius, 0, 7);
    ctx.fill();
  }

  function label(text, q, size, alpha, weight = 600) {
    ctx.font = `${weight} ${size}px system-ui, "Segoe UI", sans-serif`;
    ctx.textAlign = "center";
    ctx.fillStyle = `rgba(226,232,244,${alpha})`;
    ctx.fillText(text, q.x, q.y);
  }

  const dust = Array.from({ length: 170 }, (_, i) => [
    (rand(i, 1) - .5) * 4800, (rand(i, 2) - .5) * 4800, (rand(i, 3) - .5) * 4800]);
  const faceMap = n => {
    const out = {};
    LENSES.forEach(l => { const f = n.c.faces[l]; if (f && !f.pending) out[l] = f.unread ? "unread" : "read"; });
    if (n.c.validation && !n.c.validation.stale) out.HUMAN = "read";
    return out;
  };

  function frame(ms) {
    const time = ms / 1000, dt = Math.min(.04, (time - (frame.last || time)) || .016);
    frame.last = time;
    physics(dt, time);
    fitBoxes();

    // Glide to whatever is in focus
    const aim = focus.node ? focus.node.p : focus.cluster ? focus.cluster.c : world.c;
    const ease = 1 - Math.exp(-dt * 3.4);
    cam.t = cam.t.map((v, k) => mix(v, aim[k], ease));
    cam.dist = mix(cam.dist, cam.toDist, ease);
    if (!calm && !drag && !focus.node) cam.yaw += dt * .05;

    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    const sky = ctx.createRadialGradient(W / 2, H / 2, 60, W / 2, H / 2, Math.max(W, H) * .75);
    sky.addColorStop(0, "#141a2c"); sky.addColorStop(1, "#06070d");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, W, H);

    for (const d of dust) {
      const q = project(d);
      if (!q) continue;
      ctx.fillStyle = `rgba(190,205,235,${.09 + .3 * fog(q.d)})`;
      ctx.fillRect(q.x, q.y, 1.4, 1.4);
    }

    // Glass: the big cube, the groups and the clusters
    const inside = focus.node || focus.cluster;
    wire(world.c, world.half, "150,185,245", inside ? .12 : .5);
    groups.forEach(g => wire(g.c, g.half, "120,205,235", inside ? .1 : .36));
    clusters.forEach(cl => {
      const on = focus.cluster === cl;
      wire(cl.c, cl.half, on ? "150,215,255" : "110,150,205", on ? .5 : inside ? .06 : .22);
    });

    // Threads, with a pulse travelling along each
    const lit = focus.node;
    for (const l of links) {
      const a = project(l.a.p), b = project(l.b.p);
      if (!a || !b) continue;
      const touches = lit && (l.a === lit || l.b === lit);
      const base = l.kind === "bridge" ? .08 : l.kind === "neighbour" ? .55 : l.kind === "lens" ? .42 : .2;
      const alpha = (lit ? (touches ? .7 : .04) : base) * fog((a.d + b.d) / 2);
      const rgb = l.kind === "lens" ? RGB[l.lens].join(",") : l.kind === "neighbour" ? "242,200,100"
        : l.kind === "contra" ? "240,104,96" : "120,185,255";
      ctx.strokeStyle = `rgba(${rgb},${alpha})`;
      ctx.lineWidth = touches ? 1.4 : .8;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      if (!calm && l.kind !== "bridge") {
        const t = (time * .16 + l.seed) % 1;
        const dot = { x: mix(a.x, b.x, t), y: mix(a.y, b.y, t) };
        ctx.fillStyle = `rgba(${rgb},${Math.min(1, alpha * 2.2)})`;
        ctx.beginPath(); ctx.arc(dot.x, dot.y, touches ? 2.2 : 1.3, 0, 7); ctx.fill();
      }
    }

    // Cubes and their lenses, furthest first
    const items = [];
    for (const n of nodes) {
      n.ry += dt * n.spin * (calm ? 0 : 1);
      n.rx += dt * n.spin * .4 * (calm ? 0 : 1);
      n.open = mix(n.open, focus.node === n ? 1 : 0, 1 - Math.exp(-dt * 5));
      n.hover = mix(n.hover, hover === n ? 1 : 0, 1 - Math.exp(-dt * 10));
      if (n.fresh > 0) {
        n.fresh -= dt;
        n.trail = n.trail || [];
        n.trail.push([...n.p]);
        if (n.trail.length > 46) n.trail.shift();
      } else if (n.trail && n.trail.length) n.trail.shift();
      const q = project(n.p);
      if (n.trail && n.trail.length > 1) {
        n.trail.forEach((p, i) => {
          const dot = project(p);
          if (dot) glow(dot, 3 + i * .14, "120,235,255", .03 + i / n.trail.length * .2);
        });
      }
      if (!q) continue;
      const near = !focus.cluster || focus.cluster === n.cluster;
      const fade = (matches(n.c) ? 1 : .07) * (focus.node && focus.node !== n ? .13 : near ? 1 : .1);
      items.push({ type: "cube", n, d: q.d, q, p: n.p, size: n.r * (1 + n.hover * .18) * (1 - n.open * .25),
                   ry: n.ry, rx: n.rx, faces: faceMap(n), alpha: fade * fog(q.d) });
      if (n.open > .02) n.sats.forEach((sat, i) => {
        const dir = OUT[sat.lens], turn = time * .22 + i * .12, c = Math.cos(turn), s = Math.sin(turn);
        const off = [dir[0] * c + dir[2] * s, dir[1], -dir[0] * s + dir[2] * c];
        sat.p = add(n.p, off, n.r * 3.1 * n.open);
        const sq = project(sat.p);
        if (!sq) return;
        const live = n.c.faces[sat.lens];
        const present = sat.lens === "HUMAN" ? n.c.validation && !n.c.validation.stale : Boolean(live && !live.pending);
        sat.q = sq;
        items.push({ type: "lens", sat, q: sq, d: sq.d, p: sat.p, size: n.r * .42 * n.open * (focus.lens === sat.lens ? 1.5 : 1),
                     ry: time * .5 + i, rx: time * .3 + i, alpha: n.open, present });
      });
    }
    items.sort((a, b) => b.d - a.d);
    ctx.lineJoin = "round";
    for (const it of items) {
      if (it.type === "cube" && it.n.fresh > 0) glow(it.q, it.size * it.q.k * 4.2, "120,235,255", Math.min(.6, it.n.fresh * .2));
      if (it.type === "cube" && it.n.c.status === "attested") glow(it.q, it.size * it.q.k * 3.2, "242,190,70", .34 * it.alpha);
      if (it.type === "lens") {
        const from = project(it.sat.node.p);
        if (from) {
          ctx.strokeStyle = `rgba(${RGB[it.sat.lens].join(",")},${.55 * it.alpha})`;
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(it.q.x, it.q.y); ctx.stroke();
        }
        drawLens(it, RGB[it.sat.lens]);
        continue;
      }
      drawCube(it);
    }

    // Names
    if (!focus.node) clusters.forEach(cl => {
      const q = project(add(cl.c, [0, -cl.half - 8, 0]));
      if (q && (!focus.cluster || focus.cluster === cl)) label("#" + cl.topic, q, focus.cluster ? 16 : 13, focus.cluster ? .95 : .85 * fog(q.d));
    });
    if (!inside) groups.forEach(g => {
      const q = project(add(g.c, [0, -g.half - 12, 0]));
      if (q) label(g.name, q, 16, .95, 700);
    });
    if (focus.cluster && !focus.node) {
      // Nearest names first; one that would land on another waits for hover
      const placed = [];
      focus.cluster.nodes
        .map(n => ({ n, q: project(add(n.p, [0, n.r * 2.1, 0])) }))
        .filter(x => x.q && matches(x.n.c))
        .sort((a, b) => a.q.d - b.q.d)
        .forEach(({ n, q }) => {
          const text = shorten(n.c.content, 34);
          ctx.font = '500 12px system-ui, "Segoe UI", sans-serif';
          const half = ctx.measureText(text).width / 2 + 6;
          if (placed.some(p => Math.abs(p.x - q.x) < p.half + half && Math.abs(p.y - q.y) < 17)) return;
          placed.push({ x: q.x, y: q.y, half });
          label(text, q, 12, .9, 500);
        });
    }
    if (focus.node) focus.node.sats.forEach(sat => {
      if (sat.q) label(sat.lens === "HUMAN" ? "YOU" : sat.lens, { x: sat.q.x, y: sat.q.y + 26 + focus.node.r * .4 * sat.q.k }, 11, .9, 700);
    });
    requestAnimationFrame(frame);
  }

  function drawLens(it, rgb) {
    // A lens cube is one colour on every side
    const saved = { ...RGB };
    SIDES.forEach(([name]) => { RGB[name] = rgb; });
    drawCube({ ...it, faces: it.present ? Object.fromEntries(SIDES.map(([name]) => [name, "read"])) : {} });
    Object.assign(RGB, saved);
    if (it.present) glow(it.q, it.size * it.q.k * 2.4, rgb.join(","), .22);
  }

  const shorten = (text, n) => (text.length > n ? text.slice(0, n - 1).trimEnd() + "…" : text);

  // --- moving around -------------------------------------------------------
  const crumbs = document.getElementById("crumbs");
  const panel = document.getElementById("panel");

  function setCrumbs() {
    const parts = [["Everything", goHome]];
    if (focus.cluster) parts.push(["#" + focus.cluster.topic, () => goCluster(focus.cluster)]);
    if (focus.node) parts.push([shorten(focus.node.c.content, 30), null]);
    crumbs.replaceChildren();
    parts.forEach(([text, go], i) => {
      if (i) crumbs.append(el("span", "sep", "›"));
      const b = el("button", "", text);
      if (go) b.addEventListener("click", go); else b.disabled = true;
      crumbs.append(b);
    });
  }
  function goHome() {
    focus.cluster = focus.node = focus.lens = null;
    cam.toDist = world.half * 2.42;
    panel.hidden = true; setCrumbs();
  }
  function goCluster(cl) {
    focus.cluster = cl; focus.node = focus.lens = null;
    cam.toDist = cl.spread * 3 + 150;
    panel.hidden = true; setCrumbs();
  }
  function goNode(n) {
    focus.cluster = n.cluster; focus.node = n; focus.lens = null;
    cam.toDist = n.r * 11;
    fillPanel(n); setCrumbs();
  }
  const back = () => focus.node ? goCluster(focus.node.cluster) : goHome();

  function fillPanel(n) {
    const c = n.c;
    panel.replaceChildren();
    const shut = el("button", "shut", "×");
    shut.setAttribute("aria-label", "Back out");
    shut.addEventListener("click", back);
    panel.append(shut, el("h3", "", c.content), el("p", "id", c.id));
    const facts = [LABEL[c.status], Math.round(c.score * 100) + "% complete", "standing " + c.standing.toFixed(2)];
    panel.append(el("p", "facts", facts.join(" · ")));
    const row = (lens, title, text, note) => {
      const b = el("button", "lens" + (text ? "" : " missing"));
      b.dataset.lens = lens;
      b.style.setProperty("--c", `rgb(${RGB[lens].join(",")})`);
      const head = el("b", "", title);
      if (note) head.append(el("em", "", " · " + note));
      b.append(head, document.createTextNode(text || "Not written yet"));
      b.addEventListener("click", () => { focus.lens = focus.lens === lens ? null : lens; });
      return b;
    };
    LENSES.forEach(lens => {
      const f = c.faces[lens];
      panel.append(row(lens, lens, f && f.content, f && f.pending ? "draft, not accepted" : f && f.unread ? "accepted without reading" : ""));
    });
    const v = c.validation;
    panel.append(row("HUMAN", "HUMAN VALIDATION", v && (v.note || "Validated"), v ? (v.stale ? "stale, a face changed" : "by " + v.validator) : ""));
    if (c.source) panel.append(el("p", "facts", "Source: " + c.source));
    if (c.attestation) panel.append(el("p", "facts", c.attestation.retracted
      ? "Attestation retracted: " + c.attestation.retracted
      : "Attested by " + c.attestation.source + (c.attestation.note ? ". " + c.attestation.note : "")));
    const near = links.filter(l => l.a === n || l.b === n);
    if (near.length) {
      panel.append(el("p", "facts", "Linked cubes"));
      near.slice(0, 7).forEach(l => {
        const m = l.a === n ? l.b : l.a;
        const why = l.lens ? `${l.lens}, "${l.term}": ` : "";
        const b = el("button", "hop", why + shorten(m.c.content, 52));
        b.addEventListener("click", () => goNode(m));
        panel.append(b);
      });
    }
    if (window.cubeEdit) cubeEdit.decorate(panel, c);
    panel.hidden = false;
  }

  function pick(x, y) {
    let best = null, bestGap = 1e9;
    if (focus.node) for (const sat of focus.node.sats) {
      if (sat.q && Math.hypot(sat.q.x - x, sat.q.y - y) < 26) return { sat };
    }
    for (const n of nodes) {
      const q = project(n.p);
      if (!q) continue;
      const gap = Math.hypot(q.x - x, q.y - y);
      if (gap < Math.max(n.r * q.k * 1.5, 11) && gap < bestGap) { best = n; bestGap = gap; }
    }
    return best ? { node: best } : null;
  }
  function clusterAt(x, y) {
    let best = null, bestGap = 1e9;
    for (const cl of clusters) {
      const q = project(cl.c);
      if (!q) continue;
      const gap = Math.hypot(q.x - x, q.y - y);
      if (gap < cl.half * q.k * 1.25 && gap < bestGap) { best = cl; bestGap = gap; }
    }
    return best;
  }

  let drag = null, hover = null;
  const points = new Map();
  const tip = document.getElementById("tip");
  canvas.addEventListener("pointerdown", e => {
    canvas.setPointerCapture(e.pointerId);
    points.set(e.pointerId, [e.clientX, e.clientY]);
    drag = { x: e.clientX, y: e.clientY, moved: 0, spread: 0 };
   
  });
  canvas.addEventListener("pointermove", e => {
    if (points.has(e.pointerId)) points.set(e.pointerId, [e.clientX, e.clientY]);
    if (drag && points.size === 2) {
      const [a, b] = [...points.values()], spread = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (drag.spread) cam.toDist *= drag.spread / spread;
      drag.spread = spread; drag.moved = 99;
      return;
    }
    if (drag) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      drag.moved += Math.abs(dx) + Math.abs(dy);
      cam.yaw -= dx * .006;
      cam.pitch = Math.max(-1.45, Math.min(1.45, cam.pitch + dy * .005));
      drag.x = e.clientX; drag.y = e.clientY;
      return;
    }
    const found = pick(e.clientX, e.clientY);
    hover = found && found.node || null;
    canvas.style.cursor = found || clusterAt(e.clientX, e.clientY) ? "pointer" : "grab";
    tip.hidden = !hover;
    if (hover) {
      tip.textContent = `${hover.c.content} (${LABEL[hover.c.status]})`;
      tip.style.left = Math.min(e.clientX + 14, W - 280) + "px";
      tip.style.top = e.clientY + 14 + "px";
    }
  });
  canvas.addEventListener("pointerup", e => {
    points.delete(e.pointerId);
    const moved = drag ? drag.moved : 99;
    drag = null;
    if (moved > 6) return;
    const found = pick(e.clientX, e.clientY);
    if (found && found.sat) { focus.lens = found.sat.lens; return; }
    if (found && focus.cluster && found.node.cluster === focus.cluster) return goNode(found.node);
    const cl = found ? found.node.cluster : clusterAt(e.clientX, e.clientY);
    if (cl && cl !== focus.cluster && !focus.node) return goCluster(cl);
    if (found && focus.node) return goNode(found.node);
    if (focus.cluster && !found) back();
  });
  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    cam.toDist = Math.max(60, Math.min(7000, cam.toDist * Math.exp(e.deltaY * .001)));
  }, { passive: false });
  addEventListener("keydown", e => {
    const typing = /INPUT|TEXTAREA/.test(document.activeElement.tagName) || document.querySelector("dialog[open]");
    if (e.key === "Escape" && !typing && !document.getElementById("root").hidden) back();
  });

  function resize() {
    W = innerWidth; H = innerHeight;
    canvas.width = W * devicePixelRatio; canvas.height = H * devicePixelRatio;
    F = Math.min(W, H) * .95;
  }
  addEventListener("resize", resize);
  resize();

  window.cubeField = {
    setFilter(filter) { view.filter = filter; },
    setQuery(query) { view.query = query; },
    show() { resize(); },
    mode() { return mode; },
    setMode: applyMode,
    update,
    refresh() { if (focus.node) fillPanel(focus.node); },
    // The current view as a PNG, stamped with where you are
    snapshot() {
      const shot = document.createElement("canvas");
      shot.width = canvas.width; shot.height = canvas.height;
      const out = shot.getContext("2d");
      out.drawImage(canvas, 0, 0);
      out.scale(devicePixelRatio, devicePixelRatio);
      out.font = '600 14px system-ui, "Segoe UI", sans-serif';
      out.fillStyle = "rgba(226,232,244,.85)";
      out.fillText(["Cube Field", focus.cluster && "#" + focus.cluster.topic, focus.node && focus.node.c.content]
        .filter(Boolean).join("  ›  "), 16, H - 16);
      return new Promise(done => shot.toBlob(done, "image/png"));
    },
    screenOf(id) { return project(byId[id].p); },
    clusterOf(id) { return project(byId[id].cluster.c); },
    state() { return { cluster: focus.cluster && focus.cluster.topic, node: focus.node && focus.node.c.id, panel: !panel.hidden }; },
  };

  panelReady = true;
  applyMode(MODES.ALL ? "ALL" : "TAGS");
  cam.dist = cam.toDist * 1.25;
  const hashText = decodeURIComponent(location.hash).slice(1);
  if (hashText.startsWith("mode:") && MODES[hashText.slice(5)]) applyMode(hashText.slice(5));
  if (hashText.startsWith("mode:") || hashText === "") {
    for (let i = 0; i < 400; i++) physics(.03, i * .03);
    fitBoxes();
  }
  const openCluster = clusters.find(cl => "topic:" + cl.topic === hashText);
  if (openCluster) {
    goCluster(openCluster);
    for (let i = 0; i < 300; i++) physics(.03, i * .03);
    fitBoxes();
    cam.t = [...openCluster.c];
    cam.dist = cam.toDist;
  }
  const linked = byId[hashText];
  if (linked) {
    goNode(linked);
    cam.t = [...linked.p];
    cam.dist = cam.toDist;
    linked.open = 1;
  }
  requestAnimationFrame(frame);
})();
