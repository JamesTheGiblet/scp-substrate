// Working on cubes in the page. Only active under `kg cube serve`.
(() => {
  const api = /*API*/null;
  if (!api) return;
  const toast = document.getElementById("toast");
  const say = text => {
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(say.timer);
    say.timer = setTimeout(() => { toast.hidden = true; }, 3200);
  };

  async function act(data, flyId, message) {
    let reply;
    try {
      const res = await fetch("/api/do", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Cube-Token": api.token },
        body: JSON.stringify(data),
      });
      reply = await res.json();
      if (!res.ok) return say(reply.error || "That did not work.");
    } catch (e) {
      return say("The server has stopped. Run kg cube serve again.");
    }
    cubeField.update(reply.cubes, reply.modes, flyId || (reply.result && reply.result.cube_id) || data.cube_id);
    if (message) say(message);
    return reply;
  }

  const button = (text, onClick, cls = "tool") => {
    const b = el("button", cls, text);
    b.addEventListener("click", onClick);
    return b;
  };

  function editor(tools, c, lens, current) {
    tools.replaceChildren();
    const box = el("textarea");
    box.value = current || "";
    box.rows = 3;
    box.setAttribute("aria-label", `${lens} text`);
    const save = button("Save", () => {
      if (box.value.trim()) act({ action: "fill", cube_id: c.id, lens, content: box.value }, c.id, `${lens} saved`);
    });
    tools.append(box, save, button("Cancel", () => cubeField.refresh()));
    if (c.validation && !c.validation.stale) tools.append(el("span", "warn", "Changing this voids your validation."));
    box.focus();
  }

  function decorate(panel, c) {
    panel.querySelectorAll(".lens[data-lens]").forEach(row => {
      const lens = row.dataset.lens;
      if (lens === "HUMAN") return;
      const face = c.faces[lens];
      const tools = el("div", "tools");
      if (face && face.pending) {
        tools.append(
          button("Accept", () => act({ action: "accept", proposal_id: face.proposal_id }, c.id)),
          button("Reject", () => act({ action: "reject", proposal_id: face.proposal_id }, c.id)));
      }
      tools.append(button(face ? "Edit" : "Write", () => editor(tools, c, lens, face && face.content)));
      row.after(tools);
    });

    const block = el("div", "tools");
    const filled = LENSES.every(l => c.faces[l] && !c.faces[l].pending);
    const valid = c.validation && !c.validation.stale;
    if (filled && !valid) {
      const note = el("input");
      note.placeholder = "Why does this hold?";
      note.setAttribute("aria-label", "Validation note");
      block.append(note, button("Validate", () => {
        if (note.value.trim()) act({ action: "validate", cube_id: c.id, note: note.value }, c.id, "Validated");
      }));
    }
    const attested = c.attestation && !c.attestation.retracted;
    if (valid && !attested) {
      block.append(button("I stand behind this", () => act({ action: "attest", cube_id: c.id }, c.id, "Attested")));
    }
    if (block.childElementCount) panel.append(block);
  }

  const form = document.getElementById("newcube");
  const fresh = document.getElementById("addcube");
  fresh.hidden = false;
  fresh.addEventListener("click", () => form.showModal());
  document.getElementById("newcancel").addEventListener("click", () => form.close());
  form.querySelector("form").addEventListener("submit", async e => {
    e.preventDefault();
    const field = name => form.querySelector(`[name="${name}"]`);
    const faces = Object.fromEntries(LENSES.map(l => [l, field(l).value]));
    const tags = field("tags").value.split(",");
    form.close();
    const reply = await act({ action: "new", content: field("content").value, tags, faces }, null, "Here it comes");
    if (reply) e.target.reset();
  });

  window.cubeEdit = { decorate };
  cubeField.refresh();
})();
