# Working notes for Claude

<!-- viber:start -->
## Sessions started by Viber

When the prompt says it comes from Viber, Dani is away from his computer and
will review through a preview link, so these rules replace any local ones
about waiting for him before committing:

- You are already on the task's `feat/` branch. Commit your work there.
  Don't push, open a pull request or merge: the workflow does that.
- Don't run the app or start servers. Do run the repo's checks (typecheck,
  tests, build) before your last commit, and fix what they find.
- Never deploy, never touch production, and never change a deployed
  database.
- If the brief is unclear or would break a rule in this file, change nothing
  and explain why in the pull request description.
<!-- viber:end -->

## Pond: CAD changes

For agent sessions. A change that touches only `cad/` and `docs/` (nothing under `control-ui/`):

- Run `python cad/build_all.py quick`, then `python cad/build_all.py only <family>` for the part you changed
  (families: cart, track-supports, spine-connector, unit, water-station). That regenerates and publishes only that part's renders.
- Do NOT run the full `python cad/build_all.py` and do NOT run the sim tests.
- If `check_sim_matches_cad.py` fails, run `python cad/export_sim_model.py` and commit the regenerated `control-ui/src/generated` files.
  That is a control-ui change, so the full tests then apply.
- Run the full build_all and the full tests only when the task says "full regression".
