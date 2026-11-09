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
