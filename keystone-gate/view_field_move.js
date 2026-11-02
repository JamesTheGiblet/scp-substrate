// Part of the cube field. kg_view.py joins these inside one function.
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
      panel.append(row(lens, lens, f && f.content, faceNote(f)));
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
    if (window.cubeEdit) {
      const edit = el("button", "hop", "Open in the grid to edit");
      edit.addEventListener("click", () => { document.getElementById("togrid").click(); open(c); });
      panel.append(edit);
    }
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
