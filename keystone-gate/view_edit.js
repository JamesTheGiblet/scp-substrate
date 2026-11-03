// Working on cubes in the grid. Only active under `kg cube serve`, and only once unlocked.
(() => {
  const api = /*API*/null;
  if (!api) return;
  const $ = id => document.getElementById(id);
  const toast = $("toast"), detail = $("detail"), form = $("newcube"), fresh = $("addcube");
  const fill = $("fillblanks"), check = $("checkdrafts"), title = document.title;
  const lockButton = $("lock"), unlock = $("unlock"), wrong = $("unlockwrong");
  let key = null, shown = null, seen = null, lastError = null;
  // Lets a password manager tell this page's password apart
  unlock.querySelector('input[name="username"]').value = api.by;

  const say = text => {
    (detail.open ? detail : document.body).append(toast);
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(say.timer);
    say.timer = setTimeout(() => { toast.hidden = true; }, 3200);
  };
  const reopen = () => {
    const c = CUBES.find(x => x.id === shown);
    if (detail.open && c) open(c);
  };
  const setKey = value => {
    key = value;
    fresh.hidden = fill.hidden = !key;
    lockButton.textContent = key ? "Lock" : "Unlock to edit";
    reopen();
  };

  async function post(path, data) {
    const headers = { "Content-Type": "application/json", "X-Cube-Token": api.token };
    if (key) headers["X-Cube-Key"] = key;
    const res = await fetch(path, { method: "POST", headers, body: JSON.stringify(data) });
    return [res, await res.json()];
  }

  async function act(data, flyId, message) {
    let res, reply;
    try {
      [res, reply] = await post("/api/do", data);
    } catch (e) {
      return say("The server has stopped. Run kg cube serve again.");
    }
    if (res.status === 401) {
      setKey(null);
      return say("Locked. Unlock to edit.");
    }
    if (!res.ok) return say(reply.error || "That did not work.");
    cubeField.update(reply.cubes, reply.modes, flyId || (reply.result && reply.result.cube_id) || data.cube_id);
    cubeField.refresh();
    reopen();
    if (message) say(message);
    return reply;
  }

  const button = (text, onClick, cls = "tool") => {
    const b = el("button", cls, text);
    b.addEventListener("click", onClick);
    return b;
  };

  function writer(tools, c, label, current, warning, save) {
    tools.replaceChildren();
    const box = el("textarea");
    box.name = "text";
    box.value = current || "";
    box.rows = 3;
    box.setAttribute("aria-label", label);
    tools.append(box, button("Save", () => { if (box.value.trim()) save(box.value); }), button("Cancel", () => open(c)));
    if (warning) tools.append(el("span", "warn", warning));
    box.focus();
  }

  function lensTools(row, c) {
    const lens = row.dataset.lens, face = c.faces[lens];
    const tools = el("div", "tools");
    if (face && face.pending) {
      tools.append(
        button("Accept", () => act({ action: "accept", proposal_id: face.proposal_id }, c.id)),
        button("Reject", () => act({ action: "reject", proposal_id: face.proposal_id }, c.id)));
    }
    const warning = c.validation && !c.validation.stale ? "Changing this voids your validation." : "";
    tools.append(button(face ? "Edit" : "Write", () => writer(tools, c, `${lens} text`, face && face.content, warning,
      content => act({ action: "fill", cube_id: c.id, lens, content }, c.id, `${lens} saved`))));
    row.after(tools);
  }

  function humanTools(row, c) {
    const tools = el("div", "tools"), v = c.validation;
    const left = LENSES.filter(l => !c.faces[l] || c.faces[l].pending).length;
    const valid = v && !v.stale, attested = c.attestation && !c.attestation.retracted;
    if (v || !left) {
      const label = !v ? "Validate" : v.stale ? "Validate again" : "Edit";
      const rigid = c.tags.includes("foundational"), suggested = !v && c.note_draft && !rigid;
      tools.append(button(label, () => writer(tools, c, "Why does this hold?", v ? v.note : rigid ? "" : c.note_draft,
        suggested ? "Suggested by a model. Change anything that is not true for you."
          : rigid ? "Foundational: write this in your own words." : "",
        note => act({ action: "validate", cube_id: c.id, note }, c.id, "Validated"))));
    } else {
      tools.append(el("span", "warn", `Accept or write the ${left} unfinished ${left === 1 ? "face" : "faces"} to validate.`));
    }
    if (valid && !left && !attested) {
      tools.append(button("I stand behind this", () => act({ action: "attest", cube_id: c.id }, c.id, "Attested")));
    }
    row.after(tools);
  }

  function decorate(box, c) {
    shown = c.id;
    if (!key) return;
    box.querySelectorAll(".lens[data-lens]").forEach(row =>
      (row.dataset.lens === "HUMAN" ? humanTools : lensTools)(row, c));
    box.querySelectorAll("[data-other]").forEach(row => {
      const tools = el("div", "tools");
      const say = verdict => act({ action: "overlap", a: c.id, b: row.dataset.other, verdict }, c.id,
        verdict === "confirmed" ? "Overlap confirmed" : "Overlap hidden");
      tools.append(button("Confirm", () => say("confirmed")), button("Not related", () => say("dismissed")));
      row.after(tools);
    });
    box.querySelectorAll("[data-link]").forEach(row => linkTools(row, c));
  }

  // Choose the connecting word, and which way the sentence reads, before linking
  function linkTools(row, c) {
    const tools = el("div", "tools"), proposal_id = row.dataset.link;
    const find = id => CUBES.find(x => x.id === id);
    const pair = [find(row.dataset.from), find(row.dataset.from === c.id ? row.dataset.peer : c.id)];
    let reverse = false;
    const pick = el("select");
    pick.name = "word";
    pick.setAttribute("aria-label", "Connecting word");
    pick.append(new Option("Choose a connecting word", ""), ...api.words.map(w => new Option(w, w)));
    const said = el("span", "warn"), link = button("Link them", () =>
      act({ action: "accept", proposal_id, word: pick.value, reverse }, c.id, "Linked"));
    const show = () => {
      const [a, b] = reverse ? [pair[1], pair[0]] : pair;
      said.textContent = pick.value ? linkSentence(a, pick.value, b) : "Pick the word that says how they connect.";
      link.disabled = !pick.value;
    };
    pick.addEventListener("change", show);
    tools.append(pick, button("Swap", () => { reverse = !reverse; show(); }), link,
      button("Not related", () => act({ action: "reject", proposal_id }, c.id, "Link rejected")), said);
    show();
    row.after(tools);
  }

  lockButton.hidden = false;
  lockButton.addEventListener("click", async () => {
    if (!key) {
      wrong.hidden = true;
      return unlock.showModal();
    }
    try { await post("/api/lock", {}); } catch (e) { say("The server has stopped. Run kg cube serve again."); }
    setKey(null);
  });
  $("unlockcancel").addEventListener("click", () => unlock.close());
  unlock.querySelector("form").addEventListener("submit", async e => {
    e.preventDefault();
    const input = unlock.querySelector('input[name="password"]');
    let res, reply;
    try {
      [res, reply] = await post("/api/unlock", { password: input.value });
    } catch (err) {
      unlock.close();
      return say("The server has stopped. Run kg cube serve again.");
    }
    input.value = "";
    if (!res.ok) {
      wrong.hidden = false;
      return;
    }
    unlock.close();
    setKey(reply.key);
  });

  // The server drafts in the background, so ask it what has arrived
  async function poll() {
    let res, reply;
    try {
      [res, reply] = await post("/api/status", { seen });
    } catch (e) {
      return;
    }
    const typing = document.querySelector("#body .tools textarea, dialog[open] form");
    if (!res.ok || (reply.cubes && typing)) return;
    if (reply.cubes) {
      cubeField.update(reply.cubes, reply.modes);
      cubeField.refresh();
      reopen();
    }
    const fresh = seen === null ? 0 : reply.pending - seen;
    if (fresh > 0) say(`${fresh} new ${fresh === 1 ? "draft" : "drafts"} ready to check`);
    seen = reply.pending;
    if (reply.error && reply.error !== lastError) say(`Drafting failed. ${reply.error}`.slice(0, 160));
    lastError = reply.error;
    document.title = seen ? `(${seen}) ${title}` : title;
    check.hidden = !seen && !reply.drafting;
    check.textContent = reply.drafting ? `Drafting, ${seen} to check` : `${seen} to check`;
  }
  check.addEventListener("click", () => { $("togrid").click(); gridFilter("drafts"); });
  fill.addEventListener("click", async () => {
    const reply = await act({ action: "draft" });
    if (reply) say(reply.result.queued ? `Drafting ${reply.result.queued} cubes` : "Every face is filled or has a draft waiting.");
    poll();
  });
  poll();
  setInterval(poll, 8000);

  fresh.addEventListener("click", () => form.showModal());
  $("newcancel").addEventListener("click", () => form.close());
  form.querySelector("form").addEventListener("submit", async e => {
    e.preventDefault();
    const field = name => form.querySelector(`[name="${name}"]`);
    const faces = Object.fromEntries(LENSES.map(l => [l, field(l).value]));
    const tags = field("tags").value.split(",");
    form.close();
    const reply = await act({ action: "new", content: field("content").value, tags, faces }, null, "Here it comes");
    if (reply) {
      e.target.reset();
      $("tofield").click();
    }
  });

  window.cubeEdit = { decorate };
})();
