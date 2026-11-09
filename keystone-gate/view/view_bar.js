// The top bar: view switching, filters and cluster modes.
(() => {
  const root = document.getElementById("root"), grid = document.getElementById("grid");
  const swap = showGrid => {
    root.hidden = showGrid; root.style.display = showGrid ? "none" : "";
    grid.hidden = !showGrid;
    if (!showGrid) cubeField.show();
  };
  document.getElementById("togrid").addEventListener("click", () => swap(true));
  document.getElementById("snap").addEventListener("click", async e => {
    const blob = await cubeField.snapshot();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `cube-field-${new Date().toISOString().slice(0, 19).replace(/[T:]/g, "-")}.png`;
    link.click();
    URL.revokeObjectURL(link.href);
    e.target.textContent = "Saved";
    setTimeout(() => { e.target.textContent = "Screenshot"; }, 1400);
  });
  document.getElementById("tofield").addEventListener("click", () => swap(false));
  const chips = [...document.querySelectorAll("[data-f]")];
  chips.forEach(chip => chip.addEventListener("click", () => {
    chips.forEach(c => c.setAttribute("aria-pressed", c === chip));
    cubeField.setFilter(chip.dataset.f);
  }));
  document.getElementById("fsearch").addEventListener("input", e => cubeField.setQuery(e.target.value.trim().toLowerCase()));
  const modeBar = document.getElementById("modes");
  modeBar.append(el("span", "", "Cluster by"));
  const names = { TAGS: "Tags", REPOS: "Repos", OVERLAPS: "Overlaps", PLACES: "Entities" };
  const modes = [...Object.keys(MODES), "TAGS"];
  const modeChips = modes.map(mode => {
    const chip = el("button", "chip", names[mode] || mode[0] + mode.slice(1).toLowerCase());
    chip.setAttribute("aria-pressed", mode === cubeField.mode());
    chip.addEventListener("click", () => {
      modeChips.forEach(c => c.setAttribute("aria-pressed", c === chip));
      cubeField.setMode(mode);
    });
    modeBar.append(chip);
    return chip;
  });
  const key = document.getElementById("key");
  [...LENSES, "HUMAN"].forEach(lens => {
    const swatch = el("i");
    swatch.style.background = `var(--${VAR[lens]})`;
    key.append(swatch, document.createTextNode(lens === "HUMAN" ? "You" : lens[0] + lens.slice(1).toLowerCase()));
  });
  key.append(document.createTextNode("   ·   Green centre: you   ·   Green strand: a cube you validated   ·   Foundations around you: orange safety, pink security, blue preferences   ·   Green ring: what defines you   ·   Green glow: a claim about you   ·   Small green dot: something you are building, its parts circling it; click it for an overview   ·   Gold glow: attested   ·   Hollow: missing   ·   Dim: unread   ·   Thread colour: the lens two cubes share   ·   Dashed: a suggested link, not accepted   ·   Click a thread to see why two cubes are linked   ·   Click to go in, Esc to back out, scroll to zoom"));
})();
