# Pond – Mission and business model (18 Nov 2026)

Source content for the public page at `business-model/`. Early thinking and rough estimates, not a decision.

## Mission

We have lost the know-how to grow our own food, and we have become fully dependent on supermarket chains. Yet growing food is easy to learn and easy to teach. Pond is a quiet, almost sneaky way to get people learning without stopping their day: just by watching the robot plant and tend, and harvesting by hand, you already start learning how it's done.

Pond's main mission is to empower people to learn how to grow their own food. Pond is a community and educational project first. It will always strongly support community projects and will never drop the community arm, however strong the commercial side becomes. If the commercial side grows, it will be in a position to invest in the community arm.

## Where Pond fits

Four ways lettuce and greens are produced:

1. Big mechanised monoculture farming.
2. Small family farms near cities selling at farmers' markets.
3. Indoor hydroponic vertical farms: a big trend, but many famous companies (Infarm, AppHarvest, Bowery) closed or went bankrupt because energy and running costs were higher than what the crop earned.
4. Pond: outdoor, solar-powered, communal hydroponic units looked after by a small robot.

Pond avoids the main thing that sank vertical farms: it runs on sunlight and a solar panel, so energy is close to free. It doesn't try to beat big farms on wholesale cost; it competes with the supermarket price because it skips transport, middlemen and waste.

## Rough economics (early guesses, not promises)

Framing (Dani's voice): "This is me thinking out loud, not a studied business plan. Pond is an open-source project, nowhere near going to market, and none of these numbers are promises." Shown at the top of the page and again above the numbers.

Unit cost, estimated from `docs/part-list/part-list.json` and the cart design (4 motors, omni wheels, arm, battery, solar, pipe, tanks):

Cost is split into the growing unit (tanks, pipe/track, pods, solar share, pump) and the robot cart (4 motors, omni wheels, arm, battery, computer):

- Target (bulk): growing unit $100-150, robot $150-200 (so $250-350 with one robot per unit). Life 5 years.
- Pessimistic: growing unit $250, robot $250 ($500 with one robot per unit). Life 3 years. (Single parts at hobby prices today come to more than this.)

Robot sharing (assumption to test): one robot may service up to about 10 units joined by track. To find out: how track joins units, cart speed, battery and work time per unit.

Cost per unit = unit + robot / n, using range midpoints (target 125 + 175/n; pessimistic 250 + 250/n). Per head adds 5 cents seeds and nutrients; 200 heads/yr in São Paulo. Amounts are stored once, in US dollars (`data-usd` in `business-model/index.html`), and the reais are converted live in the browser (`assets/fx.js`) from the current USD to BRL rate (api.frankfurter.app, cached in localStorage for a day). If the fetch fails or the device is offline, it falls back to a default of R$5.50 = US$1, which is also what the HTML shows with JavaScript off. The reais figures in the tables below are at that default rate and move with the real rate on the page.

| Units per robot | Cost per unit | São Paulo per head |
|---|---|---|
| Target 1 | $300 (R$1,650) | 35c (R$1.90) |
| Target 3 | $183 (R$1,000) | 23c (R$1.30) |
| Target 10 | $143 (R$790) | 19c (R$1.10) |
| Pessimistic 1 | $500 (R$2,750) | 88c (R$4.90) |
| Pessimistic 3 | $333 (R$1,830) | 61c (R$3.40) |
| Pessimistic 10 | $275 (R$1,510) | 51c (R$2.80) |

Location: Pond will be built in Brazil, starting in São Paulo. No UK comparison.

Harvests (about 25 plants per unit): São Paulo has mild winters so lettuce grows all year (slower in the cool months, stressed in the hottest and wettest). Rough estimate, not measured: about 8 harvests, about 200 heads a year.

Not yet counted: mailing pods, and a person delivering and assembling each unit the first time.

## Who it's for

Households, schools and community projects growing their own food, not people going into the lettuce business.

- Supermarket lettuce in São Paulo is roughly R$3-6 (about $0.55-1.10) a head (rough guess, to check against shelf prices). At about 200 heads a year a unit replaces about R$600-1,200 (about $110-220).
- Yearly cost of a unit: about $40-70 (R$220-385) target (lower when the robot is shared), about $175 (R$970) pessimistic with one robot per unit. Target looks worthwhile for a household; pessimistic roughly breaks even. A subscription covering upkeep would sit around that; no price set.
- Some people might one day want several units to sell produce locally. That only makes sense if bulk pricing brings units well down and they last many years. Not the focus.

## Business model (dual; current thinking, not a plan)

- Start with the community side: green funds, grants, councils and mayors fund free or subsidised units for community and educational projects, with workshops. The robot lets people learn without being fully committed.
- In parallel, offer a subscription on the open market; each commercial unit must pay for its own maintenance, so the project never depends on commercial sales.
- Let the commercial side prove itself. If it has legs, Pond can become a commercial project with a community arm; the mission and community arm stay either way.

## Why buy if it's open source? (current thinking)

Plans stay free. People pay to not build it themselves (sourcing, printing, wiring, testing, installing), for seed pods and nutrients by subscription, for support, repairs and software updates, and for the Pond name (trademark). If someone copies Pond to grow food, that still spreads the mission.

## References and inspiration

- FarmBot (farm.bot): open-source farming robot. Pond learns from its open design and from showing a robot can plant and tend (seeding, watering, weeding) while people harvest. FarmBot works a soil raised bed that you build and fill; Pond aims to be lighter to start (no soil, self-contained solar unit). Neither FarmBot nor Pond's robot harvests. No claims about their finances. More to add.
- Click & Grow (clickandgrow.com): indoor smart gardens, not open source. Reference for a fairly cheap garden plus a plant-pod subscription, close to Pond's supplies idea.
- MIT OpenAg "food computer": open-source growing project that shut down. A reminder to stay honest and not overpromise.

## Future direction

Future idea, not current work: the same Pond track and robot could one day run along raised beds too, moving from vertical to horizontal, so one robot looks after a whole garden.
