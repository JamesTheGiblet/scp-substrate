"""Cubes from Adafruit's PCA9685 16-Channel Servo Driver guide.

Same rules as seed_cubes.py: lenses arrive as proposals, OPINION is the human's.
Claims are paraphrased, and every cube links to the source capsule. Anything
that does not come from the guide says so in its COUNTER.
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[3] / "keystone-gate"
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from substrate import Substrate
from seed_cubes import seed


SOURCE = {
    "id": "source/adafruit-pca9685-guide",
    "foundation": "foundation:knowledge",
    "state": {
        "kind": "source-document",
        "name": "Adafruit PCA9685 16-Channel Servo Driver",
        "author": "Bill Earl",
        "url": "https://learn.adafruit.com/16-channel-pwm-servo-driver",
        "last_updated": "2026-08-19",
        "note": "Vendor guide. Claims are paraphrased into cubes; the text is not stored.",
    },
}

G = "Adafruit PCA9685 guide"
T = ["pca9685", "hardware"]

CUBES = [
    {
        "id": "cube/pca9685-sixteen-channels-over-i2c",
        "content": "The PCA9685 drives 16 PWM channels over I2C using two signal pins.",
        "source": f"{G}, Overview", "tags": T + ["servo"],
        "FACT": "16 channels at 12-bit resolution, run by the on-board controller with no extra microcontroller processing.",
        "COUNTER": "The board needs its own servo power, so two signal pins is not the whole wiring job. Control is four wires: VCC, GND, SDA and SCL.",
        "FICTION": "Driving 16 servos directly would use 16 pins and tie up the controller's timers.",
        "CONTEXT": "Overview, page 5.",
    },
    {
        "id": "cube/pca9685-chains-to-992-servos",
        "content": "Up to 62 boards chain on the same two pins, for 992 servos.",
        "source": f"{G}, Overview and Chaining", "tags": T + ["i2c"],
        "FACT": "62 boards at 16 channels gives 992. Each board needs a unique address, and chained boards connect with a 6-pin cable.",
        "COUNTER": "The guide's address table shows only 5-bit offsets, which covers 32 boards, not 62. It stops at Board 4 and does not explain the gap. Check the datasheet.",
        "FICTION": "At 992 servos, power distribution would be a far bigger problem than addressing.",
        "CONTEXT": "Only the first board in a chain needs a power terminal. Pages 5, 9 and 12.",
    },
    {
        "id": "cube/pca9685-i2c-address-jumpers",
        "content": "The default I2C address is 0x40, and solder jumpers add a binary offset.",
        "source": f"{G}, Addressing the Boards", "tags": T + ["i2c"],
        "FACT": "Bridge a jumper for each binary 1. A0 gives 0x41, A1 gives 0x42, A0 and A1 give 0x43, A2 gives 0x44.",
        "COUNTER": "Jumpers are soldered, so changing an address means rework, not a software change.",
        "FICTION": "With software addresses, two boards could collide after a bad write instead of at assembly.",
        "CONTEXT": "Each board needs its own driver object, and begin called on each. Page 14.",
    },
    {
        "id": "cube/pca9685-all-call-address-0x70",
        "content": "The chip also answers an All Call address of 0x70.",
        "source": f"{G}, FAQ", "tags": T + ["i2c"],
        "FACT": "This is in addition to the configured address, and can clash with Adafruit LED Matrix or 7-segment backpacks at 0x70.",
        "COUNTER": "The FAQ is the only place this appears, and it spells the chip PCA9865. The fix it gives moves the other device, to 0x71.",
        "FICTION": "Without knowing this, a second I2C device would fail in a way that looks like bad wiring.",
        "CONTEXT": "FAQ, page 30.",
    },
    {
        "id": "cube/pca9685-vcc-is-logic-power-only",
        "content": "VCC powers the chip only. Servos need V+ connected as well.",
        "source": f"{G}, Power Pins and Hooking it Up", "tags": T + ["power"],
        "FACT": "VCC should be 3 to 5V and match the microcontroller's logic, since it also feeds the 10K pullups on SCL and SDA.",
        "COUNTER": "The output logic level also follows VCC, so at 3.3V the PWM signal is 3.3V even when servos run from 6V. The guide does not discuss whether a given servo accepts that.",
        "FICTION": "If V+ were fed from VCC, a servo stall would pull down the logic supply.",
        "CONTEXT": "Green LED shows the board has power. Pages 7, 10 and 16.",
    },
    {
        "id": "cube/pca9685-v-plus-voltage-limit",
        "content": "Servo power on V+ should be 5 to 6V DC.",
        "source": f"{G}, Power Pins and Hooking it Up", "tags": T + ["power", "servo"],
        "FACT": "V+ is not used by the chip. The guide recommends 5 to 6V DC, through the blue terminal block, which is polarity protected.",
        "COUNTER": "The guide contradicts itself. Page 7 says you can go up to 12V DC if you have to. Page 10 says V+ can be as high as 6V. Treat 6V as the limit unless the datasheet and your servos say otherwise.",
        "FICTION": "A slip that joined V+ to VCC at 12V would damage the board, as the guide warns.",
        "CONTEXT": "Pages 7 and 10.",
    },
    {
        "id": "cube/pca9685-servo-current-sizing",
        "content": "Size the servo supply for current, not just voltage.",
        "source": f"{G}, Power for the Servos", "tags": T + ["power", "servo"],
        "FACT": "Micro servos draw several hundred mA while moving, and some high-torque servos draw over 1A each under load.",
        "COUNTER": "The guide lists 5V 2A, 4A and 10A supplies but gives no sizing rule, and 2A would not cover several high-torque servos moving together.",
        "FICTION": "A supply sized for average draw would brown out the moment every joint moved at once.",
        "CONTEXT": "4xAA packs give 6V with alkaline cells and 4.8V with NiMH. Pages 10 and 20.",
    },
    {
        "id": "cube/pca9685-never-power-servos-from-the-controller",
        "content": "Do not power servos from the Arduino or Raspberry Pi 5V pin.",
        "source": f"{G}, Power for the Servos and Python Computer Wiring", "tags": T + ["power", "servo"],
        "FACT": "Electrical noise and brownouts from the current draw can make the controller act erratically, reset or overheat.",
        "COUNTER": "The guide gives this as a warning with no threshold. One idle micro servo may seem fine on the bench, which is how the habit starts.",
        "FICTION": "A controller that resets mid-move would drop every servo signal at once.",
        "CONTEXT": "Use a separate supply. Pages 11 and 20.",
    },
    {
        "id": "cube/pca9685-capacitor-sizing",
        "content": "A capacitor of about 100uF per servo is a starting point.",
        "source": f"{G}, Adding a Capacitor", "tags": T + ["power"],
        "FACT": "Use n times 100uF for n servos when the supply dips under load, such as 470uF or more for 5 servos. The kit does not include one.",
        "COUNTER": "It is a rule of thumb: the guide says there is no one magic value, because it depends on current draw, torque and supply.",
        "FICTION": "A large enough capacitor would hide an undersized supply for a moment, not fix it.",
        "CONTEXT": "Solder an electrolytic into the thru-hole slot. Page 11.",
    },
    {
        "id": "cube/pca9685-one-frequency-for-all-channels",
        "content": "All 16 channels share one PWM frequency.",
        "source": f"{G}, Output Ports", "tags": T + ["pwm"],
        "FACT": "Duty cycle is independent per channel, but frequency is not, so servos and LEDs at different frequencies cannot share a board.",
        "COUNTER": "The guide says servos need 60 Hz. Not from the guide: many servo datasheets specify 50 Hz, so check yours. The Arduino chaining example sets 1600, which is unsuitable for servos.",
        "FICTION": "Mixing a 60 Hz servo and a 1 kHz LED strip would need a second board.",
        "CONTEXT": "setPWMFreq takes 40 to 1600 Hz. Pages 7, 14 and 18.",
    },
    {
        "id": "cube/pca9685-calibrate-before-trusting-angles",
        "content": "Calibrate each servo's minimum and maximum pulse before trusting its angles.",
        "source": f"{G}, Calibrating your Servos", "tags": T + ["servo", "calibration"],
        "FACT": "Pulse timing varies between brands, models and even samples of one model. Adjust SERVOMIN and SERVOMAX gradually, and stop before the physical limit.",
        "COUNTER": "Calibrating means approaching the limit you must not hit. Hitting it can strip the gears and permanently damage the servo.",
        "FICTION": "Uncalibrated values shared across joints would put each servo slightly off, and a stop or two out of range.",
        "CONTEXT": "Once calibrated, map(degrees, 0, 180, SERVOMIN, SERVOMAX) converts angle to pulse length. Pages 16 and 17.",
    },
    {
        "id": "cube/pca9685-pwm-ticks",
        "content": "setPWM sets on and off ticks within a 4096-step cycle.",
        "source": f"{G}, Library Reference", "tags": T + ["pwm", "arduino"],
        "FACT": "Channel is 0 to 15, and on and off are ticks from 0 to 4095. setPWM(15, 1024, 3072) goes high at 25 percent and low at 75 percent.",
        "COUNTER": "Fully on and fully off break that range. They use the special value 4096, so 4095 is not fully off, as the FAQ points out.",
        "FICTION": "Code clamping values to 4095 would leave LEDs faintly lit and never fully off.",
        "CONTEXT": "Fully on is setPWM(pin, 4096, 0). Fully off is setPWM(pin, 0, 4096). Pages 18, 19 and 30.",
    },
    {
        "id": "cube/pca9685-oe-pin-disables-outputs",
        "content": "Pulling OE high disables all outputs at once.",
        "source": f"{G}, Control Pins", "tags": T + ["safety"],
        "FACT": "OE is active low and pulled low by default, so it is optional. High disables the outputs.",
        "COUNTER": "The guide does not say what servos do when the signal stops, so do not assume OE is a safe stop for a loaded mechanism without testing it.",
        "FICTION": "With OE wired to a stop switch, one input could cut every PWM signal without touching the I2C bus.",
        "CONTEXT": "Control Pins, page 7.",
    },
    {
        "id": "cube/pca9685-led-current-limits",
        "content": "PWM outputs can drive LEDs, within limited current.",
        "source": f"{G}, Output Ports and Dimming LEDs", "tags": T + ["pwm", "led"],
        "FACT": "Max current per pin is 25mA, with 220 ohm resistors in series on every PWM pin.",
        "COUNTER": "The guide disagrees with itself. Page 7 gives 25mA, page 22 says around 10mA and that no resistor is needed, and the example code says to use a resistor.",
        "FICTION": "Reading only page 22 would make the outputs seem to need no thought at all.",
        "CONTEXT": "Pages 7, 22 and 24.",
    },
    {
        "id": "cube/pca9685-python-duty-cycle-is-12-bit",
        "content": "In Python, duty_cycle takes 16 bits but the chip resolves only 12.",
        "source": f"{G}, Dimming LEDs", "tags": T + ["pwm", "python"],
        "FACT": "duty_cycle runs from 0 to 0xFFFF to match other PWM objects. The example code notes only 12 bits of real resolution.",
        "COUNTER": "So a 16-step-sized change can do nothing. Fine values give a false sense of precision.",
        "FICTION": "A smooth fade written for 16 bits would still move in 4096 real steps.",
        "CONTEXT": "Pages 23 and 24.",
    },
    {
        "id": "cube/pca9685-servokit-for-python",
        "content": "ServoKit is the simple way to drive servos from Python.",
        "source": f"{G}, Controlling Servos", "tags": T + ["servo", "python"],
        "FACT": "ServoKit(channels=16) for this breakout. Set kit.servo[0].angle for standard servos and kit.continuous_servo[1].throttle for continuous ones.",
        "COUNTER": "The guide has rough edges: it says actuation_angle in one place and actuation_range in another, uses servokit where it means kit, and its full example sets channels=8.",
        "FICTION": "Copying the example unchanged would leave channels 8 to 15 unreachable on this board.",
        "CONTEXT": "Tune with actuation_range and set_pulse_width_range, such as (1000, 2000). Requires adafruit-circuitpython-servokit. Pages 21 to 27.",
    },
    {
        "id": "cube/pca9685-wiring-for-controllers",
        "content": "Wiring is the same four lines on any I2C controller.",
        "source": f"{G}, Hooking it Up and Python Wiring", "tags": T + ["i2c", "arduino"],
        "FACT": "VCC, GND, SDA and SCL. Classic Arduino uses A4 and A5, older Mega uses 20 and 21, and R3 boards have dedicated pins. Pi and Feather use 3V logic.",
        "COUNTER": "The guide does not cover the ESP32, so that wiring has to come from the board's own pinout.",
        "FICTION": "A chip that needed a controller-specific bus would not have a guide this short.",
        "CONTEXT": "esp32 is listed among your tools, which is why the gap is noted. Pages 9, 19 and 20.",
    },
    {
        "id": "cube/pca9685-servo-plug-orientation",
        "content": "Servo plugs go ground to the bottom row, signal to the top.",
        "source": f"{G}, Connecting a Servo", "tags": T + ["servo"],
        "FACT": "Ground is usually black or brown, and signal is usually yellow, white or orange. Each port has V+, GND and PWM.",
        "COUNTER": "Wire colours are a convention. The guide says to check your servo's data sheet.",
        "FICTION": "A plug reversed on a dense 16-port header is easy to miss in a tight assembly.",
        "CONTEXT": "Pages 7, 11 and 25.",
    },
]


def main():
    s = Substrate()
    if not s.get(SOURCE["id"]):
        s.write(SOURCE)
    seed(s, CUBES)
    for cube in CUBES:
        s.link(cube["id"], "derived-from", SOURCE["id"])
    s.close()


if __name__ == "__main__":
    main()
