# Deploying the render server to Cloud Run

Everything below uses `gcloud`. Pick values once and export them; the commands use them.

```bash
export PROJECT=pond-render          # GCP project id (must be globally unique; adjust)
export REGION=europe-west1          # any Cloud Run region close to you
export BUCKET=${PROJECT}-renders    # GCS bucket for outputs
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

## 4. First deploy

Run from the repo root. `--source` builds the Dockerfile with Cloud Build (amd64) and pushes
it to Artifact Registry. `--allow-unauthenticated` is required because the server does its
own OAuth; Cloud Run's IAM check would block Claude before it could log in.

```bash
gcloud run deploy $SERVICE --source render-server --region $REGION \
    --service-account $SA_EMAIL \
    --allow-unauthenticated \
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
curl $URL/healthz
curl $URL/.well-known/oauth-protected-resource/mcp
```

Later deploys keep the env vars, so `gcloud run deploy $SERVICE --source render-server --region $REGION` is enough.

## 5. Connect Claude

Claude → Settings → Connectors → Add custom connector:

- Name: Pond render
- Remote MCP server URL: `$URL/mcp`
- Leave OAuth client id/secret empty (the server supports dynamic client registration).

Click Connect; a browser tab opens the server's login page; enter the password from
`pond-oauth-password`. Then, in a chat (voice works too), ask Claude to render something,
for example "render a 32 mm pipe with a C-clamp sleeve and check the views".

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
curl localhost:8080/healthz
```
