"""Suggested OPINION drafts, one per cube.

These are Claude's suggestions, not james's views. They arrive as proposals and
count for nothing until accepted. Reject or rewrite any that are not yours.
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[3] / "keystone-gate"
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from substrate import Substrate
from kg_agent import propose_face


DRAFTED_BY = "claude-draft-opinion"

OPINIONS = {
    # Project claims
    "compress-in-uncertain-channels": "Useful as a default with people I do not know yet. I can always say more once the channel proves safe.",
    "contract-as-data-enforcement-as-code": "Right trade for now. A list of rule names is easy to read, and a new check should be real code.",
    "events-are-audit-not-replay": "Fine while git holds sc.db. If recovery ever depends on the log, this needs another look.",
    "every-write-goes-through-substrate": "What matters is that every change leaves a record, not which function made it.",
    "everything-is-capsules": "It has held up as a way to store things. Links and events show it is a strong habit, not a literal law.",
    "gate-checks-structure-not-reasoning": "This is the right limit. A pass means the references are real, and I still have to read the answer.",
    "keystone-gate-shares-one-database": "Worth it. Checking answers against the real data matters more than clean separation.",
    "llm-handles-language-not-truth": "This is the core rule of the project. Models are useful for wording and should not be the source of facts.",
    "log-everything-fail-loud": "Quiet failures cost the most to find later, so I want them loud even when it is annoying.",
    "own-ed25519-for-local-signing": "Fine for my own documents. Anything facing other people should use an audited library.",
    "phase-0-is-documentation": "Still right, but documents have to be kept current or they mislead. This project showed that.",
    "refused-answers-are-withheld": "A warning gets skimmed past. Withheld is better, as long as I can see why.",
    "repos-store-metadata-not-bytes": "Right choice. git already holds the bytes, and I only need to find things.",
    "schema-changes-are-rare-and-logged": "The stable schema is what let the project grow this far, so it is worth protecting.",
    "split-files-over-400-lines": "A good prompt to look for a natural split, but the number should not force a bad one.",
    "symlm-has-no-weights": "Worth keeping for tracing where an answer came from, but it is not where the fluency will come from.",
    "trust-is-shown-not-claimed": "Keeping them separate is right. The numbers are not calibrated, so I treat them as a rough signal.",
    "two-layer-rule": "It keeps what kinds of thing exist apart from the things themselves, and that has been easy to work with.",
    # Storage, crypto, trust and language
    "binary-database-in-git": "Acceptable for one person. I lose readable diffs, but I get a simple recovery path.",
    "calibration-needs-ground-truth": "Until I log outcomes, trust scores are a ranking aid at best, not probabilities.",
    "canonical-json-must-match-exactly": "A local convention is fine while I am the only verifier. Sharing documents would mean moving to a standard.",
    "copying-a-live-sqlite-file-is-risky": "Easy to get right once and worth doing properly, because a bad backup is found too late.",
    "ed25519-signatures-are-deterministic": "One less thing to get wrong, though it does not fix the timing weakness.",
    "event-sourcing-needs-full-payloads": "Not worth the storage yet. Audit is what I actually use the log for.",
    "idempotent-imports-make-re-runs-safe": "Essential for anything I run by hand, because I will run it twice.",
    "keys-need-a-backup-and-a-rotation-plan": "I should write this plan down before I need it, not after a key is lost.",
    "quoting-sources-reduces-hallucination": "The best cheap check available, as long as a passing quote is not mistaken for a true claim.",
    "sqlite-wal-allows-one-writer": "One writer suits a one-person system. I should treat it as a design rule.",
    "structured-output-limits-free-text": "Needed for anything a program has to check. It controls shape, and the content still needs checking.",
    "treat-retrieved-text-as-data": "Non-negotiable once a model reads stored documents, since some of them I did not write.",
    # Servos, power and wiring
    "bulk-and-decoupling-capacitors": "Cheap insurance on a servo board, but I fix the supply first.",
    "common-ground-between-supplies": "The first thing to check when servos twitch for no clear reason.",
    "emergency-stop-cuts-power": "Needed on any arm big enough to hurt something, but I must test what it does when power goes.",
    "esp32-brownout-resets": "If this shows up, the supply is the real fault. I will not disable the detector.",
    "esp32-i2c-pins-are-configurable": "Handy, but I should stick to the defaults unless there is a reason, and write down any change.",
    "esp32-logic-is-3v3": "I will run the whole I2C bus at 3.3V and avoid the question.",
    "gear-backlash-limits-precision": "I should design for this from the start instead of expecting software to hide it.",
    "i2c-bus-length-limits": "Keep the controller close to the servo board and run power and signal apart.",
    "i2c-needs-pull-up-resistors": "Normally handled by the breakout. Worth checking the total when chaining boards.",
    "inverse-kinematics-maps-position-to-angles": "Worth doing once the joints are calibrated. Before that it gives precise-looking wrong answers.",
    "pla-creeps-under-load": "Fine for prototypes. Parts holding load near a warm servo should be PETG or better.",
    "print-orientation-sets-strength": "Orient for load first and accept extra supports on anything structural.",
    "ramp-motion-instead-of-jumping": "Should be the default for all moves. It helps the mechanics and the supply together.",
    "servo-pulse-width-convention": "Treat the numbers as a starting point and calibrate each servo.",
    "servo-stall-current": "Size the supply from measured stall current, not the typical figures.",
    "set-software-joint-limits": "No move should reach a servo without passing these limits.",
    "torque-falls-with-arm-length": "This should decide the design early, with weight kept near the shoulder.",
    "wire-gauge-voltage-drop": "Measure at the far joint under load, because the supply reading will not show this.",
    # PCA9685
    "pca9685-all-call-address-0x70": "Easy to forget, so worth keeping here for the day a second I2C device acts up.",
    "pca9685-calibrate-before-trusting-angles": "Worth doing for every servo, slowly, before any automated motion.",
    "pca9685-capacitor-sizing": "A fair starting rule. If the supply dips under load, I look at the supply as well.",
    "pca9685-chains-to-992-servos": "A headline number. I only need one or two boards, so the real concern is power.",
    "pca9685-i2c-address-jumpers": "Simple and reliable. Having to solder it is a fair price for an address that cannot drift.",
    "pca9685-led-current-limits": "The guide disagrees with itself, so I take the lower figure and use a resistor.",
    "pca9685-never-power-servos-from-the-controller": "A firm rule. Separate supplies, with grounds joined.",
    "pca9685-oe-pin-disables-outputs": "Useful, but I would not call it a safety stop until I have tested a loaded joint.",
    "pca9685-one-frequency-for-all-channels": "Fine for servos alone. LEDs that need another frequency go on their own board.",
    "pca9685-pwm-ticks": "Fine to know, but I would use a library's angle call and only drop to ticks when needed.",
    "pca9685-python-duty-cycle-is-12-bit": "A detail to remember when fades look stepped. 12 bits is plenty for what I need.",
    "pca9685-servo-current-sizing": "Measure it. A generous supply costs less than chasing brownouts.",
    "pca9685-servo-plug-orientation": "Worth a check every time a plug is reconnected, since it is easy to get wrong in a tight space.",
    "pca9685-servokit-for-python": "A good way to start on a Linux board, though on an ESP32 I would be using a different library.",
    "pca9685-sixteen-channels-over-i2c": "This is why I would use the board: it takes the PWM work off the controller.",
    "pca9685-v-plus-voltage-limit": "I stay at 6V or below. A guide that disagrees with itself gets the cautious reading.",
    "pca9685-vcc-is-logic-power-only": "An easy mistake to make once, so worth keeping as a checklist item.",
    "pca9685-wiring-for-controllers": "The wiring is simple, and the only care needed is matching VCC to the controller's logic.",
}


def main():
    s = Substrate()
    created = skipped = 0
    for slug, text in OPINIONS.items():
        r = propose_face(s, f"cube/{slug}", "OPINION", text, proposed_by=DRAFTED_BY,
                         rationale="suggested view, not yet the human's")
        if r.get("status") == "created":
            created += 1
        else:
            skipped += 1
    print(f"opinion drafts: {created} new, {skipped} unchanged")
    s.close()


if __name__ == "__main__":
    main()
