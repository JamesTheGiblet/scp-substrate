// Part of the cube field. kg_view.py joins these inside one function.
  // --- cluster forms ----------------------------------------------------------
  // Each cluster grows its own form: its cubes joined by their shortest links, with
  // a soft skin around them. The shape comes from where the cubes are, so it changes
  // as they move, and a cluster with no cubes yet has no shape at all.
  const skin = document.createElement("canvas");
  const sk = skin.getContext("2d");

  function reach(points) {
    const left = points.slice(1), edges = [], tree = [points[0]];
    while (left.length) {
      let best = 1e12, from = 0, to = 0;
      tree.forEach((p, i) => left.forEach((q, j) => {
        const d = (p.x - q.x) ** 2 + (p.y - q.y) ** 2;
        if (d < best) { best = d; from = i; to = j; }
      }));
      edges.push([tree[from], left[to]]);
      tree.push(left.splice(to, 1)[0]);
    }
    return edges;
  }

  function trace(points, edges, width) {
    sk.lineWidth = width;
    sk.beginPath();
    for (const [a, b] of edges) { sk.moveTo(a.x, a.y); sk.lineTo(b.x, b.y); }
    for (const p of points) { sk.moveTo(p.x + .01, p.y); sk.lineTo(p.x, p.y); }
    sk.stroke();
  }

  function growForm(cl, rgb, alpha, time) {
    const points = cl.nodes.filter(n => shows(n.c)).map(n => project(n.p)).filter(Boolean);
    if (!points.length) return;
    const k = points.reduce((t, q) => t + q.k, 0) / points.length;
    const breath = calm ? 1 : 1 + Math.sin(time * .5 + cl.topic.length) * .05;
    const width = Math.max(30, Math.min(150, 44 * k * breath)), edges = reach(points);
    sk.lineCap = sk.lineJoin = "round";
    sk.globalCompositeOperation = "source-over";
    sk.strokeStyle = `rgba(${rgb},${alpha})`;
    trace(points, edges, width + 2.4);
    sk.globalCompositeOperation = "destination-out";
    sk.strokeStyle = "#000";
    trace(points, edges, width);
    sk.globalCompositeOperation = "source-over";
    sk.strokeStyle = `rgba(${rgb},${alpha * .13})`;
    trace(points, edges, width);
  }
