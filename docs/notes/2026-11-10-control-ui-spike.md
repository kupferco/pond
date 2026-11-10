# Pond – Sim control UI spike (10 Nov 2026)

Working note. First step toward one web page with a live MuJoCo sim and a command panel.

## What was built

- A page at `/sim` inside the Pond hub (source in `control-ui/`, TypeScript + Vite), with the hub header, burger menu entry "Sim control" and the hub's look.
- SO-101 follower arm, six STS3215 joints A to F with limits, rendered with three.js from the official MuJoCo WASM build, in real time.
- Panel: target angle and Go per motor, Go all, Home, live joint readout, Sim/Real toggle.
- One command layer (`CommandLayer`) with `SimDriver` (working) and `RealDriver` (stub, "not connected yet"; Web Serial + Feetech STS later). Cart and pick-pod commands go on the same layer.
- Hosting: a NEW Firebase project hosts the whole hub (`docs/` plus `/sim`), built by `npm run build:site` into `control-ui/site/`. COOP/COEP headers are set in `control-ui/firebase.json`. GitHub Actions deploys a preview channel per pull request and live on merge to main. GitHub Pages is untouched and keeps running; `/sim` only exists on Firebase.
- `docs/sw.js` has one added line so the service worker ignores `/sim/` requests; `docs/assets/site.js` has the one menu link.

## How sim performance felt

Not judged in a browser yet (this run could not open one). Headless in node, 5 s of simulated time took about 21 ms, so the physics is far from the bottleneck. Rendering ~25 primitive meshes is light. Check on the preview URL.

## Single-threaded WASM

The default single-threaded build is almost certainly enough for one arm. COOP/COEP are set anyway so threads stay possible later.

## Fix on the computer

Needs Dani's permissions; nothing was created or changed on Firebase or GCP.

1. Create a NEW Firebase project (not an existing one), e.g. `pond-hub`, and enable Hosting:
   ```
   npm i -g firebase-tools
   firebase login
   firebase projects:create pond-hub-<suffix> --display-name "Pond hub"
   ```
2. Create a service account with the Firebase Hosting Admin role and a key:
   ```
   PROJECT=pond-hub-<suffix>
   gcloud iam service-accounts create github-deploy --project $PROJECT
   gcloud projects add-iam-policy-binding $PROJECT \
     --member serviceAccount:github-deploy@$PROJECT.iam.gserviceaccount.com --role roles/firebasehosting.admin
   gcloud projects add-iam-policy-binding $PROJECT \
     --member serviceAccount:github-deploy@$PROJECT.iam.gserviceaccount.com --role roles/serviceusage.serviceUsageConsumer
   gcloud iam service-accounts keys create key.json \
     --iam-account github-deploy@$PROJECT.iam.gserviceaccount.com --project $PROJECT
   ```
3. Add to GitHub (repo kupferco/pond), then delete `key.json`:
   ```
   gh secret set FIREBASE_SERVICE_ACCOUNT_POND_CONTROL < key.json
   gh variable set FIREBASE_PROJECT_ID --body $PROJECT
   rm key.json
   ```
4. Re-run the "Control UI hosting" workflow on the pull request.

Prompt for Claude Code: "Create a new Firebase project for the Pond hub, enable Hosting, make a service account with Firebase Hosting Admin, and set the GitHub secret FIREBASE_SERVICE_ACCOUNT_POND_CONTROL and variable FIREBASE_PROJECT_ID on kupferco/pond. Don't reuse any existing project. Then re-run the Control UI hosting workflow and open the preview URL's /sim page."
