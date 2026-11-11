# Pond – Sim control UI spike (10 Nov 2026)

Working note. First step toward one web page with a live MuJoCo sim and a command panel.

## What was built

- A page at `/sim` inside the Pond hub (source in `control-ui/`, TypeScript + Vite), with the hub header, burger menu entry "Sim control" and the hub's look.
- SO-101 follower arm, six STS3215 joints A to F with limits, rendered with three.js from the official MuJoCo WASM build, in real time.
- Panel: target angle and Go per motor, Go all, Home, live joint readout, Sim/Real toggle.
- One command layer (`CommandLayer`) with `SimDriver` (working) and `RealDriver` (stub, "not connected yet"; Web Serial + Feetech STS later). Cart and pick-pod commands go on the same layer.
- Hosting: a NEW Firebase project hosts the whole hub (`docs/` plus `/sim`), built by `npm run build:site` into `control-ui/site/`. COOP/COEP headers are set in `control-ui/firebase.json` for `/sim/**` only: site-wide `require-corp` blocked the cross-origin render-server images on the hub pages. GitHub Actions deploys a preview channel per pull request and live on merge to main. GitHub Pages is untouched and keeps running; `/sim` only exists on Firebase.
- `docs/sw.js` has one added line so the service worker ignores `/sim/` requests; `docs/assets/site.js` has the one menu link.

## How sim performance felt

Not judged in a browser yet (this run could not open one). Headless in node, 5 s of simulated time took about 21 ms, so the physics is far from the bottleneck. Rendering ~25 primitive meshes is light. Check on the preview URL.

## Single-threaded WASM

The default single-threaded build is almost certainly enough for one arm. COOP/COEP are set anyway so threads stay possible later.

## Fix on the computer

**Update 11 Nov:** steps 1 to 3 are done by Dani (project `pond-grow`, service account `github-deployer@pond-grow.iam.gserviceaccount.com` with Hosting Admin, secret `FIREBASE_SERVICE_ACCOUNT_POND_CONTROL`). Original steps kept below for reference.

Needed Dani's permissions; nothing was created or changed on Firebase or GCP by Claude.

1. Create a NEW Firebase project with ID `pond-grow` (hub at https://pond-grow.web.app, sim at /sim) and enable Hosting. If `pond-grow` is taken, pick the closest free ID (for example `pond-grow-hub`), **say which one you used**, and update it in one place: `control-ui/.firebaserc` (and `projectId` in `.github/workflows/control-ui.yml`).
   ```
   npm i -g firebase-tools
   firebase login
   firebase projects:create pond-grow --display-name "Pond grow"
   ```
2. Create a service account with the Firebase Hosting Admin role and a key:
   ```
   PROJECT=pond-grow
   gcloud iam service-accounts create github-deploy --project $PROJECT
   gcloud projects add-iam-policy-binding $PROJECT \
     --member serviceAccount:github-deploy@$PROJECT.iam.gserviceaccount.com --role roles/firebasehosting.admin
   gcloud projects add-iam-policy-binding $PROJECT \
     --member serviceAccount:github-deploy@$PROJECT.iam.gserviceaccount.com --role roles/serviceusage.serviceUsageConsumer
   gcloud iam service-accounts keys create key.json \
     --iam-account github-deploy@$PROJECT.iam.gserviceaccount.com --project $PROJECT
   ```
3. Add the key to GitHub (repo kupferco/pond), then delete `key.json`:
   ```
   gh secret set FIREBASE_SERVICE_ACCOUNT_POND_CONTROL < key.json
   rm key.json
   ```
4. Re-run the "Control UI hosting" workflow on the pull request. Until the secret exists the deploy steps are skipped with a warning instead of failing.

Prompt for Claude Code: "Create a new Firebase project with ID pond-grow (if taken, the closest free ID such as pond-grow-hub, and tell me which, then update control-ui/.firebaserc and the workflow projectId), enable Hosting, make a service account with Firebase Hosting Admin, and set the GitHub secret FIREBASE_SERVICE_ACCOUNT_POND_CONTROL on kupferco/pond. Don't reuse any existing project. Then re-run the Control UI hosting workflow and open the preview URL's /sim page."

## Fix on the computer: report deploys to Viber (task #54)

`.github/workflows/control-ui.yml` does not yet tell Viber about previews or live deploys. The session could not read `kupferco/housekeeper`'s `.github/workflows/deploy.yml` (steps "Tell Viber the preview is ready" and "Tell Viber how the deploy went") or list this repo's secrets, so the hook URL and payload were not guessed. To finish: copy those two steps into the Preview and Live jobs, and make sure the same names exist on this repo:

```
gh secret set VIBER_HOOK_SECRET -R kupferco/pond
gh variable set VIBER_URL -R kupferco/pond --body "<same value as on kupferco/housekeeper>"
```

(Check with `gh variable list -R kupferco/housekeeper` and `gh secret list -R kupferco/housekeeper` whether Housekeeper uses a variable or a secret for `VIBER_URL`, and match it.)
