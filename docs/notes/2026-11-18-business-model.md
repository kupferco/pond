# Pond – Mission and business model (18 Nov 2026)

Source content for the public page at `business-model/`. Early thinking and rough estimates, not a decision.

## Mission

We have lost the know-how to grow our own food, and we have become fully dependent on supermarket chains. Yet growing food is easy to learn and easy to teach. Pond is a quiet, almost sneaky way to get people learning without stopping their day: just by watching the robot plant, tend and harvest, you already start learning how it's done.

Pond's main mission is to empower people to learn how to grow their own food. Pond is a community and educational project first. It will always strongly support community projects and will never drop the community arm, however strong the commercial side becomes. If the commercial side grows, it will be in a position to invest in the community arm.

## Where Pond fits

Four ways lettuce and greens are produced:

1. Big mechanised monoculture farming.
2. Small family farms near cities selling at farmers' markets.
3. Indoor hydroponic vertical farms: a big trend, but many famous companies (Infarm, AppHarvest, Bowery) closed or went bankrupt because energy and running costs were higher than what the crop earned.
4. Pond: outdoor, solar-powered, communal hydroponic units looked after by a small robot.

Pond avoids the main thing that sank vertical farms: it runs on sunlight and a solar panel, so energy is close to free. It doesn't try to beat big farms on wholesale cost; it competes with the supermarket price because it skips transport, middlemen and waste.

## Rough economics (early guesses, not promises)

Framing: early, very high-level, preemptive thinking. Pond is open source and nowhere near going to market; nothing is for sale and none of these numbers are promises.

Unit cost, estimated from `docs/part-list/part-list.json` and the cart design (4 motors, omni wheels, arm, battery, solar, pipe, tanks):

- Target: about $250-350 per unit including the cart, assuming bulk buying and production. Rough split: battery + solar + charger $120-150; arm servos + cart motors $70-90; Pi and electronics $60-80; printed parts, pipe, tanks $40-60. Assumed life 5 years.
- Pessimistic: about $500 per unit, life 3 years. (Single parts at hobby prices today come to more than this.)

Harvests (about 25 plants per unit):

- Warm all year (e.g. Rio): about 10 harvests, about 250 heads a year.
- Temperate outdoors (e.g. UK): maybe 4 harvests, about 100 heads a year.

Cost per head (hardware over lifetime + about 5 cents seeds and nutrients):

- Target: Rio about 25-35 cents; UK about 55-75 cents.
- Pessimistic: Rio about 70-75 cents; UK about $1.70 (too dear).

Not yet counted: mailing pods, and a person delivering and assembling each unit the first time.

## Who it's for

Households, schools and community projects growing their own food, not people going into the lettuce business.

- Supermarket lettuce in Rio (e.g. Prezunic) is roughly R$4-10 (about $0.75-2) a head. At about 250 heads a year a unit replaces about R$1,000-2,500 (about $190-500).
- Yearly cost of a unit: about $60-85 (target), about $180 (pessimistic). A subscription covering upkeep would sit around that; no price set.
- Some people might one day want several units to sell produce locally. That only makes sense if bulk pricing brings units well down and they last many years. Not the focus.

## Business model (dual; current thinking, not a plan)

- Start with the community side: green funds, grants, councils and mayors fund free or subsidised units for community and educational projects, with workshops. The robot lets people learn without being fully committed.
- In parallel, offer a subscription on the open market; each commercial unit must pay for its own maintenance, so the project never depends on commercial sales.
- Let the commercial side prove itself. If it has legs, Pond can become a commercial project with a community arm; the mission and community arm stay either way.
