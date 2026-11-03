"""Cubes for wire gauge, wire colours and connectors, cross-referenced.

Current figures for wire vary by assumption, so these cubes say which table is
used. Connector figures come from makers' sheets where they could be read.
Nobody has tested these here, so every face is a proposal.
Run: python keystone-gate/seed_cubes_wiring.py
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not tested on hardware"
UNTESTED = "I have not tested this myself."
SOURCE = {
    "id": "source/wiring",
    "name": "Wiring and connectors",
    "urls": [
        "https://en.wikipedia.org/wiki/American_wire_gauge",
        "https://www.powerstream.com/Wire_Size.htm",
        "https://www.jst.co.uk/downloads/series/eXH-H_(23-05-22).pdf",
        "https://docs.holybro.com/power-module-and-pdb/power-module/connector-and-wire-rating",
        "https://www.andymark.com/products/xt60-2-pin-connectors",
        "https://www.unmannedtechshop.co.uk/fr/blogs/knowledge-base/fpv-drone-battery-connector-guide-xt30-xt60-xt90-ratings",
        "https://www.molex.com/molex/products/family/microfit_connector",
        "https://atta.szlcsc.com/upload/public/pdf/source/20251016/38486B725DEBDAF79EA5BB31EAF6B42B.pdf",
        "https://www.tinytronics.nl/en/cables-and-connectors/cables-and-adapters/grove-compatible/grove-female-compatible-cable-4p-50cm",
        "https://www.flitetest.com/articles/choosing-the-right-servo-extension",
        "https://www.gambica.org.uk/static/uploaded/5d0ab14c-e6e0-4cd8-a1f83e520c2fea16.pdf",
        "https://estates.admin.ox.ac.uk/files/ouesbsegn006lightingwiringcolourspdf",
        "https://www.telewiretech.com/blogs/news/solder-wicking-and-vibration-failures-the-engineers-guide-to-crimping-vs-soldering",
    ],
}

CUBES = [
    ("awg-lower-number-is-thicker", "In AWG, a smaller number is thicker wire, and resistance grows fast as wire thins.", {
        "FACT": "Wikipedia's AWG table and PowerStream agree on copper at about: 18 AWG 21 ohms/km, 22 AWG 53, 24 AWG 84, 26 AWG 134, 28 AWG 213, 30 AWG 339. Each 3 AWG steps roughly doubles resistance.",
        "COUNTER": "Those are for solid copper at 20°C. Cheap wire may be copper-clad aluminium with higher resistance, though I did not source figures for that, and resistance rises as wire warms.",
        "OPINION": "Learn 22 AWG as the everyday power wire and 28 AWG as signal only.",
        "FICTION": "Suppose thin wire is chosen because it looks tidy. It routes beautifully and browns out the first time a servo stalls.",
        "CONTEXT": "UK suppliers often sell by mm2: 22 AWG is about 0.33 mm2 and 18 AWG about 0.82 mm2.",
    }, "Two sources agree on the table. " + UNTESTED),
    ("wire-current-ratings-depend-on-assumptions", "A wire's current rating varies 8 times by which table you read, so check voltage drop too.", {
        "FACT": "PowerStream gives 22 AWG 7A for chassis wiring and 0.92A for power transmission. It calls both rules of thumb, and the second very conservative. Wikipedia's table gives its figures by insulation temperature.",
        "COUNTER": "Chassis figures are for a single wire in air, not a bundle. Neither table covers a warm, enclosed robot. These ratings are about heating, and voltage drop can be the limit first.",
        "OPINION": "Choose by voltage drop for low-voltage work, and use the chassis figure only as a heat limit.",
        "FICTION": "Suppose 22 AWG carries 7A at 6V on a 1m run, which is 2m of copper out and back. The wire survives, and the far end loses about 0.74V.",
        "CONTEXT": "At low voltage a small loss matters, because 0.5V is a large share of a 6V servo supply.",
    }, "From PowerStream and Wikipedia. The 0.74V is my arithmetic. " + UNTESTED),
    ("voltage-drop-counts-both-wires", "Voltage drop counts the wire both ways, so a 1m run is 2m of copper.", {
        "FACT": "Using the AWG table, 1m out and back in 22 AWG is about 0.106 ohms, so 2.5A loses about 0.26V. In 28 AWG the same run is about 0.43 ohms and loses about 1.06V.",
        "COUNTER": "That is my arithmetic from the table, and it leaves out connector resistance, which can be worse than the wire. A stall is short, though it comes at the worst moment.",
        "OPINION": "Keep servo power runs short, and use the thickest wire that fits for the shared feed.",
        "FICTION": "Suppose the wrist servo on an arm is fed through 1m of 28 AWG. At stall it loses a sixth of a 6V supply, right when it needs the most torque.",
        "CONTEXT": "This puts numbers on the existing thin wire cube, using the MG996R's 2.5A stall figure.",
    }, "My arithmetic from the AWG table. " + UNTESTED),
    ("stranded-wire-notation", "Stranded wire is named by total area, so 22 AWG 7/30 is seven 30 AWG strands.", {
        "FACT": "Wikipedia says a stranded wire's AWG reflects the strands' combined area, and that it is about 13% wider than solid wire of the same gauge. It gives 22 AWG 7/30 as seven 30 AWG strands.",
        "COUNTER": "That source covers notation, not flexibility. That more strands bend better is general knowledge, and I did not source any fatigue figures.",
        "OPINION": "Use stranded in anything that moves, and silicone wire with many strands at joints.",
        "FICTION": "Suppose solid wire runs through an arm's elbow. It works for weeks, then breaks inside the insulation where nobody can see it.",
        "CONTEXT": "Solid wire is still useful on a breadboard, where it holds its shape.",
    }, "Notation from Wikipedia, and the advice is general knowledge. " + UNTESTED),
    ("servo-wire-colours", "On servos, red is power, the darkest wire is ground, and the lightest is signal.", {
        "FACT": "Flite Test gives the rule that the lightest colour is signal and the darkest is negative. Forum lists give Futaba as red, black, white, and JR as red, brown, orange. Your SG90 and MG90S listing gives brown, red and orange.",
        "COUNTER": "Sources disagree on the JR signal, orange or yellow. Colours are a convention on cheap parts, not a guarantee, so check the sheet.",
        "OPINION": "Red in the middle is why a reversed servo plug often survives, and I would still check before power-on.",
        "FICTION": "Suppose an unknown servo has three grey wires. No rule helps, and only its documentation or a meter will.",
        "CONTEXT": "This sits with the PCA9685 plug orientation cube, where ground goes to the bottom row.",
    }, "From Flite Test, forum lists and ProtoSupplies. " + UNTESTED),
    ("dc-wire-colours-are-a-habit", "Red for positive and black for negative is a habit in DC work, so measure before connecting.", {
        "FACT": "Hobby leads follow red positive and black or brown negative, as Core Electronics and servo sources show. I found no standard for general low-voltage DC in this search.",
        "COUNTER": "A claim of habit is hard to source. Some cheap modules and imported packs are known to swap colours, though I have no source for that, and wire colour proves nothing.",
        "OPINION": "Put a meter on any battery or supply lead before connecting it for the first time.",
        "FICTION": "Suppose an imported pack has its leads reversed. The first connection could destroy everything on the rail.",
        "CONTEXT": "Sticking to my own colours inside a project matters more than which ones I choose.",
    }, "Convention, with no standard found. " + UNTESTED),
    ("uk-mains-cable-colours", "UK mains is brown live, blue neutral and green-and-yellow earth, and older wiring is red and black.", {
        "FACT": "GAMBICA and Oxford University estates guidance agree: live brown, neutral blue, protective earth green-and-yellow, under BS 7671. New work has had to use these since 31 March 2006. Older fixed wiring used red live and black neutral.",
        "COUNTER": "I found no primary BS 7671 or HSE text. Black means neutral in old UK wiring, but a phase in three-phase, and it is ground in low-voltage DC, so colour alone is unsafe.",
        "OPINION": "Treat this as reference only. I would not work on mains on the strength of a cube.",
        "FICTION": "Suppose old red and black wiring meets a new brown and blue extension. Black looks like DC negative, and it is really neutral.",
        "CONTEXT": "This is the one in this set where a mistake can kill. Mains work is for competent people, and some of it is notifiable in England under Part P.",
    }, "From GAMBICA and Oxford estates guidance, not BS 7671 itself. Reference only. " + UNTESTED),
    ("dupont-jumpers-are-for-signals", "Dupont jumpers are for signals and light loads, not servo power.", {
        "FACT": "One seller lists 26 AWG 2.54mm jumpers at 1A. The wire table gives a 20cm out-and-back run in 26 AWG about 0.05 ohms, so 2.5A would lose over 0.13V before the contacts.",
        "COUNTER": "I found no maker's rating or measurement for Dupont-style connectors, and the housings come from many makers. The 1A is a seller's claim, and contact resistance is unknown.",
        "OPINION": "Use them on the bench, and solder or crimp anything that stays.",
        "FICTION": "Suppose a working prototype is left on jumpers and put in a moving robot. One pin works loose, and the fault comes and goes.",
        "CONTEXT": "They do not lock, unlike XH or XT connectors. That they work loose under vibration is a common view, not a sourced fact.",
    }, "From a seller's claim and my arithmetic, no measurement found. " + UNTESTED),
    ("jst-xh-is-3a-on-22awg", "A JST XH connector is rated 3A, but only on 22 AWG wire.", {
        "FACT": "JST's XH datasheet lists 3A AC/DC at AWG 22 and 250V, from -25 to +85°C. Digi-Key and TechOverflow agree, with wire from 22 to 30 AWG.",
        "COUNTER": "The rating is tied to AWG 22, so thinner wire should be assumed to carry less. Many cheap parts sold as JST are copies, so the rating may not carry over.",
        "OPINION": "This is a good choice for balance leads and small servo runs.",
        "FICTION": "Suppose XH-style connectors on 28 AWG wire feed a 2.5A servo. The connector's rating looks fine, and the wire is the problem.",
        "CONTEXT": "XH is the usual connector on 2S balance leads.",
    }, "From JST's own datasheet. " + UNTESTED),
    ("xt60-is-30a-continuous", "An XT60 is rated 30A continuous, and 60A only for short bursts.", {
        "FACT": "Holybro's documentation gives 30A continuous and 60A for under a minute on 12 AWG wire, and AndyMark and a blog citing AMASS sheets give the same. XT30 is 15A continuous and 30A momentary.",
        "COUNTER": "Some retailers advertise 60A continuous, and I did not read an AMASS sheet directly. The number in the name is the burst figure, not the working one.",
        "OPINION": "An XT30 is plenty for a 2S pack feeding a few servos, and is smaller.",
        "FICTION": "Suppose an XT90 is fitted to feel safe. It adds weight and still leaves a thin wire as the true limit.",
        "CONTEXT": "XT connectors are polarised, which helps a battery lead. Adapters do not raise the limit of the smaller connector.",
    }, "Holybro and AndyMark agree, with retailers disagreeing. " + UNTESTED),
    ("grove-is-for-signals", "Grove HY2.0 connectors are for sensors, at up to about 2A, not for motors.", {
        "FACT": "A Chinese datasheet gives 2.0A for the HY2.0 connector, and a retailer lists 2A. A Grove cable listing gives 1A maximum, so the cable may be the limit.",
        "COUNTER": "These figures are from a part sheet and retailers rather than M5Stack or Seeed. No servo current from an M5Stick is sensible here anyway.",
        "OPINION": "Keep Grove for I2C sensors, and never feed a servo from it.",
        "FICTION": "Suppose an MG996R is run from the Stick's Grove port. A 2.5A stall meets a 1A cable and a 200mAh battery.",
        "CONTEXT": "This links to the M5Stick Grove port cube and the VL53L0X, which draws very little by comparison.",
    }, "From a part sheet and retailers. " + UNTESTED),
    ("crimp-over-solder-for-vibration", "In anything that vibrates, a good crimp is usually safer than solder on stranded wire.", {
        "FACT": "Vendor guides say solder wicks up stranded wire and makes a rigid section where fatigue starts, and that a crimp keeps the strands flexible. They also say not to tin a wire before crimping, because solder creeps and loosens.",
        "COUNTER": "These are vendor blogs selling harnesses, and I found no NASA or IPC text or test data. A bad crimp is worse than good solder, and a good crimp needs the right tool. Support matters either way.",
        "OPINION": "Crimp connectors with a proper tool, and solder with strain relief on boards that do not move.",
        "FICTION": "Suppose a soldered servo lead sits on a walking robot. After months, it breaks just past the joint, and the insulation hides the break.",
        "CONTEXT": "A forum poster adds that the wire must be mechanically supported whichever method is used.",
    }, "Vendor sources only, no standard or test data read. " + UNTESTED),
]

NEIGHBOURS = [
    ("voltage-drop-counts-both-wires", "wire-gauge-voltage-drop", "worked figures for the same claim"),
    ("voltage-drop-counts-both-wires", "mg996r-current", "the 2.5A used in the sum"),
    ("wire-current-ratings-depend-on-assumptions", "wire-gauge-voltage-drop", "voltage drop can be the true limit"),
    ("servo-wire-colours", "pca9685-servo-plug-orientation", "colour tells you which way round"),
    ("xt60-is-30a-continuous", "li-ion-30q-current-rating", "the connector can be the weak link"),
    ("jst-xh-is-3a-on-22awg", "li-ion-2s-needs-a-bms", "XH carries balance leads"),
    ("grove-is-for-signals", "m5stick-plus2-grove-port", "the current limit on that port"),
    ("dc-wire-colours-are-a-habit", "li-ion-2s-is-8v4-full", "check a pack before connecting"),
    ("dupont-jumpers-are-for-signals", "esp32-gpio-input-and-current-limits", "fine for signals, not power"),
    ("crimp-over-solder-for-vibration", "stranded-wire-notation", "both protect moving wire"),
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
        create_cube(s, claim, source="Cross-referenced by Claude, see source/wiring",
                    tags=["wiring", "hardware"], cube_id=cube_id)
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
    print(f"Added {len(seed(s))} wiring cubes, as drafts.")
    s.close()
