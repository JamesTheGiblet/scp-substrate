"""Safety cubes across the hardware set, cross-referenced and linked to it.

Sources are the HSE, UK fire services, councils and Battery University where
they could be found. These are reference notes, not a substitute for official
guidance, a competent person, or the emergency services. Nobody has tested
anything here, so every face is a proposal.
Run: python keystone-gate/seed_cubes_safety.py
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not tested"
SOURCE = {
    "id": "source/hardware-safety",
    "name": "Hardware safety",
    "urls": [
        "https://www.notts-fire.gov.uk/community/safety-in-your-home/e-scooters-and-e-bikes",
        "https://scilly.gov.uk/node/5580",
        "https://www.staffordshirefire.gov.uk/news/posts/firefighters-urge-public-to-remain-safe-around-lithium-ion-batteries-following-house-fire",
        "https://batteryuniversity.com/article/bu-304a-safety-concerns-with-li-ion",
        "https://batteryuniversity.com/article/bu-304b-making-lithium-ion-safe",
        "https://www.naturalresourceswales.gov.uk/about-us/news-and-blogs/news/dispose-of-lithium-ion-batteries-safely-to-prevent-fires/?lang=en",
        "https://www.southampton.ac.uk/estates/Battery_Storage_and_Disposal_Reference_Guide_2025_v1.pdf",
        "https://www.reading.ac.uk/health-safety-services/fire-safety/lithium-battery-information/i-have-a-swollen-lithium-ion-battery-what-should-i-do",
        "https://hse.gov.uk/lung-disease/electronics-soldering.htm",
        "https://www.hse.gov.uk/PUBNS/indg249.pdf",
        "https://www.sparkyfacts.co.uk/_documents/Electricity-At-Work-hsg85.pdf",
        "https://www.theiet.org/media/9450/the-need-for-isolation-for-electrical-work.pdf",
        "https://www.electricalcompetentperson.co.uk/building-regulations-explained/",
        "https://ftc-docs.firstinspires.org/tech_tips/tech-tips/tech-tip-battery-care/tech-tip-battery-care.html",
        "https://www.escapeforum.org/goto/post?id=1270272",
        "https://components101.com/articles/design-guide-pmos-mosfet-for-reverse-voltage-polarity-protection",
        "https://www.evs.ee/en/evs-en-iso-14118-2018",
        "https://www.elecrow.com/download/VL53L0X.pdf",
    ],
}

CUBES = [
    ("do-not-charge-li-ion-unattended", "Do not charge Li-ion unattended or overnight, and use the right charger on a hard surface.", {
        "FACT": "Nottinghamshire Fire and Rescue says not to charge overnight, to use the chargers provided, and not to cover chargers or packs. Leicestershire and Devon and Somerset say the same on unattended charging, and West Sussex says to use a flat, solid surface.",
        "COUNTER": "This guidance is written mainly for e-bikes and e-scooters, whose packs are far larger than a 22Wh 2S pack. The same fire mechanism applies, though the size of a fire would differ. I did not find the national NFCC or OPSS text.",
        "OPINION": "Charge on a non-flammable surface, away from anything that burns and from the way out, while I am awake and nearby.",
        "FICTION": "Suppose a pack charges on a bed overnight. If it fails at 3am, nobody is there, and it is sitting on fuel.",
        "CONTEXT": "This goes with the charging and BMS cubes. A smoke alarm where you charge is the obvious companion, which is general advice.",
    }, "From UK fire services, whose advice agrees. It is written mainly for larger packs."),
    ("li-ion-warning-signs", "If a Li-ion cell gets hot, bulges or hisses, stop using it at once.", {
        "FACT": "The Isles of Scilly service says to unplug at once if a battery gets hot, bulges or hisses. Battery University says to stop if temperature rises over 10°C on a normal charge, and to move an overheating cell onto something non-combustible.",
        "COUNTER": "A protected pack can fail with no warning, and unplugging may not stop a failure that has begun, according to Battery University. Absence of these signs does not prove a pack is safe.",
        "OPINION": "Retire any pack that swells, with no second chances.",
        "FICTION": "Suppose a slightly puffy pack still works well. It is tempting to use it for one more session, and that is exactly the pack that fails.",
        "CONTEXT": "Battery University lists heat build-up and bulging as early signs of a problem.",
    }, "From a UK fire service and Battery University, which agree."),
    ("li-ion-fire-get-out-and-call-999", "In a Li-ion fire, get people out and call 999: the fumes are dangerous and it can re-ignite.", {
        "FACT": "Battery University says runaway can reach about 500°C, smoke or gas may be more toxic than ordinary fires, you should leave if they are present, and cells can keep igniting. It advises ventilating the area.",
        "COUNTER": "Battery University's two pages differ: one says to dowse a Li-ion fire with water, the other says to use water only to stop it spreading. They also suggest letting it burn out outdoors. Carrying a failing pack is my concern, as it can flare. Call 999 was not in the text I read, and is my addition.",
        "OPINION": "Do not fight it or carry it. Get out, shut the door, and call 999.",
        "FICTION": "Suppose a small pack flares and seems to die down. It is put in a bin to deal with later, and a second cell lights it up.",
        "CONTEXT": "Class D extinguishers are for lithium metal, not Li-ion, according to Battery University.",
    }, "Battery University's pages disagree on water, so this puts getting out first, which is my judgement."),
    ("li-ion-disposal", "Never put a Li-ion battery in a household bin, and tape the terminals before recycling it.", {
        "FACT": "Councils and fire services say to use a recycling point, and the Recycle Your Electricals locator finds one. Southampton University says to tape terminals of damaged packs. Reading University warns puncturing a swollen cell may cause fire and explosion.",
        "COUNTER": "Acceptance varies, and some sites refuse damaged batteries, so ring first. Advice on damaged cells comes mostly from institutions rather than national guidance.",
        "OPINION": "Keep a metal tin with sand for dead cells, and take them in when there are a few. That part is my suggestion.",
        "FICTION": "Suppose an old cell goes in the bin. The lorry crushes it, and the load catches fire on the road.",
        "CONTEXT": "This links to the storage cube, because a dead pack is not a safe pack.",
    }, "From UK councils, a regulator and universities, which agree."),
    ("protection-cannot-stop-internal-faults", "A BMS guards against outside abuse, not a fault inside the cell.", {
        "FACT": "Battery University says Li-ion packs need a protection circuit, but that it guards only against outside abuse and not internal defects. It lists PTC, CID and fuse layers, and metallic particles as one internal cause of shorts.",
        "COUNTER": "That is one source, and well regarded. Good cells from known makers have fewer defects, but I have no failure rates, so the risk is unquantified.",
        "OPINION": "A BMS makes a pack safer, and it is not a reason to stop watching one.",
        "FICTION": "Suppose a pack has the best BMS money can buy, and a cell has a tiny defect. Every voltage stays normal until it does not.",
        "CONTEXT": "This is why the charging advice still applies to protected packs.",
    }, "From Battery University, one source."),
    ("fuse-the-battery-positive-near-the-pack", "Fuse the positive lead close to the battery, rated to protect the wire.", {
        "FACT": "FIRST Tech Challenge rules require an in-line fuse on the main battery's positive cable. A forum citing ABYC marine standards puts the fuse within about 7 inches of the terminal. Sources agree the fuse protects the wire.",
        "COUNTER": "Those are robot competition and marine rules, not a standard for hobby packs, and the forum post is second-hand. That the fuse must be below the wire's rating is my general knowledge. A fuse does nothing upstream of itself.",
        "OPINION": "Fit one on every pack that leaves the bench, sized between normal peak current and the wire's limit.",
        "FICTION": "Suppose a chafed wire shorts at the servo end with no fuse. The wire itself becomes the fuse, inside the robot.",
        "CONTEXT": "Forum reports warn lithium packs can deliver huge short-circuit currents, and a fuse needs enough interrupt rating. Those numbers were for larger packs.",
    }, "From competition rules and forum posts, plus general knowledge. No hobby standard was found."),
    ("prevent-reversed-battery", "A reversed battery can destroy a whole rail, so use a polarised connector and input protection.", {
        "FACT": "CircuitDigest and Nexperia describe series diodes and P-channel MOSFETs for this. Specialised diodes drop about 250-300mV, and one vendor gives under 0.12V at 10A for a MOSFET. The XT connector cube covers polarised plugs.",
        "COUNTER": "A MOSFET needs gate protection and more parts, and TI warns P-channel parts degrade when supply falls below about 4V. Those results are about designs in general, not this project.",
        "OPINION": "A polarised connector is the cheapest protection, and a meter check is the first one.",
        "FICTION": "Suppose a home-made lead has its colours swapped. A plain two-pin connector fits either way, and everything on the rail dies at once.",
        "CONTEXT": "This links to the DC colour cube, where colour is shown to be only a habit.",
    }, "From vendor and engineering articles, not tested here."),
    ("solder-fume-is-a-real-hazard", "Rosin solder fume can cause permanent asthma, so extract it rather than breathe it.", {
        "FACT": "HSE describes rosin-based solder fume as one of the most significant causes of occupational asthma in Britain, with fully developed effects being permanent. It expects local exhaust ventilation for most production soldering.",
        "COUNTER": "HSE's guidance is for workplaces, and occasional hobby use is a smaller exposure. HSE says positioning and ventilation may be enough for small-scale, very infrequent soldering with no rosin flux, so rosin itself still needs care. Some documents I saw are older.",
        "OPINION": "Use a fan that pulls fume away and a window open, and do not lean over the joint. Wash my hands too, which is general advice for leaded solder.",
        "FICTION": "Suppose years of evenings spent over an iron bring on a cough. By the time it is diagnosed, the damage cannot be undone.",
        "CONTEXT": "This links to the crimp cube, since HSE's first suggestion is to replace soldering where possible.",
    }, "From HSE guidance for workplaces, applied to hobby use."),
    ("mains-work-is-for-competent-people", "Keep mains work to competent people, and treat mains as dead only when proved dead.", {
        "FACT": "Regulation 14 of the Electricity at Work Regulations makes dead working the normal method, according to HSG85. The IET says isolation must be verified by a competent person. England's Part P makes new circuits and consumer units notifiable.",
        "COUNTER": "The Electricity at Work Regulations apply at work, not at home. I read secondary copies, and sources differ on where Part P applies. Some small work at home is allowed, so check Approved Document P.",
        "OPINION": "Never open mains equipment in these projects. Buy certified power supplies, and work only on the low-voltage side.",
        "FICTION": "Suppose a cheap unboxed supply sits in a project. Its mains terminals are bare, an inch from a hand.",
        "CONTEXT": "This extends the UK mains colours cube. Everything else in this set is low voltage for this reason.",
    }, "From HSE and IET material via secondary copies. Reference only."),
    ("robots-can-move-without-warning", "Treat a powered robot as able to move at any time, including at power-up.", {
        "FACT": "ISO 14118 covers preventing unexpected start-up, including from stored energy such as gravity. A CMU standards summary lists pinch points, crushing, and unexpected start-up among robot hazards.",
        "COUNTER": "These are industrial standards, read through listings and summaries, and I found no hobby guidance. A small SG90 arm is a much smaller hazard, while an MG996R can still pinch a finger, which is my judgement.",
        "OPINION": "Start power with the arm in a safe pose and hands clear, and test new code at low speed.",
        "FICTION": "Suppose a servo with no signal snaps to a position at power-on. The arm sweeps through where a hand was resting.",
        "CONTEXT": "This links to the ramp motion and calibration cubes, which are safety measures as much as quality ones.",
    }, "From industrial standards through summaries, applied to hobby robots by my judgement."),
    ("emergency-stop-and-gravity", "Cutting power stops the motors, but it does not hold up an arm.", {
        "FACT": "A CMU summary defines stop category 0 as immediate removal of power from actuators. A commercial arm's manual says its joints have fail-safe brakes for this reason. Your existing cube says an emergency stop should cut actuator power in hardware.",
        "COUNTER": "Hobby servos have no brakes, so a loaded arm falls when power goes. For a small arm that may matter little, and for a heavy one it does. I found no hobby guidance on this.",
        "OPINION": "Use the stop anyway, and design so that a dropped arm lands somewhere safe.",
        "FICTION": "Suppose the stop is pressed with a load held high. The danger of motion is gone, and a falling load takes its place.",
        "CONTEXT": "This builds on the emergency stop cube and on normally closed switches.",
    }, "From a standards summary and a commercial manual, applied here by my judgement."),
    ("vl53l0x-laser-is-class-1", "The VL53L0X uses an invisible laser that ST rates Class 1, eye safe in normal use.", {
        "FACT": "ST's datasheet describes it as a 940nm VCSEL, totally invisible to the human eye, and lists it as eye safe, Class 1.",
        "COUNTER": "That rating applies in the conditions ST specifies, and I did not read the detail. Invisible means no warning, and a cheap clone may not meet it. Other laser parts can be far more dangerous.",
        "OPINION": "This one is fine, and it does not make lasers in general harmless.",
        "FICTION": "Suppose a stronger laser module is swapped in for more range. It looks the same to the eye, which is to say it looks like nothing.",
        "CONTEXT": "This links to the VL53L0X range cube, the only laser part in this set.",
    }, "From ST's datasheet."),
    ("static-can-kill-parts-silently", "Static can damage parts with no visible sign, so touch ground before handling bare boards.", {
        "FACT": "My search on this found no source, so this is general knowledge: a charge on a person can discharge through a sensitive component, and the damage may not show at first.",
        "COUNTER": "With no source here, treat it as unverified. Hobby parts on boards are fairly tough, and a strap may be excessive at home.",
        "OPINION": "Touch something earthed, and hold boards by the edges.",
        "FICTION": "Suppose an ESP32 works, then starts failing weeks later. The cause was a spark nobody felt.",
        "CONTEXT": "This is the lowest risk in this set, as it threatens parts, not people.",
    }, "General knowledge with no source found."),
    ("first-power-on-checks", "Before first power-on: meter the leads, check for shorts, use a current limit, and keep hands clear.", {
        "FACT": "This gathers the other cubes: measure pack polarity, fit a fuse, check V+ is 6V or less after the regulator, keep 3.3V pins below 3.6V, confirm ground is common, and start the arm in a safe pose.",
        "COUNTER": "This is my synthesis, not a standard, and no list is complete. A current-limited bench supply for first power-on is general practice I did not source.",
        "OPINION": "Follow this every time with new wiring, however small the change.",
        "FICTION": "Suppose a small change goes straight onto the battery because it is only one wire. That one wire is on the wrong rail.",
        "CONTEXT": "This is the practical summary of the hardware cubes, so it is the one to read before building.",
    }, "My summary of the other cubes, not a standard."),
]

NEIGHBOURS = [
    ("do-not-charge-li-ion-unattended", "li-ion-2s-charging", "where and how to charge"),
    ("do-not-charge-li-ion-unattended", "li-ion-warning-signs", "what to watch for"),
    ("li-ion-warning-signs", "li-ion-fire-get-out-and-call-999", "what to do next"),
    ("li-ion-warning-signs", "li-ion-disposal", "a swollen pack must be retired"),
    ("li-ion-disposal", "li-ion-storage", "a dead pack still needs care"),
    ("li-ion-disposal", "li-ion-2s-cut-off-voltage", "cells left below 2V"),
    ("protection-cannot-stop-internal-faults", "li-ion-2s-needs-a-bms", "what a BMS can and cannot do"),
    ("fuse-the-battery-positive-near-the-pack", "wire-current-ratings-depend-on-assumptions", "the fuse protects the wire"),
    ("fuse-the-battery-positive-near-the-pack", "li-ion-30q-current-rating", "fuses sit against pack current"),
    ("prevent-reversed-battery", "dc-wire-colours-are-a-habit", "colour alone will not protect you"),
    ("prevent-reversed-battery", "xt60-is-30a-continuous", "polarised plugs"),
    ("solder-fume-is-a-real-hazard", "crimp-over-solder-for-vibration", "another reason to crimp"),
    ("mains-work-is-for-competent-people", "uk-mains-cable-colours", "colours are not a licence"),
    ("robots-can-move-without-warning", "ramp-motion-instead-of-jumping", "ramping limits sudden moves"),
    ("robots-can-move-without-warning", "pca9685-calibrate-before-trusting-angles", "calibrate before moving"),
    ("emergency-stop-and-gravity", "emergency-stop-cuts-power", "what happens after the stop"),
    ("emergency-stop-and-gravity", "normally-closed-limit-switches", "failing safe"),
    ("vl53l0x-laser-is-class-1", "vl53l0x-range-depends-on-target-and-light", "the same part"),
    ("first-power-on-checks", "li-ion-2s-too-high-for-servos", "check V+ first"),
    ("first-power-on-checks", "esp32-gpio-input-and-current-limits", "check pin voltages"),
    ("first-power-on-checks", "common-ground-between-supplies", "confirm a common ground"),
    ("first-power-on-checks", "fuse-the-battery-positive-near-the-pack", "fit the fuse first"),
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
        create_cube(s, claim, source="Cross-referenced by Claude, see source/hardware-safety",
                    tags=["safety", "hardware", "foundational"], cube_id=cube_id)
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
    print(f"Added {len(seed(s))} safety cubes, as drafts.")
    s.close()
