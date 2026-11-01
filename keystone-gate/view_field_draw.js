// Part of the cube field. kg_view.py joins these inside one function.
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

