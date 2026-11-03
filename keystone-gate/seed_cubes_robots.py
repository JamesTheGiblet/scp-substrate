"""Cubes for common robot shapes and configurations, cross-referenced.

Covers wheeled bases, arms and legged robots, with sums worked using this
store's own servo and battery cubes. Sources are mostly reference articles, so
they describe the geometry well and say less about real-world limits. Nobody
has built these here, so every face is a proposal.
Run: python keystone-gate/seed_cubes_robots.py
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face, propose_neighbour


BY = "model-draft:claude"
WHY = "written by Claude from the sources listed on the capsule, not built or tested"
UNBUILT = "I have not built this."
SOURCE = {
    "id": "source/robot-configurations",
    "name": "Robot configurations",
    "urls": [
        "https://en.wikipedia.org/wiki/Differential_wheeled_robot",
        "https://en.wikipedia.org/wiki/Mecanum_wheel",
        "https://en.wikipedia.org/wiki/Ackermann_steering_geometry",
        "https://en.wikipedia.org/wiki/Kiwi_drive",
        "https://en.wikipedia.org/wiki/SCARA",
        "https://en.wikipedia.org/wiki/Delta_robot",
        "https://en.wikipedia.org/wiki/Cartesian_coordinate_robot",
        "https://en.wikipedia.org/wiki/Serial_manipulator",
        "https://zbotic.in/hexapod-vs-bipedal-robot-stability/",
        "https://oscarliang.com/quadruped-robot-gait-study",
        "https://arxiv.org/pdf/2310.12142",
        "https://people.ece.cornell.edu/land/courses/ece4760/FinalProjects/f2015/dc686_nn233_hz263/final_project_webpage_v2/dc686_nn233_hz263/",
        "https://microcontrollerslab.com/best-tank-robot-kits-tracked-chassis-buying-guide/",
    ],
}

CUBES = [
    ("differential-drive-is-the-simple-base", "Differential drive steers two wheels by speed alone, which makes it the simplest mobile base.", {
        "FACT": "Wikipedia says equal speeds go straight, and opposite speeds rotate about the axle centre. No steering motion is needed, and casters are typically used to stop it tilting. Forward speed is the average of the wheel speeds, and turn rate is their difference over the wheel spacing.",
        "COUNTER": "Its heading depends entirely on the wheel speeds, so small differences make it drift, and those rates need sensing. The maths assumes no slip. The claim that nearly all consumer robots use it is tagged as needing a citation.",
        "OPINION": "This is where I would start any mobile robot.",
        "FICTION": "Suppose two cheap motors differ by 3%. It is told to go straight, and it draws a long curve across the floor.",
        "CONTEXT": "This needs geared motors, or continuous-rotation servos such as the 360 degree ones sold under the same names as your servos.",
    }, "From Wikipedia. " + UNBUILT),
    ("ackermann-steering-suits-car-shapes", "Ackermann steering turns the inner wheel more than the outer, so a car-shaped robot turns without tyre scrub.", {
        "FACT": "Wikipedia says the wheels on a turn trace circles of different radii, so the linkage turns the inner wheel more to avoid sideways slip. It says pure Ackermann suits low speeds.",
        "COUNTER": "It needs a linkage and a steering servo. That it cannot rotate in place follows from fixed rear wheels, which is my inference, as the article does not say so.",
        "OPINION": "Choose it for outdoor speed, and not for tight indoor spaces.",
        "FICTION": "Suppose a car-shaped robot meets a dead end. Where a differential base just turns, this one has to make a three-point turn.",
        "CONTEXT": "An SG90 or MG90S suits the steering on a small car, as it only needs to reach an angle and hold it.",
    }, "From Wikipedia, plus my inference on turning in place. " + UNBUILT),
    ("mecanum-moves-any-direction", "Mecanum wheels let a robot slide sideways, using rollers at 45 degrees and four driven wheels.", {
        "FACT": "Wikipedia says each independently driven wheel has rollers at 45 degrees. All four the same way goes forward, one side reversed rotates, and diagonal pairs opposed go sideways. It says this suits suitable terrain.",
        "COUNTER": "The article gave no figures on slip or efficiency, and they are known limits from general knowledge: rollers slip, which ruins wheel-count position, and a rough floor hurts. Four motors means four drivers.",
        "OPINION": "Worth it on a flat floor when sideways motion is really needed, and otherwise too much.",
        "FICTION": "Suppose a mecanum base is taken onto gravel. Rollers jam with stones, and the sideways trick stops working.",
        "CONTEXT": "Rotation in place takes low torque compared with skid steering, according to Wikipedia.",
    }, "From Wikipedia, and the slip limits are general knowledge. " + UNBUILT),
    ("kiwi-drive-is-three-omni-wheels", "A kiwi drive uses three omni wheels 120 degrees apart to move any direction with fewer motors.", {
        "FACT": "Wikipedia and Luis Llamas describe three omni wheels at 120 degrees forming a holonomic base that moves any way without turning first. Wikipedia traces the name to a FIRST team's codeword for a Killough platform.",
        "COUNTER": "FIRST forum posts report less usable thrust than four-wheel designs and difficulty driving straight without feedback, with one team using a gyro. Three wheels can also feel tippy. Those are forum reports.",
        "OPINION": "A good compromise for a small indoor robot if I have an IMU.",
        "FICTION": "Suppose a kiwi base with no gyro is told to go forward. It slowly rotates as it travels, because three motors never match exactly.",
        "CONTEXT": "The M5StickC Plus2's MPU6886 gives you that gyro.",
    }, "From Wikipedia and forum reports. " + UNBUILT),
    ("tracks-grip-but-waste-power", "Tracks grip rough ground, but they scrub sideways on every turn and drain the battery faster.", {
        "FACT": "A buying guide says tracked robots draw more current and drain batteries faster than wheeled ones of the same size, because skid steering scrubs sideways. Vehicle research reports significant turning losses, and Wikipedia says skid-steer turns need high torque.",
        "COUNTER": "The robot figures are from a buying guide, and I have no measured numbers at this scale. The research is on full-size vehicles.",
        "OPINION": "Use tracks only when the ground demands them.",
        "FICTION": "Suppose a tracked robot turns on a carpet. The motors stall, the current leaps, and a small BMS cuts the power.",
        "CONTEXT": "Plan motor current for turning, not driving straight, and check it against the pack's limit.",
    }, "From a buying guide and full-scale vehicle research. " + UNBUILT),
    ("self-balancing-needs-a-fast-loop", "A two-wheel balancer is an inverted pendulum, so it falls without constant correction from an IMU.", {
        "FACT": "A Cornell project describes the design as inherently unstable. A 2023 arXiv paper uses geared DC motors with encoders, an IMU and PID. Another project fuses gyro and accelerometer readings into a tilt angle with a complementary filter.",
        "COUNTER": "These are student projects and one paper, not a design standard. A slow control loop or Wi-Fi jitter can make it fail, which is my inference from the C3 cube. Hobby servos are not a good fit, as motors need quick reversals.",
        "OPINION": "A great control project, and a poor way to get a useful robot quickly.",
        "FICTION": "Suppose a balancer runs on a single core during a Wi-Fi burst. A few missed readings, and it is on its face.",
        "CONTEXT": "One project needed a heat sink on its motor driver because of high motor current.",
    }, "From student projects and one paper. " + UNBUILT),
    ("six-joints-for-any-pose", "An arm needs six joints to reach any position at any orientation.", {
        "FACT": "Wikipedia's serial manipulator article describes joints placing an object at an arbitrary position and orientation. Three cover position and three rotation, making six the minimum for a full pose.",
        "COUNTER": "Many jobs need far fewer: a 4-joint pick-and-place arm keeps a tool pointing down. An arm also reaches any pose only within its workspace, and singularities lose directions of motion.",
        "OPINION": "Start with four joints and a gripper, because six costs a lot more for little gain.",
        "FICTION": "Suppose a six-servo arm meets a singularity mid-move. Two joints try to spin fast for a tiny move of the tool.",
        "CONTEXT": "This links to the inverse kinematics cube, and designs with three intersecting wrist axes have closed-form solutions.",
    }, "From Wikipedia and robotics papers. " + UNBUILT),
    ("arm-base-joint-carries-the-most-torque", "On a hobby arm, torque is what limits it, and the joint nearest the base works hardest.", {
        "FACT": "Torque is force times distance, so 200 g held 15 cm out needs 3 kg-cm, more than an SG90's 1.8 kg-cm at best. An MG996R's 9.4 to 11 kg-cm covers it, with the arm's own weight and the outer servos to add.",
        "COUNTER": "The sum is mine, as my search found no source on the shoulder carrying the most, and it leaves out the arm's own weight. A real arm also needs a margin, and stall is a limit, not a working load.",
        "OPINION": "Use MG996R at the shoulder, MG90S further out, and SG90 only at the gripper.",
        "FICTION": "Suppose every joint uses an SG90 because it fits. The arm holds itself up, and can lift nothing else.",
        "CONTEXT": "This builds on your cube that torque needed grows with reach. Keep heavy servos near the base, because each one is a load on all before it.",
    }, "My arithmetic from the servo cubes, not a sourced design rule. " + UNBUILT),
    ("scara-is-stiff-up-and-down", "A SCARA arm is stiff vertically and slightly compliant sideways, which suits assembly.", {
        "FACT": "Wikipedia says SCARA stands for selective compliance assembly robot arm. It uses parallel-axis joints, stays stiff vertically and gives slightly sideways, suiting a pin into a hole. It says they are faster than Cartesian robots and use less floor space.",
        "COUNTER": "Wikipedia also says they cost more than Cartesian systems and need inverse kinematics for straight lines. They are industrial examples, so a hobby version with servos will have backlash.",
        "OPINION": "Gravity is carried by the structure, so this suits weak servos better than a vertical arm.",
        "FICTION": "Suppose a SCARA is built with SG90s. They only swing the arm sideways, so they barely fight gravity at all.",
        "CONTEXT": "That is why the shape matters as much as the servo: the same motor does far more in a horizontal arm.",
    }, "From Wikipedia. The hobby point is my judgement. " + UNBUILT),
    ("delta-robots-keep-motors-on-the-base", "A delta robot keeps its motors on the base, so its light arms can move very fast.", {
        "FACT": "Wikipedia describes three arms joined to a small platform, with the actuators above the workspace. Low moving mass allows high speed, some up to 300 picks per minute, and parallelograms keep the platform level. It came from Clavel's team at EPFL in the early 1980s.",
        "COUNTER": "Wikipedia says joining all arms reduces working volume, and it is stiffer for that. Its small payload and its maths are harder than a Cartesian machine's. Three good servos may also be needed, with backlash multiplying at the tool.",
        "OPINION": "This is a fun build, and it shows off speed more than usefulness.",
        "FICTION": "Suppose a chocolate factory needs thousands of quick, gentle moves. That really was the original motive, according to Wikipedia.",
        "CONTEXT": "This is the opposite of a serial arm, whose motors ride on the arm itself.",
    }, "From Wikipedia. " + UNBUILT),
    ("cartesian-machines-are-simple-to-control", "A Cartesian robot moves straight along right-angled axes, as 3D printers and CNC machines do.", {
        "FACT": "Wikipedia says the three main axes are linear and at right angles, which simplifies control and gives high reliability and precision. It names CNC machines, 3D printers and pen plotters as the same layout, and says gantries are often large.",
        "COUNTER": "The article lists no drawbacks. The robot must also be larger than what it works on, which is general knowledge, and linear axes need rails rather than hobby servos.",
        "OPINION": "This is the jig of robots, and the right choice for anything precise on a flat bed.",
        "FICTION": "Suppose a pen plotter is the first arm project. It teaches more, with much less maths, than a six-axis arm.",
        "CONTEXT": "Stepper motors are usual here, and they are not in this store yet.",
    }, "From Wikipedia. " + UNBUILT),
    ("hexapods-stay-stable-walking", "A hexapod can always keep three legs down, so it stays stable while walking.", {
        "FACT": "A Zbotic guide says a hexapod standing is passively stable, and a tripod gait keeps three legs down. Static stability needs the centre of mass over the support polygon formed by the feet.",
        "COUNTER": "The guide is a retailer's. That 18 servos at 3 per leg is usual is from a product page. That is a heavy budget: 18 MG90S moving draw about 4.5A, and 12.6A if all stall, using your cubes.",
        "OPINION": "The most forgiving legged robot, and the most expensive in servos and current.",
        "FICTION": "Suppose a hexapod runs from a 3A BMS. It stands well, and on the first step up a slope it cuts out.",
        "CONTEXT": "About 40 minutes of runtime is possible from 3.1Ah at 4.5A, which is my arithmetic from the battery runtime cube.",
    }, "From a retailer's guide, plus my arithmetic. " + UNBUILT),
    ("quadrupeds-trade-stability-for-speed", "A quadruped can creep stably with one leg up, or trot faster with dynamic balance.", {
        "FACT": "Oscar Liang's gait study describes the creep gait as statically stable with one leg lifted at a time, and the diagonal trot as dynamically stable.",
        "COUNTER": "This is a hobbyist study, and I found no source for a standard servo count. Twelve at 3 per leg is the common build I would expect, and that is unverified.",
        "OPINION": "Start with creep, and only then attempt trot, which needs an IMU and quick control.",
        "FICTION": "Suppose a quadruped trots on a slight slope. Two feet are down at any moment, and it tips with nothing to catch it.",
        "CONTEXT": "This sits between the hexapod's stability and the biped's constant balancing.",
    }, "From a hobbyist study. " + UNBUILT),
    ("bipeds-need-active-balance", "A biped falls over without active balance, so it is the hardest shape here.", {
        "FACT": "A Zbotic guide says a biped without active balance control will fall when pushed or on uneven ground. A standing biped needs active control or wide flat feet, and balance uses IMU feedback at ankles and hips.",
        "COUNTER": "That guide is a retailer's, and small desktop bipeds with big feet do manage slow static walks, which is general knowledge. Hobby servos have backlash, which makes fine balance harder.",
        "OPINION": "Leave this until after everything else on this list.",
        "FICTION": "Suppose a biped steps on a cable. A hexapod would not notice, and the biped goes over with its servos still driving.",
        "CONTEXT": "This links to the backlash cube, which matters more here than on any other shape.",
    }, "From a retailer's guide and general knowledge. " + UNBUILT),
    ("shape-sets-the-power-budget", "The robot's shape sets its servo count, which sets everything else about power.", {
        "FACT": "Using this store's figures: a 4-joint MG90S arm stalls at about 2.8A, an 18-servo MG90S hexapod at 12.6A, and a 6-joint MG996R arm at 15A, while your 2S pack holds about 22Wh.",
        "COUNTER": "This is my arithmetic from your cubes, and every servo stalling at once is a worst case. The servo counts are illustrative, not sourced standards, and real duty is much lower.",
        "OPINION": "Choose the shape first, then size the regulator, wire, fuse and BMS from its count.",
        "FICTION": "Suppose a hexapod is designed around a 5A regulator. It fine-tunes its gait for weeks, and the fix was always the power stage.",
        "CONTEXT": "This is the link between the shape cubes and the servo, battery, wiring and safety cubes.",
    }, "My arithmetic from the other cubes. " + UNBUILT),
]

NEIGHBOURS = [
    ("arm-base-joint-carries-the-most-torque", "torque-falls-with-arm-length", "the same claim with figures"),
    ("arm-base-joint-carries-the-most-torque", "mg996r-torque", "the shoulder servo"),
    ("arm-base-joint-carries-the-most-torque", "sg90-torque-figures-disagree", "the gripper servo"),
    ("six-joints-for-any-pose", "inverse-kinematics-maps-position-to-angles", "how joints are solved"),
    ("self-balancing-needs-a-fast-loop", "esp32-c3-is-single-core-risc-v", "control loops against Wi-Fi"),
    ("kiwi-drive-is-three-omni-wheels", "m5stick-plus2-chip-and-memory", "a board with a built-in gyro"),
    ("bipeds-need-active-balance", "gear-backlash-limits-precision", "backlash matters most here"),
    ("hexapods-stay-stable-walking", "mg90s-stall-current", "12.6A with 18 servos"),
    ("hexapods-stay-stable-walking", "li-ion-30q-current-rating", "what the pack must supply"),
    ("shape-sets-the-power-budget", "li-ion-2s-runtime-estimate", "runtime depends on the shape"),
    ("shape-sets-the-power-budget", "pca9685-servo-current-sizing", "the same sizing question"),
    ("shape-sets-the-power-budget", "fuse-the-battery-positive-near-the-pack", "fuse for the chosen shape"),
    ("shape-sets-the-power-budget", "robots-can-move-without-warning", "more joints, more moving parts"),
    ("tracks-grip-but-waste-power", "li-ion-30q-current-rating", "turning current meets the BMS"),
    ("scara-is-stiff-up-and-down", "arm-base-joint-carries-the-most-torque", "gravity is on the structure"),
    ("cartesian-machines-are-simple-to-control", "james-carpenter-by-trade", "jigs and fixtures"),
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
        create_cube(s, claim, source="Cross-referenced by Claude, see source/robot-configurations",
                    tags=["robot", "hardware"], cube_id=cube_id)
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
    print(f"Added {len(seed(s))} robot configuration cubes, as drafts.")
    s.close()
