// Part of the cube field. kg_view.py joins these inside one function.
  // Entities you are building sit out from you as smaller green dots, with
  // their parts circling them and each part's claims gathered round it
  // The ring of hubs widens as hubs are added, so their parts never overlap
  const PART_R = 190, HUB_R = Math.max(640, HUBS.length * (PART_R * 2 + 420) / (Math.PI * 2)), GREEN = "94,235,130";
  const hubGroup = (topic, reach) => ({ group: "", topic, rgb: "110,190,255", rigid: true, loose: true, hub: true,
                                        turn: .05, angle: 0, home: [0, 0, 0], nodes: [], c: [0, 0, 0], half: 40, reach });
  const hubs = HUBS.map((h, i) => ({
    ...h, angle: .8 + i * Math.PI * 2 / HUBS.length, spin: 0, turn: -.06, home: [0, 0, 0],
    own: hubGroup(h.name, 50), parts: h.parts.map(p => ({ ...p, cl: hubGroup(p.name, 60) })),
  }));
  const hubGroups = () => hubs.flatMap(h => [h.own, ...h.parts.map(p => p.cl)]);
  const hubOf = c => {
    const h = c.hub && hubs.find(x => x.id === c.hub.entity);
    if (!h) return null;
    const part = h.parts.find(p => p.id === c.hub.part);
    return part ? part.cl : h.own;
  };

  function placeHubs() {
    hubs.forEach(h => {
      h.home = add(world.c, turned([HUB_R, (hubs.indexOf(h) % 2 ? 1 : -1) * 60, 0], h.angle));
      h.own.home = [...h.home];
      h.parts.forEach((p, k) => {
        p.cl.home = add(h.home, turned([PART_R, Math.sin(k * 2.1) * 40, 0], h.spin + k * Math.PI * 2 / h.parts.length));
      });
    });
  }

  function orbitHubs(dt) {
    placeHubs();
    if (calm) return;
    hubs.forEach(h => {
      const held = focus.cluster && hubGroups().includes(focus.cluster);
      if (!held) { h.angle += .012 * dt; h.spin += h.turn * dt; }
      [h.own, ...h.parts.map(p => p.cl)].forEach(cl => { if (focus.cluster !== cl) cl.angle += cl.turn * dt; });
    });
  }

  // Hubs hold their claims in the opening view, by tags and by entity. A
  // single lens or repos is about that mode's clusters, so the hubs step aside.
  const hubsShown = () => mode === "ALL" || mode === "TAGS" || mode === "PLACES";
  // Claims about a hub's parts leave their word clusters for the hub
  function gatherHubs(placed) {
    hubGroups().forEach(cl => { cl.nodes = []; });
    if (!hubsShown()) return;
    const moved = nodes.filter(n => !placed.includes(n) && hubOf(n.c));
    if (!moved.length) return;
    const kept = clusters.filter(cl => (cl.nodes = cl.nodes.filter(n => !moved.includes(n))).length);
    clusters.length = 0;
    clusters.push(...kept);
    moved.forEach(n => { n.cluster = hubOf(n.c); n.cluster.nodes.push(n); });
    hubGroups().forEach(cl => { if (cl.nodes.length) clusters.push(cl); });
    placeHubs();
  }

  // A green strand from you to each hub and from the hub to each part
  const hidden = h => !hubsShown() || (view.entity && view.entity !== h.id);
  function drawHubs(you, dim, time) {
    hubs.forEach(h => {
      if (hidden(h)) return;
      const q = project(h.home);
      if (!q) return;
      const strand = (a, b, alpha) => {
        ctx.strokeStyle = `rgba(${GREEN},${alpha * dim})`;
        ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      };
      if (you) strand(you, q, .35);
      h.parts.forEach(p => {
        const pq = project(p.cl.home);
        if (!pq) return;
        strand(q, pq, .5);
        glow(pq, 14 * pq.k, GREEN, .4 * dim);
        ctx.fillStyle = `rgba(205,255,216,${.85 * dim})`;
        ctx.beginPath(); ctx.arc(pq.x, pq.y, 3.2 * Math.max(pq.k, .6), 0, 7); ctx.fill();
      });
      const r = 15 * q.k * (calm ? 1 : 1 + Math.sin(time * 1.3 + 1) * .07);
      glow(q, r * 5, GREEN, .3 * dim);
      glow(q, r * 2, "150,255,175", .7 * dim);
      ctx.fillStyle = `rgba(205,255,216,${dim})`;
      ctx.beginPath(); ctx.arc(q.x, q.y, r * .62, 0, 7); ctx.fill();
    });
  }

  // The hub's name under its dot, and each part's name by its point
  function nameHubs(dim) {
    hubs.forEach(h => {
      if (hidden(h)) return;
      const q = project(h.home);
      if (q) label(h.name, { x: q.x, y: q.y + 15 * q.k + 18 }, 14, .95 * dim, 700);
      h.parts.forEach(p => {
        const pq = project(p.cl.home);
        if (pq && !p.cl.nodes.length) label(p.name, { x: pq.x, y: pq.y + 16 }, 12, .85 * dim, 600);
      });
    });
  }

  function hubAt(x, y) {
    for (const h of hubs) {
      if (hidden(h)) continue;
      const q = project(h.home);
      if (q && Math.hypot(q.x - x, q.y - y) < Math.max(22 * q.k, 14)) return h;
    }
    return null;
  }

  function goHub(h) {
    focus.cluster = focus.node = focus.lens = focus.link = null;
    focus.hub = h;
    cam.toDist = (PART_R + 150) * 2.6;
    hubPanel(h); setCrumbs();
  }

  // An overview of the entity: who builds it, its parts, its claims and its wiring
  function hubPanel(h) {
    const groups = [h.own, ...h.parts.map(p => p.cl)], all = groups.flatMap(cl => cl.nodes);
    const count = test => all.filter(n => test(n.c)).length;
    panel.replaceChildren();
    const shut = el("button", "shut", "×");
    shut.setAttribute("aria-label", "Back out");
    shut.addEventListener("click", goHome);
    panel.append(shut, el("h3", "", h.name), el("p", "id", h.id));
    const who = h.builders.length ? ` · ${h.builders.join(", ")} is building it` : "";
    panel.append(el("p", "facts", (h.kind ? h.kind[0].toUpperCase() + h.kind.slice(1) : "Entity") + who));
    panel.append(el("p", "facts", `${all.length} claims · ${count(c => c.score > 0)} started · `
      + `${count(c => c.validation && !c.validation.stale)} validated · ${count(c => c.status === "attested")} attested`));
    panel.append(el("p", "facts", "Parts"));
    h.parts.forEach(p => {
      const card = el("button", "lens");
      card.style.setProperty("--c", `rgb(${GREEN})`);
      const head = el("b", "", (p.count > 1 ? `${p.count} × ` : "") + p.name);
      head.append(el("em", "", ` · ${p.cl.nodes.length} claim${p.cl.nodes.length === 1 ? "" : "s"}`));
      card.append(head, document.createTextNode(p.role || "No role given"));
      if (p.cl.nodes.length) card.addEventListener("click", () => goCluster(p.cl));
      else card.disabled = true;
      panel.append(card);
    });
    if (h.own.nodes.length) {
      panel.append(el("p", "facts", `About ${h.name} as a whole`));
      h.own.nodes.forEach(n => {
        const b = el("button", "hop", shorten(n.c.content, 60));
        b.addEventListener("click", () => goNode(n));
        panel.append(b);
      });
    }
    if (h.nets.length) {
      panel.append(el("p", "facts", "Wiring, traced from its wiring claims"));
      h.nets.forEach(net => {
        const card = el("div", "lens");
        card.style.setProperty("--c", net.ground ? `rgb(${GREEN})` : "rgb(150,215,255)");
        card.append(el("b", "", net.ground ? (net.pins.length > 2 ? "Common ground" : "Ground") : "Joined"),
                    document.createTextNode(net.pins.join(" · ")));
        panel.append(card);
      });
    }
    const grid = el("button", "hop", `Open ${h.name} in the grid`);
    grid.addEventListener("click", () => { state.about = h.id; document.getElementById("togrid").click(); draw(); });
    panel.append(grid);
    panel.append(el("p", "facts", "Click a part to go to its claims. Esc or a click on empty space backs out."));
    panel.hidden = false;
  }

  // Clustered by entity: pick an entity to see only its claims, then one of
  // its subjects to go to it
  function inEntity(c, id) {
    return (c.hub && c.hub.entity === id) || (c.entities || []).includes(id);
  }
  function renderPicker() {
    let bar = document.getElementById("picker");
    if (!bar) {
      bar = el("div", "");
      bar.id = "picker";
      document.getElementById("modes").after(bar);
    }
    bar.replaceChildren();
    bar.hidden = mode !== "PLACES" || !(THINGS.entities || []).length;
    if (bar.hidden) return;
    const row = el("div", "row");
    row.append(el("span", "", "Entity"));
    THINGS.entities.forEach(e => {
      const chip = el("button", "chip", e.name);
      chip.setAttribute("aria-pressed", view.entity === e.id);
      chip.addEventListener("click", () => pickEntity(view.entity === e.id ? null : e));
      row.append(chip);
    });
    bar.append(row);
    const e = view.entity && THINGS.entities.find(x => x.id === view.entity);
    if (!e) return;
    const mine = clusters.filter(cl => cl.nodes.some(n => inEntity(n.c, e.id)));
    const name = cl => cl.topic === e.name ? "No subject" : cl.topic.replace(e.name + " · ", "");
    const list = el("div", "row");
    list.append(el("span", "", "Subjects"));
    mine.sort((a, b) => (name(a) === "No subject") - (name(b) === "No subject") || name(a).localeCompare(name(b)))
      .forEach(cl => {
        const chip = el("button", "chip", `${name(cl)} · ${cl.nodes.length}`);
        chip.setAttribute("aria-pressed", focus.cluster === cl);
        chip.addEventListener("click", () => (focus.cluster === cl ? pickEntity(e) : goCluster(cl)));
        list.append(chip);
      });
    bar.append(list);
  }
  function pickEntity(e) {
    view.entity = e ? e.id : null;
    const hub = e && hubs.find(h => h.id === e.id);
    if (hub) goHub(hub); else goHome();
  }
