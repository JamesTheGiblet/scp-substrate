<!-- ACEBOTT Bionic Spider chassis. Drafted by Claude on 2026-11-03 from the Amazon UK listing James pasted. -->
<!-- Electronics (ESP8266 board, shield, app, coding) are left out on purpose. Every claim is needs-check until measured on the real kit. -->
<!-- Tags say where each claim comes from: seller = listing copy or images, review = one customer's report, inferred = read from the images. -->

# entity ACEBOTT Bionic Spider chassis
id: entity/acebott-spider-chassis
kind: chassis
definition: The mechanical frame of ACEBOTT's four-legged Bionic Spider robot kit: the acrylic body, legs, joints, servo mounts, fasteners and feet, without its electronics.
aliases: ACEBOTT spider, spider chassis, bionic spider
bought: 2026-09-13, per the Amazon order history
part-of: entity/scpbot

### claim SCPBot uses only the ACEBOTT spider's chassis; its electronics are SCPBot's own, not the kit's.
id: cube/scpbot-uses-acebott-chassis-only
source: Stated by James, 2026-11-04
also: subject/pca9685, subject/m5stickc-plus2

## subject MG90S
uses: yes

## subject 18650 cell
kind: component
uses: yes

## subject Spider chassis frame
kind: topic

### claim The ACEBOTT spider chassis body is made of acrylic plates.
id: cube/spider-chassis-acrylic-body
source: Customer review (Ernestina, Vine, 2025-03-11), and a listing image labelled "Acrylic Board"
tags: needs-check, review, seller

### claim The ACEBOTT spider chassis is held together with M3 x 25 mm dual-pass copper pillars.
id: cube/spider-chassis-copper-standoffs
source: The listing image "Powerful Hardware"
tags: needs-check, seller

## subject Spider chassis legs
kind: topic

### claim The ACEBOTT spider chassis has four legs.
id: cube/spider-chassis-four-legs
source: The listing copy and images ("four-legged")
tags: needs-check, seller
COUNTER: One review says "8 legs", which is likely its 8 servos mistaken for legs. Count them on the real kit.

### claim Each ACEBOTT spider leg has two servo-driven joints, eight servos in total.
id: cube/spider-chassis-two-servos-per-leg
source: Inferred from the listing images; the listing doesn't say
tags: needs-check, inferred

### claim The ACEBOTT spider's legs are driven by MG90-series metal-gear micro servos.
id: cube/spider-chassis-mg90-metal-gear-servos
source: The listing copy ("MG90 metal servo"), and an underside image showing TowerPro MG90S
also: subject/mg90s
tags: needs-check, seller
CONTEXT: The copy says MG90 and the image shows MG90S. Check the label on the units.

## subject Spider chassis size
kind: topic

### claim The assembled ACEBOTT spider chassis stands about 82 mm tall.
id: cube/spider-chassis-82mm-tall
source: The listing's dimension image
tags: needs-check, seller

### claim The assembled ACEBOTT spider chassis spans about 159 mm per side.
id: cube/spider-chassis-159mm-span
source: The listing's dimension image
tags: needs-check, seller

### claim The ACEBOTT listing gives two sizes that disagree: 82 mm tall and 159 mm wide in its image, but 5.1 x 10.2 x 12.7 cm in its item details.
id: cube/spider-chassis-listing-dimensions-conflict
source: The listing's image against its item details
tags: needs-check, seller
CONTEXT: The 5.1 x 10.2 x 12.7 cm figure is probably the box, not the robot.

## subject Spider chassis fasteners
kind: topic

### claim The ACEBOTT spider chassis uses the same screws throughout.
id: cube/spider-chassis-uniform-screws
source: The listing copy
tags: needs-check, seller

### claim Assembling the ACEBOTT spider chassis means positioning very small nuts, which is fiddly.
id: cube/spider-chassis-small-fiddly-nuts
source: Customer review (Ernestina, Vine)
tags: needs-check, review

## subject Spider chassis feet
kind: topic

### claim The ACEBOTT spider's stock feet can fail to grip a laminate floor.
id: cube/spider-chassis-poor-grip-on-laminate
source: Customer review (Ry01, 2026-09-07)
tags: needs-check, review

### claim Adding non-slip rubber to the ACEBOTT spider's feet improves its grip.
id: cube/spider-chassis-rubber-feet-fix
source: Customer review (Ry01, 2026-09-07): one owner's fix
tags: needs-check, review

## subject Spider chassis assembly
kind: topic

### claim Assembling the ACEBOTT spider chassis is repetitive, because every leg is built the same way.
id: cube/spider-chassis-repetitive-leg-assembly
source: Customer review (Ernestina, Vine)
tags: needs-check, review

### claim The ACEBOTT spider chassis parts fit together without modification.
id: cube/spider-chassis-parts-fit
source: Customer review (Ernestina, Vine)
tags: needs-check, review
COUNTER: One review (Julio, Mexico) reports being sent the wrong parts.

## subject Spider chassis battery bay
kind: topic

### claim The ACEBOTT spider chassis holds one 18650 flat-top cell, and button-top cells don't fit.
id: cube/spider-chassis-one-18650-flat-top
source: The listing copy and image, and a customer review (Ernestina)
also: subject/18650-cell
tags: needs-check, seller, review

### claim On the ACEBOTT spider, the battery has to go in during assembly, not after.
id: cube/spider-chassis-battery-in-during-build
source: Customer review (Ernestina, Vine)
tags: needs-check, review

### claim SCPBot's ACEBOTT chassis is modified to hold its two 7.4V Li-ion packs instead of the stock 18650 cell.
id: cube/scpbot-chassis-modded-for-7-4v-packs
source: Stated by James, 2026-11-04
also: subject/7-4v-li-ion-pack, subject/18650-cell
