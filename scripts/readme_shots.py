"""Take the README's screenshots of the cube page with headless Edge.

  python scripts/readme_shots.py              # every shot, into images/
  python scripts/readme_shots.py grid phone   # only these

Each shot renders the page from sc.db, then sets it up by a link (#entity:,
#mode:, a cube id) or a few lines of script. Edge sometimes hangs on a shot;
that shot is reported and the rest carry on, so run it again for the missing
ones; the old image stays until its new one is taken. Archive the old images
first if you want to keep them.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO / "src"), str(REPO / "keystone-gate")]

from substrate import Substrate
from kg_view import collect, hubs, render, things, user_name

EDGE = os.environ.get("EDGE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
CHIP = 'const chip = (bar, text) => [...document.querySelectorAll(bar + " .chip")].find(b => b.textContent === text);'
CUBE = "cube/pca9685-does-not-power-servos"
WIDE, PHONE = (1280, 820), (390, 844)
# name: (size, link, script run once the page has loaded)
SHOTS = {
    "overview": (WIDE, "", ""),
    "entity-scpbot": (WIDE, "entity:entity/scpbot", ""),
    "cube-open": (WIDE, CUBE, ""),
    "pull-word-match": (WIDE, "", f'cubeField.pull("lens", "{CUBE}") || cubeField.pull("lens");'),
    "repos": (WIDE, "mode:REPOS", ""),
    "time-bar": (WIDE, "", 'const r = document.getElementById("timerange"); r.value = Math.round(r.max * .45);'
                           ' r.dispatchEvent(new Event("input"));'),
    "grid": (WIDE, "", 'document.getElementById("togrid").click();'),
    "grid-entity": (WIDE, "", 'document.getElementById("togrid").click(); state.about = "entity/scpbot"; draw();'),
    "grid-cube": (WIDE, "", f'document.getElementById("togrid").click(); open(CUBES.find(c => c.id === "{CUBE}"));'),
    "phone": (PHONE, "", ""),
    "phone-entity": (PHONE, "entity:entity/scpbot", ""),
}


def shoot(name, page, work, out):
    (w, h), link, script = SHOTS[name]
    html = work / f"{name}.html"
    if script:
        page = page.replace("</body>", f'<script>{CHIP} addEventListener("load", () => '
                                       f'setTimeout(() => {{ {script} }}, 300));</script></body>', 1)
    html.write_text(page, encoding="utf-8")
    # A new shot replaces the old only once it exists, so a hang keeps the old one
    png = work / f"{name}.png"
    try:
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--user-data-dir={work / 'profile'}",
                        f"--window-size={w},{h}", f"--force-device-scale-factor={2 if (w, h) == PHONE else 1}",
                        "--hide-scrollbars", "--virtual-time-budget=6000", f"--screenshot={png}",
                        html.as_uri() + (f"#{link}" if link else "")], timeout=120, capture_output=True)
    except subprocess.TimeoutExpired:
        return "Edge hung, the old one is kept; run it again"
    if not png.exists():
        return "missing, the old one is kept"
    png.replace(out / f"{name}.png")
    return "ok"


def main(names):
    unknown = [n for n in names if n not in SHOTS]
    if unknown:
        raise SystemExit(f"no such shot: {', '.join(unknown)}. Shots: {', '.join(SHOTS)}")
    s = Substrate()
    try:
        page = render(collect(s), user=user_name(s), hubs=hubs(s), things=things(s))
    finally:
        s.close()
    out = REPO / "images"
    # A hung Edge can still hold its profile open, so the folder may not empty
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        for name in names or SHOTS:
            print(name, shoot(name, page, Path(tmp), out))


if __name__ == "__main__":
    main(sys.argv[1:])
