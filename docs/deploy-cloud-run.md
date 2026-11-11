# Deploying the render server to Cloud Run

Everything below uses `gcloud`. These are the values in use (set up 31 Oct 2026):

```bash
export PROJECT=pond-render-kupfer   # project number 500653746288, billing "My Billing Account 1"
export REGION=us-east1              # cheapest Cloud Run tier, between London and São Paulo
export BUCKET=pond-render-kupfer-renders
export SERVICE=pond-render
export SA=pond-render-sa
```

## 1. Project and APIs

```bash
gcloud projects create $PROJECT --name="Pond"
gcloud config set project $PROJECT
gcloud billing accounts list                      # note the ACCOUNT_ID, check free credits here too
gcloud billing projects link $PROJECT --billing-account=ACCOUNT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
    storage.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
```

## 2. Bucket and service account

The service runs as its own service account that can only touch the renders bucket.
`serviceAccountTokenCreator` on itself lets it sign download URLs without a key file.

```bash
gcloud storage buckets create gs://$BUCKET --location=$REGION --uniform-bucket-level-access
gcloud iam service-accounts create $SA --display-name="Pond render server"
export SA_EMAIL=$SA@$PROJECT.iam.gserviceaccount.com
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
    --member=serviceAccount:$SA_EMAIL --role=roles/storage.objectAdmin
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --member=serviceAccount:$SA_EMAIL --role=roles/iam.serviceAccountTokenCreator
```

## 3. Secrets

The password is what you type in the browser when Claude connects. The signing secret
signs OAuth tokens; rotate it to log every client out.

```bash
printf '%s' "$(openssl rand -hex 32)" | gcloud secrets create pond-oauth-signing-secret --data-file=-
printf '%s' "choose-a-long-password-here" | gcloud secrets create pond-oauth-password --data-file=-
for s in pond-oauth-signing-secret pond-oauth-password; do
  gcloud secrets add-iam-policy-binding $s --member=serviceAccount:$SA_EMAIL --role=roles/secretmanager.secretAccessor
done
```

### GitHub token (for the repo_* tools and render auto-save)

Create a fine-grained personal access token as the repo owner at
https://github.com/settings/personal-access-tokens/new: repository access limited to the
`pond` repo, permissions Contents read/write and Pull requests read/write. Then:

```bash
printf '%s' 'github_pat_...' | gcloud secrets create pond-github-token --data-file=-
gcloud secrets add-iam-policy-binding pond-github-token --member=serviceAccount:$SA_EMAIL --role=roles/secretmanager.secretAccessor
gcloud run services update $SERVICE --region $REGION \
    --update-secrets POND_GITHUB_TOKEN=pond-github-token:latest \
    --update-env-vars POND_GITHUB_REPO=kupferco/pond
```

The server only ever writes to the `claude/drafts` branch (created from `main` on first
use) and only under `docs/`, `cad/` and `sim/`. Review and merge its PRs on GitHub.
To revoke: delete the token on GitHub, or remove the two settings and redeploy.

### Bucket CORS (for the /viewer page)

The viewer page at `$URL/viewer` loads GLB files straight from the bucket, so the bucket must
allow that origin:

```bash
cat > /tmp/cors.json <<EOF
[{"origin": ["$URL"], "method": ["GET", "HEAD"], "responseHeader": ["Content-Type", "Range"], "maxAgeSeconds": 3600}]
EOF
gcloud storage buckets update gs://$BUCKET --cors-file=/tmp/cors.json
```

(Needs `$URL`, so run it after the first deploy.)

## 4. First deploy

Run from the repo root. `--source` builds the Dockerfile with Cloud Build (amd64) and pushes
it to Artifact Registry.

```bash
gcloud run deploy $SERVICE --source render-server --region $REGION \
    --service-account $SA_EMAIL \
    --no-allow-unauthenticated \
    --memory 4Gi --cpu 2 --cpu-boost --timeout 300 --concurrency 4 \
    --min-instances 0 --max-instances 2 \
    --set-env-vars POND_AUTH_MODE=oauth,POND_STORAGE=gs://$BUCKET,POND_CAD_TIMEOUT_S=60,POND_CAD_MEMORY_MB=3072 \
    --set-secrets POND_OAUTH_PASSWORD=pond-oauth-password:latest,POND_OAUTH_SIGNING_SECRET=pond-oauth-signing-secret:latest
```

The server starts, but `POND_PUBLIC_URL` is not set yet, so its OAuth metadata advertises
`http://localhost:8080` as the issuer. Set the real URL now that you know it:

```bash
export URL=$(gcloud run services describe $SERVICE --region $REGION --format='value(status.url)')
gcloud run services update $SERVICE --region $REGION --update-env-vars POND_PUBLIC_URL=$URL
curl $URL/health
curl $URL/.well-known/oauth-protected-resource/mcp
```

Later deploys keep the env vars, so `gcloud run deploy $SERVICE --source render-server --region $REGION` is enough.

Live service (31 Oct 2026): `https://pond-render-500653746288.us-east1.run.app`

### Make it reachable by Claude

The server does its own OAuth, so Cloud Run's IAM check must be switched off for it, or Claude
is blocked before it can log in. This grants "invoke" to everyone; the app still refuses anything
without a valid token. Run it yourself (Claude Code's permission rules block it):

```bash
gcloud run services add-iam-policy-binding $SERVICE --region $REGION \
    --member=allUsers --role=roles/run.invoker
curl -s -o /dev/null -w '%{http_code}\n' $URL/health      # 200 once the binding is active
```

Until then, you can still test with your own Google identity by sending it in a second header
(Cloud Run reads `X-Serverless-Authorization`, leaving `Authorization` for the app's token):

```bash
curl -H "X-Serverless-Authorization: Bearer $(gcloud auth print-identity-token)" $URL/health
```

Note: Cloud Run's front end swallows the path `/healthz` (404 for everyone), which is why the
health route is `/health`.

## 5. Connect Claude

Claude → Settings → Connectors → Add custom connector:

- Name: Pond render
- Remote MCP server URL: `$URL/mcp`
- Leave OAuth client id/secret empty (the server supports dynamic client registration).

Click Connect; a browser tab opens the server's login page; enter the password from
`pond-oauth-password`. Then, in a chat (voice works too), ask Claude to render something,
for example "render a 32 mm pipe with a C-clamp sleeve and check the views".

### Simulations

The image sets `MUJOCO_GL=osmesa` for headless rendering. Sims read their models from the
repo through the GitHub token, so adding or editing `sim/*.py` needs no redeploy. A 5 s sim
of the pipe-climb model takes well under a second of CPU; the 300 s request timeout and 4 GiB
are plenty. Raise `POND_SIM_MAX_DURATION_S` if longer runs are wanted, remembering Claude's
own connector timeout.

## 6. Operating

```bash
gcloud run services logs read $SERVICE --region $REGION --limit 100
gcloud storage ls gs://$BUCKET/renders/                    # one folder per render
gcloud secrets versions add pond-oauth-signing-secret --data-file=<(openssl rand -hex 32)  # log everyone out
gcloud run services update $SERVICE --region $REGION --update-secrets POND_OAUTH_SIGNING_SECRET=pond-oauth-signing-secret:latest
```

Cost: with `min-instances 0` the service scales to zero. A cold start is a few seconds
(container start plus CadQuery import). Each render runs in a subprocess inside the Cloud Run
sandbox (gVisor); the service account only has access to the renders bucket, so even an
escaped script can at most read or write renders.

## Local Docker check

```bash
cd render-server
docker build -t pond-render:dev .
docker run --rm -p 8080:8080 -e POND_AUTH_MODE=token -e POND_API_TOKEN=dev-token \
    -e POND_PUBLIC_URL=http://localhost:8080 -e POND_STORAGE=local:/tmp/renders pond-render:dev
curl localhost:8080/health
```
