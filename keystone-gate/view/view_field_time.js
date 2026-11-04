// Part of the cube field. kg_view.py joins these inside one function.
  // --- going back through time ----------------------------------------------
  // Each step is a moment when something changed, so quiet hours take no room.
  const timeRange = document.getElementById("timerange");
  const timeLabel = document.getElementById("timelabel");
  const timePlay = document.getElementById("timeplay");
  let moments = [], playing = null;

  function stampsOf(c) {
    const faces = Object.values(c.faces).filter(Boolean).map(f => f.at);
    return [c.created, ...faces, c.validation && c.validation.at, c.attestation && c.attestation.at].filter(Boolean);
  }

  // A cube as it stood at time t. Only what is dated can be undone: a face
  // edited since shows only from that edit, because older wording is not kept.
  function asOf(c, t) {
    const by = item => (item && item.at && item.at > t ? null : item);
    const faces = Object.fromEntries(LENSES.map(l => [l, by(c.faces[l])]));
    const validation = by(c.validation), attestation = by(c.attestation);
    const filled = LENSES.filter(l => faces[l] && !faces[l].pending).length;
    const valid = validation && !validation.stale;
    const status = attestation ? (attestation.retracted ? "retracted" : "attested")
      : validation && validation.stale ? "stale" : filled === 5 && valid ? "validated" : "draft";
    return { ...c, faces, validation, attestation, status, score: filled * .16 + (valid ? .2 : 0) };
  }

  function setTime(index) {
    const now = index >= moments.length;
    view.time = now ? null : moments[index];
    nodes.forEach(n => {
      const c = CUBES.find(x => x.id === n.c.id) || n.c;
      n.c = now ? c : asOf(c, view.time);
      n.r = 11 + n.c.score * 6;
    });
    if (focus.link && !(shows(focus.link.a.c) && shows(focus.link.b.c))) goHome();
    else if (focus.link) linkPanel(focus.link);
    if (focus.node && !shows(focus.node.c)) back();
    else if (focus.node) fillPanel(focus.node);
    const live = nodes.filter(n => shows(n.c));
    const attested = live.filter(n => n.c.status === "attested").length;
    const when = now ? "Now" : new Date(view.time).toLocaleString("en-GB",
      { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    timeLabel.textContent = `${when} · ${live.length} cubes · ${attested} attested`;
  }

  function loadMoments() {
    const seen = new Set(CUBES.flatMap(stampsOf).map(t => t.slice(0, 16)));
    moments = [...seen].sort().map(t => t + ":59Z");
    const wasNow = !view.time;
    timeRange.max = moments.length;
    if (wasNow) timeRange.value = moments.length;
    setTime(Number(timeRange.value));
  }

  const stopPlay = () => { clearInterval(playing); playing = null; timePlay.textContent = "Play"; };
  timeRange.addEventListener("input", () => { stopPlay(); setTime(Number(timeRange.value)); });
  timePlay.addEventListener("click", () => {
    if (playing) return stopPlay();
    if (Number(timeRange.value) >= moments.length) timeRange.value = 0;
    timePlay.textContent = "Pause";
    playing = setInterval(() => {
      timeRange.value = Number(timeRange.value) + 1;
      setTime(Number(timeRange.value));
      if (Number(timeRange.value) >= moments.length) stopPlay();
    }, 450);
  });
