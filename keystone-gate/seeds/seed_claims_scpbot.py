#!/usr/bin/env python3
"""Claims about SCPBot and its parts, agreed with James on 2026-11-03.

Claims about a part hang on that part's subject, so another build that uses
the part shares them. Claims about how SCPBot is built also link to
entity/scpbot. Part claims come from general knowledge and say so in their
source until a datasheet is cited as evidence. Faces are left blank.
Wiring claims list the wires they describe, so kg wiring can trace which
pins end up joined. Create-only: a claim whose id exists is skipped.
"""
import sys
from pathlib import Path

# keystone-gate, 1 folder up
_here = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from substrate import Substrate
from kg_agent import create_cube
from kg_cube import _update_state
from kg_entities import link_claim
from kg_subjects import accept_subject, propose_subject

BOT = "entity/scpbot"
GENERAL = "Claude's general knowledge, 2026-11-03; not yet checked against a datasheet"
STATED = "Stated by James on 2026-11-03"

# Subjects shared between parts: slug -> name
SHARED = {"i2c": "I2C", "pwm": "PWM", "servo-power": "Servo power", "wiring": "Wiring"}

# (slug, claim, subjects, about SCPBot, source)
CLAIMS = [
    ("pca9685-uses-i2c", "The PCA9685 is controlled over I2C.", ["pca9685", "i2c"], False, GENERAL),
    ("pca9685-has-16-pwm-channels", "The PCA9685 drives 16 PWM channels from one board.",
     ["pca9685", "pwm"], False, GENERAL),
    ("pca9685-does-not-power-servos", "The PCA9685 doesn't power the servos: they run from its V+ terminal, "
     "which needs its own supply.", ["pca9685", "servo-power"], False, GENERAL),
    ("pca9685-boards-can-share-a-bus", "Up to 62 PCA9685 boards can share one I2C bus, each on its own address.",
     ["pca9685", "i2c"], False, GENERAL),
    ("m5stickc-plus2-is-an-esp32", "The M5StickC Plus2 is built on an ESP32 (ESP32-PICO-V3-02), with Wi-Fi "
     "and Bluetooth.", ["m5stickc-plus2"], False, GENERAL),
    ("m5stickc-plus2-has-an-imu", "The M5StickC Plus2 has a built-in IMU, the MPU6886.",
     ["m5stickc-plus2"], False, GENERAL),
    ("m5stickc-plus2-io-is-3v3", "The M5StickC Plus2's I/O pins run at 3.3V.", ["m5stickc-plus2"], False, GENERAL),
    ("vl53l0x-times-reflected-light", "The VL53L0X measures distance by timing reflected infrared light, and "
     "reports over I2C.", ["vl53l0x", "i2c"], False, GENERAL),
    ("vl53l0x-depends-on-the-surface", "VL53L0X readings depend on the target's colour and surface, and its "
     "range is about 2 m at best.", ["vl53l0x"], False, GENERAL),
    ("mg90s-has-metal-gears", "The MG90S has metal gears and more torque than the SG90.", ["mg90s"], False, GENERAL),
    ("mg90s-stall-current", "An MG90S can draw several hundred mA when stalled, so several at once can brown "
     "out a weak supply.", ["mg90s", "servo-power"], False, GENERAL),
    ("li-ion-7v4-pack-is-2s", "A 7.4V Li-ion pack is two cells in series (2S), and reaches 8.4V fully charged.",
     ["7-4v-li-ion-pack"], False, GENERAL),
    ("li-ion-7v4-pack-care", "A 2S Li-ion pack needs a balance charger, and shouldn't be run below about 6V.",
     ["7-4v-li-ion-pack"], False, GENERAL),
    ("ubec-steps-down-for-servos", "A UBEC steps a battery down to a steady servo voltage.",
     ["ubec", "servo-power"], False, GENERAL),
    ("scpbot-ubec-is-5v", "SCPBot's UBEC is set to 5V.", ["ubec", "servo-power"], True, STATED),
    ("scpbot-servos-run-from-the-ubec", "SCPBot powers its servos from the UBEC, separate from the M5Stick, so "
     "servo current can't brown out the controller.", ["ubec", "mg90s", "m5stickc-plus2", "servo-power"],
     True, STATED),
]


M5, PCA, TOF, SERVO, PACK, UBEC = ("m5stickc-plus2", "pca9685", "vl53l0x", "mg90s", "7-4v-li-ion-pack", "ubec")
# (slug, claim, subjects, wires as ((part, pin), (part, pin))), all stated by James on 2026-11-03
WIRING = [
    ("scpbot-m5-to-pca-by-grove", "SCPBot's M5StickC Plus2 connects to the PCA9685 through its Grove port: "
     "G32 to SDA, G33 to SCL, 5V to VCC and GND to GND.", [M5, PCA, "i2c"],
     [((M5, "G32"), (PCA, "SDA")), ((M5, "G33"), (PCA, "SCL")), ((M5, "5V"), (PCA, "VCC")),
      ((M5, "GND"), (PCA, "GND"))]),
    ("scpbot-vl53l0x-on-pca-header", "SCPBot's VL53L0X connects to the PCA9685's I2C header: SDA, SCL, VCC "
     "and GND.", [TOF, PCA, "i2c"],
     [((TOF, "SDA"), (PCA, "SDA")), ((TOF, "SCL"), (PCA, "SCL")), ((TOF, "VIN"), (PCA, "VCC")),
      ((TOF, "GND"), (PCA, "GND"))]),
    ("scpbot-ubec-feeds-pca-v-plus", "SCPBot's UBEC takes one 7.4V pack and feeds 5V to the PCA9685's V+ "
     "terminal, its output ground to the PCA9685's GND.", [UBEC, PACK, PCA, "servo-power"],
     [((PACK, "+"), (UBEC, "IN+")), ((PACK, "-"), (UBEC, "IN-")), ((UBEC, "OUT+"), (PCA, "V+")),
      ((UBEC, "OUT-"), (PCA, "GND"))]),
    ("scpbot-servos-on-pca-headers", "SCPBot's 8 MG90S servos plug into the PCA9685's servo headers, which "
     "carry V+, GND and the PWM signal.", [SERVO, PCA, "pwm", "servo-power"],
     [((SERVO, "V+"), (PCA, "V+")), ((SERVO, "GND"), (PCA, "GND")), ((SERVO, "SIG"), (PCA, "PWM"))]),
]


def main():
    s = Substrate()
    for slug, name in SHARED.items():
        if s.get(f"subject/{slug}") is None:
            pid = propose_subject(s, name, [], "james", kind="topic",
                                  rationale="Shared by SCPBot's parts; agreed with James on 2026-11-03")["proposal_id"]
            print(f"  subject {name}: {accept_subject(s, pid, 'james')}")
    made = 0
    for slug, claim, subjects, about_bot, source in CLAIMS:
        cid = f"cube/{slug}"
        if s.get(cid):
            print(f"  skipped, exists: {cid}")
            continue
        create_cube(s, claim, source=source, tags=["scpbot"], cube_id=cid)
        link_claim(s, cid, subjects=[f"subject/{x}" for x in subjects], entities=[BOT] if about_bot else [])
        made += 1
    for slug, claim, subjects, wires in WIRING:
        cid = f"cube/{slug}"
        if s.get(cid):
            print(f"  skipped, exists: {cid}")
            continue
        create_cube(s, claim, source=STATED, tags=["scpbot"], cube_id=cid)
        _update_state(s, cid, {**s.get(cid)["state"],
                               "wires": [[[f"subject/{a[0]}", a[1]], [f"subject/{b[0]}", b[1]]] for a, b in wires]})
        link_claim(s, cid, subjects=[f"subject/{x}" for x in ["wiring", *subjects]], entities=[BOT])
        made += 1
    print(f"{made} claims made")
    s.close()


if __name__ == "__main__":
    main()
