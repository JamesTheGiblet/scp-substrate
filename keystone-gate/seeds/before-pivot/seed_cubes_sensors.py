"""Cubes for common sensors and outputs, cross-referenced across sources.

One real part stands in for each type: VL53L0X for time-of-flight, HC-SR04 for
ultrasonic, Sharp GP2Y0A21 for IR distance, WS2812B for addressable LEDs and the
Omron D2F for microswitches. Figures come from the datasheets where they could
be read. Nobody has tested these here, so every face is a proposal.
Run: python keystone-gate/seeds/before-pivot/seed_cubes_sensors.py
"""
import sys
from pathlib import Path

# keystone-gate, 2 folders up
_here = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not tested on hardware"
UNTESTED = "I have not tested this myself."
SOURCE = {
    "id": "source/sensors-and-outputs",
    "name": "Sensors and outputs",
    "urls": [
        "https://documentation.espressif.com/esp32_datasheet_en.pdf",
        "https://www.elecrow.com/download/VL53L0X.pdf",
        "https://git.wmi.amu.edu.pl/s442333/EmpatycznyRobot_v2/raw/branch/master/datasheets/VL53L0X.pdf",
        "https://cse.unl.edu/~jfalkinburg/cse_courses/2019/236/HC-SR04.pdf",
        "https://cdn.sparkfun.com/assets/a/8/9/c/a/HC-SR04-33_Datasheet.pdf",
        "https://www.rgbautomatyka.pl/it/p/file/1078/GP2Y0A21YK0F__SHARP_44_1_2.pdf",
        "https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf",
        "https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices",
        "https://www.ganssle.com/debouncing.htm",
        "https://eejournal.com/article/ultimate-guide-to-switch-debounce-part-4",
        "https://circuitdigest.com/microcontroller-projects/understanding-difference-between-active-and-passive-buzzer-with-arduino",
        "https://www.makerguides.com/active-and-passive-piezo-buzzers-with-arduino/",
    ],
}

CUBES = [
    ("esp32-gpio-input-and-current-limits", "ESP32 pins allow 3.6V at most, and give about 40mA at full drive.", {
        "FACT": "Espressif's datasheet lists allowed input voltage of -0.3 to 3.6 V, high-level source current of 40 mA at maximum drive on most pins, sink of 28 mA, and 1200 mA cumulative output.",
        "COUNTER": "Forum posts still quote 12 mA from older documents, and that is the safer working figure. The 40 mA is a typical value at maximum drive strength, with the output sagging to 2.64 V, not a target to run at.",
        "OPINION": "Treat 12 mA as my working limit and 40 mA as what the chip can survive doing, and use a transistor above that.",
        "FICTION": "Suppose a project drives ten LEDs at 20 mA from ten pins. It is within the 1200 mA total, and each pin is already past the safer limit.",
        "CONTEXT": "This gives Espressif's figures for the existing 3.3V logic cube, and every sensor in this set depends on it.",
    }, "Read directly from Espressif's datasheet, version 5.3. The 12 mA working limit is my caution. " + UNTESTED),
    ("vl53l0x-range-depends-on-target-and-light", "The VL53L0X reaches 2m only on white targets in the dark.", {
        "FACT": "ST's datasheet gives typical range of 200cm+ on a white target indoors, 80cm on grey, and 80cm on white in overcast daylight, 50cm on grey. Its long range mode is for dark conditions only. The field of view is 25 degrees.",
        "COUNTER": "Those are lab conditions with the target filling the field of view, and the 2m needs long range mode. A dark object in sunlight can be well under 50cm. Rev 1 of the datasheet was read, and later revisions exist.",
        "OPINION": "Plan on about 50cm for a robot, and treat anything further as a bonus.",
        "FICTION": "Suppose a robot works in the workshop and then goes outside. The same sensor loses over half its reach, with no error to explain it.",
        "CONTEXT": "Its modes trade speed for accuracy: 20ms at +/-5% to 1.2m, or 200ms at under +/-3%.",
    }, "From ST's datasheet, rev 1. " + UNTESTED),
    ("vl53l0x-voltage-and-address", "The VL53L0X chip runs at 2.6 to 3.5V on I2C, so it suits a 3.3V ESP32 directly.", {
        "FACT": "ST's datasheet lists 2.6 to 3.5 V and I2C up to 400 kHz with address 0x52. Libraries usually show the 7-bit form 0x29. A Melopero carrier board is rated 2.6 to 5.5 V because it adds a regulator.",
        "COUNTER": "Check which you have: a bare module is not a 5V part, while a carrier board may be. The address can be changed, but it resets on power cycle, so two sensors on one bus need XSHUT to start them one at a time.",
        "OPINION": "This is the easiest of the three distance sensors to connect to an ESP32.",
        "FICTION": "Suppose two sensors share a bus without XSHUT. Both answer at the same address, and readings make no sense.",
        "CONTEXT": "0x52 and 0x29 are the same address written two ways, which is a common source of confusion.",
    }, "From ST's datasheet and a carrier board listing. " + UNTESTED),
    ("hc-sr04-echo-is-5v", "A 5V HC-SR04 needs its Echo line divided down for an ESP32.", {
        "FACT": "The HC-SR04 sheet lists 5V supply, and Trigger and Echo as TTL signals. Espressif allows 3.6V at most on an input. A guide suggests 1k and 2k as a divider, which gives about 3.3V.",
        "COUNTER": "The sheet does not state Echo's voltage outright, so that it is 5V is from guides. Two 10k resistors give 2.5V, just above the 0.75 x VDD (2.48V) high threshold, so that divider is marginal.",
        "OPINION": "Use a 3.3V version if I am buying new, and otherwise the 1k and 2k divider.",
        "FICTION": "Suppose Echo goes straight to a pin and it works for weeks. The chip has been run beyond its limit the whole time, and it may fail later for no visible reason.",
        "CONTEXT": "An HC-SR04-33 sheet lists 3.3V to 5V working voltage. One guide says range falls by about a metre at 3.3V, and I could not confirm that.",
    }, "From the HC-SR04 sheets, Espressif and guides. " + UNTESTED),
    ("hc-sr04-range-and-limits", "An HC-SR04 reads 2cm to 4m within a 15 degree cone, on hard flat targets.", {
        "FACT": "The ElecFreaks sheet gives 2cm to 400cm, a 15 degree measuring angle, 15mA, and a 10us trigger pulse. It also says 40Hz, which is a typo for the 40kHz ultrasonic burst that other sources give.",
        "COUNTER": "Accuracy is listed as 3mm, which is a best case. Foam, fabric and angled surfaces absorb or deflect the sound. The speed of sound also changes with temperature, so readings drift.",
        "OPINION": "Good and cheap for detecting a wall, and poor for measuring precisely.",
        "FICTION": "Suppose a robot meets a sofa. The sound soaks in, no echo returns, and it reports open space and drives on.",
        "CONTEXT": "Ultrasonic does not care about colour or light, so it covers the gaps of optical sensors.",
    }, "From the ElecFreaks sheet, with the surface limits from guides. " + UNTESTED),
    ("sharp-gp2y0a21-ir-distance", "The Sharp GP2Y0A21 measures 10 to 80cm as a 5V analog voltage.", {
        "FACT": "Sharp's datasheet gives 10 to 80 cm, analog output, 4.5 to 5.5 V supply and typical 30 mA. A tutorial reports about 2.3V at 10cm and 0.4V at 80cm.",
        "COUNTER": "The output is not linear. The voltage figures come from a tutorial, and I did not read the output table. Check the range on an ESP32 ADC, and note this was not the 3.3V part. Its 30 mA is an average, and I could not confirm the advice to add a capacitor.",
        "OPINION": "This suits a fixed job in a narrow range, but the VL53L0X is easier for new work.",
        "FICTION": "Suppose something comes closer than 10cm. The curve folds back, and a near object can read as far away.",
        "CONTEXT": "It needs 5V power while the ESP32 reads its output, so it needs both rails.",
    }, "Range and supply are from Sharp's datasheet, and the output voltages from a tutorial. " + UNTESTED),
    ("no-one-distance-sensor-sees-everything", "Each distance sensor type has a blind spot, so a robot benefits from two kinds.", {
        "FACT": "Optical range falls with dark targets and sunlight in ST's table. Ultrasonic sound is absorbed by soft materials and deflected by angled ones, according to guides.",
        "COUNTER": "That is my synthesis, and no single source says this. Two sensors add cost, wiring and code, and many simple robots manage with one.",
        "OPINION": "Pair ultrasonic and time-of-flight if the robot has to avoid things reliably.",
        "FICTION": "Suppose a dark sofa in a sunny room. The optical sensor struggles with the colour, the ultrasonic with the fabric, and one of them still might see it.",
        "CONTEXT": "This links the three distance sensor cubes together.",
    }, "My synthesis of the other cubes, not a sourced claim. " + UNTESTED),
    ("active-vs-passive-buzzer", "An active buzzer sounds on DC, and a passive one needs a tone from the controller.", {
        "FACT": "CircuitDigest and MakerGuides agree: an active buzzer has an internal oscillator and a fixed pitch, while a passive one needs a square wave that sets the pitch. On 5V DC an active buzzer beeps, and a passive one only clicks.",
        "COUNTER": "Sources disagree on current, and one gives 25-30 mA active and 2-10 mA passive. Magnetic buzzers can draw much more, so check the part. Guides are not datasheets.",
        "OPINION": "Use passive when I want different tones, as with the M5Stick, and active for a simple alarm.",
        "FICTION": "Suppose an active buzzer is sent a melody. Instead of a tune, it just chops one fixed tone on and off.",
        "CONTEXT": "The M5StickC Plus2's buzzer is passive, on G2, according to M5Stack's docs.",
    }, "From guides that agree, not a datasheet. " + UNTESTED),
    ("led-resistor-at-3v3", "On 3.3V, a red LED needs about 68 ohms, and a blue one has almost no headroom.", {
        "FACT": "The formula is R = (Vs - Vf) / I. At 3.3V and 20 mA, a 2V red LED needs 65 ohms, so 68. A 3V blue LED needs 15 ohms, and the WS2812B sheet lists blue at 3.0-3.4V, so it may barely light.",
        "COUNTER": "20 mA is above the 12 mA I treat as safe for a pin, so a real design should use less, about 110 ohms for red at 12 mA. Forward voltage also varies with the LED and with current.",
        "OPINION": "Use 220 ohms for an indicator, which is bright enough and easy on the pin.",
        "FICTION": "Suppose a blue LED is fitted with no resistor, because 3.3V looks about right. Nothing limits the current except the pin.",
        "CONTEXT": "The PCA9685 has its own LED current limits, in its cube.",
    }, "Ohm's law, with forward voltages from a general guide. " + UNTESTED),
    ("ws2812b-needs-level-shifting", "A 5V WS2812B needs 3.5V data, which a 3.3V ESP32 cannot reach.", {
        "FACT": "The WS2812B datasheet gives supply of 3.5 to 5.3 V and input high of 0.7 x VDD, which is 3.5V at 5V. Adafruit says that with a 3.3V microcontroller you must use a logic level shifter.",
        "COUNTER": "Many people report it working without one, and one reference says it often works but is out of spec. Adafruit also says a 3.3V signal is fine for pixels on about 3.7V. Many general level shifters are too slow for this timing.",
        "OPINION": "Use a fast one-way buffer such as a 74AHCT125, and not rely on luck.",
        "FICTION": "Suppose a strip works on the bench, then flickers when the supply rises a little or the room warms up. Nothing has changed except the margin.",
        "CONTEXT": "Lowering the pixel supply also lowers the threshold, which is why the 3.7V case works.",
    }, "From the WS2812B datasheet and Adafruit, which agree. " + UNTESTED),
    ("ws2812b-power-and-protection", "WS2812B strips need a large capacitor, a data resistor, and their own power.", {
        "FACT": "Adafruit recommends a 500-1000 uF capacitor at 6.3V or higher across the supply, a 300-500 ohm resistor at the pixel end of the data line, and powering pixels before the microcontroller. Circuit Rocks gives up to 60 mA per LED at full white.",
        "COUNTER": "60 mA comes from one source and is the top end, as the WS2812B sheet I read gives no such total. Adafruit's page gave no per-pixel figure. Real colours and brightness draw less.",
        "OPINION": "Budget 60 mA per LED, and cap the brightness in software.",
        "FICTION": "Suppose 30 pixels go full white on the ESP32's regulator. That is 1.8A, far beyond what it can give, and the controller resets.",
        "CONTEXT": "This is the same lesson as servos: LEDs need their own supply, sized for peak current.",
    }, "From Adafruit and one reference. " + UNTESTED),
    ("switch-contacts-bounce", "Switch contacts bounce for over a millisecond, so input must be debounced.", {
        "FACT": "Ganssle tested a set of switches, pressing each 300 times. EE Journal reports an average bounce of 1557 microseconds and a maximum of 6200. Ganssle excluded one switch that bounced for 157 ms.",
        "COUNTER": "I could not open Ganssle's page, so these come via EE Journal and search summaries. It was his sample of switches, and new switches may differ. Ganssle also says bounce can reach hundreds of milliseconds.",
        "OPINION": "Debounce for 20 ms in software, and check a real switch with a scope if it matters.",
        "FICTION": "Suppose a bump counter uses a plain interrupt. One hit counts as seven, and the robot thinks it has been hit seven times.",
        "CONTEXT": "An ESP32 runs far faster than a bounce, so without debouncing it sees every one.",
    }, "Figures reported by EE Journal from Ganssle, and I did not read the original. The 20 ms is my judgement. " + UNTESTED),
    ("esp32-pull-ups-for-switches", "A contact switch to ground can use the ESP32's internal pull-up of about 45k, except on input-only pins.", {
        "FACT": "Espressif's datasheet gives internal pull-up and pull-down resistance of 45 kilohms typical. It says the input-only pins lack pull-up and pull-down resistors, and there are 6 input-only GPIOs.",
        "COUNTER": "A 45k pull-up is weak, so long wires near motors can pick up noise, and an external 4.7k or 10k is steadier. That advice is general, not from Espressif.",
        "OPINION": "Use the internal pull-up on the bench, and an external one on anything with long wires.",
        "FICTION": "Suppose a limit switch is wired to GPIO 35 with internal pull-up turned on in code. The pin floats, and the switch triggers by itself.",
        "CONTEXT": "That is why the M5Stick's buttons on G35, G37 and G39 rely on the board's own circuit, which I infer rather than read.",
    }, "From Espressif's datasheet, with general advice on external resistors. " + UNTESTED),
    ("normally-closed-limit-switches", "Wire safety limit switches normally closed, so a broken wire reads as triggered.", {
        "FACT": "An Omron D2F is a snap-action SPDT switch, so it offers both normally open and normally closed contacts. With a normally closed circuit, a broken wire opens the circuit just as a press does.",
        "COUNTER": "The wiring logic is my own reasoning, as I found no source for it in this search. D2F ratings also differ by model, and listings disagree on electrical life, 100,000 against 300,000 operations.",
        "OPINION": "Use normally closed for anything safety related, and pick by the exact part number.",
        "FICTION": "Suppose a normally open end stop has a broken wire. The arm runs into the end of its travel, and the switch never reports a thing.",
        "CONTEXT": "This links to the emergency stop cube. A limit switch read by software is not a substitute for cutting power in hardware.",
    }, "Standard engineering reasoning, but not sourced here. " + UNTESTED),
]

NEIGHBOURS = [
    ("esp32-gpio-input-and-current-limits", "esp32-logic-is-3v3", "Espressif's figures for the same claim"),
    ("hc-sr04-echo-is-5v", "esp32-logic-is-3v3", "a 5V output on a 3.3V input"),
    ("ws2812b-needs-level-shifting", "esp32-logic-is-3v3", "3.3V logic below the threshold"),
    ("sharp-gp2y0a21-ir-distance", "esp32-logic-is-3v3", "5V power with a read at 3.3V"),
    ("vl53l0x-voltage-and-address", "i2c-needs-pull-up-resistors", "it shares the I2C bus"),
    ("vl53l0x-voltage-and-address", "m5stick-plus2-grove-port", "a likely sensor for that port"),
    ("hc-sr04-range-and-limits", "no-one-distance-sensor-sees-everything", "sound's blind spots"),
    ("vl53l0x-range-depends-on-target-and-light", "no-one-distance-sensor-sees-everything", "light's blind spots"),
    ("sharp-gp2y0a21-ir-distance", "no-one-distance-sensor-sees-everything", "a third way of measuring"),
    ("active-vs-passive-buzzer", "m5stick-plus2-pins-moved", "the Stick's buzzer is passive"),
    ("led-resistor-at-3v3", "esp32-gpio-input-and-current-limits", "current per pin"),
    ("led-resistor-at-3v3", "pca9685-led-current-limits", "the same limit on another driver"),
    ("ws2812b-power-and-protection", "servos-and-the-esp32-should-have", "the same separate supply rule"),
    ("switch-contacts-bounce", "esp32-pull-ups-for-switches", "both shape a clean input"),
    ("normally-closed-limit-switches", "emergency-stop-cuts-power", "failing to the safe state"),
    ("esp32-pull-ups-for-switches", "m5stick-plus2-buttons", "buttons sit on input-only pins"),
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
        create_cube(s, claim, source="Cross-referenced by Claude, see source/sensors-and-outputs",
                    tags=["sensor", "hardware"], cube_id=cube_id)
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
    print(f"Added {len(seed(s))} sensor and output cubes, as drafts.")
    s.close()
