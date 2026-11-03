// The cube field: you at the centre, clusters that shape themselves, cubes, and their lenses.
// Canvas 2D with its own small 3D maths, so the page needs no network.
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
  const focus = { cluster: null, node: null, lens: null, link: null };
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
  // Foundational cubes gather loosely in their own group
  const cloud = cl => {
    const count = cl.nodes.length;
    cl.reach = 80 + Math.sqrt(count) * 18;
    cl.spread = cl.reach * 2;
    cl.nodes.forEach((n, i) => {
      const y = count > 1 ? 1 - (2 * i) / (count - 1) : 0, r = Math.sqrt(1 - y * y), a = i * 2.399963;
      const out = cl.reach * (.75 + rand(n.seed, 8) * .5);
      n.slot = [Math.cos(a) * r * out, y * out * .8, Math.sin(a) * r * out];
    });
  };
  // The three kinds of foundation (FOUNDATIONS, in view_grid.js) circle you together
  const FOUND_R = 170, orbit = { angle: 0, turn: .03 };
  const cores = FOUNDATIONS.map(([kind, topic, rgb], k) => ({
    group: "", topic, kind, rgb, rigid: true, loose: true, turn: .05, angle: 0, slotAngle: k * Math.PI * 2 / 3,
    home: [0, 0, 0], nodes: [], c: [0, 0, 0], half: 40, reach: 80 }));
  const kindOf = c => foundationOf(c)[0];
  const placeCores = () => cores.forEach(cl => {
    cl.home = add(world.c, turned([FOUND_R, 0, 0], orbit.angle + cl.slotAngle));
  });

  // What defines you circles outside the foundations, the other way round
  const ring = cl => {
    cl.reach = FOUND_R + Math.max(...cores.map(f => f.nodes.length ? f.reach : 0)) + 50;
    cl.spread = cl.reach * 1.4;
    cl.nodes.forEach((n, i) => {
      const a = i / cl.nodes.length * Math.PI * 2;
      n.slot = [Math.cos(a) * cl.reach, Math.sin(i * 2.4) * 22, Math.sin(a) * cl.reach];
    });
  };
  const self = { group: "", topic: `What defines ${USER}`, rigid: true, circle: true, turn: -.09, angle: 0, home: [0, 0, 0], nodes: [], c: [0, 0, 0], half: 40, reach: 100 };
  const turned = (p, a) => [p[0] * Math.cos(a) - p[2] * Math.sin(a), p[1], p[0] * Math.sin(a) + p[2] * Math.cos(a)];

  const shell = cl => {
    if (cl.circle) return ring(cl);
    if (cl.loose) return cloud(cl);
    const count = cl.nodes.length;
    cl.spread = 60 + count * 24;
    cl.nodes.forEach((n, i) => {
      const y = count > 1 ? 1 - (2 * i) / (count - 1) : 0, r = Math.sqrt(1 - y * y), a = i * 2.399963;
      n.slot = [Math.cos(a) * r * cl.spread, y * cl.spread * .75, Math.sin(a) * r * cl.spread];
    });
  };
  clusters.forEach(shell);

  const links = [], byId = Object.fromEntries(nodes.map(n => [n.c.id, n]));
  const link = (a, b, kind, into = links) => {
    if (a !== b && !into.some(l => (l.a === a && l.b === b) || (l.a === b && l.b === a)))
      into.push({ a, b, kind, seed: rand(a.seed, b.seed % 97) });
  };
  // Links that come from the cubes themselves, the same in every view:
  // your neighbours, contradictions, and suggested links waiting for you
  const OWN = ["neighbour", "contra", "proposed"];
  const relate = into => {
    for (let i = into.length - 1; i >= 0; i--) if (OWN.includes(into[i].kind)) into.splice(i, 1);
    nodes.forEach(n => {
      n.c.neighbours.forEach(id => byId[id] && link(n, byId[id], "neighbour", into));
      if (n.c.contradicts && byId[n.c.contradicts]) link(n, byId[n.c.contradicts], "contra", into);
    });
    nodes.forEach(n => (n.c.link_drafts || []).forEach(d => byId[d.other] && link(n, byId[d.other], "proposed", into)));
  };
  relate(links);
  clusters.forEach(cl => cl.nodes.forEach((n, i) => {
    if (cl.nodes.length > 1) link(n, cl.nodes[(i + 1) % cl.nodes.length], "topic");
    if (cl.nodes.length > 4) link(n, cl.nodes[(i + 2) % cl.nodes.length], "topic");
  }));
  nodes.forEach(n => {
    const other = nodes.find(m => m.cluster !== n.cluster && m.c.group === n.c.group
      && m.c.tags.some(t => n.c.tags.includes(t) && t !== "pca9685" && t !== "hardware"));
    if (other) link(n, other, "bridge");
  });

  const tagClusters = [...clusters], tagHome = new Map(nodes.map(n => [n, n.cluster]));
  const tagLinks = [...links];
  let mode = "TAGS";

  function physics(dt, time) {
    for (const n of nodes) {
      const open = focus.cluster === n.cluster || n.cluster.rigid;
      const pull = open ? add(n.cluster.home, n.cluster.rigid ? turned(n.slot, n.cluster.angle) : n.slot) : n.cluster.home;
      // Loose clusters keep only a light hold on their places, so their cubes wander
      const grip = n.cluster.loose ? .4 : open ? 7 : n.fresh > 0 ? 2.4 : .3;
      for (let k = 0; k < 3; k++) {
        n.v[k] += (pull[k] - n.p[k]) * grip * dt;
        if (!calm) n.v[k] += Math.sin(time * .35 + n.seed + k * 2) * 9 * dt;
      }
      // Closed clusters turn slowly, each cube round its own tilted axis
      if (!calm && !open) {
        const r = [n.p[0] - pull[0], n.p[1] - pull[1], n.p[2] - pull[2]];
        const tilt = (n.seed % 7 - 3) * .18;
        n.v[0] += (r[2] + r[1] * tilt) * .16 * dt;
        n.v[2] -= r[0] * .16 * dt;
        n.v[1] -= r[0] * tilt * .16 * dt;
      }
    }
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      if (a.cluster.rigid && b.cluster.rigid && !(a.cluster.loose && b.cluster.loose)) continue;
      const d = [a.p[0] - b.p[0], a.p[1] - b.p[1], a.p[2] - b.p[2]];
      const dist = Math.max(Math.hypot(...d), 1);
      if (dist > 240) continue;
      const force = 13000 / (dist * dist) * dt;
      for (let k = 0; k < 3; k++) { a.v[k] += d[k] / dist * force; b.v[k] -= d[k] / dist * force; }
    }
    for (const l of links) {
      if (l.kind === "bridge" || l.kind === "proposed" || l.a.cluster !== l.b.cluster) continue;
      const d = [l.b.p[0] - l.a.p[0], l.b.p[1] - l.a.p[1], l.b.p[2] - l.a.p[2]];
      const pull = (Math.hypot(...d) - 110) * .28 * dt / Math.max(Math.hypot(...d), 1);
      for (let k = 0; k < 3; k++) { l.a.v[k] += d[k] * pull; l.b.v[k] -= d[k] * pull; }
    }
    // A pulled strand draws its two cubes towards each other, out of their clusters
    if (focus.link) {
      const { a, b } = focus.link, d = [b.p[0] - a.p[0], b.p[1] - a.p[1], b.p[2] - a.p[2]];
      const gap = Math.max(Math.hypot(...d), 1), pull = Math.max(0, gap - 280) * 1.2 * dt / gap;
      for (let k = 0; k < 3; k++) { a.v[k] += d[k] * pull; b.v[k] -= d[k] * pull; }
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
    focus.cluster = focus.node = focus.lens = focus.link = null;
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
      relate(links);
      groups = [];
    }
    const found = nodes.filter(n => n.c.tags.includes("foundational"));
    const defining = nodes.filter(n => n.c.tags.includes("defining") && !found.includes(n));
    const placed = [...found, ...defining];
    if (placed.length) {
      clusters.forEach(cl => { cl.nodes = cl.nodes.filter(n => !placed.includes(n)); });
      const kept = clusters.filter(cl => cl.nodes.length);
      clusters.length = 0;
      clusters.push(...kept);
      const lists = [...cores.map(cl => [cl, found.filter(n => kindOf(n.c) === cl.kind)]), [self, defining]];
      for (const [cl, list] of lists) {
        cl.nodes = list;
        list.forEach(n => { n.cluster = cl; });
        if (list.length) clusters.push(cl);
      }
    }
    clusters.forEach(shell);
    fitBoxes();
    placeCores();
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
    relate(tagLinks);
    loadMoments();
    applyMode(MODES[mode] || mode === "TAGS" ? mode : "ALL", true);
    if (byId[flyId]) { byId[flyId].fresh = 7; byId[flyId].trail = byId[flyId].trail || []; }
    draw();
    renderStats();
  }

