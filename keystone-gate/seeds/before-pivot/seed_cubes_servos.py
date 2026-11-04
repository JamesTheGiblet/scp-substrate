"""Cubes for the SG90, MG90S and MG996R, cross-referenced across sources.

Servo listings copy each other, so a figure repeated by many sellers is one
source. These cubes separate datasheet copies from a seller's own measurements,
and put disagreements in COUNTER. No original Tower Pro document was found, and
nobody has tested these servos, so every face is a proposal.
Run: python keystone-gate/seeds/before-pivot/seed_cubes_servos.py
"""
import sys
from pathlib import Path

# keystone-gate, 2 folders up
_here = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not tested on a servo"
UNTESTED = "I have not measured this on my own servos."
SOURCE = {
    "id": "source/hobby-servos",
    "name": "Hobby servos",
    "urls": [
        "https://static.rapidonline.com/pdf/37-1330t.pdf",
        "https://w3.braude.ac.il/wp-content/uploads/2021/03/MG90.pdf",
        "https://people.ece.cornell.edu/land/courses/ece4760/FinalProjects/f2017/kmv48_rp625/kmv48_rp625/kmv48_rp625/MG996RTowerPro.pdf",
        "https://protosupplies.com/product/servo-motor-micro-sg90/",
        "https://protosupplies.com/product/servo-motor-micro-mg90s/",
        "https://docs.circuit.rocks/motors/sg90-servo/",
        "https://www.getfpv.com/towerpro-mg90s-digital-servo.html",
        "https://blog.kpower.com/servo/630.html",
        "https://www.baud-dance.com/assets/files/舵机SG90规格书-a814e35ca5db3b0d4da2ff7ae3dc3d01.pdf",
    ],
}

CUBES = [
    ("sg90-torque-figures-disagree", "SG90 stall torque is published anywhere from 1.2 to 1.8 kg-cm.", {
        "FACT": "Rapid's SG90 sheet and Circuit Rocks give 1.8 kg-cm at 4.8V. Other datasheet copies give 1.2 at 4.8V, and a Chinese datasheet gives 1.3. ProtoSupplies measured 1.7 on a generic unit.",
        "COUNTER": "These may describe different products sold under one name, so no single figure is the SG90's. The measured 1.7 comes from one seller and one kind of unit. Stall torque is also a limit, not a working load.",
        "OPINION": "Plan around about 1 kg-cm of useful torque, and treat 1.8 as a ceiling.",
        "FICTION": "Suppose an arm is designed to use exactly 1.8 kg-cm. A batch from another seller arrives at 1.2, and the arm can no longer lift.",
        "CONTEXT": "A forum rule of thumb is to halve the stall figure for real use. That is advice, not a measurement.",
    }, "Sources disagree, so this records the spread, not one true value. " + UNTESTED),
    ("sg90-stall-current", "An SG90 stall current is listed between 360 and 750 mA.", {
        "FACT": "ProtoSupplies measured 360 mA on a generic unit, Circuit Rocks gives about 550 mA, and a Chinese datasheet gives 750 mA ±10%. Idle is about 10 mA, and moving is 100 to 250 mA.",
        "COUNTER": "The figures differ by a factor of two, and the only labelled measurement is one seller's. It is also the low end, so it should not be used for sizing.",
        "OPINION": "Size power for 750 mA per servo, the highest figure, because being wrong that way costs little.",
        "FICTION": "Suppose four SG90s jam at once on a 1A supply sized from the 360 mA figure. On the 750 mA figure they could draw 3A.",
        "CONTEXT": "This gives real numbers to the general servo stall current cube.",
    }, "Sources disagree, and I am using the highest figure for sizing. " + UNTESTED),
    ("mg90s-same-torque-as-sg90-at-4v8", "At 4.8V, the MG90S and SG90 share a 1.8 kg-cm rating, so metal gears are about strength.", {
        "FACT": "The MG90S datasheet copy gives 1.8 kgf-cm at 4.8V, 13.4 g and metal gears with one bearing. GetFPV gives 1.8 at 4.8V and 2.2 at 6V. Rapid's SG90 sheet also gives 1.8 at 4.8V and 9 g.",
        "COUNTER": "SG90 sheets vary down to 1.2, so the two may not be equal in practice. A KPower blog says the MG90S datasheet specifies a nylon composite gear train, which conflicts with the datasheet copy and every listing I read, so I think that is wrong.",
        "OPINION": "Choose the MG90S to survive shock and stalls, not for more torque, and accept the 4.4 g extra.",
        "FICTION": "Suppose an SG90 strips its gears in a crash. An MG90S in the same place would survive, then pass the shock into the bracket.",
        "CONTEXT": "Both are the same size class, so the MG90S is usually a drop-in swap. ProtoSupplies also describes it as an upgrade over the SG90.",
    }, "The MG90S figures are from a datasheet copy and a retailer, and SG90 figures vary. " + UNTESTED),
    ("mg90s-stall-current", "An MG90S stalls at about 650 to 700 mA.", {
        "FACT": "ProtoSupplies measured 700 mA at stall, and a KPower blog gives 650 mA. Idle is 10 mA, and moving is 120 to 250 mA.",
        "COUNTER": "That is only two sources, and KPower's is not a measurement. Neither datasheet copy gives a stall current at all.",
        "OPINION": "Use 700 mA per servo.",
        "FICTION": "Suppose eight MG90S servos all hit their end stops at power-on. That is 5.6A from a supply that may only be rated for 2A.",
        "CONTEXT": "ProtoSupplies warns that driving to 0 or 180 degrees can stall it, and suggests staying near 20 to 160 degrees.",
    }, "From one seller's measurement and one blog. " + UNTESTED),
    ("mg996r-torque", "An MG996R is rated 9.4 kg-cm at 4.8V and 11 kg-cm at 6V.", {
        "FACT": "The MG996R datasheet copy gives 9.4 kgf-cm at 4.8V and 11 kgf-cm at 6V, weighing 55 g, with metal gears and double ball bearings. Several retailers repeat those figures.",
        "COUNTER": "The same sheet's introduction says 10kg, and one seller sells it as 13kg. Resellers warn some units are not original Tower Pro, so real torque can be lower.",
        "OPINION": "This is the one to reach for when a joint outgrows the 9g servos, but plan on about half the rating.",
        "FICTION": "Suppose one replaces every SG90 in an arm. The base can now lift, and it also carries 55 g at each joint.",
        "CONTEXT": "It is about 6 times heavier than an SG90 and gives about 5 times the torque, so it changes the design rather than just the part.",
    }, "From a datasheet copy, repeated by retailers. Original Tower Pro documents were not found. " + UNTESTED),
    ("mg996r-current", "An MG996R runs at 500 to 900 mA and stalls at 2.5A at 6V.", {
        "FACT": "The MG996R datasheet copy gives running current of 500 to 900 mA at 6V and stall current of 2.5A at 6V. Retailer listings repeat these figures.",
        "COUNTER": "I found no independent measurement of this, and the listings look copied from the sheet. Clones could differ either way.",
        "OPINION": "Give each one 2.5A in the power budget, and never run it from a controller's supply.",
        "FICTION": "Suppose sixteen on one PCA9685 stall together. That is 40A through a board and wiring not meant for it.",
        "CONTEXT": "At 2.5A a stall is over three times an MG90S. This is the servo where the separate-supplies and capacitor cubes really matter.",
    }, "From one datasheet copy, no independent measurement found. " + UNTESTED),
    ("mg996r-travel-is-120-degrees", "The MG996R sheet says about 120 degrees of travel, though sellers say 180.", {
        "FACT": "The MG996R datasheet copy says it can rotate approximately 120 degrees, 60 in each direction. Retail listings commonly sell it as 180 degree.",
        "COUNTER": "The range may depend on the pulse width used, and I found no measurement. Some sellers also sell a continuous-rotation version under the same name.",
        "OPINION": "Measure the travel on my own unit before designing a joint around it.",
        "FICTION": "Suppose a joint needs 170 degrees and the design is printed before testing. The servo stops short, and the mount has to be redone.",
        "CONTEXT": "This is exactly what the PCA9685 calibration cube warns about: find each servo's real limits first.",
    }, "The datasheet copy and sellers disagree, and I have not measured it. " + UNTESTED),
    ("mg996r-voltage-exceeds-pca9685", "An MG996R is rated to 7.2V, but the PCA9685 guide says to keep V+ at 5 to 6V.", {
        "FACT": "The MG996R datasheet copy lists 4.8 V to 7.2 V. One reseller says 6.6V. The existing PCA9685 cube says V+ should be 5 to 6V DC.",
        "COUNTER": "The rating covers the servo, not the board. The board's limit is what matters here, and 6V is also where the rated torque is given, so little is lost.",
        "OPINION": "Run it at 6V, as the lower of the two limits.",
        "FICTION": "Suppose a 7.2V pack is connected because the servo allows it. The servo is fine, and the driver board may not be.",
        "CONTEXT": "This links the servo's datasheet to the board guide you have already validated.",
    }, "The limit comes from the PCA9685 guide, not from testing. " + UNTESTED),
    ("servo-pulse-range-needs-checking", "Datasheets say 1 to 2 ms, but listings say 500 to 2400 us, so a servo's real range must be measured.", {
        "FACT": "The MG90S datasheet copy gives 1.5 ms as middle and about 2 ms and 1 ms as the ends. ProtoSupplies and Circuit Rocks give 1 to 2 ms with a 20 ms frame. Some SG90 listings give 500 to 2400 us.",
        "COUNTER": "I could not find a test showing which range real units accept. Listings may be right for some units, and pushing past the mechanical end can stall a servo.",
        "OPINION": "Start at 1 to 2 ms and widen in small steps while watching for the end stops.",
        "FICTION": "Suppose a library sends 500 us to a servo that ends at 1 ms. It grinds against its stop, drawing stall current the whole time.",
        "CONTEXT": "This backs up the pulse width cube and the PCA9685 calibration cube.",
    }, "Sources disagree on the range, and I found no test of it. " + UNTESTED),
    ("cheap-servos-may-not-be-tower-pro", "A cheap SG90, MG90S or MG996R is often not a real Tower Pro part.", {
        "FACT": "ProtoSupplies sells its SG90 and MG90S as generic, made in China, and one reseller states its MG996R units are not original Tower Pro.",
        "COUNTER": "Those are only a few sellers saying so, and I found no count of how common it is. Generic units can also work fine: ProtoSupplies reports no stripping at maximum load.",
        "OPINION": "Trust my own measurements over any listing, and buy a few to compare.",
        "FICTION": "Suppose two bags of SG90s from different sellers go in one robot. They will not be matched, and one joint will behave differently.",
        "CONTEXT": "This is why published figures disagree so much. I did not find Tower Pro's own datasheets, so every figure here comes from a copy or a seller.",
    }, "From a few sellers' statements, not a survey. " + UNTESTED),
]

NEIGHBOURS = [
    ("sg90-stall-current", "servo-stall-current", "real figures for the general claim"),
    ("mg90s-stall-current", "servo-stall-current", "real figures for the general claim"),
    ("mg996r-current", "servo-stall-current", "real figures for the general claim"),
    ("mg996r-current", "pca9685-servo-current-sizing", "2.5A per servo sets the supply size"),
    ("mg996r-current", "servos-and-the-esp32-should-have", "the strongest case for separate supplies"),
    ("mg996r-current", "pca9685-capacitor-sizing", "large current peaks need the capacitor"),
    ("mg996r-travel-is-120-degrees", "pca9685-calibrate-before-trusting-angles", "real travel has to be measured"),
    ("mg996r-voltage-exceeds-pca9685", "pca9685-v-plus-voltage-limit", "the board limit is lower than the servo's"),
    ("servo-pulse-range-needs-checking", "servo-pulse-width-convention", "sources for the 1 to 2 ms convention"),
    ("servo-pulse-range-needs-checking", "pca9685-calibrate-before-trusting-angles", "the range differs per servo"),
    ("mg996r-current", "m5stick-plus2-battery", "one stall is far beyond a 200mAh cell"),
]

M5_UPDATES = {
    "cube/m5stick-plus2-end-of-life": ("CONTEXT", "Its driver library has also moved on: M5StickCPlus2 is deprecated in favour of M5Unified and M5GFX. Espressif also lists the ESP32-PICO-V3-02 chip as Not Recommended for New Designs, which fits the board being retired."),
    "cube/m5stick-plus2-chip-and-memory": ("FACT", "M5Stack's docs and Espressif's datasheet agree: ESP32-PICO-V3-02, 8 MB flash, 2 MB PSRAM. The datasheet also gives 3.0~3.6 V and -40~85 °C for the chip. M5GFX also identifies this board by that chip package."),
}


def seed(s):
    made = []
    if not s.get(SOURCE["id"]):
        s.write({"id": SOURCE["id"], "foundation": "foundation:knowledge", "state": {
            "kind": "source", "name": SOURCE["name"], "urls": SOURCE["urls"]}})
    for slug, claim, faces, note in CUBES:
        cube_id = f"cube/{slug}"
        if s.get(cube_id):
            continue
        create_cube(s, claim, source="Cross-referenced by Claude, see source/hobby-servos",
                    tags=["servo", "hardware"], cube_id=cube_id)
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


def update_m5_drafts(s):
    """New facts from reading Espressif's datasheet. Leaves anything already accepted alone."""
    for cube_id, (lens, text) in M5_UPDATES.items():
        if s.get(cube_id) and not s.get(f"{cube_id}/face/{lens}"):
            print(lens, cube_id, propose_face(s, cube_id, lens, text, BY, rationale=WHY).get("status"))
        elif s.get(cube_id):
            print(f"{cube_id} {lens} is already accepted, left alone")


if __name__ == "__main__":
    s = Substrate()
    print(f"Added {len(seed(s))} servo cubes, as drafts.")
    update_m5_drafts(s)
    s.close()
