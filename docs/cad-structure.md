# How the CAD is organised (single source)

Every part of the Pond unit and cart is defined **once**, as a function in its own file, and every assembly, render, GLB and drawing imports it.
Nothing rebuilds the cart, the tank or the track on its own. (OpenPocket #365; this is what went wrong in #330, where an assembly script
copied the cart's track pipe and drew it twice.)

## Where each part lives

| Part | Defined in | Used by |
|---|---|---|
| Tank (open box), lid | `cad/parts/tank.py` | unit, complete unit, water station, all unit drawings |
| **Water volume** (normal level 15 cm, translucent blue, named part `water_volume`) | `cad/parts/water_volume.py` | same as the tank |
| Track loop | `cad/parts/track.py` | unit, track supports, complete unit, water station |
| Frame: growing pipe, spine, collars, legs, lid plates, panel, feet, sandbags | `cad/parts/unit_frame.py` | via `cad/parts/unit.py` (`unit_parts()`, the whole unit as a list) |
| Pods | `cad/parts/pods.py` | complete unit, water station |
| **Shelf** (4 mm plate at z 155..159, 5 mm over the 150 water, under the lid, hole for the spine tube) | `cad/parts/shelf.py` (`SHELF_Z`/`SHELF_T` in `unit_dims.py`) | `unit_parts()`, so every unit drawing |
| Seedling tray (6 x 3 cells), **gravity-feed dry pod store** (7 lanes, sloping `SLOPE_DEG`, flat landing, stop lip) and their pods, standing ON the shelf under the lid | `cad/parts/shelf_items.py`, numbers in `cad/pod_layout.py` (also read by `sim/pod_grab.py`) | full unit, complete unit, dimensioned unit, water station |
| **Lid with pick slots** (one over every tray cell and store landing, at least 70 x 50, sized to the claw by the sim: `cad/pod_slots.json`) | `cad/parts/tank.py` | every drawing that draws the lid |
| Unit numbers (tank size, track, heights, water level) | `cad/parts/unit_dims.py` | everything above |
| **Cart** (plate, two hands with the motors inward, battery, arm) | `cad/cart_assembly.py` (with `cart_sleeves.py`, `cart_omni.py`, `cart_base.py`, `cart_arm.py`, shared numbers in `cart_dims.py`) | `cad/parts/cart.py` is the one way to reuse it (`add_cart`) |
| Track pipe | the cart has **none** (#447). Only `cad/parts/track.py` draws track. `cart_geom.track_pipe()` is a gauge for clash/gap checks, never drawn | water assembly and sampler checks |
| **Sample tubing coil** (pump link, PU coil, tail) | `cad/parts/sample_coil.py` | water sampler, cart, complete unit, water assembly |
| Sampling connector (male nozzle, female socket) | `cad/parts/water_connector.py` | sampler, station |
| Track supports (#315) | `cad/track_supports.py` | track supports renders, water assembly |
| Water testing station | `cad/water_station.py` | water assembly, renders |

**The full unit** is `cad/pond_full_unit.py`: the ONE assembly renders and sims import (unit + pods + tray + store + station + two upright carts with the real SO-101 in its pick pose). `cad/render_full_unit.py` makes its pictures and GLBs, `cad/check_pod_layout.py` checks it against the sim. See `docs/pod-grab.md`.

Assemblies (they only place parts, never draw them): `cad/unit_v3_aframe.py`, `cad/unit_v3_dimensioned.py`, `cad/track_supports.py`,
`cad/complete_unit.py` (unit + pods + shelf items + the real cart on the right track run), `cad/water_assembly.py` (cart at the water testing station).

## One command

```
python cad/build_all.py          # checks, every render and GLB, then the Drawings and 3D Models pages (about 20 minutes)
python cad/build_all.py quick    # only the single-source check and the clash checks
```

It runs `check_single_source.py`, the clash checks (`water_assembly.py`, `complete_unit.py`), the render scripts (`render_omni_sleeve.py` for the cart family,
`render_track_supports.py`, `render_unit.py`, `render_water_station.py`) and `publish_drawings.py`, which copies the GLBs to `docs/drawings/renders/`,
draws the line views, and updates `docs/drawings/renders.json` (Drawings page) and `docs/models/models.json` (3D Models page). Needs `cadquery numpy matplotlib pillow scipy trimesh`.

## The check

`python cad/check_single_source.py` fails if

1. a function defined in `cad/parts/` is defined again in another script,
2. a script that does not import from `cad/parts/` gives an assembly child one of the unit's part names (`tank`, `water_volume`, `track_loop`, ...), or
3. two scripts define the same top-level function (apart from generic helpers such as `box`, a frozen list of known cases, and the superseded design
   studies listed in `STUDIES`, which the build no longer runs),
4. (#447) the cart source carries a `track_pipe*` child, or any assembly adds one (the track comes only from `cad/parts/track.py`), or
5. (#447) the shelf is not above the water and under the lid, or the seedling tray / storage do not stand on the shelf top and under the lid.

## Adding or changing a part

Change the one function. Run `python cad/build_all.py`. Do not copy it into an assembly: import it. If a script needs the part in another frame,
move it with a plain translation or rotation (`add_cart(..., shift=...)`, `water_assembly.to_cart`), never by redrawing.

## Still not single-source

* The superseded studies in `STUDIES` (`unit_v1_assembly.py`, `pod_store_reach.py`, `flatpack_*.py`, `charging_dock.py`, ...) keep their own simplified tank and track copies.
  They made older drawings and are not part of the build.
* `cad/cart_arm.py` still draws its own seedling-tray and lid stand-ins for the reach study.
* The sim's own SO-101 arm (`control-ui/src/model.ts`, the moving arm with its servos) and the scene furniture (pod store, tray, sample station, the water-sample scene's box cart) are still the sim's own shapes.
  The cart, the track loop and the unit numbers are NOT: see the next section.

## The MuJoCo sim takes the cart from the CAD (#447)

`python cad/export_sim_model.py` (run by `build_all.py`) reads the cart (every child of `cart_assembly.result`, the same cart `add_cart()` gives the Complete unit) and the numbers of `hand_sleeve.py`, `cart_dims.py`,
`cart_omni.py`, `cart_sleeves.py`, `cart_base.py`, `cart_geom.py`, `parts/unit_dims.py` and `layout.py`, and writes `control-ui/src/generated/cad-sim.ts` (numbers, part list with CAD bounding boxes, cart placement on the unit)
and `cad-sim-cart.ts` (the cart meshes, thinned by vertex clustering). The sim imports both: `cart/omni.ts` and `cart/track.ts` and `transplant/layout.ts` have no copy of those numbers any more, and every scene draws the
CAD meshes (`cart/cad-cart.ts`); the sim's primitive shapes are only the collision shapes and are invisible.

`python cad/check_sim_matches_cad.py` (in `build_all.py`) fails if the generated files differ from what the CAD gives now, or if the sim code stops importing them. `control-ui/test/sim.test.ts` then checks every scene against the
Complete unit (`scripts/audit-scenes.ts` prints the table): the riding hand's pipe axis on the track leg, the cart upright, the roll about the leg, the side of the free hand.
Pictures: `control-ui/scripts/export-*.ts` + `render_*.py` into `cad/renders/`, then `python cad/publish_sim_scenes.py` and `python cad/render_line_thumbs.py views <ids>` for the Drawings page (group "Sim scenes (CAD cart)").
