"""Cubes for the M5StickC Plus2, cross-referenced across independent sources.

Each FACT names what was compared: M5Stack's docs, M5Stack's driver code,
Espressif's datasheet, and outside reviews. Disagreements go in COUNTER. The
words are Claude's and nobody has tested these on a device, so every face is a
proposal, and the suggested note says so.
Run: python keystone-gate/seed_cubes_m5stick.py
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not tested on a device"
SOURCE = {
    "id": "source/m5stickc-plus2",
    "name": "M5StickC Plus2",
    "urls": [
        "https://docs.m5stack.com/en/core/M5StickC%20PLUS2",
        "https://github.com/m5stack/M5Unified",
        "https://github.com/m5stack/M5GFX",
        "https://documentation.espressif.com/esp32-pico_series_datasheet_en.pdf",
        "https://www.cnx-software.com/2023/12/13/m5stickc-plus2-iot-development-kit-esp32-pico-v3-02-sip-200-mah-battery/",
        "https://www.atomic14.com/esp32/boards/m5stickc-plus2/",
        "https://www.switch-science.com/products/9350",
    ],
}

CUBES = [
    ("m5stick-plus2-chip-and-memory", "The M5StickC Plus2 runs an ESP32-PICO-V3-02 with 8MB flash and 2MB PSRAM.", {
        "FACT": "M5Stack's docs and Espressif's datasheet agree: ESP32-PICO-V3-02, 8 MB flash, 2 MB PSRAM. M5GFX also identifies this board by that chip package.",
        "COUNTER": "CNX Software's introduction says 2MB flash, though its own spec list says 8MB, and a distributor lists 2MB SRAM. Both look like errors, because Espressif's figures are the primary source. The PSRAM is also slower than internal SRAM.",
        "OPINION": "This is the one to trust most, because the chip maker and the board maker agree.",
        "FICTION": "Suppose a sketch assumes all 2MB is ordinary fast memory. It would run, then slow down badly in the one loop that matters.",
        "CONTEXT": "The original Plus used an ESP32-PICO-D4 with 4MB flash and no PSRAM, so this is the main reason to choose the Plus2.",
    }, "Cross-checked by Claude against M5Stack's docs, Espressif's datasheet and M5GFX. I have not tested it on a device."),
    ("m5stick-plus2-hold-pin", "On battery, the Plus2 stays on only if the program sets G4 high.", {
        "FACT": "M5Stack's docs say a program must set HOLD (G4) to 1 after wake-up or the device shuts down. M5Unified maps this board's power hold to GPIO 4, and Switch Science's manual says setting G4 low powers it off.",
        "COUNTER": "This applies on battery. With USB connected, the same long press only sleeps, so a missing HOLD line can pass on the bench and fail in use.",
        "OPINION": "This is the Plus2 trap most worth remembering, so I would set G4 first in every sketch.",
        "FICTION": "Suppose a robot works all week on USB, then switches off the moment it is unplugged. The code would look fine, and only this pin would explain it.",
        "CONTEXT": "It exists because the AXP192 power chip was removed, so the program now keeps its own power on.",
    }, "Cross-checked by Claude against M5Stack's docs, M5Unified and Switch Science. I have not tested it on a device."),
    ("m5stick-plus2-no-axp192", "The Plus2 has no AXP192, and reads its battery on G38.", {
        "FACT": "M5Stack's docs list the AXP192 as removed and battery detect on G38. M5Unified's code sets ADC pin 38 with a ratio of 2.0 for this board, and Switch Science also lists no PMIC.",
        "COUNTER": "CNX Software's spec list still names an AXP192, though its introduction says there is none, so that is an error in the article. A reader's comment there says a TP4057 handles charging, which I could not confirm. Plain ADC readings give an estimate, not a precise charge level.",
        "OPINION": "Old AXP192 examples will mislead here, so I would only use Plus2 code or M5Unified.",
        "FICTION": "Suppose old Plus code is flashed and calls the AXP192 at startup. Nothing answers, and the battery reading is simply wrong.",
        "CONTEXT": "M5Stack says the change improved Wi-Fi and IR signal. That is their claim, and I found no independent measurement.",
    }, "Cross-checked by Claude against M5Stack's docs, M5Unified and Switch Science. I have not tested it on a device."),
    ("m5stick-plus2-buttons", "Button A is G37, B is G39, and C is G35, which also wakes the device.", {
        "FACT": "M5Stack's docs give these three pins. M5Unified sets 35, 37 and 39 as inputs for this board and uses 35 as the wake pin.",
        "COUNTER": "The docs also describe a separate power/reset button, so labels can mislead: C is the power button in M5Unified's code. All three are input-only pins on the ESP32, so they cannot drive anything.",
        "OPINION": "Check by pressing them, as button names are the sort of thing that differs between diagrams and code.",
        "FICTION": "Suppose a menu uses C for select. A long press would switch the device off in the middle of a choice.",
        "CONTEXT": "Button C holding for over 2 seconds powers it on, and over 6 seconds powers it off on battery.",
    }, "Cross-checked by Claude against M5Stack's docs and M5Unified. I have not tested it on a device."),
    ("m5stick-plus2-pins-moved", "Code written for the StickC Plus needs its pins changed for the Plus2.", {
        "FACT": "M5Stack's docs list TFT DC moved from G23 to G14 and RST from G18 to G12, with IR moved from G9 to G19. M5GFX uses G14 and G12 for this board.",
        "COUNTER": "M5Unified and M5GFX detect the board and handle this, so it only matters for code that hard-codes pins or uses another display library.",
        "OPINION": "Use M5Unified rather than copying pin numbers, as the old M5StickCPlus2 library is now marked deprecated.",
        "FICTION": "Suppose a Plus sketch is flashed unchanged. The screen stays blank and it looks like a dead board.",
        "CONTEXT": "The two boards look almost the same, so this mistake is easy to make.",
    }, "Cross-checked by Claude against M5Stack's docs and M5GFX. I have not tested it on a device."),
    ("m5stick-plus2-led-ir-share-g19", "The red LED and the IR emitter share G19.", {
        "FACT": "M5Stack's docs put both on G19. M5Unified's code also defines this board's LED pin as GPIO 19.",
        "COUNTER": "The driver code confirms the LED pin only. The IR side rests on M5Stack's docs and Switch Science's pin list.",
        "OPINION": "Treat it as one output: you cannot use the LED as a status light while sending IR without one affecting the other.",
        "FICTION": "Suppose a status blink runs while a remote command goes out. The IR signal would be corrupted, and the fault would look like a bad receiver.",
        "CONTEXT": "On the original Plus these were separate pins, G9 and G10.",
    }, "Cross-checked by Claude against M5Stack's docs and M5Unified. I have not tested it on a device."),
    ("m5stick-plus2-grove-port", "The Grove port gives 5V power but its G32 and G33 signals are ESP32 pins.", {
        "FACT": "M5Stack's docs list the HY2.0-4P port as GND, 5V, G32 and G33. The ESP32's GPIO runs at 3.3V, as Espressif's datasheet supply range of 3.0 to 3.6 V reflects.",
        "COUNTER": "The pin list has one direct source, M5Stack's docs. That the signals cannot take 5V is my inference from the chip, and the docs do not say it here.",
        "OPINION": "A 5V sensor on this port needs level care, even though the port offers 5V power.",
        "FICTION": "Suppose a 5V I2C sensor is plugged in because the port says 5V. It may work for a while and slowly damage the pins.",
        "CONTEXT": "This links directly to the ESP32 3.3V logic cube, and to the PCA9685 wiring cubes for running servos from this board.",
    }, "Cross-checked by Claude against M5Stack's docs and Espressif's datasheet. The 3.3V limit on these pins is an inference. I have not tested it on a device."),
    ("m5stick-plus2-battery", "The Plus2 has a 200mAh battery.", {
        "FACT": "M5Stack's docs, CNX Software, Atomic14 and Switch Science all give 200 mAh, and M5Stack and CNX Software give 3.7V. The original Plus had 120 mAh.",
        "COUNTER": "That is a small battery. I found no measured runtime for this board in any source, so how long it lasts on Wi-Fi is unknown.",
        "OPINION": "Measure it on my own workload before planning anything around it.",
        "FICTION": "Suppose it runs a Wi-Fi logger overnight. It would probably stop long before morning, but only a test would say when.",
        "CONTEXT": "This is the best-agreed number here, and it links to the ESP32 brownout cube, since Wi-Fi bursts on a small cell can pull the supply down.",
    }, "Cross-checked by Claude against four sources that agree. Runtime is not known. I have not tested it on a device."),
    ("m5stick-plus2-temperature", "M5Stack rates the Plus2 for 0 to 40 degrees C.", {
        "FACT": "M5Stack's docs say 0 ~ 40°C. Espressif rates the chip itself at -40 ~ 85 °C.",
        "COUNTER": "CNX Software says 0°C to 60°C, which disagrees with M5Stack. I could not settle why, and the board's limit is probably set by the battery or display, which is my guess.",
        "OPINION": "Use 0 to 40, the maker's figure and the cautious one, until a current M5Stack source says otherwise.",
        "FICTION": "Suppose it is left on a dashboard in summer. The chip would cope, and the lithium battery is what would worry me.",
        "CONTEXT": "This is the one spec where sources openly conflict, so the claim is what M5Stack states, not the true limit.",
    }, "Sources disagree: M5Stack says 0 to 40, CNX Software says 0 to 60. I am using M5Stack's figure and have not tested it."),
    ("m5stick-plus2-end-of-life", "The Plus2 is end-of-life, with the M5StickS3 as its successor.", {
        "FACT": "Atomic14 lists it as EOL, succeeded by the M5StickS3 (ESP32-S3), and Switch Science says it is no longer manufactured.",
        "COUNTER": "Both are third parties, and I did not find this stated on M5Stack's own product page. Stock can stay on sale after production ends.",
        "OPINION": "If I plan to build more than one, check stock before designing around it.",
        "FICTION": "Suppose a project is built around this board, and a replacement is needed in two years. The S3 uses a different chip, so code and pins may not carry over.",
        "CONTEXT": "Its driver library has also moved on: M5StickCPlus2 is deprecated in favour of M5Unified and M5GFX.",
    }, "Cross-checked by Claude against Atomic14 and Switch Science, but not confirmed on M5Stack's own page."),
]

NEIGHBOURS = [
    ("m5stick-plus2-grove-port", "esp32-logic-is-3v3", "same 3.3V limit on a port that offers 5V"),
    ("m5stick-plus2-grove-port", "esp32-i2c-pins-are-configurable", "the port's I2C runs on chosen pins"),
    ("m5stick-plus2-battery", "esp32-brownout-resets", "Wi-Fi bursts on a small battery"),
    ("m5stick-plus2-hold-pin", "m5stick-plus2-no-axp192", "the hold pin exists because the AXP192 went"),
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
        create_cube(s, claim, source="Cross-referenced by Claude, see source/m5stickc-plus2",
                    tags=["m5stick", "hardware"], cube_id=cube_id)
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
    print(f"Added {len(seed(s))} M5StickC Plus2 cubes, as drafts.")
    s.close()
