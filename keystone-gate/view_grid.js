// The grid view, and the data every view shares.
const CUBES = /*CUBES*/[];
const MODES = /*MODES*/{};
const USER = /*USER*/"You";
const LENSES = ["FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"];
const VAR = { FACT: "fact", COUNTER: "counter", OPINION: "opinion", FICTION: "fiction", CONTEXT: "context", HUMAN: "human" };
const LABEL = { attested: "Attested", validated: "Validated", stale: "Validation stale", retracted: "Attestation retracted", draft: "Needs you" };
const POSE = { FACT: [-18, -24], COUNTER: [-18, -114], CONTEXT: [-18, -204], FICTION: [-18, 66], OPINION: [-72, -24], HUMAN: [72, -24] };
const FILTERS = [["all", "All"], ["attested", "Attested"], ["validated", "Validated"], ["needs", "Needs you"], ["drafts", "Drafts to check"], ["overlaps", "Overlaps"], ["foundational", "Foundational"]];

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
const state = { filter: "all", tag: null, query: "" };
const faceNote = f => !f ? "" : f.pending ? `draft by ${f.drafted_by || "a model"}, not accepted` : f.unread ? "accepted without reading" : "";

function cubeNode(c, size) {
  const stage = el("div", "stage" + (c.status === "attested" ? " sealed" : ""));
  stage.style.setProperty("--s", size + "px");
  const cube = el("div", "cube");
  for (const lens of [...LENSES, "HUMAN"]) {
    const face = lens === "HUMAN" ? c.validation : c.faces[lens];
    const live = lens === "HUMAN" ? c.validation && !c.validation.stale : Boolean(face && !face.pending);
    const side = el("div", `side f-${lens} ` + (live ? `fill-${lens}` : "empty"));
    if (live && lens !== "HUMAN" && face.unread) side.classList.add("unread");
    if (size > 100) side.textContent = lens === "HUMAN" ? "YOU" : lens;
    cube.append(side);
  }
  stage.append(cube);
  return stage;
}

function matches(c) {
  if (state.filter === "needs" && ["attested", "validated"].includes(c.status)) return false;
  if (state.filter === "drafts" && !Object.values(c.faces).some(f => f && f.pending)) return false;
  if (state.filter === "overlaps" && !(c.overlaps || []).length) return false;
  if (state.filter === "foundational" && !c.tags.includes("foundational")) return false;
  if (["attested", "validated"].includes(state.filter) && c.status !== state.filter) return false;
  if (state.tag && !c.tags.includes(state.tag)) return false;
  if (state.query) {
    const hay = [c.id, c.content, ...Object.values(c.faces).map(f => f ? f.content : "")].join(" ").toLowerCase();
    if (!hay.includes(state.query)) return false;
  }
  return true;
}

function card(c) {
  const button = el("button", "card" + (c.tags.includes("foundational") ? " foundational" : ""));
  button.setAttribute("aria-label", `${c.content} ${LABEL[c.status]}`);
  const strip = el("div", "strip");
  for (const lens of [...LENSES, "HUMAN"]) {
    const face = lens === "HUMAN" ? c.validation : c.faces[lens];
    const live = lens === "HUMAN" ? c.validation && !c.validation.stale : Boolean(face && !face.pending);
    const bit = el("i", live ? (face.unread ? "unread" : "") : "off");
    bit.style.setProperty("--c", `var(--${VAR[lens]})`);
    bit.title = lens;
    strip.append(bit);
  }
  button.append(cubeNode(c, 74), strip, el("p", "", c.content));
  const meta = el("div", "meta");
  meta.append(el("span", "pill " + c.status, LABEL[c.status]), el("span", "", Math.round(c.score * 100) + "%"));
  button.append(meta);
  button.addEventListener("click", () => open(c));
  return button;
}

function draw() {
  const root = document.getElementById("groups");
  root.replaceChildren();
  const shown = CUBES.filter(matches);
  if (!shown.length) root.append(el("p", "none", "No cubes match that."));
  const order = g => (g === "Project claims" ? "" : g);
  for (const group of [...new Set(shown.map(c => c.group))].sort((a, b) => order(a).localeCompare(order(b)))) {
    root.append(el("h2", "", group));
    const grid = el("div", "grid");
    shown.filter(c => c.group === group)
      .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
      .forEach(c => grid.append(card(c)));
    root.append(grid);
  }
}

function open(c) {
  const body = document.getElementById("body");
  body.replaceChildren();
  const left = el("div", "left");
  const stage = cubeNode(c, 150);
  const cube = stage.querySelector(".cube");
  left.append(stage, el("div", "hint", "Drag to turn it. Pick a lens to face it."));

  let rx = -26, ry = -38, from = null;
  const pose = () => { cube.style.setProperty("--rx", rx + "deg"); cube.style.setProperty("--ry", ry + "deg"); };
  stage.addEventListener("pointerdown", e => { from = [e.clientX, e.clientY]; stage.setPointerCapture(e.pointerId); cube.style.transition = "none"; });
  stage.addEventListener("pointermove", e => {
    if (!from) return;
    ry += (e.clientX - from[0]) * .6; rx -= (e.clientY - from[1]) * .6;
    from = [e.clientX, e.clientY]; pose();
  });
  stage.addEventListener("pointerup", () => { from = null; cube.style.transition = ""; });

  const right = el("div", "right");
  right.append(el("h3", "", c.content), el("p", "id", c.id));
  const facts = [LABEL[c.status], Math.round(c.score * 100) + "% complete", "standing " + c.standing.toFixed(2)];
  if (c.source) facts.push(c.source);
  if (c.tags.includes("foundational")) facts.unshift("Foundational: read each face and write your own note");
  right.append(el("p", "facts", facts.join(" · ")));

  const row = (lens, title, text, note) => {
    const b = el("button", "lens" + (text ? "" : " missing"));
    b.dataset.lens = lens;
    b.style.setProperty("--c", `var(--${VAR[lens]})`);
    const head = el("b", "", title);
    if (note) head.append(el("em", "", " · " + note));
    b.append(head, document.createTextNode(text || "Not written yet"));
    b.addEventListener("click", () => { [rx, ry] = POSE[lens]; pose(); });
    return b;
  };
  for (const lens of LENSES) {
    const f = c.faces[lens];
    right.append(row(lens, lens, f && f.content, faceNote(f)));
  }
  const v = c.validation;
  right.append(row("HUMAN", "HUMAN VALIDATION", v && (v.note || "Validated"),
    v ? (v.stale ? "stale, a face changed" : "by " + v.validator) : ""));
  if (c.attestation) {
    const a = c.attestation;
    right.append(el("p", "facts", a.retracted ? "Attestation retracted: " + a.retracted : "Attested by " + a.source + (a.note ? ". " + a.note : "")));
  }
  if (c.neighbours.length) right.append(el("p", "facts", "Neighbours: " + c.neighbours.join(", ")));
  (c.link_drafts || []).forEach(d => {
    const other = CUBES.find(x => x.id === d.other);
    const b = el("button", "lens");
    b.dataset.link = d.proposal_id;
    b.style.setProperty("--c", c.tags.includes("foundational") || (other && other.tags.includes("foundational")) ? "#ffb000" : "var(--context)");
    const head = el("b", "", "SUGGESTED LINK");
    head.append(el("em", "", " · not accepted" + (d.why ? ", " + d.why : "")));
    b.append(head, document.createTextNode(other ? other.content : d.other));
    if (other) b.addEventListener("click", () => open(other));
    right.append(b);
  });
  if (c.contradicts) right.append(el("p", "facts", "Contradicts: " + c.contradicts));
  (c.overlaps || []).forEach(o => {
    const other = CUBES.find(x => x.id === o.other);
    const words = o.shared.slice(0, 3).map(s => `${s.lens.toLowerCase()}: ${s.term}`).join(", ");
    const b = el("button", "lens");
    b.dataset.other = o.other;
    b.style.setProperty("--c", "var(--human)");
    const head = el("b", "", `OVERLAP · λ ${o.lambda.toFixed(2)}`);
    head.append(el("em", "", ` · ${o.confirmed ? "confirmed, " : ""}${words}`));
    b.append(head, document.createTextNode(other ? other.content : o.other));
    if (other) b.addEventListener("click", () => open(other));
    right.append(b);
  });
  body.append(left, right);
  if (window.cubeEdit) cubeEdit.decorate(right, c);
  const dialog = document.getElementById("detail");
  if (!dialog.open) dialog.showModal();
}

function setup() {
  renderStats();
  setupControls();
}
function renderStats() {
  const n = s => CUBES.filter(c => c.status === s).length;
  const stats = document.getElementById("stats");
  stats.replaceChildren();
  [[CUBES.length, "cubes"], [n("attested"), "attested"], [n("validated"), "validated, not attested"],
   [CUBES.length - n("attested") - n("validated"), "need you"],
   [CUBES.reduce((t, c) => t + Object.values(c.faces).filter(f => f && f.unread && !f.pending).length, 0), "faces not read"]]
    .forEach(([value, label]) => {
      const s = el("div", "stat");
      s.append(el("b", "", value), el("span", "", label));
      stats.append(s);
    });
}
function setupControls() {
  const legend = document.getElementById("legend");
  [...LENSES, "HUMAN"].forEach(lens => {
    const item = el("span");
    const swatch = el("i");
    swatch.style.background = `var(--${VAR[lens]})`;
    item.append(swatch, document.createTextNode(lens === "HUMAN" ? "Your validation" : lens[0] + lens.slice(1).toLowerCase()));
    legend.append(item);
  });

  const controls = document.getElementById("controls");
  const search = el("input");
  search.id = "search"; search.type = "search"; search.placeholder = "Search cubes"; search.setAttribute("aria-label", "Search cubes");
  search.addEventListener("input", () => { state.query = search.value.trim().toLowerCase(); draw(); });
  controls.append(search);
  const chips = [];
  FILTERS.forEach(([value, label]) => {
    const chip = el("button", "chip", label);
    chips.push([chip, value]);
    chip.addEventListener("click", () => {
      state.filter = value;
      chips.forEach(([b, v]) => b.setAttribute("aria-pressed", v === value));
      draw();
    });
    controls.append(chip);
  });
  chips.forEach(([b, v]) => b.setAttribute("aria-pressed", v === "all"));
  window.gridFilter = value => chips.find(([, v]) => v === value)[0].click();
  const seen = t => CUBES.filter(c => c.tags.includes(t)).length;
  const tags = [...new Set(CUBES.flatMap(c => c.tags))].filter(t => seen(t) >= 3).sort();
  tags.forEach(tag => {
    const chip = el("button", "chip", "#" + tag);
    chip.setAttribute("aria-pressed", "false");
    chip.addEventListener("click", () => {
      state.tag = state.tag === tag ? null : tag;
      controls.querySelectorAll(".chip").forEach(b => { if (b.textContent[0] === "#") b.setAttribute("aria-pressed", b.textContent === "#" + state.tag); });
      draw();
    });
    controls.append(chip);
  });

  const dialog = document.getElementById("detail");
  document.getElementById("close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", e => { if (e.target === dialog) dialog.close(); });
  draw();
}
setup();
