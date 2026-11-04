"""Cubes for five dev boards, cross-referenced across sources.

The boards are the ESP32-C3, Raspberry Pi 3 Model B+, Arduino Uno R3, BBC
micro:bit V2 and Raspberry Pi Pico. Figures come from makers' sheets where they
could be read. Nobody has tested these here, so every face is a proposal.
Run: python seeds/claims/before-pivot/seed_cubes_boards.py
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[3] / "keystone-gate"
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not tested on hardware"
UNTESTED = "I have not tested this myself."
SOURCE = {
    "id": "source/dev-boards",
    "name": "Dev boards",
    "urls": [
        "https://documentation.espressif.com/esp32-c3_datasheet_en.pdf",
        "https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-plus-product-brief.pdf",
        "https://www.raspberrypi.com/products/raspberry-pi-3-model-b/",
        "https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf",
        "https://docs.arduino.cc/hardware/uno-rev3/",
        "https://tech.microbit.org/hardware/powersupply/",
        "https://microbit.org/get-started/features/overview/",
        "https://cnx-software.com/?p=81263",
        "https://cdn.shopify.com/s/files/1/1509/1638/files/Raspberry_Pi_Pico_datasheet.pdf",
        "https://www.adafruit.com/product/4864",
    ],
}

CUBES = [
    ("esp32-c3-is-single-core-risc-v", "The ESP32-C3 is a single-core 160MHz RISC-V chip with Wi-Fi and Bluetooth LE.", {
        "FACT": "Espressif's datasheet v2.4 gives a 32-bit RISC-V single core up to 160 MHz, 400 KB SRAM, 384 KB ROM, 2.4 GHz Wi-Fi and Bluetooth 5 (LE).",
        "COUNTER": "It is one core, where the classic ESP32 in the M5Stick has two, so Wi-Fi shares time with my code. Bluetooth is LE only in this sheet's description, so check before planning on Classic audio.",
        "OPINION": "This is my first choice for a small connected sensor node.",
        "FICTION": "Suppose a servo loop runs alongside heavy Wi-Fi on the one core. Timing jitters, and the servo twitches for no obvious reason.",
        "CONTEXT": "RISC-V is a different instruction set to the classic ESP32's, so anything compiled for one needs rebuilding for the other.",
    }, "From Espressif's datasheet v2.4. " + UNTESTED),
    ("esp32-c3-pins-are-limited", "An ESP32-C3 has at most 22 GPIOs, and in-package flash takes 6 of them.", {
        "FACT": "Espressif's datasheet gives 22 programmable GPIOs, with 3 strapping GPIOs and 6 allocated to in-package flash on those variants. Inputs allow 3.6V at most, with 40 mA source at maximum drive and 1000 mA cumulative.",
        "COUNTER": "A dev board brings out only some of them, and which depends on the board. I read no dev board's own guide, so the usable count is unknown here.",
        "OPINION": "Use it with I2C parts or a PCA9685, not as a board for lots of direct wires.",
        "FICTION": "Suppose a design needs ten switches and four LEDs. The pins run out, and a strapping pin gets used by mistake and stops the board booting.",
        "CONTEXT": "The input limit is the same 3.6V as the classic ESP32, so all the 5V warnings still apply.",
    }, "From Espressif's datasheet v2.4. " + UNTESTED),
    ("pi-3-is-a-linux-computer", "A Raspberry Pi 3 is a Linux computer, unlike the four microcontroller boards here.", {
        "FACT": "Raspberry Pi's product brief gives the 3 Model B+ as a quad-core 64-bit BCM2837B0 at 1.4GHz with 1GB RAM, 2.4 and 5 GHz Wi-Fi and Bluetooth 4.2. The earlier 3 Model B page gives 1.2GHz.",
        "COUNTER": "Which Pi 3 matters, as the Model B is slower and has 2.4 GHz only as far as this page shows. Linux is not real-time, and an OS has to boot and shut down. That is general knowledge, not from the brief.",
        "OPINION": "Use it for vision, logging and networking, and let a microcontroller handle timing.",
        "FICTION": "Suppose a robot is run from Pi GPIO alone. Linux pauses at a bad moment, and a servo pulse stretches.",
        "CONTEXT": "This suits the same pattern as your substrate: one part does the thinking and a separate part does the checking.",
    }, "From Raspberry Pi's product brief. The Linux point is general knowledge. " + UNTESTED),
    ("pi-3-power-and-lifetime", "A Pi 3 B+ needs 5V at 2.5A, and stays in production until at least January 2028.", {
        "FACT": "Raspberry Pi's product brief gives 5V/2.5A DC by micro USB, 5V by GPIO header, 0 to 50°C, and production until at least January 2028. The Model B page also says January 2028.",
        "COUNTER": "That 2.5A is more than the whole ESP32-based stack. Its GPIO is 3.3V and not 5V tolerant according to a third-party guide, and I did not read official documents on that, or a per-pin limit.",
        "OPINION": "Give it its own regulator, because it is the wrong thing to run from a small battery.",
        "FICTION": "Suppose a Pi 3 runs from the 2S pack through a regulator. At 2.5A and 5V it takes 12.5W, so 22Wh lasts under two hours, before any servos.",
        "CONTEXT": "An abrupt power cut can also corrupt the SD card, which is general knowledge, so a battery robot needs a clean shutdown.",
    }, "From Raspberry Pi's product brief, and the runtime is my arithmetic. " + UNTESTED),
    ("uno-r3-is-5v-with-2kb-ram", "An Uno R3 is a 16MHz 5V board with just 2KB of RAM.", {
        "FACT": "Arduino's datasheet gives an ATmega328P at up to 16 MHz with 32 kB flash, 2 kB SRAM and 1 kB EEPROM. Arduino's page gives 14 digital pins, 6 with PWM, and 6 analog inputs. DigiKey lists 5V logic.",
        "COUNTER": "2KB is small, and strings or a display buffer can use it up, usually with confusing faults rather than errors. There is no Wi-Fi. I read no per-pin current figure from Arduino.",
        "OPINION": "It is the most forgiving board for 5V parts, and the wrong choice for anything connected.",
        "FICTION": "Suppose a sketch prints long messages. Memory quietly runs out, and it starts resetting in odd ways.",
        "CONTEXT": "Its 5V logic makes it the only board here that takes an HC-SR04 with no divider. A later R4 exists, which is a different chip.",
    }, "From Arduino's datasheet and page. " + UNTESTED),
    ("uno-vin-takes-6-to-20v", "Arduino's sheet gives Uno VIN as 6 to 20V, so a 2S pack can feed it directly.", {
        "FACT": "Arduino's Uno R3 datasheet lists VIN from 6 to 20 V and USB up to 5.5 V. Some retailers say 7 to 12 V, and one says 7 to 9 V. A 2S pack runs from 8.4V down to about 5V.",
        "COUNTER": "The higher voltages make the regulator hot, which is why retailers quote less. Near empty, the pack falls below 6V and the board will brown out, so the safe window is shorter than the battery's.",
        "OPINION": "Stay in the 7 to 12V range, which a 2S pack fits for most of its charge.",
        "FICTION": "Suppose a 20V supply runs a busy Uno. It is in the table, and the regulator runs far hotter than at 8V.",
        "CONTEXT": "This is unlike the servos, PCA9685, ESP32 and Pi, which all need the pack stepped down.",
    }, "From Arduino's datasheet, while retailers give narrower ranges. " + UNTESTED),
    ("microbit-v2-has-sensors-built-in", "A micro:bit V2 has sensors, a display, sound and radio on the board.", {
        "FACT": "The micro:bit site lists an accelerometer, compass, temperature and light sensing, a touch logo, a speaker, a microphone, 25 LEDs, two buttons, radio and Bluetooth. CNX Software gives a nRF52833 at 64 MHz, 128 KB RAM and 512 KB flash.",
        "COUNTER": "Sources differ between Bluetooth 5.0 and 5.1. The chip figures come from a report and retailers, not the site page I read. Some display pins are shared, so using extra pins can mean turning the display off.",
        "OPINION": "The fastest way to get a working idea with no wiring, especially for teaching.",
        "FICTION": "Suppose a project needs only motion and a light. A micro:bit does it with no soldering at all.",
        "CONTEXT": "The V1 has no speaker or microphone, so check which version you have.",
    }, "From the micro:bit site and CNX Software. " + UNTESTED),
    ("microbit-power-limits", "A micro:bit V2 runs at 1.7 to 3.6V, with up to about 190mA for external parts.", {
        "FACT": "The micro:bit power page gives V2 at 1.7 to 3.6V and warns never to exceed it. It says the regulator sources 300mA, leaving an external budget of 270mA in one section and 190mA in another.",
        "COUNTER": "That page contradicts itself on the budget and marks part of V2 power as TBC, so use 190mA. I did not confirm that the edge pins are not 5V tolerant, though the supply limit suggests it.",
        "OPINION": "Never power servos from its 3V pin, and use 190mA as the limit.",
        "FICTION": "Suppose a fully charged LiPo is wired straight to the 3V pad. At 4.2V it is above the maximum, and it feeds the chips directly.",
        "CONTEXT": "The power page warns the 3V ring is the raw supply to the chips, and advises against USB battery packs.",
    }, "From the micro:bit power page, which disagrees with itself. " + UNTESTED),
    ("pico-is-a-cheap-dual-core", "A Raspberry Pi Pico is a dual-core 133MHz board, with no radio and 264KB of RAM.", {
        "FACT": "A Pico datasheet summary gives dual Cortex-M0+ up to 133MHz, 2MB flash, 264kB SRAM, 26 GPIOs at 3.3V, 3 analog, and 16 PWM channels. Adafruit lists the same chip, RP2040.",
        "COUNTER": "I could not open Raspberry Pi's own Pico PDF, so this is from a reseller's copy. Sources say it is not 5V tolerant. This is the original Pico, and it has no wireless, while a Pico W does.",
        "OPINION": "Choose it for more pins and steady timing when Wi-Fi is not needed.",
        "FICTION": "Suppose one core runs a servo loop and the other reads sensors. The timing stays steady, which a single-core C3 under Wi-Fi may not manage.",
        "CONTEXT": "Despite the name, it is a microcontroller, not a small Pi 3: no Linux, no OS.",
    }, "From a reseller's copy of the datasheet summary. " + UNTESTED),
    ("dev-board-memory-spans-500000-times", "These five boards span from 2KB to 1GB of RAM, about 500,000 times.", {
        "FACT": "Uno 2 KB, micro:bit V2 128 KB, Pico 264 KB, ESP32-C3 400 KB, Pi 3 1 GB, from the other cubes' sources.",
        "COUNTER": "RAM alone does not make a board better, as the Pi's memory comes with Linux and a 2.5A power budget. The C3's 400 KB also includes 16 KB for cache, and Wi-Fi uses a share of it.",
        "OPINION": "Choose the smallest board that does the job.",
        "FICTION": "Suppose every project used a Pi 3. A door sensor would need 2.5A and a clean shutdown to do what a coin cell could.",
        "CONTEXT": "This is a comparison across the board cubes, so check those for sources.",
    }, "My comparison of figures in the other cubes. " + UNTESTED),
    ("choose-a-dev-board-by-job", "Choose a board by the job: Uno for 5V parts, C3 for wireless, Pico for pins, micro:bit for no wiring, Pi for Linux.", {
        "FACT": "Each comes from the other cubes: Uno at 5V, C3 with Wi-Fi, Pico with 26 GPIOs, micro:bit with built-in sensors, and Pi 3 with Linux and 1GB.",
        "COUNTER": "This is my judgement rather than a sourced ranking, and I have not used a benchmark. Boards also overlap, and what you already know matters a lot.",
        "OPINION": "For your robots, a Pi for thinking with a microcontroller for moving seems the natural split.",
        "FICTION": "Suppose a project starts on an Uno and then needs Wi-Fi. Moving to a C3 also means moving from 5V to 3.3V on every sensor.",
        "CONTEXT": "Top 5 here means common in hobby use, chosen by you and me, not a measured ranking. The fifth, the Pico, was my pick.",
    }, "My judgement built on the other cubes, not a sourced ranking. " + UNTESTED),
]

NEIGHBOURS = [
    ("esp32-c3-pins-are-limited", "esp32-gpio-input-and-current-limits", "the same 3.6V input limit"),
    ("esp32-c3-is-single-core-risc-v", "m5stick-plus2-chip-and-memory", "one core against two"),
    ("uno-r3-is-5v-with-2kb-ram", "hc-sr04-echo-is-5v", "the Uno needs no divider"),
    ("uno-vin-takes-6-to-20v", "li-ion-2s-is-8v4-full", "a pack that fits VIN"),
    ("uno-vin-takes-6-to-20v", "li-ion-2s-too-high-for-servos", "the Uno can take what servos cannot"),
    ("pi-3-power-and-lifetime", "li-ion-2s-is-22wh-not-6000mah", "12.5W against 22Wh"),
    ("pi-3-power-and-lifetime", "servos-and-the-esp32-should-have", "the same separate supply rule"),
    ("microbit-power-limits", "esp32-logic-is-3v3", "another 3.3V family board"),
    ("pico-is-a-cheap-dual-core", "esp32-c3-is-single-core-risc-v", "two cores against one"),
    ("dev-board-memory-spans-500000-times", "choose-a-dev-board-by-job", "both compare the five"),
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
        create_cube(s, claim, source="Cross-referenced by Claude, see source/dev-boards",
                    tags=["board", "hardware"], cube_id=cube_id)
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
    print(f"Added {len(seed(s))} dev board cubes, as drafts.")
    s.close()
