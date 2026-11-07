// The Build panel: say what a project uses in your own words, see what the
// store knows about it, and answer what it doesn't. Only under kg cube serve.
(() => {
  const $ = id => document.getElementById(id);
  const panel = $("build"), opener = [$("tobuild"), $("tobuild2")];
  if (!window.cubeEdit) return;
  opener.forEach(b => { b.hidden = false; b.addEventListener("click", () => { panel.showModal(); $("bname").focus(); }); });
  $("bclose").addEventListener("click", () => panel.close());
  const parts = $("bparts"), spec = $("bspec"), save = $("bsave");
  // What you chose for each word, and the counts and answers you typed
  let picked = {}, counts = {}, answers = {}, last = null, timer = null;
  const others = () => [...(THINGS.subjects || []), ...(THINGS.entities || [])]
    .filter(t => t.id !== "james").sort((a, b) => a.name.localeCompare(b.name));

  async function check() {
    const name = $("bname").value.trim();
    if (!name) return;
    let res, reply;
    try {
      [res, reply] = await cubeEdit.post("/api/spec", { name, uses: $("buses").value, picked });
    } catch (e) {
      return cubeEdit.say("The server has stopped. Run kg cube serve again.");
    }
    if (!res.ok) return cubeEdit.say(reply.error || "That did not work.");
    last = reply;
    draw();
  }
  const soon = () => { clearTimeout(timer); timer = setTimeout(check, 400); };

  function chip(term, m, on) {
    const b = el("button", "chip", m.name);
    b.type = "button";
    b.setAttribute("aria-pressed", on);
    b.addEventListener("click", () => {
      const now = new Set(picked[term] || last.parts.find(p => p.term === term).picked);
      now.has(m.id) ? now.delete(m.id) : now.add(m.id);
      picked[term] = [...now];
      check();
    });
    return b;
  }

  function alias(term) {
    const box = el("span", "balias");
    const pick = el("select");
    pick.append(new Option(`"${term}" is another name for…`, ""));
    others().forEach(t => pick.append(new Option(t.name, t.id)));
    const go = el("button", "tool", "Add alias");
    go.type = "button";
    go.addEventListener("click", async () => {
      if (!pick.value) return;
      const reply = await cubeEdit.act({ action: "alias", id: pick.value, alias: term });
      if (!reply) return;
      delete picked[term];
      cubeEdit.say(`${term} now finds ${pick.selectedOptions[0].text}`);
      check();
    });
    box.append(pick, go);
    return box;
  }

  function drawParts() {
    parts.replaceChildren();
    last.parts.forEach(p => {
      const row = el("div", "bpart");
      const state = !p.picked.length ? "new" : p.matches.length > 1 ? "pick" : "ok";
      row.dataset.state = state;
      row.append(el("b", "", p.term));
      p.matches.forEach(m => row.append(chip(p.term, m, p.picked.includes(m.id))));
      if (state === "new") row.append(el("span", "bnote", "nothing in the store: saved as a new part"), alias(p.term));
      if (state === "pick") row.append(el("span", "bnote", "matches more than one, so pick"));
      const n = el("input");
      Object.assign(n, { type: "number", min: 1, placeholder: "how many", value: counts[p.term] || "" });
      n.setAttribute("aria-label", `How many ${p.term}`);
      n.addEventListener("input", () => { counts[p.term] = parseInt(n.value, 10) || null; });
      row.append(n);
      parts.append(row);
    });
  }

  function claim(c, extra) {
    const li = el("li");
    const a = el("button", "blink", c.text);
    a.type = "button";
    a.addEventListener("click", () => { const cube = CUBES.find(x => x.id === c.id); if (cube) open(cube); });
    li.append(a, el("span", "bnote", extra));
    return li;
  }

  function section(title, items, row) {
    const box = el("section");
    box.append(el("h4", "", `${title} · ${items.length}`));
    const ul = el("ul");
    items.forEach(i => ul.append(row(i)));
    box.append(ul);
    spec.append(box);
  }

  function draw() {
    drawParts();
    spec.replaceChildren();
    const where = c => (c.from.length ? `from ${c.from.join(", ")}` : "general") + ` · on ${c.on.join(", ")}`;
    section("Known, validated", last.known, c => claim(c, where(c)));
    section("Known, not validated yet", last.unvalidated, c => claim(c, where(c)));
    section("Safety: protects or limits the above", last.safety,
            c => claim(c, `${c.word} ${c.other}${c.validated ? "" : " · not validated yet"}`));
    section("Not known", last.unknown, q => {
      const li = el("li", "bq");
      const box = el("textarea");
      Object.assign(box, { rows: 2, placeholder: "What you know, as one claim. Leave it blank if you don't know yet.",
                           value: answers[q.term] || "" });
      box.addEventListener("input", () => { answers[q.term] = box.value; });
      li.append(el("span", "", q.question), box);
      return li;
    });
    save.disabled = false;
    save.textContent = last.exists ? `Save to ${last.entity}` : `Make ${last.entity} and save`;
  }

  $("bcheck").addEventListener("click", check);
  $("buses").addEventListener("input", soon);
  $("bname").addEventListener("change", check);
  save.addEventListener("click", async () => {
    if (!last) return;
    if (!cubeEdit.unlocked()) return cubeEdit.askUnlock();
    const body = {
      action: "build", name: $("bname").value.trim(),
      parts: last.parts.map(p => ({ term: p.term, ids: p.picked, count: counts[p.term] || null })),
      answers: Object.entries(answers).filter(([, v]) => v.trim()).map(([term, claim]) => ({ term, claim })),
    };
    const reply = await cubeEdit.act(body);
    if (!reply) return;
    const r = reply.result;
    answers = {};
    cubeEdit.say(`Saved: ${r.parts} parts${r.subjects.length ? `, ${r.subjects.length} new` : ""}, ${r.claims.length} claims`);
    check();
  });
})();
