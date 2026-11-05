// Part of the cube field. kg_view.py joins these inside one function.
  // --- moving around -------------------------------------------------------
  const crumbs = document.getElementById("crumbs");
  const panel = document.getElementById("panel");

  function setCrumbs() {
    const parts = [["Everything", goHome]];
    if (focus.hub) parts.push([focus.hub.name, null]);
    if (focus.link) parts.push([`Why #${focus.link.a.cluster.topic} meets #${focus.link.b.cluster.topic}`, null]);
    const owner = ownerOf(focus.cluster);
    if (owner) parts.push([owner.name, () => goHub(owner)]);
    if (focus.cluster) parts.push(["#" + focus.cluster.topic, () => goCluster(focus.cluster)]);
    if (focus.node) parts.push([shorten(focus.node.c.content, 30), null]);
    crumbs.replaceChildren();
    parts.forEach(([text, go], i) => {
      if (i) crumbs.append(el("span", "sep", "›"));
      const b = el("button", "", text);
      b.title = text;
      if (go) b.addEventListener("click", go); else b.disabled = true;
      crumbs.append(b);
    });
    renderPicker();
  }
  function goHome() {
    focus.cluster = focus.node = focus.lens = focus.link = focus.hub = null;
    cam.toDist = world.half * 2.42;
    panel.hidden = true; setCrumbs();
  }
  function goCluster(cl) {
    focus.cluster = cl; focus.node = focus.lens = focus.link = focus.hub = null;
    cam.toDist = cl.spread * 3 + 150;
    panel.hidden = true; setCrumbs();
  }
  function goNode(n) {
    focus.cluster = n.cluster; focus.node = n; focus.lens = focus.link = focus.hub = null;
    cam.toDist = n.r * 11;
    fillPanel(n); setCrumbs();
  }
  function goLink(l) {
    focus.cluster = focus.node = focus.lens = focus.hub = null;
    focus.link = l;
    tip.hidden = true;
    const gap = Math.hypot(...l.a.p.map((v, k) => v - l.b.p[k]));
    cam.toDist = Math.max(420, Math.min(1400, gap * .9 + 380));
    linkPanel(l); setCrumbs();
  }
  const ownerOf = cl => cl && hubs.find(h => h.own === cl || h.parts.some(p => p.cl === cl));
  const back = () => focus.node ? goCluster(focus.node.cluster) : ownerOf(focus.cluster) ? goHub(ownerOf(focus.cluster)) : goHome();

  // Why two cubes are linked, in plain words, with the shared word marked
  function marked(text, word) {
    const p = el("span", "said");
    const at = word ? text.toLowerCase().indexOf(word.toLowerCase()) : -1;
    if (at < 0) { p.textContent = text; return p; }
    p.append(text.slice(0, at), el("mark", "", text.slice(at, at + word.length)), text.slice(at + word.length));
    return p;
  }
  // The connecting word on one of your links, and which cube the sentence starts from
  function saidOf(l) {
    return l.kind === "neighbour" ? (l.a.c.link_words || {})[l.b.c.id] || null : null;
  }
  function reasonOf(l) {
    const { a, b } = l, said = saidOf(l);
    if (l.kind === "lens") return `Both cubes use the word "${l.term}" on their ${l.lens.toLowerCase()} side. This is a match on words, so it can be a coincidence.`;
    if (l.kind === "neighbour") {
      const why = (a.c.link_reasons || {})[b.c.id] || (b.c.link_reasons || {})[a.c.id];
      const [from, to] = said && said.from === b.c.id ? [b, a] : [a, b];
      return (said ? `You linked these: ${linkSentence(from.c, said.word, to.c, 400)}.` : "You linked these, without a connecting word.")
        + (why ? ` The reason given: ${why}.` : "");
    }
    if (l.kind === "proposed") {
      const d = [...(a.c.link_drafts || []), ...(b.c.link_drafts || [])].find(x => x.other === b.c.id || x.other === a.c.id);
      return "A model suggested this link, and you have not accepted it yet." + (d && d.why ? ` Its reason: ${d.why}.` : "");
    }
    if (l.kind === "contra") return "You marked these as contradicting each other.";
    if (l.kind === "bridge") return "They come from the same source and share a tag.";
    return `They sit in the same cluster, #${a.cluster.topic}.`;
  }
  function linkPanel(l) {
    panel.replaceChildren();
    const shut = el("button", "shut", "×");
    shut.setAttribute("aria-label", "Let go");
    shut.addEventListener("click", goHome);
    panel.append(shut, el("h3", "", "Why these are linked"), el("p", "facts", reasonOf(l)));
    for (const n of [l.a, l.b]) {
      const card = el("button", "lens");
      card.style.setProperty("--c", l.lens ? `rgb(${RGB[l.lens].join(",")})` : n.cluster.loose ? `rgb(${n.cluster.rgb})` : "rgb(150,215,255)");
      const head = el("b", "", "#" + n.cluster.topic);
      head.append(el("em", "", " · " + LABEL[n.c.status]));
      card.append(head, document.createTextNode(n.c.content));
      const face = l.lens && n.c.faces[l.lens];
      if (face && face.content) card.append(marked(face.content, l.term));
      card.addEventListener("click", () => goNode(n));
      panel.append(card);
    }
    if (l.kind === "proposed" && window.cubeEdit) {
      const decide = el("button", "hop", "Open in the grid to accept or reject");
      decide.addEventListener("click", () => { document.getElementById("togrid").click(); open(l.a.c); });
      panel.append(decide);
    }
    panel.append(el("p", "facts", "Click a cube to open it. Esc or a click on empty space lets go."));
    panel.hidden = false;
  }

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
    panel.append(el("p", "facts", restsOn(c)));
    if (c.attestation) panel.append(el("p", "facts", c.attestation.retracted
      ? "Attestation retracted: " + c.attestation.retracted
      : "Attested by " + c.attestation.source + (c.attestation.note ? ". " + c.attestation.note : "")));
    const near = links.filter(l => l.a === n || l.b === n);
    if (near.length) {
      panel.append(el("p", "facts", "Linked cubes"));
      near.slice(0, 7).forEach(l => {
        const m = l.a === n ? l.b : l.a;
        const said = saidOf(l);
        const why = l.lens ? `${l.lens}, "${l.term}": ` : said ? (said.from === n.c.id ? `${said.word} → ` : `← ${said.word}: `) : "";
        const b = el("button", "hop", why + shorten(m.c.content, 52));
        b.title = "See why these are linked";
        b.addEventListener("click", () => goLink(l));
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
      if (!q || !shows(n.c)) continue;
      const gap = Math.hypot(q.x - x, q.y - y);
      if (gap < Math.max(n.r * q.k * 1.5, 11) && gap < bestGap) { best = n; bestGap = gap; }
    }
    return best ? { node: best } : null;
  }
  // Strands you can pull: the ones between cubes, not the ones that shape a cluster
  const PULLABLE = ["lens", "neighbour", "proposed", "contra"];
  function strandAt(x, y, reach) {
    let best = null, bestGap = reach;
    for (const l of links) {
      if (!PULLABLE.includes(l.kind) || !shows(l.a.c) || !shows(l.b.c)) continue;
      if (focus.link && l !== focus.link) continue;
      const a = project(l.a.p), b = project(l.b.p);
      if (!a || !b) continue;
      const dx = b.x - a.x, dy = b.y - a.y, len = dx * dx + dy * dy;
      if (len < 400) continue;
      const t = Math.max(.08, Math.min(.92, ((x - a.x) * dx + (y - a.y) * dy) / len));
      const gap = Math.hypot(a.x + dx * t - x, a.y + dy * t - y);
      if (gap < bestGap) { best = l; bestGap = gap; }
    }
    return best;
  }
  function clusterAt(x, y) {
    let best = null, bestGap = 1e9;
    for (const cl of clusters) {
      const q = project(cl.c);
      if (!q || !cl.nodes.some(n => shows(n.c))) continue;
      const gap = Math.hypot(q.x - x, q.y - y);
      if (gap < cl.half * q.k * 1.25 && gap < bestGap) { best = cl; bestGap = gap; }
    }
    return best;
  }

  let drag = null, hover = null, hoverLink = null;
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
    hoverLink = hover || focus.node ? null : strandAt(e.clientX, e.clientY, 7);
    const overHub = !found && hubAt(e.clientX, e.clientY);
    canvas.style.cursor = found || hoverLink || overHub || clusterAt(e.clientX, e.clientY) ? "pointer" : "grab";
    tip.hidden = !hover && !hoverLink && !overHub;
    if (overHub) {
      tip.textContent = `${overHub.name}: click for an overview`;
      tip.style.left = Math.min(e.clientX + 14, W - 280) + "px";
      tip.style.top = e.clientY + 14 + "px";
    }
    if (hover || hoverLink) {
      tip.textContent = hover ? `${hover.c.content} (${LABEL[hover.c.status]})`
        : hoverLink === focus.link ? "Click to let go"
        : (saidOf(hoverLink) ? `"${saidOf(hoverLink).word}" · ` : "") + "Pull to see why these are linked";
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
    const hub = !found && hubAt(e.clientX, e.clientY);
    if (hub) return goHub(hub);
    if (focus.hub && !found) return goHome();
    if (found && found.sat) { focus.lens = found.sat.lens; return; }
    if (found && focus.link) return goNode(found.node);
    if (!found && !focus.node) {
      // A finger is wider than a pointer, so touch gets more room
      const strand = strandAt(e.clientX, e.clientY, e.pointerType === "touch" ? 16 : 7);
      if (strand) return strand === focus.link ? goHome() : goLink(strand);
      if (focus.link) return goHome();
    }
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
    skin.width = W; skin.height = H;
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
    worldOf(id) { return [...byId[id].p]; },
    centre() { return [...world.c]; },
    clusterOf(id) { return project(byId[id].cluster.c); },
    state() { return { cluster: focus.cluster && focus.cluster.topic, node: focus.node && focus.node.c.id, panel: !panel.hidden,
                       link: focus.link && [focus.link.a.c.id, focus.link.b.c.id, focus.link.kind] }; },
    // For checks: pull the first strand of a kind, touching a given cube if named
    pull(kind, id) {
      const l = links.find(x => x.kind === kind && (!id || x.a.c.id === id || x.b.c.id === id));
      if (l) goLink(l);
      return Boolean(l);
    },
    strandScreen(kind) { const l = links.find(x => x.kind === kind); return l && [project(l.a.p), project(l.b.p)]; },
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
  // #entity:<id> opens the page on that entity, its parts round it
  const openHub = hashText.startsWith("entity:") && hubs.find(h => h.id === hashText.slice(7));
  if (openHub) {
    applyMode("PLACES");
    pickEntity(openHub);
    for (let i = 0; i < 300; i++) physics(.03, i * .03);
    cam.t = [...openHub.home];
    cam.dist = cam.toDist;
  }
  const linked = byId[hashText];
  if (linked) {
    goNode(linked);
    cam.t = [...linked.p];
    cam.dist = cam.toDist;
    linked.open = 1;
  }
  loadMoments();
  requestAnimationFrame(frame);
