"""Cubes for 7.4V 3000mAh Li-ion packs, cross-referenced across sources.

These assume two 18650 cells in series (2S). Cell figures come from Samsung's
INR18650-30Q specification as a representative 3000mAh cell, so a specific pack
may differ. Nobody has tested a pack here, so every face is a proposal.
Run: python seeds/claims/before-pivot/seed_cubes_batteries.py
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[3] / "keystone-gate"
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from store.substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not tested on a pack"
UNTESTED = "I have not tested this on my own pack."
SOURCE = {
    "id": "source/li-ion-2s-packs",
    "name": "7.4V Li-ion packs",
    "urls": [
        "https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/samsung_5F00_30q_5F00_data_5F00_sheet.pdf",
        "https://batteryuniversity.com/article/bu-409-charging-lithium-ion",
        "https://batteryuniversity.com/article/bu-702-how-to-store-batteries",
        "https://budgetlightforum.com/t/test-review-of-samsung-inr18650-30q-3000mah-pink/38884",
        "https://www.18650batterystore.com/Sony-18650-p/sony-vtc6.htm",
        "https://docs.cirkitdesigner.com/component/5084f9d4-5f87-426d-a947-9e8b7edf1da6/2s-bms",
    ],
}

CUBES = [
    ("li-ion-2s-is-8v4-full", "A 7.4V Li-ion pack is two cells in series and reads 8.4V when full.", {
        "FACT": "Samsung's 30Q sheet gives 4.20V charge per cell, so two in series is 8.4V. Battery University gives 4.20V per cell, and 2S BMS listings state 7.4V nominal and 8.4V full.",
        "COUNTER": "Samsung's nominal is 3.6V, which makes 7.2V, so 7.4V is a label from 3.7V cells, not a measured working voltage. The pack spends its life anywhere from 8.4V down to its cut-off.",
        "OPINION": "Design for 8.4V, and treat 7.4V as just the name on the label.",
        "FICTION": "Suppose a part rated to 8V is fitted because the pack says 7.4V. It works on a part-charged pack and fails on the first full one.",
        "CONTEXT": "This assumes the common 2S layout. A pack sold as 7.4V 3000mAh could also be LiPo, which has similar voltages but a different build.",
    }, "The arithmetic is confirmed by Samsung and Battery University. " + UNTESTED),
    ("li-ion-2s-too-high-for-servos", "A 2S pack cannot feed servos or a PCA9685 directly: it needs a regulator.", {
        "FACT": "A full pack is 8.4V. The SG90 and MG90S are listed at 4.8 to 6V, the MG996R to 7.2V, and the PCA9685 guide says 5 to 6V on V+.",
        "COUNTER": "Some sellers and hobbyists do run high-voltage servos on 2S directly, but none of the servos here are rated for it. A regulator also adds its own current limit and heat.",
        "OPINION": "Use a step-down converter set to 6V or below, and size it for stall current rather than average.",
        "FICTION": "Suppose a fresh pack is wired straight to V+. Everything may twitch once, and the board and every servo have had 8.4V.",
        "CONTEXT": "This joins the battery to your servo and PCA9685 cubes, and it is the most important practical point in this set.",
    }, "Follows from the ratings on the servo and PCA9685 cubes. " + UNTESTED),
    ("li-ion-2s-is-22wh-not-6000mah", "Two 3000mAh cells in series are still 3000mAh, about 22 watt-hours.", {
        "FACT": "In series the voltage adds and the capacity does not, so 2S stays at 3000mAh. Using Samsung's 3.6V gives 21.6Wh, and using 7.4V gives 22.2Wh.",
        "COUNTER": "The arithmetic is mine, from the voltages in the sources. Real capacity depends on current: Samsung rates 3000mAh at a low 0.2C discharge, and a test measured just over 3100mAh at that rate.",
        "OPINION": "Compare batteries in watt-hours, because mAh alone misleads across voltages.",
        "FICTION": "Suppose someone expects 6000mAh from two cells. A robot built on that sum runs half as long as planned.",
        "CONTEXT": "Stepping down to 6V gives more current than 3000mA, which is how a 2S pack can feed a heavy servo load for a while.",
    }, "My arithmetic from Samsung's figures. " + UNTESTED),
    ("li-ion-2s-runtime-estimate", "Six MG90S servos moving would run about 2 hours on this pack, as an estimate.", {
        "FACT": "22Wh at an assumed 85% converter efficiency gives about 18.7Wh, or 3.1Ah at 6V. Six MG90S moving at 250 mA each take 1.5A, which gives about 2 hours.",
        "COUNTER": "The 85% efficiency is my assumption, 250 mA is the top of the listed range, and servos do not move all the time. The controller's own draw is not counted, and capacity falls at high current.",
        "OPINION": "Treat this as a planning figure, and measure a real session before trusting it.",
        "FICTION": "Suppose the arm lifts a load all the time. Current rises towards stall, and the two hours shrinks to minutes.",
        "CONTEXT": "This is a worked example, so swap in your own servo count and duty.",
    }, "An estimate with stated assumptions, not a measurement. " + UNTESTED),
    ("li-ion-2s-cut-off-voltage", "Stop discharging a 2S pack at no lower than 5V, and earlier is better.", {
        "FACT": "Samsung's sheet gives end of discharge at 2.5V per cell, which is 5V for two. A 2S BMS datasheet gives over-discharge protection at 2.5V ±0.05V per cell. Battery University warns copper shunts can form below about 2V.",
        "COUNTER": "5V at the pack can hide one cell at 2.2V and another at 2.8V if they have drifted apart, which is why per-cell protection matters. Stopping at a higher voltage is general advice, not in Samsung's sheet.",
        "OPINION": "Set a low-battery warning well above 5V, for example 6V, and shut down before the BMS has to.",
        "FICTION": "Suppose a project is left on until the BMS cuts out, and then sits in a drawer for months. A cell can drop below 2V and may not be safe to recharge.",
        "CONTEXT": "Battery University advises discarding a cell left below 2.00V for more than a week.",
    }, "From Samsung, a BMS datasheet and Battery University. " + UNTESTED),
    ("li-ion-2s-charging", "Charge a 2S pack with a CC-CV charger to 8.4V, and never trickle-charge it.", {
        "FACT": "Samsung's sheet gives CC-CV at 1.50A to 4.20V per cell with a 150mA cut-off, and a rapid 4A charge. Battery University describes the same CC-CV method and says Li-ion takes no trickle charge.",
        "COUNTER": "Those are one 30Q cell's figures, and a pack from another maker may have different limits. The 4A rapid rate gives far fewer cycles than careful charging.",
        "OPINION": "Use a proper 2S charger at 1.5A or less, and do not improvise from a bench supply.",
        "FICTION": "Suppose a supply is set to 8.4V and left connected for days. The voltage looks right, and the cells still sit at full charge the whole time.",
        "CONTEXT": "Samsung's standard charge takes about 180 minutes. Battery University also says to avoid charging at freezing temperatures.",
    }, "Samsung and Battery University agree. " + UNTESTED),
    ("li-ion-2s-needs-a-bms", "A 2S pack needs per-cell protection, because the pack voltage can look fine with one bad cell.", {
        "FACT": "Battery University says Li-ion cannot tolerate overcharge, with plating and possible venting above about 4.30V on a 4.20V cell. 2S BMS documents describe per-cell monitoring, with one giving over-charge protection at 4.25V ±0.05V.",
        "COUNTER": "The BMS sources are vendor pages. Not every 2S board balances, as one listing says plainly, and balance currents of 30 to 60 mA are slow. Some packs include no protection at all.",
        "OPINION": "Check what is inside any pack before buying, and do not assume it has a BMS.",
        "FICTION": "Suppose one cell ages faster. The pack still reads 8.4V at full, with one cell at 4.35V and the other at 4.05V, and only a per-cell reading would show it.",
        "CONTEXT": "This is the safety cube of the set, because Li-ion failure can mean venting with flame.",
    }, "Battery University is solid, and the BMS details are from vendor pages. " + UNTESTED),
    ("li-ion-30q-current-rating", "A good 3000mAh 18650 is rated 15A, but the pack's real limit may be far lower.", {
        "FACT": "Samsung's sheet gives 15A continuous at 25°C for the 30Q, and the Sony VTC6 is also listed at 15A. A 2S BMS can be rated from 3A to 20A, depending on the board.",
        "COUNTER": "Forum reports say the 30Q manages about 20A with a temperature limit, but Samsung specifies 15A. Unbranded cells may be nowhere near this, and the pack's weakest part sets the limit.",
        "OPINION": "Find the BMS rating first, because it will usually be the limit.",
        "FICTION": "Suppose six MG996Rs stall together and call for 15A through a 3A BMS. It cuts out, and the whole robot goes limp mid-move.",
        "CONTEXT": "This links to the MG996R current cube, since one stall is 2.5A.",
    }, "Samsung's figure is first-hand, and it covers that cell only. " + UNTESTED),
    ("li-ion-cycle-life-at-high-drain", "At maximum discharge, a 30Q is only guaranteed 60% capacity after 250 cycles.", {
        "FACT": "Samsung's sheet gives capacity of at least 1,800mAh, 60% of nominal, after 250 cycles with standard charge and maximum continuous discharge at 25°C.",
        "COUNTER": "That is a worst-case guarantee at 15A, far harder than a hobby load, so gentler use should last longer. I found no cycle figure for my use, and this is a tentative 2014 spec, version 0.0.",
        "OPINION": "Expect capacity to fall with use, and keep a log of runtime to see when.",
        "FICTION": "Suppose a project runs daily at high current. Within a year it may be doing half the runtime it first did, with no visible fault.",
        "CONTEXT": "This is the source of the 60 percent figure in the Samsung sheet, and it applies to this cell model only.",
    }, "Directly from Samsung's sheet, version 0.0. " + UNTESTED),
    ("li-ion-storage", "Store Li-ion at about 40 percent charge somewhere cool, not full and not empty.", {
        "FACT": "Battery University recommends about 40 percent charge and about 15°C. Its table shows Li-ion kept a year at 25°C held about 96% at 40 percent charge, and about 80% when full.",
        "COUNTER": "That is one source, though a well-regarded one. Samsung's sheet has its own storage section, which I did not compare in detail.",
        "OPINION": "Leave packs at about 3.8V per cell, or 7.6V for two, if they will sit for weeks.",
        "FICTION": "Suppose a fully charged pack is left in a hot car all summer. At 40°C it could lose about 35 percent of its capacity in a year, by the same table.",
        "CONTEXT": "Battery University gives about 3.82V per cell at 40 percent, after 90 minutes' rest. Removable packs also ship at about 30 percent charge.",
    }, "From Battery University, one source. " + UNTESTED),
    ("li-ion-3000mah-labels-need-checking", "A pack's 3000mAh label needs checking, because cells are often faked or re-wrapped.", {
        "FACT": "Forum reports describe the Sony VTC6 as a frequent target for clones and re-wraps. Thunderheart's test found a genuine 30Q slightly above its label at low current, so a real cell has a clear benchmark.",
        "COUNTER": "This is forum reporting. I could not find bench numbers showing how far fakes fall short, so any figure would be a guess.",
        "OPINION": "Buy cells from a known supplier, and run one measured discharge to check.",
        "FICTION": "Suppose a cheap pack says 3000mAh and delivers 1500. The runtime estimate is out by half, and nothing looks wrong.",
        "CONTEXT": "A simple capacity test, discharging at 0.2C (0.6A) to the cut-off, gives a direct comparison with Samsung's rating.",
    }, "From forum reports, and no bench figures for fakes were found. " + UNTESTED),
]

NEIGHBOURS = [
    ("li-ion-2s-too-high-for-servos", "mg996r-voltage-exceeds-pca9685", "8.4V is above both limits"),
    ("li-ion-2s-too-high-for-servos", "pca9685-v-plus-voltage-limit", "the pack needs stepping down for V+"),
    ("li-ion-2s-too-high-for-servos", "servos-and-the-esp32-should-have", "a single pack still needs separate rails"),
    ("li-ion-2s-is-8v4-full", "esp32-logic-is-3v3", "the controller also needs its own regulated rail"),
    ("li-ion-2s-runtime-estimate", "mg90s-stall-current", "runtime depends on servo current"),
    ("li-ion-30q-current-rating", "mg996r-current", "stall current sets the current the pack must give"),
    ("li-ion-30q-current-rating", "pca9685-servo-current-sizing", "the same supply sizing question"),
    ("li-ion-2s-cut-off-voltage", "esp32-brownout-resets", "a sagging pack can reset the controller"),
    ("li-ion-2s-is-22wh-not-6000mah", "m5stick-plus2-battery", "22Wh against about 0.74Wh in the M5Stick"),
]


def seed(s):
    made = []
    if not s.get(SOURCE["id"]):
        s.write({"id": SOURCE["id"], "foundation": "foundation:knowledge", "state": {
            "kind": "source", "name": SOURCE["name"], "urls": SOURCE["urls"]}})
    for slug, claim, faces, note in CUBES:
        cube_id = f"cube/{slug}"
        if s.get(cube_id):
            continue
        create_cube(s, claim, source="Cross-referenced by Claude, see source/li-ion-2s-packs",
                    tags=["battery", "hardware"], cube_id=cube_id)
        s.link(cube_id, "derived-from", SOURCE["id"])
        for lens, text in faces.items():
            propose_face(s, cube_id, lens, text, BY, rationale=WHY)
        s.write({"id": f"{cube_id}/validation-draft", "foundation": "foundation:knowledge", "state": {
            "kind": "validation-draft", "cube_id": cube_id, "content": note, "proposed_by": BY}})
        made.append(cube_id)
    for a, b, why in NEIGHBOURS:
        if s.get(f"cube/{a}") and s.get(f"cube/{b}"):
            propose_neighbour(s, f"cube/{a}", f"cube/{b}", BY, rationale=why)
    return made


if __name__ == "__main__":
    s = Substrate()
    print(f"Added {len(seed(s))} battery cubes, as drafts.")
    s.close()
