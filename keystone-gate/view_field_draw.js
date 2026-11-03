// Part of the cube field. kg_view.py joins these inside one function.
  // --- camera --------------------------------------------------------------
  const cam = { yaw: .6, pitch: .34, dist: 1300, t: [...world.c], toDist: 1300 };
  let W = 0, H = 0, F = 800;
  const view = { filter: "all", query: "", time: null };
  const shows = c => !view.time || !c.created || c.created <= view.time;

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
  const mid = () => W / 2 - ((focus.node || focus.link) && W > 760 ? Math.min(W * .16, 205) : 0);
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

  // From far away each cluster shows its strongest cubes; the rest wait for a zoom
  const LEADS = 3;
  function markLeads() {
    for (const cl of clusters) {
      const strong = cl.nodes.filter(n => shows(n.c))
        .sort((a, b) => b.c.score - a.c.score || b.c.standing - a.c.standing || a.c.id.localeCompare(b.c.id));
      cl.nodes.forEach(n => { n.lead = false; });
      strong.slice(0, cl.rigid ? strong.length : LEADS).forEach(n => { n.lead = true; });
    }
  }
  const zoomedIn = () => (focus.cluster ? 1 : Math.max(0, Math.min(1, (1 - cam.dist / (world.half * 2.42)) / .45)));
  // More cubes, smaller cubes, down to half size
  const crowding = () => Math.max(.5, Math.min(1, Math.sqrt(48 / Math.max(nodes.filter(n => shows(n.c)).length, 1))));

  function orbitClusters(dt) {
    placeCores();
    self.home = [...world.c];
    if (calm) return;
    if (!cores.includes(focus.cluster)) orbit.angle += orbit.turn * dt;
    for (const cl of [...cores, self]) if (focus.cluster !== cl) cl.angle += cl.turn * dt;
    if (focus.cluster || focus.link) return;
    for (const cl of clusters) {
      if (cl.rigid) continue;
      const x = cl.home[0] - world.c[0], z = cl.home[2] - world.c[2];
      // Inner clusters go round faster, so they pass one another
      const turn = dt * .05 * Math.min(1.6, 300 / Math.max(Math.hypot(x, z), 120));
      const c = Math.cos(turn), s = Math.sin(turn);
      cl.home[0] = world.c[0] + x * c - z * s;
      cl.home[2] = world.c[2] + x * s + z * c;
    }
  }

  function frame(ms) {
    const time = ms / 1000, dt = Math.min(.04, (time - (frame.last || time)) || .016);
    frame.last = time;
    orbitClusters(dt);
    physics(dt, time);
    fitBoxes();
    if (time - (frame.marked || 0) > .5) { markLeads(); frame.marked = time; }
    const zoom = zoomedIn(), shrink = mix(crowding(), 1, zoom), sifted = view.query || view.filter !== "all";

    // Glide to whatever is in focus
    const pulled = focus.link;
    const aim = focus.node ? focus.node.p : focus.cluster ? focus.cluster.c
      : pulled ? pulled.a.p.map((v, k) => (v + pulled.b.p[k]) / 2) : world.c;
    const ease = 1 - Math.exp(-dt * 3.4);
    cam.t = cam.t.map((v, k) => mix(v, aim[k], ease));
    cam.dist = mix(cam.dist, cam.toDist, ease);
    if (!calm && !drag && !focus.node && !pulled) cam.yaw += dt * .05;
    // While a strand is pulled, its two cubes and their clusters stay, and the rest fades
    const end = n => pulled && (n === pulled.a || n === pulled.b);
    const kin = cl => pulled && (cl === pulled.a.cluster || cl === pulled.b.cluster);

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

    // Each cluster's own form
    const inside = focus.node || focus.cluster || pulled;
    sk.setTransform(1, 0, 0, 1, 0, 0);
    sk.clearRect(0, 0, skin.width, skin.height);
    clusters.forEach(cl => {
      const on = focus.cluster === cl || kin(cl);
      if (cl.loose) growForm(cl, cl.rgb, on ? .7 : inside ? .12 : .45, time);
      else if (!cl.rigid) growForm(cl, on ? "150,215,255" : "110,160,215", on ? .6 : inside ? .1 : .34, time);
    });
    ctx.drawImage(skin, 0, 0, W, H);
    if (self.nodes.length) {
      ctx.strokeStyle = `rgba(94,235,130,${inside && focus.cluster !== self ? .2 : .8})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i <= 64; i++) {
        const q = project(add(self.home, turned([self.reach, 0, 0], i / 64 * Math.PI * 2)));
        if (q) ctx.lineTo(q.x, q.y);
      }
      ctx.stroke();
    }

    // Threads, with a pulse travelling along each
    const lit = focus.node;
    for (const l of links) {
      if (!shows(l.a.c) || !shows(l.b.c)) continue;
      const a = project(l.a.p), b = project(l.b.p);
      if (!a || !b) continue;
      const held = l === pulled, near = l === hoverLink;
      const touches = (lit && (l.a === lit || l.b === lit)) || held || near;
      const proposed = l.kind === "proposed";
      // A thread from a foundational cube takes that foundation's colour
      const amber = l.a.cluster.loose ? l.a.cluster.rgb : l.b.cluster.loose ? l.b.cluster.rgb : null;
      const base = l.kind === "bridge" ? .08 : l.kind === "neighbour" ? .55 : l.kind === "lens" ? .42 : proposed ? (amber ? .4 : .22) : .2;
      const alpha = (held ? 1 : near ? .9 : pulled ? (kin(l.a.cluster) && kin(l.b.cluster) ? .1 : .02)
        : lit ? (touches ? .7 : .04) : base * mix(.35, 1, zoom)) * (held ? 1 : fog((a.d + b.d) / 2));
      const rgb = l.kind === "lens" ? RGB[l.lens].join(",") : l.kind === "neighbour" ? (amber || "242,200,100")
        : l.kind === "contra" ? "240,104,96" : proposed ? (amber || "170,185,215") : "120,185,255";
      if (held) {
        // The pulled strand glows along its length
        for (let i = 0; i <= 8; i++) glow({ x: mix(a.x, b.x, i / 8), y: mix(a.y, b.y, i / 8) }, 14, rgb, .16);
      }
      ctx.strokeStyle = `rgba(${rgb},${alpha})`;
      ctx.lineWidth = held ? 3 : near ? 2.2 : touches ? 1.4 : .8;
      // A suggested link is dashed until you accept it
      if (proposed) ctx.setLineDash([4, 5]);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      ctx.setLineDash([]);
      if (!calm && l.kind !== "bridge" && !proposed) {
        const t = (time * .16 + l.seed) % 1;
        const dot = { x: mix(a.x, b.x, t), y: mix(a.y, b.y, t) };
        ctx.fillStyle = `rgba(${rgb},${Math.min(1, alpha * 2.2)})`;
        ctx.beginPath(); ctx.arc(dot.x, dot.y, held ? 3.2 : touches ? 2.2 : 1.3, 0, 7); ctx.fill();
      }
    }

    // You, at the centre, with a strand to every cube you have vouched for
    const you = project(world.c);
    if (you) {
      const dim = pulled ? .12 : inside ? .3 : 1;
      for (const n of nodes) {
        const valid = n.c.validation && !n.c.validation.stale, amber = n.cluster.loose ? n.cluster.rgb : null;
        if (!shows(n.c) || (!valid && !n.cluster.rigid)) continue;
        const q = project(n.p);
        if (!q) continue;
        const on = lit === n, alpha = (on ? .85 : valid ? .26 : .1) * dim * fog(q.d);
        ctx.strokeStyle = `rgba(${amber || "94,235,130"},${alpha})`;
        ctx.lineWidth = on ? 1.8 : 1;
        ctx.beginPath(); ctx.moveTo(you.x, you.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        if (!calm) {
          const t = (time * .1 + n.seed * .013) % 1;
          ctx.fillStyle = `rgba(170,255,190,${Math.min(1, alpha * 2.6)})`;
          ctx.beginPath(); ctx.arc(mix(you.x, q.x, t), mix(you.y, q.y, t), 1.5, 0, 7); ctx.fill();
        }
      }
      const r = 26 * you.k * (calm ? 1 : 1 + Math.sin(time * 1.3) * .07);
      glow(you, r * 5.5, "94,235,130", .34 * dim);
      glow(you, r * 2, "150,255,175", .75 * dim);
      ctx.fillStyle = `rgba(205,255,216,${dim})`;
      ctx.beginPath(); ctx.arc(you.x, you.y, r * .62, 0, 7); ctx.fill();
    }

    // Cubes and their lenses, furthest first
    const items = [];
    for (const n of nodes) {
      const still = calm || (n.cluster.rigid && !n.cluster.loose);
      n.ry += dt * n.spin * (still ? 0 : 1);
      n.rx += dt * n.spin * .4 * (still ? 0 : 1);
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
      const fade = (!shows(n.c) ? 0 : matches(n.c) ? 1 : .07)
        * (pulled ? (end(n) ? 1 : kin(n.cluster) ? .4 : .04)
          : (focus.node && focus.node !== n ? .13 : near ? 1 : .1) * (n.lead || sifted || hover === n ? 1 : mix(.16, 1, zoom)));
      if (end(n) && q) glow(q, n.r * q.k * 4, "255,236,180", .28);
      items.push({ type: "cube", n, d: q.d, q, p: n.p, size: n.r * shrink * (1 + n.hover * .18) * (1 - n.open * .25),
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
      if (it.type === "cube" && it.n.cluster.rigid) glow(it.q, it.size * it.q.k * 2.8, it.n.cluster.circle ? "94,235,130" : it.n.cluster.rgb, .32 * it.alpha);
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
    if (you && !inside) label(USER, { x: you.x, y: you.y + 26 * you.k + 20 }, 15, .95, 700);
    if (!focus.node) clusters.forEach(cl => {
      const q = project(add(cl.c, [0, -cl.half - 8, 0]));
      if (pulled && !kin(cl)) return;
      if (q && cl.nodes.some(n => shows(n.c)) && (!focus.cluster || focus.cluster === cl)) label("#" + cl.topic, q, focus.cluster || pulled ? 16 : 13, focus.cluster || pulled ? .95 : .85 * fog(q.d));
    });
    if (pulled) for (const n of [pulled.a, pulled.b]) {
      const q = project(add(n.p, [0, n.r * 2.4, 0]));
      if (q) label(shorten(n.c.content, 40), q, 13, .95, 600);
    }
    if (!inside) groups.forEach(g => {
      const q = project(add(g.c, [0, -g.half - 12, 0]));
      if (q) label(g.name, q, 16, .95, 700);
    });
    if (focus.cluster && !focus.node) {
      // Nearest names first; one that would land on another waits for hover
      const placed = [];
      focus.cluster.nodes
        .map(n => ({ n, q: project(add(n.p, [0, n.r * 2.1, 0])) }))
        .filter(x => x.q && shows(x.n.c) && matches(x.n.c))
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

